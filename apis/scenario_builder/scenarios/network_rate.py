#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
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

from scenario_builder import Scenario
from scenario_builder.helpers.transport.iperf3 import iperf3_rate_tcp, iperf3_find_server
from scenario_builder.helpers.transport.nuttcp import nuttcp_rate_tcp, nuttcp_rate_udp, nuttcp_find_client
from scenario_builder.helpers.metrology.d_itg import ditg_rate, ditg_pcket_rate
from scenario_builder.helpers.postprocessing.time_series import time_series_on_same_graph
from scenario_builder.helpers.postprocessing.histogram import cdf_on_same_graph, pdf_on_same_graph
from scenario_builder.openbach_functions import StartJobInstance, StartScenarioInstance



SCENARIO_DESCRIPTION = """This network_rate scenario allows to:
 - Compare the TCP rate measurement of iperf3, d-itg
   and nuttcp jobs and the UDP rate of nuttcp and d-itg
 - Perform two postprocessing tasks to compare the
   time-series and the CDF of the rate measurements.
"""
SCENARIO_NAME = 'network_rate'


def network_rate(
        client, server, ip_sender, ip_destination,
        server_port, command_port, duration,
        num_flows, tos, mtu, rate, scenario_name=SCENARIO_NAME):
    scenario = Scenario(scenario_name, SCENARIO_DESCRIPTION)
    scenario.add_constant('ip_dst', ip_destination)
    scenario.add_constant('ip_snd', ip_sender)
    scenario.add_constant('port', server_port)
    scenario.add_constant('command_port', command_port)
    scenario.add_constant('duration', duration)
    scenario.add_constant('num_flows', num_flows)
    scenario.add_constant('tos', tos)
    scenario.add_constant('mtu', mtu)
    scenario.add_constant('rate', rate)

    wait = iperf3_rate_tcp(
            scenario, client, server, '$ip_dst', '$port', '$duration', '$num_flows', '$tos', '$mtu')
    wait = nuttcp_rate_tcp(
            scenario, client, server, '$ip_dst', '$port', '$command_port',
            '$duration', '$num_flows', '$tos', '$mtu', wait, None, 2)
    wait = ditg_pcket_rate(
            scenario, client, server, '$ip_dst', '$ip_snd', 'TCP', '/tmp/',
            1000, '$mtu', 100000, '$duration', 'owdm', 50, '$port', '$command_port', wait, None, 2)
    wait = nuttcp_rate_udp(
            scenario, client, server, '$ip_dst', '$port', '$command_port', '$duration', '$rate', wait, None, 2)
    ditg_rate(
            scenario, client, server, '$ip_dst', '$ip_snd', 'UDP', '/tmp/',
            1000, '$mtu', '$rate', '$duration', 'owdm', 50, '$port', '$command_port', wait, None, 2)

    return scenario


def build(
        client, server, ip_destination, ip_sender,
        server_port, command_port, duration,
        rate, num_flows, tos, mtu,
        post_processing_entity=None, scenario_name=SCENARIO_NAME):
    scenario = network_rate(
            client, server, ip_sender, ip_destination, server_port,
            command_port, duration, num_flows, tos, mtu, rate, scenario_name)

    if post_processing_entity is not None:
        post_processed = list(scenario.extract_function_id('d-itg_send', iperf3=iperf3_find_server, nuttcp=nuttcp_find_client))
        jobs = scenario.openbach_functions.copy()
        no_suffix = num_flows != '1'
        legends = [
                ['{} TCP flow with iperf3'.format(num_flows)],
                ['{} TCP flows with nuttcp'.format(num_flows)],
                ['1 TCP flows with d-itg'],
                ['1 UDP flow with nuttcp'],
                ['1 UDP flow with d-itg'],
        ]

        time_series_on_same_graph(
                scenario,
                post_processing_entity,
                post_processed,
                [['bitrate_receiver', 'rate', 'throughput']],
                [['Rate (b/s)']], [['Rate time series']],
                legends,
                jobs, None, 2, no_suffix)
        cdf_on_same_graph(
                scenario,
                post_processing_entity,
                post_processed,
                100,
                [['rate', 'throughput', 'bitrate_receiver']],
                [['Rate (b/s)']], [['Rate CDF']],
                legends,
                jobs, None, 2, no_suffix)

    return scenario
