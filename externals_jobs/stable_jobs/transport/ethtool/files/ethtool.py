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


"""Sources of the Job ethtool"""


__author__ = 'Viveris Technologies'
__credits__ = '''Contributors:
 * Bastien TAURAN <bastien.tauran@viveris.com>
'''

import sys
import syslog
import argparse
import subprocess
import collect_agent
import time

def main(interface, gso, tso):
    collect_agent.register_collect(
        '/opt/openbach/agent/jobs/ethtool/'
        'ethtool_rstats_filter.conf'
    )
    collect_agent.send_log(syslog.LOG_DEBUG, "Starting job ethool")

    # loading new configuration
    rc = subprocess.call("ethtool -K "+interface+
            " gso "+("on" if gso else "off"), shell=True)
    if rc:
        message = "WARNING \'{}\' exited with non-zero code".format(cmd)
        collect_agent.send_log(syslog.LOG_ERR, message)
    rc = subprocess.call("ethtool -K "+interface+
            " tso "+("on" if tso else "off"), shell=True)
    if rc:
        message = "WARNING \'{}\' exited with non-zero code".format(cmd)
        collect_agent.send_log(syslog.LOG_ERR, message)

    # retrieving new values
    statistics = {}
    p = subprocess.Popen(["ethtool", "-k",interface], stdout=subprocess.PIPE)
    while 1:
        line = p.stdout.readline().decode().strip()
        if not line:
            break
        if "generic-segmentation-offload" in line:
            statistics["gso"] = 1 if line.split()[1]=="on" else 0
        if "tcp-segmentation-offload" in line:
            statistics["tso"] = 1 if line.split()[1]=="on" else 0
    collect_agent.send_stat(int(time.time() * 1000), **statistics)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
            description=__doc__,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('interface', type=str,
            help='The interface to modify')
    parser.add_argument('--gso', action='store_true',
            help='Activate GSO, if this flag is absent, GSO is disabled')
    parser.add_argument('--tso', action='store_true',
            help='Activate TSO, if this flag is absent, TSO is disabled')

    args = vars(parser.parse_args())
    main(**args)