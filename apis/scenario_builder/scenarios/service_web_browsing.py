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
from scenario_builder.helpers.service.web_browsing_qoe import web_browsing_qoe
from scenario_builder.helpers.postprocessing.time_series import time_series_on_same_graph
from scenario_builder.helpers.postprocessing.histogram import cdf_on_same_graph


SCENARIO_DESCRIPTION = """This scenario launches one web transfer.

It can then, optionally, plot the page load time using time-series and CDF.
"""
SCENARIO_NAME = 'service_web_browsing'


def web_browsing(
        source, destination, duration, nb_runs, parallel_runs,
        compression=True, proxy_address=None, proxy_port=None,
        launch_server=False, scenario_name=SCENARIO_NAME):
    scenario = Scenario(scenario_name, SCENARIO_DESCRIPTION)

    if launch_server:
        server = apache2(scenario, source)
        traffic = web_browsing_qoe(scenario, destination, nb_runs, parallel_runs, duration, not compression, proxy_address, proxy_port, wait_launched=start_server, wait_delay=5)
        stopper = scenario.add_function('stop_job_instance', wait_finished=traffic, wait_delay=5)
        stopper.configure(server[0])
    else:
        web_browsing_qoe(scenario, destination, nb_runs, parallel_runs, duration, not compression, proxy_address, proxy_port)

    return scenario


def build(
        source, destination, duration, nb_runs, parallel_runs,
        compression=True, proxy_address=None, proxy_port=None, launch_server=False,
        post_processing_entity=None, scenario_name=SCENARIO_NAME):
    scenario = web_browsing(source, destination, duration, nb_runs, parallel_runs, compression, proxy_address, proxy_port, launch_server, scenario_name)

    if post_processing_entity is not None:
        post_processed = list(scenario.extract_function_id('web_browsing_qoe'))
        legends = ['web browsing from {} to {}'.format(source, destination)]
        jobs = scenario.openbach_functions.copy()

        time_series_on_same_graph(
                scenario,
                post_processing_entity,
                post_processed,
                [['page_load_time']],
                [['PLT (ms)']],
                [['PLT time series']],
                [legends],
                jobs, None, 2)
        cdf_on_same_graph(
                scenario,
                post_processing_entity,
                post_processed,
                100,
                [['page_load_time']],
                [['PLT (ms)']],
                [['PLT CDF']],
                [legends],
                jobs, None, 2)

    return scenario
