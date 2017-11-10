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


"""Call the openbach-function list_scenario_instance"""


__author__ = 'Viveris Technologies'
__credits__ = '''Contributors:
 * Adrien THIBAUD <adrien.thibaud@toulouse.viveris.com>
 * Mathias ETTINGER <mathias.ettinger@toulouse.viveris.com>
'''


from frontend import FrontendBase


class ListScenarioInstances(FrontendBase):
    def __init__(self):
        super().__init__('OpenBACH — List Instances of a Scenario')
        self.parser.add_argument(
                '-s', '--scenario',
                help='name of the scenario whose instances should be listed')
        self.parser.add_argument(
                '-p', '--project',
                help='name of the project the scenario is associated with')

    def execute(self):
        scenario = self.args.scenario
        project = self.args.project

        if project is None:
            self.request('GET', 'scenario_instance')
        else:
            if scenario is None:
                self.request('GET', 'project/{}/scenario_instance/'.format(project))
            else:
                route = 'project/{}/scenario/{}/scenario_instance/'.format(project, scenario)
                self.requset('GET', route)


if __name__ == '__main__':
    ListScenarioInstances.autorun()
