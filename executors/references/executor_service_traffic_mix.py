#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# OpenBACH is a generic testbed able to control/configure multiple
# network/physical entities (under test) and collect data from them.
# It is composed of an Auditorium (HMIs), a Controller, a Collector
# and multiple Agents (one for each network entity that wants to be
# tested).
#
#
# Copyright © 2016-2020 CNES
#
#
# This file is part of the OpenBACH testbed.
#
#
# OpenBACH is a free software : you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY, without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see http://www.gnu.org/licenses/.

"""This executor builds or launches the *service_traffic_mix* scenario
from /openbach-extra/apis/scenario_builder/scenarios/
It is a complex executor configured by "executor_service_traffic_mix_arg.txt" file
which can mix several services scenarios such as video_dash, voip, web_browsing
and service_data_transfer in a flexible manner.
"""

import argparse
import sys
import shlex

from auditorium_scripts.scenario_observer import ScenarioObserver
from scenario_builder.scenarios import service_traffic_mix


def _parse_waited_ids(ids):
    if ids == "None":
        return []
    return list(map(int, ids.split('-')))


def _prepare_argparse_arguments(validator):
    fields = validator.TRAFFIC_TYPE._fields
    return {
            'nargs': len(validator.VALIDATOR),
            'metavar': fields[:1] + fields[2:],
            'action': validator,
            'dest': 'traffic',
    }


class _Validate(argparse.Action):
    VALIDATOR = (int, None, None, int, _parse_waited_ids, _parse_waited_ids, int, None, None)
    TRAFFIC_TYPE = None
    TRAFFIC_NAME = None

    def __call__(self, parser, args, values, option_string=None):
        items = getattr(args, self.dest)
        if items is None:
            items = []
            setattr(args, self.dest, items)

        try:
            validated = [
                    argument if validate is None else validate(argument)
                    for validate, argument in zip(self.VALIDATOR, values)
            ]
        except ValueError as e:
            raise argparse.ArgumentError(self, e)

        validated.insert(1, self.TRAFFIC_NAME)
        try:
            argument = self.TRAFFIC_TYPE(*validated)
        except (ValueError, TypeError) as e:
            raise argparse.ArgumentError(self, e)

        existing_ids = {arg.id for arg in items}
        if argument.id in existing_ids:
            raise argparse.ArgumentError(self, 'duplicate traffic ID: {}'.format(argument.id))

        for dependency in argument.wait_launched + argument.wait_finished:
            if dependency not in existing_ids:
                raise argparse.ArgumentError(self, 'dependency {} not found for traffic ID {}'.format(dependency, argument.id))

        items.append(argument)


class ValidateVoip(_Validate):
    VALIDATOR = _Validate.VALIDATOR + (int, None)
    TRAFFIC_NAME = 'voip'
    TRAFFIC_TYPE = service_traffic_mix.VoipArguments


class ValidateWebBrowsing(_Validate):
    VALIDATOR = _Validate.VALIDATOR + (int, int)
    TRAFFIC_NAME = 'web_browsing'
    TRAFFIC_TYPE = service_traffic_mix.WebBrowsingArguments


class ValidateDash(_Validate):
    VALIDATOR = _Validate.VALIDATOR + (None, int)
    TRAFFIC_NAME = 'dash'
    TRAFFIC_TYPE = service_traffic_mix.DashArguments


class ValidateDataTransfer(_Validate):
    VALIDATOR = _Validate.VALIDATOR + (int, None, int, int)
    TRAFFIC_NAME = 'data_transfer'
    TRAFFIC_TYPE = service_traffic_mix.DataTransferArguments


def main(argv=None):
    observer = ScenarioObserver()
    observer.add_scenario_argument(
            '--voip', **_prepare_argparse_arguments(ValidateVoip),
            help='add a VoIP traffic generator sub-scenario')
    observer.add_scenario_argument(
            '--dash', **_prepare_argparse_arguments(ValidateDash),
            help='add a Dash traffic generator sub-scenario')
    observer.add_scenario_argument(
            '--web-browsing', **_prepare_argparse_arguments(ValidateWebBrowsing),
            help='add a web browsing traffic generator sub-scenario')
    observer.add_scenario_argument(
            '--data-transfer', **_prepare_argparse_arguments(ValidateDataTransfer),
            help='add a data transfer traffic generator sub-scenario')
    observer.add_scenario_argument(
            '--maximal-synchronization-offset', default=0.0,
            help='Maximal offset difference where we have to do a resynchronization between agents (float). If 0, no resynchronization')
    observer.add_scenario_argument(
            '--synchronization-timeout', default=30,
            help='Maximal synchronization duration in seconds (float)')
    observer.add_scenario_argument(
            '--post-processing-entity', help='The entity where the post-processing will be performed '
            '(histogram/time-series jobs must be installed) if defined')

    argv = [x for l in sys.argv[1:] for x in shlex.split(l, comments=True)]
    args = observer.parse(argv, service_traffic_mix.SCENARIO_NAME)

    scenario = service_traffic_mix.build(
            args.traffic or [],
            args.maximal_synchronization_offset,
            args.synchronization_timeout,
            args.post_processing_entity,
            scenario_name=args.scenario_name)

    observer.launch_and_wait(scenario)


if __name__ == '__main__':
    main()
