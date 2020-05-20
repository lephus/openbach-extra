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

""" Helpers of opensand job """

import itertools
import ipaddress

from ..network.ip_address import ip_address
from ..network.ip_route import ip_route
from ..network.ip_link import ip_link_add, ip_link_set, ip_link_del
from ..admin.command_shell import command_shell
from ..transport.sysctl import sysctl_configure_ip_forwarding


def opensand_network_ip(
        scenario, entity, address_mask, tap_name='opensand_tap',
        bridge_name='opensand_br', tap_mac_address=None,
        wait_finished=None, wait_launched=None, wait_delay=0):
    tap_add = ip_tuntap(
            scenario, entity, tap_name, 'add',
            wait_finished=wait_finished,
            wait_launched=wait_launched,
            wait_delay=wait_delay)
    bridge_add = ip_link_add(
            scenario, entity, bridge_name, type='bridge',
            wait_finished=wait_finished,
            wait_launched=wait_launched,
            wait_delay=wait_delay)

    if tap_mac_address is not None:
        tap_add = ip_link_set(scenario, entity, tap_name, address=tap_mac_address, wait_finished=tap_add)

    bridge_add = ip_address(scenario, entity, bridge_name, 'add', address_mask, wait_finished=bridge_add)
    tap_in_bridge = ip_link_set(scenario, entity, tap_name, master=bridge_name, wait_finished=tap_add + bridge_add)

    tap_up = ip_link_set(scenario, entity, tap_name, up=True, wait_finished=tap_in_bridge)
    bridge_up = ip_link_set(scenario, entity, bridge_name, up=True, wait_finished=tap_in_bridge)

    try:
        interface = ipaddress.ip_interface(address_mask)
    except ValueError:
        # Do not bother much as `ip_address` will likely fail anyway
        return tap_up + bridge_up
    else:
        return sysctl_configure_ip_forwarding(
                scenario, entity, bridge_name,
                version=interface.version,
                wait_finished=tap_up + bridge_up)


def opensand_network_ethernet(
        scenario, entity, interface, tap_name='opensand_tap',
        bridge_name='opensand_br', tap_mac_address=None,
        wait_finished=None, wait_launched=None, wait_delay=0):
    tap_add = ip_tuntap(
            scenario, entity, tap_name, 'add',
            wait_finished=wait_finished,
            wait_launched=wait_launched,
            wait_delay=wait_delay)
    bridge_add = ip_link_add(
            scenario, entity, bridge_name, type='bridge',
            wait_finished=wait_finished,
            wait_launched=wait_launched,
            wait_delay=wait_delay)

    if tap_mac_address is not None:
        tap_add = ip_link_set(scenario, entity, tap_name, address=tap_mac_address, wait_finished=tap_add)

    tap_in_bridge = ip_link_set(scenario, entity, tap_name, master=bridge_name, wait_finished=tap_add + bridge_add)
    interface_in_bridge = ip_link_set(scenario, entity, interface, master=bridge_name, wait_finished=bridge_add)

    wait = tap_in_bridge + interface_in_bridge
    tap_up = ip_link_set(scenario, entity, tap_name, up=True, wait_finished=wait)
    bridge_up = ip_link_set(scenario, entity, bridge_name, up=True, wait_finished=wait)

    return tap_up + bridge_up


def opensand_network_clear(
        scenario, entity, tap_name, bridge_name,
        wait_finished=None, wait_launched=None, wait_delay=0):
    tap_del = ip_link_del(
            scenario, entity, tap_name,
            wait_finished=wait_finished,
            wait_launched=wait_launched,
            wait_delay=wait_delay)
    bridge_del = ip_link_del(
            scenario, entity, bridge_name,
            wait_finished=wait_finished,
            wait_launched=wait_launched,
            wait_delay=wait_delay)

    return tap_del + bridge_del


def opensand_run(
        scenario, agent_entity, entity, configuration=None,
        output_address=None, logs_port=None, stats_port=None,
        binaries_directory=None, entity_id=None,
        emulation_address=None, interconnection_address=None, 
        wait_finished=None, wait_launched=None, wait_delay=0):

    opensand = scenario.add_function(
            'start_job_instance',
            wait_finished=wait_finished,
            wait_launched=wait_launched,
            wait_delay=wait_delay)

    run = {
            entity: {'id': entity_id, 'emulation_address': emulation_address},
    }

    if configuration:
        run['configuration'] = configuration
    if output_address:
        run['output_address'] = output_address
    if logs_port:
        run['logs_port'] = logs_port
    if stats_port:
        run['stats_port'] = stats_port
    if binaries_directory:
        run['binaries_directory'] = binaries_directory

    if entity == 'sat': 
        del run[entity]['id']
    elif entity == 'gw-phy':
        run[entity]['interconnection_address'] = interconnection_address
    elif entity == 'gw-net-acc':
        del run[entity]['emulation_address']
        run[entity]['interconnection address'] = interconnection_address
    opensand.configure('opensand', agent_entity, **run)

    return [opensand]


def configure_interfaces(
        scenario, entity, interfaces, ips,
        wait_finished=None, wait_launched=None, wait_delay=0):

    for interface, ip in zip(interfaces, ips):
        wait_finished = ip_address(
                scenario, entity, interface, 'add', ip,
                wait_finished=wait_finished,
                wait_launched=wait_launched,
                wait_delay=wait_delay)
        wait_launched = None
        wait_delay = 0

    return wait_finished


