#!/usr/bin/env python3

# OpenBACH is a generic testbed able to control/configure multiple
# network/physical entities (under test) and collect data from them. It is
# composed of an Auditorium (HMIs), a Controller, a Collector and multiple
# Agents (one for each network entity that wants to be tested).
#
#
# Copyright © 2016 CNES
#
#
# This file is part of the OpenBACH testbed.
#
#
# OpenBACH is a free software : you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY, without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see http://www.gnu.org/licenses/.


"""Call the openbach-function add_collector"""


__author__ = 'Viveris Technologies'
__credits__ = '''Contributors:
 * Adrien THIBAUD <adrien.thibaud@toulouse.viveris.com>
 * Mathias ETTINGER <mathias.ettinger@toulouse.viveris.com>
'''


import argparse
from frontend import add_collector, state_collector, pretty_wait


if __name__ == "__main__":
    # Define Usage
    parser = argparse.ArgumentParser(
            description='OpenBach - Add Collector',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('collector_ip', help='IP Address of the Collector')
    parser.add_argument('username', help='Username of the Collector')
    parser.add_argument('password', help='Password of the Collector')
    parser.add_argument('name', help='Name of the Collector')
    parser.add_argument(
            '-l', '--logs-port', type=int,
            help='Port for the logs')
    parser.add_argument(
            '-s', '--stats-port', type=int,
            help='Port for the Stats')

    # get args
    args = parser.parse_args()
    collector = args.collector_ip
    username = args.username
    password = args.password
    name = args.name
    logs_port = args.logs_port
    stats_port = args.stats_port

    add_collector(collector, username, password, name, logs_port, stats_port)
    pretty_wait(state_collector, status='add',  address=collector_ip)
