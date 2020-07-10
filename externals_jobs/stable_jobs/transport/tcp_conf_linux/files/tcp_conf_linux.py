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


"""Sources of the Job tcp_conf_linux"""


__author__ = 'Viveris Technologies'
__credits__ = '''Contributors:
 * Bastien TAURAN <bastien.tauran@viveris.com>
 * Francklin SIMO <francklin.simo@viveris.com>
'''

import sys
import syslog
import argparse
import subprocess
from subprocess import check_output
import collect_agent
import time


def run_command(command, debug_log, exit=False):
    try:
        subprocess.call(command)
        collect_agent.send_log(syslog.LOG_DEBUG, debug_log)
    except Exception as ex:
        message = '{}:{}'.format(command, ex)
        collect_agent.send_log(
                syslog.LOG_WARNING,
                message)
        if exit:
           sys.exit(message)

def check_cc(congestion_control_name):
    out = check_output(["sysctl", "net.ipv4.tcp_allowed_congestion_control"])
    out = out.decode('utf-8')
    allowed_ccs = out.split('=')[1].rstrip().split()
    if congestion_control_name not in allowed_ccs:
       message = ('Specified congestion control \'{}\' is not allowed. May be its kernel module is not loaded or not installed. \n'
                  'You can choose one from this list: {}.'.format(congestion_control_name, allowed_ccs))
       collect_agent.send_log(
                syslog.LOG_ERR,
                message)
       sys.exit(message)

