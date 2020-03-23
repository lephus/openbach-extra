#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# OpenBACH is a generic testbed able to control/configure multiple
# network/physical entities (under test) and collect data from them.
# It is composed of an Auditorium (HMIs), a Controller, a Collector
# and multiple Agents (one for each network entity that wants to be
# tested).
#
#
# Copyright © 2016-2020 CNES
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

"""This scenario builds and launches the OpenSAND scenario
from /openbach-extra/apis/scenario_builder/scenarios/
"""

import argparse 
import tempfile
import warnings
import ipaddress
from pathlib import Path
from collections import defaultdict

from auditorium_scripts.push_file import PushFile
from auditorium_scripts.scenario_observer import ScenarioObserver
from scenario_builder.scenarios.access_opensand import SAT, GW, SPLIT_GW, ST, build as build_opensand


class Entity:
    def __init__(self, entity, emulation_ip, opensand_id):
        self.entity = entity
        self.opensand_id = int(opensand_id)
        self.emulation_ip = validate_ip(emulation_ip)


class GatewayPhy:
    def __init__(self, entity, net_access_entity, interco_phy, interco_net_access):
        self.entity = entity
        self.net_access_entity = net_access_entity
        self.interconnect_net_access = validate_ip(interco_net_access)
        self.interconnect_phy = validate_ip(interco_phy)


class Satellite:
    def __init__(self, entity, ip):
        self.entity = entity
        self.ip = validate_ip(ip)


class ValidateSatellite(argparse.Action):
    def __call__(self, parser, args, values, option_string=None): 
        satellite = Satellite(*values)
        setattr(args, self.dest, satellite)


class _Validate(argparse.Action):
    ENTITY_TYPE = None

    def __call__(self, parser, args, values, option_string=None): 
        if getattr(args, self.dest) == None:
            self.items = []

        try:
            entity = self.ENTITY_TYPE(*values)
        except TypeError as e:
            raise argparse.ArgumentError(self, str(e).split('__init__() ', 1)[-1])
        except ValueError as e:
            raise argparse.ArgumentError(self, e)
        self.items.append(entity)
        setattr(args, self.dest, self.items)


class ValidateGateway(_Validate):
    ENTITY_TYPE = Entity


class ValidateGatewayPhy(_Validate):
    ENTITY_TYPE = GatewayPhy


class ValidateSatelliteTerminal(_Validate):
    ENTITY_TYPE = Entity


def validate_ip(ip):
    return ipaddress.ip_address(ip).compressed


def create_gateways(gateways, gateways_phy):
    for gateway in gateways:
        for gateway_phy in gateways_phy:
            if gateway.entity == gateway_phy.net_access_entity:
                yield SPLIT_GW(
                        gateway.entity, gateway_phy.entity,
                        gateway.opensand_id, gateway.emulation_ip,
                        gateway_phy.interconnect_net_access,
                        gateway_phy.interconnect_phy)
                break
        else:
            yield GW(gateway.entity, gateway.opensand_id, gateway.emulation_ip)


