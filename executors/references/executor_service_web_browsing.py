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

"""This executor builds or launches *web_browsing* scenario
from /openbach-extra/apis/scenario_builder/scenarios/
 It launches one web_browsing flow with the specified parameters
 """

from auditorium_scripts.scenario_observer import ScenarioObserver
from scenario_builder.scenarios import service_web_browsing

def main(argv=None):
    observer = ScenarioObserver()
    observer.add_scenario_argument(
            '--server-entity', required=True,
            help='name of the server entity which sends the web_browsing traffic')
    observer.add_scenario_argument(
            '--client-entity', required=True,
            help='name of the client entity which receives the web_browsing traffic')
    observer.add_scenario_argument(
            '--duration', required=True,
            help='duration of Web browsing transmission')
    observer.add_scenario_argument(
            '--nb-runs', required=True,
            help='the number of fetches to perform for each website')
    observer.add_scenario_argument(
            '--nb-parallel-runs', required=True,
            help='the maximum number of fetches that can work simultaneously')
    observer.add_scenario_argument(
            '--no-compression', action = 'store_true', required = False,
            help = 'Prevent compression for transmission')
    observer.add_scenario_argument(
            '--proxy-address', type = str, required = False,
            help = 'Set the proxy address (also needs a proxy port)')
    observer.add_scenario_argument(
            '--proxy-port', type = int, required = False,
            help = 'Set the proxy port (also needs a proxy address)')
    observer.add_scenario_argument(
            '--launch-server', default=True,
            help='Launch server or not. Optional. Default : True')
    observer.add_scenario_argument(
            '--post-processing-entity', help='The entity where the post-processing will be performed '
            '(histogram/time-series jobs must be installed) if defined')

    args = observer.parse(argv, service_web_browsing.SCENARIO_NAME)

    scenario = service_web_browsing.build(
            args.server_entity,
            args.client_entity,
            args.duration,
            args.nb_runs,
            args.nb_parallel_runs,
            not args.no_compression,
            args.proxy_address,
            args.proxy_port,
            args.launch_server,
            args.post_processing_entity,
            scenario_name=args.scenario_name)

    observer.launch_and_wait(scenario)

if __name__ == '__main__':
    main()