def set_main_args(reset,
        tcp_congestion_control,
        tcp_slow_start_after_idle,
        tcp_no_metrics_save,
        tcp_sack,
        tcp_recovery,
        tcp_wmem_min,
        tcp_wmem_default,
        tcp_wmem_max,
        tcp_rmem_min,
        tcp_rmem_default,
        tcp_rmem_max,
        tcp_fastopen,
        core_wmem_default,
        core_wmem_max,
        core_rmem_default,
        core_rmem_max):
    collect_agent.register_collect(
        '/opt/openbach/agent/jobs/tcp_conf_linux/'
        'tcp_conf_linux_rstats_filter.conf'
    )
    collect_agent.send_log(syslog.LOG_DEBUG, "Starting job tcp_conf_linux")

    # reset to defaults config if asked
    if reset:
        # removing conf files
        command = ['rm', '-f', '/etc/sysctl.d/60-openbach-job.conf']
        debug_log = 'removing config files'
        run_command(command, debug_log)
        command = ['rm', '-f', '/etc/sysctl.d/60-openbach-job-cubic.conf']
        run_command(command, debug_log)
        # loading default config
        src = open("/opt/openbach/agent/jobs/tcp_conf_linux/default_tcp_conf_linux.conf","r")
        for line in src:
            name,value = line.split("=")
            while '.' in name:
                name = name.replace('.','/')
            dst=open("/proc/sys/"+name,"w")
            dst.write(value)
            dst.close()
        src.close()
        src = open("/opt/openbach/agent/jobs/tcp_conf_linux/default_tcp_conf_linux_cubic.conf","r")
        for line in src:
            name,value = line.split("=")
            value = value.rstrip()
            dst = open("/sys/module/tcp_cubic/parameters/"+name,"w")
            dst.write(value)
            dst.close()
        src.close()

    # writing changes in /etc/sysctl.d/60-openbach-job.conf
    conf_file = open("/etc/sysctl.d/60-openbach-job.conf","w")
    conf_file.write("# configuration file generated by the OpenBACH job tcp_conf_linux\n")
    if tcp_congestion_control is not None:
        conf_file.write("net.ipv4.tcp_congestion_control="+tcp_congestion_control+"\n")
    else:
        src = open("/proc/sys/net/ipv4/tcp_congestion_control","r")
        conf_file.write("net.ipv4.tcp_congestion_control="+src.readline())
        src.close()

    if tcp_slow_start_after_idle is not None:
        conf_file.write("net.ipv4.tcp_slow_start_after_idle="+str(tcp_slow_start_after_idle)+"\n")
    else:
        src = open("/proc/sys/net/ipv4/tcp_slow_start_after_idle","r")
        conf_file.write("net.ipv4.tcp_slow_start_after_idle="+src.readline())
        src.close()

    if tcp_no_metrics_save is not None:
        conf_file.write("net.ipv4.tcp_no_metrics_save="+str(tcp_no_metrics_save)+"\n")
    else:
        src = open("/proc/sys/net/ipv4/tcp_no_metrics_save","r")
        conf_file.write("net.ipv4.tcp_no_metrics_save="+src.readline())
        src.close()

    if tcp_sack is not None:
        conf_file.write("net.ipv4.tcp_sack="+str(tcp_sack)+"\n")
    else:
        src = open("/proc/sys/net/ipv4/tcp_sack","r")
        conf_file.write("net.ipv4.tcp_sack="+src.readline())
        src.close()

    if tcp_recovery is not None:
        conf_file.write("net.ipv4.tcp_recovery="+str(tcp_recovery)+"\n")
    else:
        src = open("/proc/sys/net/ipv4/tcp_recovery","r")
        conf_file.write("net.ipv4.tcp_recovery="+src.readline())
        src.close()

    if tcp_wmem_min is not None or tcp_wmem_default is not None or tcp_wmem_max is not None:
        rc = subprocess.Popen("cat /proc/sys/net/ipv4/tcp_wmem", shell=True, 
            stdout=subprocess.PIPE)
        wmem_old = [x.decode("utf-8") for x in rc.stdout.read().split()]
        if tcp_wmem_min is None:
            tcp_wmem_min = wmem_old[0]
        if tcp_wmem_default is None:
            tcp_wmem_default = wmem_old[1]
        if tcp_wmem_max is None:
            tcp_wmem_max = wmem_old[2]
        conf_file.write("net.ipv4.tcp_wmem="+str(tcp_wmem_min)+" "+
            str(tcp_wmem_default)+" "+str(tcp_wmem_max)+"\n")
    else:
        src = open("/proc/sys/net/ipv4/tcp_wmem","r")
        conf_file.write("net.ipv4.tcp_wmem="+src.readline())
        src.close()

    if tcp_rmem_min is not None or tcp_rmem_default is not None or tcp_rmem_max is not None:
        rc = subprocess.Popen("cat /proc/sys/net/ipv4/tcp_rmem", shell=True,
            stdout=subprocess.PIPE)
        rmem_old = [x.decode("utf-8") for x in rc.stdout.read().split()]
        if tcp_rmem_min is None:
            tcp_rmem_min = rmem_old[0]
        if tcp_rmem_default is None:
            tcp_rmem_default = rmem_old[1]
        if tcp_rmem_max is None:
            tcp_rmem_max = rmem_old[2]
        conf_file.write("net.ipv4.tcp_rmem="+str(tcp_rmem_min)+" "+
            str(tcp_rmem_default)+" "+str(tcp_rmem_max)+"\n")
    else:
        src = open("/proc/sys/net/ipv4/tcp_rmem","r")
        conf_file.write("net.ipv4.tcp_rmem="+src.readline())
        src.close()

    if tcp_fastopen is not None:
        conf_file.write("net.ipv4.tcp_fastopen="+str(tcp_fastopen)+"\n")
    else:
        src = open("/proc/sys/net/ipv4/tcp_fastopen","r")
        conf_file.write("net.ipv4.tcp_fastopen="+src.readline())
        src.close()

    if core_wmem_default is not None:
        conf_file.write("net.core.wmem_default="+str(core_wmem_default)+"\n")
    else:
        src = open("/proc/sys/net/core/wmem_default","r")
        conf_file.write("net.core.wmem_default="+src.readline())
        src.close()

    if core_wmem_max is not None:
        conf_file.write("net.core.wmem_max="+str(core_wmem_max)+"\n")
    else:
        src = open("/proc/sys/net/core/wmem_max","r")
        conf_file.write("net.core.wmem_max="+src.readline())
        src.close()

    if core_rmem_default is not None:
        conf_file.write("net.core.rmem_default="+str(core_rmem_default)+"\n")
    else:
        src = open("/proc/sys/net/core/rmem_default","r")
        conf_file.write("net.core.rmem_default="+src.readline())
        src.close()

    if core_rmem_max is not None:
        conf_file.write("net.core.rmem_max="+str(core_rmem_max)+"\n")
    else:
        src = open("/proc/sys/net/core/rmem_max","r")
        conf_file.write("net.core.rmem_max="+src.readline())
        src.close()

    conf_file.close()

    # loading new configuration
    command = ['systemctl', 'restart', 'procps.service']
    debug_log = 'Loading new configuration'
    run_command(command, debug_log, exit=True)
    rc = subprocess.call("systemctl restart procps", shell=True)

    # retrieving new values
    statistics = {}
    for param in ["tcp_congestion_control", "tcp_slow_start_after_idle",
            "tcp_no_metrics_save", "tcp_sack", "tcp_recovery", "tcp_fastopen"]:
        file = open("/proc/sys/net/ipv4/"+param)
        statistics[param] = file.readline()
        file.close()
    for param in ["wmem_default", "wmem_max",
            "rmem_default", "rmem_max"]:
        file = open("/proc/sys/net/core/"+param)
        statistics["core_" + param] = file.readline()
        file.close()

    file = open("/proc/sys/net/ipv4/tcp_wmem")
    new_wmem = file.readline().split()
    statistics["tcp_wmem_min"] = new_wmem[0]
    statistics["tcp_wmem_default"] = new_wmem[1]
    statistics["tcp_wmem_max"] = new_wmem[2]
    file.close()

    file = open("/proc/sys/net/ipv4/tcp_rmem")
    new_rmem = file.readline().split()
    statistics["tcp_rmem_min"] = new_rmem[0]
    statistics["tcp_rmem_default"] = new_rmem[1]
    statistics["tcp_rmem_max"] = new_rmem[2]
    file.close()

    collect_agent.send_stat(int(time.time() * 1000), **statistics)