def create_network(satellite_ip, satellite_subnet_mask, gateways, gateways_phy, terminals, workstations):
    satellite_subnet = '{}/{}'.format(extract_ip(satellite_ip), satellite_subnet_mask)
    host_route_ip = extract_network(satellite_subnet)

    opensand_ids = set()
    work_stations = []
    opensand_gateways = []

    for gateway in gateways:
        route_ips = [extract_network(gateway.lan_ip)]
        route_gateway_ip = extract_ip(gateway.opensand_bridge_ip)
        opensand_terminals = []
        terminal_ips = []
        gateway_phy_entity = None
        gateway_phy_interfaces = []
        gateway_phy_ips = []

        if gateway.opensand_id in opensand_ids:
            warnings.warn('Gateway {} uses an ID already used by another entity'.format(gateway.entity))
        opensand_ids.add(gateway.opensand_id)

        found = False
        for workstation in workstations:
            if workstation.opensand_entity == gateway.entity:
                if found:
                    warnings.warn('More than one server workstation configured for gateway {}'.format(gateway.entity))
                work_stations.append(WS(
                    workstation.entity,
                    workstation.interface,
                    workstation.ip,
                    host_route_ip,
                    extract_ip(gateway.lan_ip)))
                found = True

        if not found:
            warnings.warn('No server workstation configured for gateway {}'.format(gateway.entity))

        for gateway_phy in gateways_phy:
            if gateway_phy.net_access_entity == gateway.entity:
                if gateway_phy_entity is not None:
                    warnings.warn('More than one gateway_phy configured for the gateway_net_acc {}, keeping only the last one'.format(gateway.entity))
                gateway_phy_entity = gateway_phy.entity
                gateway_phy_interfaces = [gateway_phy.lan_interface, gateway_phy.emu_interface]
                gateway_phy_ips = [gateway_phy.lan_ip, gateway_phy.emu_ip]

        for terminal in terminals:
            if terminal.gateway_entity == gateway.entity:
                route_ips.append(extract_network(terminal.lan_ip))
                terminal_ips.append(extract_ip(terminal.opensand_bridge_ip))
                opensand_terminals.append(terminal)

                if terminal.opensand_id in opensand_ids:
                    warnings.warn('Terminal {} uses an ID already used by another entity'.format(terminal.entity))
                opensand_ids.add(terminal.opensand_id)

                found = False
                for workstation in workstations:
                    if workstation.opensand_entity == terminal.entity:
                        if found:
                            warnings.warn('More than one client workstation configured for terminal {}'.format(terminal.entity))
                        work_stations.append(WS(
                            workstation.entity,
                            workstation.interface,
                            workstation.ip,
                            host_route_ip,
                            extract_ip(terminal.lan_ip)))
                        found = True

                if not found:
                    warnings.warn('No client workstation configured for terminal {}'.format(terminal.entity))

        if not opensand_terminals:
            warnings.warn('Gateway {} does not have any associated terminal'.format(gateway.entity))

        gw_terminals = [
                ST(
                    terminal.entity,
                    [terminal.lan_interface, terminal.emu_interface],
                    [terminal.lan_ip, terminal.emu_ip],
                    find_routes(route_ips, terminal.lan_ip),
                    route_gateway_ip,
                    terminal.opensand_bridge_ip,
                    terminal.opensand_bridge_mac_address,
                    terminal.opensand_id)
                for terminal in opensand_terminals
        ]
        
        opensand_gateways.append(GW(
            gateway.entity,
            [gateway.lan_interface, gateway.emu_interface],
            [gateway.lan_ip, gateway.emu_ip],
            find_routes(route_ips, gateway.lan_ip),
            terminal_ips,
            gateway.opensand_bridge_ip,
            gateway.opensand_bridge_mac_address,
            gateway.opensand_id,
            gw_terminals,
            gateway_phy_entity,
            gateway_phy_interfaces,
            gateway_phy_ips))

    return opensand_gateways, work_stations


def main(scenario_name='access_opensand', argv=None):
    observer = ScenarioObserver()
    observer.add_scenario_argument(
            '--sat', '-s', required=True, action=ValidateSatellite,
            nargs=2, metavar=('ENTITY', 'EMULATION_IP'),
            help='The satellite of the platform. Must be supplied only once.')
    observer.add_scenario_argument(
            '--gateway', '-gw', required=True, action=ValidateGateway,
            nargs=3, metavar=('ENTITY', 'EMULATION_IP', 'OPENSAND_ID'),
            help='A gateway in the platform. Must be supplied at least once.')
    observer.add_scenario_argument(
            '--gateway-phy', '-gwp', required=False, action=ValidateGatewayPhy,
            nargs=4, metavar=('ENTITY_PHY', 'ENTITY_NET_ACC', 'INTERCONNECT_PHY', 'INTERCONNECT_NET_ACC'),
            help='The physical part of a split gateway. Must reference the '
            'net access part previously provided using the --gateway option. '
            'Optional, can be supplied only once per gateway.')
    observer.add_scenario_argument(
            '--satellite-terminal', '-st', required=True, action=ValidateSatelliteTerminal,
            nargs=3, metavar=('ENTITY', 'EMULATION_IP', 'OPENSAND_ID'),
            help='A satellite terminal in the platform. Must be supplied at least once.')
    observer.add_scenario_argument(
            '--duration', '-d', required=False, default=0, type=int,
            help='Duration of the opensand run test, leave blank for endless emulation.')
    observer.add_scenario_argument(
            '--configuration-folder', '--configuration', '-c',
            required=False, type=Path, metavar='PATH',
            help='Path to a configuration folder that should be '
            'dispatched on agents before the simulation.')

    args = observer.parse(argv, scenario_name)

    gateways = list(create_gateways(args.gateway, args.gateway_phy or []))
    terminals = [ST(st.entity, st.opensand_id, st.emulation_ip) for st in args.satellite_terminal]
    satellite = SAT(args.sat.entity, args.sat.ip)
  
    config_files = None
    configuration_folder = args.configuration_folder
    if configuration_folder:
        config_files = [
                p.relative_to(configuration_folder)
                for extension in ('conf', 'txt', 'csv', 'input')
                for p in configuration_folder.rglob('*.' + extension)
        ]

        #Store files on the controller
        pusher = observer._share_state(PushFile)
        pusher.args.keep = True
        for config_file in config_files:
            with configuration_folder.joinpath(config_file).open() as local_file:
                pusher.args.local_file = local_file
                pusher.args.remote_path = config_file.as_posix()
                pusher.execute(False)

    scenario = build_opensand(satellite, gateways, terminals, args.duration, config_files)
    observer.launch_and_wait(scenario)


if __name__ == '__main__':
    main()
