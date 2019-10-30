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


from scenario_builder import Scenario
from scenario_builder.openbach_functions import StartJobInstance
from scenario_builder.helpers.service.apache2 import apache2
from scenario_builder.scenarios import service_data_transfer, service_video_dash, service_web_browsing, service_voip
from scenario_builder.helpers.postprocessing.time_series import time_series_on_same_graph
from scenario_builder.helpers.postprocessing.histogram import cdf_on_same_graph


SCENARIO_DESCRIPTION="""This scenario launches the traffics as defined in the configuration file, then post processes generated data
"""
SCENARIO_NAME="""service_traffic_mix"""

def load_args(args_list):
    args_main = []
    id_explored = []
    for args_str in args_list:
        try:
            if len(args_str) < 10:
                continue
            if args_str[0] == '#':
                continue
            args = args_str.split()
            for traffic, nb in [("voip",12), ("web",11), ("dash",11), ("iperf3",13)]:
                if args[1] == traffic and len(args) != nb:
                    print("\033[91mWARNING:", "Wrong argument format,", nb, "elements needed for", traffic, "traffic:", "\"" + " ".join(args) + "\"", "but got", len(args), "... ignoring", "\033[0m")
                    break
            else:
                ids = list(map(int,args[5].split("-")) if args[5] != "None" else []) + list(map(int,args[6].split("-")) if args[6] != "None" else [])
                cur_id = int(args[0])
                if cur_id in id_explored:
                    print("\033[91mWARNING:", "Duplicated id:", " ".join(args), "... ignoring")
                    continue
                int(args[4])
                int(args[7])
                for dependency in ids:
                    if cur_id <= dependency:
                        print("\033[91mWARNING:", "This traffic depends on future ones:", " ".join(args), "... ignoring", "\033[0m")
                        break
                    if dependency not in id_explored:
                        print("\033[91mWARNING:", "This traffic depends on missing ones:", " ".join(args), "... ignoring", "\033[0m")
                        break
                else:
                    args_main.append(args)
                    id_explored.append(cur_id)
        except ValueError:
            print("\033[91mWARNING:", "Cannot parse this line:", args_str, "\033[0m")

    return args_main


def extract_jobs_to_postprocess(scenarios, traffic):
    for scenario, start_scenario in scenarios:
        for function_id, function in enumerate(scenario.openbach_functions):
            if isinstance(function, StartJobInstance):
                if traffic == "iperf3" and function.job_name == 'iperf3':
                    if 'server' in function.start_job_instance['iperf3']:
                        port = function.start_job_instance['iperf3']['port']
                        address = function.start_job_instance['iperf3']['server']['bind']
                        dst = function.start_job_instance['entity_name']
                        yield (start_scenario, function_id, dst + " " + address + " " + str(port))
                if traffic == "dash" and function.job_name == 'dash player&server':
                    yield (None, function_id, "")
                if traffic == "web" and function.job_name == 'web_browsing_qoe':
                    dst = function.start_job_instance['entity_name']
                    yield (start_scenario, function_id, dst)
                if traffic == "voip" and function.job_name == 'voip_qoe_src':
                    port = function.start_job_instance['voip_qoe_src']['starting_port']
                    address = function.start_job_instance['voip_qoe_src']['dest_addr']
                    dst = function.start_job_instance['entity_name']
                    yield (start_scenario, function_id, dst + " " + address + " " + str(port))


def build(post_processing_entity, extra_args_traffic, scenario_name=SCENARIO_NAME):
    # Create top network_traffix_mix scenario
    scenario_mix = Scenario(scenario_name, SCENARIO_DESCRIPTION)
    list_wait_finished = []
    list_scenarios = []
    apache_servers = {}
    map_scenarios = {}
    
    extra_args = []
    try:
        file = open(extra_args_traffic,"r")
        for line in file:
            extra_args.append(line.rstrip())
        file.close()
    except (OSError, IOError):
        print("\033[91mERROR:", "Cannot open args file, exiting", "\033[0m")
        return

    args_list = load_args(extra_args)

    print("Loading traffics")

    # Launching Apache2 servers first (via apache2 or dash player&server job)
    start_servers = []
    for args in args_list:
        if args[1] == "dash" and args[2] not in apache_servers:
            start_server = scenario_mix.add_function('start_job_instance')
            start_server.configure('dash player&server', args[2], offset=0)
            apache_servers[args[2]] = start_server
            start_servers.append(start_server)
            list_scenarios.append((scenario_mix, None))
    for args in args_list:
        if args[1] == "web" and args[2] not in apache_servers:
            start_server = apache2(scenario_mix, args[2])[0]
            apache_servers[args[2]] = start_server
            start_servers.append(start_server)

    # Creating and launching traffic scenarios
    for args in args_list:
        traffic = args[1]
        scenario_id = args[0]

        wait_launched_list = []
        wait_finished_list = []
        if args[5] != "None" or args[6] != "None":
            if args[5] != "None":
                wait_launched_list = [map_scenarios[i] for i in args[5].split('-')]
            if args[6] != "None":
                wait_finished_list = [map_scenarios[i] for i in args[6].split('-')]

        if not wait_launched_list and not wait_finished_list:
            wait_launched_list = start_servers if start_servers else []
            offset_delay = 5 if start_servers else 0
        else:
            offset_delay = 0

        start_scenario = scenario_mix.add_function('start_scenario_instance',
                    wait_finished=wait_finished_list, wait_launched=wait_launched_list, wait_delay=int(args[7]) + offset_delay)
        if traffic == "iperf3":
            scenario = service_data_transfer.build(post_processing_entity, args)
        if traffic == "dash":
            scenario = service_video_dash.build(post_processing_entity, args)
        if traffic == "web":
            scenario = service_web_browsing.build(post_processing_entity, args)
        if traffic == "voip":
            scenario = service_voip.build(post_processing_entity, args)

        start_scenario.configure(scenario)
        list_wait_finished += [start_scenario]
        map_scenarios[scenario_id] = start_scenario
        list_scenarios.append((scenario, start_scenario))
        
    # Stopping all Apache2 servers
    for server_entity,scenario_server in apache_servers.items():
        stopper = scenario_mix.add_function('stop_job_instance',
                wait_finished=list_wait_finished, wait_delay=5)
        stopper.configure(scenario_server)

    # Post processing data
    if post_processing_entity is not None:
        print("Loading:", "post processing")
        for traffic, name, y_axis in [("iperf3", "throughput", "Rate (b/s)"),
                                        ("dash", "bitrate", "Rate (b/s)"),
                                        ("web", "page_load_time", "PLT (ms)"),
                                        ("voip", "instant_mos", "MOS")]:
            post_processed = []
            legends = []
            for scenario_id, function_id, legend in extract_jobs_to_postprocess(list_scenarios, traffic):
                post_processed.append([scenario_id, function_id] if scenario_id is not None else [function_id])
                legends.append([] if traffic == "dash" else [traffic + " - " + legend])
            if post_processed:
                time_series_on_same_graph(scenario_mix, post_processing_entity, post_processed, [[name]], [[y_axis]], [['Rate time series']], legends, list_wait_finished, None, 2)
                cdf_on_same_graph(scenario_mix, post_processing_entity, post_processed, 100, [[name]], [[y_axis]], [['Rate CDF']], legends, list_wait_finished, None, 2)

    return scenario_mix