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
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY, without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see http://www.gnu.org/licenses/.


"""Call the openbach-function list_job_instances"""


__author__ = 'Viveris Technologies'
__credits__ = '''Contributors:
 * Adrien THIBAUD <adrien.thibaud@toulouse.viveris.com>
 * Mathias ETTINGER <mathias.ettinger@toulouse.viveris.com>
'''


from urllib.parse import urlencode

from frontend import FrontendBase, pretty_print


class ListJobInstances(FrontendBase):
    def __init__(self):
        super().__init__('OpenBACH — List Instances')
        self.parser.add_argument(
                'agent', nargs='+',
                help='IP addresses of the agents')
        self.parser.add_argument(
                '-u', '--update', action='store_true',
                help='contact the agent to get the last '
                'status of the jobs instances')

    def execute(self, show_response_content=True):
        agents = self.args.agent
        update = self.args.update

        query_string = [('address', ip) for ip in agents]
        if update:
            query_string.append(('update', ''))

        response = self.session.get(
                self.base_url + 'job_instance',
                params=urlencode(query_string))
        if show_response_content:
            pretty_print(response)
        return response


if __name__ == '__main__':
    ListJobInstances.autorun()
