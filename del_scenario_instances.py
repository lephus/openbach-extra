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


"""Call the openbach-function del_scenario_instances"""


__author__ = 'Viveris Technologies'
__credits__ = '''Contributors:
 * Mathias ETTINGER <mathias.ettinger@toulouse.viveris.com>
'''


import pprint

from frontend import FrontendBase


class DeleteScenarioInstances(FrontendBase):
    def __init__(self):
        super().__init__('OpenBACH — Delete a Scenario Instance')
        self.parser.add_argument(
                'id', nargs='+', type=int,
                help='scenario instance ID to delete')

    def execute(self, show_response_content=True):
        responses = [
                self.request(
                    'DELETE',
                    'scenario_instance/{}'.format(scenario_instance_id),
                    show_response_content=False)
                for scenario_instance_id in self.args.id
        ]

        if show_response_content:
            for response in responses:
                pprint.pprint(response.json(), width=120)

        return responses


if __name__ == '__main__':
    DeleteScenarioInstances.autorun()