def configure_routing(
        scenario, entity, network_mask, ips, gateway_ips, bridge_mac_address,
        tap_name='opensand_tap', bridge_name='opensand_br',
        wait_finished=None, wait_launched=None, wait_delay=0):
    wait_finished = opensand_network_ip(
            scenario, entity, network_mask,
            tap_name, bridge_name, bridge_mac_address,
            wait_finished=wait_finished,
            wait_launched=wait_launched,
            wait_delay=wait_delay)

    for ip, gateway_ip in zip(ips, gateway_ips):
        wait_finished = ip_route(scenario, entity, 'add', ip, gateway_ip, wait_finished=wait_finished)

    return wait_finished


def configure_satellite(
        scenario, entity, interface, ip,
        wait_finished=None, wait_launched=None, wait_delay=0):
    return configure_interfaces(
            scenario, entity, [interface], [ip],
            wait_finished=wait_finished,
            wait_launched=wait_launched,
            wait_delay=wait_delay)


def configure_terminal(
        scenario, entity, interfaces, ips, mask, lan_ips, gateway_ip, bridge_mac_address,
        wait_finished=None, wait_launched=None, wait_delay=0): 
    interfaces = configure_interfaces(
            scenario, entity, interfaces, ips,
            wait_finished=wait_finished,
            wait_launched=wait_launched,
            wait_delay=wait_delay)
    return configure_routing(
            scenario, entity, mask, lan_ips, itertools.repeat(gateway_ip), bridge_mac_address,
            wait_finished=interfaces)


def configure_gateway_phy(
        scenario, entity, interfaces, ips,
        wait_finished=None, wait_launched=None, wait_delay=0):
    return configure_interfaces(
            scenario, entity, interfaces, ips,
            wait_finished=wait_finished,
            wait_launched=wait_launched,
            wait_delay=wait_delay)


def configure_gateway(
        scenario, entity, interfaces, ips, mask, lan_ips, gateway_ips, bridge_mac_address,
        wait_finished=None, wait_launched=None, wait_delay=0):
    interfaces = configure_interfaces(
            scenario, entity, interfaces, ips,
            wait_finished=wait_finished,
            wait_launched=wait_launched,
            wait_delay=wait_delay)
    return configure_routing(
            scenario, entity, mask, lan_ips, gateway_ips, bridge_mac_address,
            wait_finished=interfaces)


def configure_workstation(
        scenario, entity, interface, ip, lan_ip, gateway_ip,
        wait_finished=None, wait_launched=None, wait_delay=0):
    interface = ip_address(
            scenario, entity, interface, 'add', ip,
            wait_finished=wait_finished,
            wait_launched=wait_launched,
            wait_delay=wait_delay)
    return ip_route(
            scenario, entity, 'add', lan_ip, gateway_ip,
            wait_finished=interface)


def clear_interfaces(
        scenario, entity, interfaces,
        wait_finished=None, wait_launched=None, wait_delay=0):

    for interface in interfaces:
        wait_finished = ip_address(
                scenario, entity, interface, 'flush',
                wait_finished=wait_finished,
                wait_launched=wait_launched,
                wait_delay=wait_delay)
        wait_launched = None
        wait_delay = 0

    return wait_finished


def clear_routing(
        scenario, entity,
        wait_finished=None, wait_launched=None, wait_delay=0):

    wait_finished = opensand_network_clear(
            scenario, entity,
            wait_finished=wait_finished,
            wait_launched=wait_launched,
            wait_delay=wait_delay)
    return wait_finished


def clear_satellite(
        scenario, entity, interface,
        wait_finished=None, wait_launched=None, wait_delay=0):
    return clear_interfaces(
            scenario, entity, [interface],
            wait_finished=wait_finished,
            wait_launched=wait_launched,
            wait_delay=wait_delay)


def clear_terminal(
        scenario, entity, interfaces,
        wait_finished=None, wait_launched=None, wait_delay=0):
    interfaces = clear_interfaces(
            scenario, entity, interfaces,
            wait_finished=wait_finished,
            wait_launched=wait_launched,
            wait_delay=wait_delay)
    return clear_routing(
            scenario, entity,
            wait_finished=interfaces)


def clear_gateway_phy(
        scenario, entity, interfaces,
        wait_finished=None, wait_launched=None, wait_delay=0):
    return clear_interfaces(
            scenario, entity, interfaces,
            wait_finished=wait_finished,
            wait_launched=wait_launched,
            wait_delay=wait_delay)


def clear_gateway(
        scenario, entity, interfaces,
        wait_finished=None, wait_launched=None, wait_delay=0):
    interfaces = clear_interfaces(
            scenario, entity, interfaces,
            wait_finished=wait_finished,
            wait_launched=wait_launched,
            wait_delay=wait_delay)
    return clear_routing(
            scenario, entity,
            wait_finished=interfaces)


def clear_workstation(
        scenario, entity, interfaces, 
        wait_finished=None, wait_launched=None, wait_delay=0):
    return clear_interfaces(
            scenario, entity, [interfaces],
            wait_finished=wait_finished,
            wait_launched=wait_launched,
            wait_delay=wait_delay)
