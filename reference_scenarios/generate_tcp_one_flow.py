#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# OpenBACH is a generic testbed able to control/configure multiple
# network/physical entities (under test) and collect data from them.
# It is composed of an Auditorium (HMIs), a Controller, a Collector
# and multiple Agents (one for each network entity that wants to be
# tested).
#
#
# Copyright © 2016-2019 CNES
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

"""This scenario launches the *transport_tcp_one_flow* scenario
from /openbach-extra/apis/scenario_builder/scenarios/
"""


from auditorium_scripts.scenario_observer import ScenarioObserver
from scenario_builder.scenarios import transport_tcp_one_flow


def main(scenario_name='generate_tcp_one_flow', argv=None):
    observer = ScenarioObserver()
    observer.add_scenario_argument(
            '--client', '--client-entity', required=True,
            help='name of the entity for the client iperf3')
    observer.add_scenario_argument(
            '--server', '--server-entity', required=True,
            help='name of the entity for the server iperf3')
    observer.add_scenario_argument(
            '--ip_dst', required=True, help='The server IP address')
    observer.add_scenario_argument(
            '--port', default=7000,  help='The iperf3 server port for data')
    observer.add_scenario_argument(
            '--transmitted_size', required=True, help='The iperf3 '
            'transmitted_size (in bytes - you can use [K/M/G]: '
            'set 100M to send 100 MBytes)')
    observer.add_scenario_argument(
            '--tos', default=0, help='Type of Service of the trafic (default : 0)')
    observer.add_scenario_argument(
            '--mtu', default=1000-40, help='MTU size (default : 1000-40)')
    observer.add_scenario_argument(
            '--entity_pp', help='The entity where the post-processing will be '
            'performed (histogram/time-series jobs must be installed) if defined')

    args = observer.parse(argv, scenario_name)

    scenario = transport_tcp_one_flow.build(
            args.client,
            args.server,
            args.ip_dst,
            args.port,
            args.transmitted_size,
            args.tos,
            args.mtu,
            args.entity_pp)
    observer.launch_and_wait(scenario)


if __name__ == '__main__':
    main()
