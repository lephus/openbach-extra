#!/usr/bin/env python3
# -*- coding: utf-8 -*-


#   OpenBACH is a generic testbed able to control/configure multiple
#   network/physical entities (under test) and collect data from them. It is
#   composed of an Auditorium (HMIs), a Controller, a Collector and multiple
#   Agents (one for each network entity that wants to be tested).
#
#
#   Copyright © 2016−2019 CNES
#
#
#   This file is part of the OpenBACH testbed.
#
#
#   OpenBACH is a free software : you can redistribute it and/or modify it under
#   the terms of the GNU General Public License as published by the Free Software
#   Foundation, either version 3 of the License, or (at your option) any later
#   version.
#
#   This program is distributed in the hope that it will be useful, but WITHOUT
#   ANY WARRANTY, without even the implied warranty of MERCHANTABILITY or FITNESS
#   FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
#   details.
#
#   You should have received a copy of the GNU General Public License along with
#   this program. If not, see http://www.gnu.org/licenses/.

""" Helpers of tcp_conf_linux job """

def tcp_conf_linux(
        scenario, entity, congestion_control, hystart, tcp_slow_start_after_idle,
        tcp_no_metrics_save, tcp_sack, tcp_recovery, tcp_fastopen,
        wait_finished=None, wait_launched=None, wait_delay=0):

    function1 = scenario.add_function(
           'start_job_instance',
            wait_finished=wait_finished,
            wait_launched=wait_launched,
            wait_delay=wait_delay)
    function1.configure(
            'tcp_conf_linux', entity,
            CUBIC={
                'hystart': hystart},
            tcp_slow_start_after_idle=tcp_slow_start_after_idle,
            tcp_no_metrics_save=tcp_no_metrics_save,
            tcp_sack=tcp_sack,
            tcp_recovery=tcp_recovery,
            tcp_fastopen=tcp_fastopen)

    function2 = scenario.add_function(
            'start_job_instance',
            wait_finished=[function1],
            wait_launched=wait_launched,
            wait_delay=5)
    function2.configure(
            'tcp_conf_linux', entity,
            other={
                'congestion_control_name':congestion_control})
    return function2

