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


"""Call the openbach-function push_file"""


__author__ = 'Viveris Technologies'
__credits__ = '''Contributors:
 * Adrien THIBAUD <adrien.thibaud@toulouse.viveris.com>
 * Mathias ETTINGER <mathias.ettinger@toulouse.viveris.com>
'''


from argparse import FileType

from frontend import FrontendBase


class PushFile(FrontendBase):
    def __init__(self):
        super().__init__('OpenBACH — Push File')
        self.parser.add_argument('agent', help='IP address of the agent')
        self.parser.add_argument(
                'remote_path',
                help='path where the file should be pushed')
        group = self.parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--path', help='path of the file on the controller')
        group.add_argument(
                '--local-file', type=FileType('r'),
                help='path of a file on the current '
                'computer to be sent to the agent')

    def execute(self):
        agent = self.args.agent
        remote_path = self.args.remote_path
        local_path = self.args.path

        form_data = {
                'path': remote_path,
                'agent_ip': agent,
        }

        if local_path is not None:
            form_data['local_path'] = local_path
            self.session.post(self.base_url + 'file', data=form_data)
        else:
            local_file = self.args.local_file
            with local_file:
                self.session.post(
                        self.base_url + 'file',
                        data=form_data,
                        files={'file': local_file})


if __name__ == '__main__':
    PushFile.autorun()