def cubic(reset,
        tcp_slow_start_after_idle,
        tcp_no_metrics_save,
        tcp_sack,
        tcp_recovery,
        tcp_wmem_min,
        tcp_wmem_default,
        tcp_wmem_max,
        tcp_rmem_min,
        tcp_rmem_default,
        tcp_rmem_max,
        tcp_fastopen,
        core_wmem_default,
        core_wmem_max,
        core_rmem_default,
        core_rmem_max,
        beta,
        fast_convergence,
        hystart_ack_delta,
        hystart_low_window,
        tcp_friendliness,
        hystart,
        hystart_detect,
        initial_ssthresh):
    check_cc('cubic')
    set_main_args(reset,
            "cubic",
            tcp_slow_start_after_idle,
            tcp_no_metrics_save,
            tcp_sack,
            tcp_recovery,
            tcp_wmem_min,
            tcp_wmem_default,
            tcp_wmem_max,
            tcp_rmem_min,
            tcp_rmem_default,
            tcp_rmem_max,
            tcp_fastopen,
            core_wmem_default,
            core_wmem_max,
            core_rmem_default,
            core_rmem_max)

    # getting changes to CUBIC parameters in /etc/module/tcp_cubic/parameters and
    # writing changes in /etc/sysctl.d/60-openbach-job-cubic.conf
    changes = {}
    conf_file = open("/etc/sysctl.d/60-openbach-job-cubic.conf","w")
    conf_file.write("# configuration file generated by the OpenBACH job tcp_conf_linux\n")
    conf_file.write("# warning: these values are not loaded on system startup\n")
    if beta is not None:
        conf_file.write("beta="+str(beta)+"\n")
        changes["beta"] = beta
    else:
        src = open("/sys/module/tcp_cubic/parameters/beta","r")
        conf_file.write("beta="+src.readline())
        src.close()
    if fast_convergence is not None:
        conf_file.write("fast_convergence="+str(fast_convergence)+"\n")
        changes["fast_convergence"] = fast_convergence
    else:
        src = open("/sys/module/tcp_cubic/parameters/fast_convergence","r")
        conf_file.write("fast_convergence="+src.readline())
        src.close()
    if hystart_ack_delta is not None:
        conf_file.write("hystart_ack_delta="+str(hystart_ack_delta)+"\n")
        changes["hystart_ack_delta"] = hystart_ack_delta
    else:
        src = open("/sys/module/tcp_cubic/parameters/hystart_ack_delta","r")
        conf_file.write("hystart_ack_delta="+src.readline())
        src.close()
    if hystart_low_window is not None:
        conf_file.write("hystart_low_window="+str(hystart_low_window)+"\n")
        changes["hystart_low_window"] = hystart_low_window
    else:
        src = open("/sys/module/tcp_cubic/parameters/hystart_low_window","r")
        conf_file.write("hystart_low_window="+src.readline())
        src.close()
    if tcp_friendliness is not None:
        conf_file.write("tcp_friendliness="+str(tcp_friendliness)+"\n")
        changes["tcp_friendliness"] = tcp_friendliness
    else:
        src = open("/sys/module/tcp_cubic/parameters/tcp_friendliness","r")
        conf_file.write("tcp_friendliness="+src.readline())
        src.close()
    if hystart is not None:
        conf_file.write("hystart="+str(hystart)+"\n")
        changes["hystart"] = hystart
    else:
        src = open("/sys/module/tcp_cubic/parameters/hystart","r")
        conf_file.write("hystart="+src.readline())
        src.close()
    if hystart_detect is not None:
        conf_file.write("hystart_detect="+str(hystart_detect)+"\n")
        changes["hystart_detect"] = hystart_detect
    else:
        src = open("/sys/module/tcp_cubic/parameters/hystart_detect","r")
        conf_file.write("hystart_detect="+src.readline())
        src.close()
    if initial_ssthresh is not None:
        conf_file.write("initial_ssthresh="+str(initial_ssthresh)+"\n")
        changes["initial_ssthresh"] = initial_ssthresh
    else:
        src = open("/sys/module/tcp_cubic/parameters/initial_ssthresh","r")
        conf_file.write("initial_ssthresh="+src.readline())
        src.close()
    conf_file.close()

    #applying changes
    for name,value in changes.items():
        dst=open("/sys/module/tcp_cubic/parameters/"+name,"w")
        dst.write(str(value))
        dst.close()

    #retrieving new values for tcp_cubic parameters
    statistics = {}
    for param in ["beta", "fast_convergence", "hystart_ack_delta",
    "hystart_low_window", "tcp_friendliness", "hystart", "hystart_detect",
    "initial_ssthresh"]:
        file = open("/sys/module/tcp_cubic/parameters/"+param)
        statistics[param] = file.readline()
        file.close()

    collect_agent.send_stat(int(time.time() * 1000), **statistics)

def other_CC(reset,
        tcp_slow_start_after_idle,
        tcp_no_metrics_save,
        tcp_sack,
        tcp_recovery,
        tcp_wmem_min,
        tcp_wmem_default,
        tcp_wmem_max,
        tcp_rmem_min,
        tcp_rmem_default,
        tcp_rmem_max,
        tcp_fastopen,
        core_wmem_default,
        core_wmem_max,
        core_rmem_default,
        core_rmem_max,
        congestion_control_name):
    congestion_control_name = congestion_control_name.lower()
    check_cc(congestion_control_name)
    set_main_args(reset,
            congestion_control_name,
            tcp_slow_start_after_idle,
            tcp_no_metrics_save,
            tcp_sack,
            tcp_recovery,
            tcp_wmem_min,
            tcp_wmem_default,
            tcp_wmem_max,
            tcp_rmem_min,
            tcp_rmem_default,
            tcp_rmem_max,
            tcp_fastopen,
            core_wmem_default,
            core_wmem_max,
            core_rmem_default,
            core_rmem_max)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
            description=__doc__,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--reset', action='store_true', help='Resets the parameters to default configuration before applying changes')
    parser.add_argument('--tcp_slow_start_after_idle', type=int)
    parser.add_argument('--tcp_no_metrics_save', type=int)
    parser.add_argument('--tcp_sack', type=int)
    parser.add_argument('--tcp_recovery', type=int)
    parser.add_argument('--tcp_wmem_min', type=int)
    parser.add_argument('--tcp_wmem_default', type=int)
    parser.add_argument('--tcp_wmem_max', type=int)
    parser.add_argument('--tcp_rmem_min', type=int)
    parser.add_argument('--tcp_rmem_default', type=int)
    parser.add_argument('--tcp_rmem_max', type=int)
    parser.add_argument('--tcp_fastopen', type=int)
    parser.add_argument('--core_wmem_default', type=int)
    parser.add_argument('--core_wmem_max', type=int)
    parser.add_argument('--core_rmem_default', type=int)
    parser.add_argument('--core_rmem_max', type=int)

    subparsers = parser.add_subparsers(
            title='Subcommand mode',
            help='Choose the congestion control')
    subparsers.required=True
    parser_cubic = subparsers.add_parser('CUBIC', help='CUBIC chosen')
    parser_cubic.add_argument('--beta', type=int)
    parser_cubic.add_argument('--fast_convergence', type=int)
    parser_cubic.add_argument('--hystart_ack_delta', type=int)
    parser_cubic.add_argument('--hystart_low_window', type=int)
    parser_cubic.add_argument('--tcp_friendliness', type=int)
    parser_cubic.add_argument('--hystart', type=int)
    parser_cubic.add_argument('--hystart_detect', type=int)
    parser_cubic.add_argument('--initial_ssthresh', type=int)

    parser_other = subparsers.add_parser('other', help='other CC chosen')
    parser_other.add_argument('congestion_control_name', type=str)

    parser_cubic.set_defaults(function=cubic)
    parser_other.set_defaults(function=other_CC)

    args = vars(parser.parse_args())

    main = args.pop('function')
    main(**args)
