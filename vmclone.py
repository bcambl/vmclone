#!/usr/bin/env python
"""
vmclone.py
----------
Re-Identify a cloned Linux Virtual Machine (Hostname & Networking)

See README.md for usage and more information
"""
__author__ = 'Blayne Campbell'
__date__ = '2014-01-29'
__version__ = '1.2.0'

from time import sleep
import subprocess
import datetime
import shutil
import json
import glob
import sys
import os
import re

date = str(datetime.datetime.now().strftime('%Y-%m-%d'))

# Set Working Directory
abspath = os.path.abspath(__file__)
script_path = os.path.dirname(abspath)
os.chdir(script_path)
try:
    from subprocess import DEVNULL  # py3k
except ImportError:
    DEVNULL = open(os.devnull, 'wb')

# Import Settings #
try:
    from settings import *
except ImportError:
    sys.exit("Unable to import settings..\n"
             "Try re-naming example-settings.py to settings.py")


# Validations #
valip = '\\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.)' \
        '{3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\b'
valmac = '\\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\\b'
valproto = '\\b((?i)dhcp|(?i)none)\\b'
valtabs = '\\b(\\t+)\\b'
valyesno = '\\b((?i)yes|(?i)no)\\b'
# Validations End #

# Minimal Mode - Skip all dependency checks
minimal_mode = 0


def dependency_check():
    """
    Dependency check for required utilities
    """
    # List of applications required by script #
    all_dependencies = ['nc', 'ntp', 'ntpdate']
    missing_dependencies = []
    for dependency in all_dependencies:
        d = subprocess.Popen(['which', '%s' % dependency], stderr=DEVNULL)
        if d.wait() != 0:
            missing_dependencies.append(dependency)
    if len(missing_dependencies) >= 1:
        print('The following dependencies are not installed: %s'
              % " ".join(str(x) for x in missing_dependencies))
        dep_prompt = raw_input("Would you like to install these now?[y/N]")
        if dep_prompt.lower() == 'y':
            for dependency in missing_dependencies:
                d = subprocess.Popen(['yum', 'install', '%s' % dependency])
                if d.wait() != 0:
                    sys.exit("Problem while installing dependency: %s"
                             % dependency)
        else:
            sys.exit('You chose not to install dependencies.. Exiting.')
    return True


def get_release():
    release = subprocess.Popen(['cat', '/etc/redhat-release'],
                               stdout=subprocess.PIPE)
    release = release.stdout.read()
    release_number = re.match(r'^.*release\s(\d{1,2}).*$', release)
    if release_number:
        return release_number.group(1)
    else:
        return False


def get_interfaces():
    """ Return interface(s) reporting a permanent address via ethtool utility.
    :return: dict = {'interface': {'perm_address': '00:00:00:00:00:00'}
    """
    procnetdev = subprocess.Popen(['cat', '/proc/net/dev'],
                                  stdout=subprocess.PIPE).stdout.readlines()
    interface_list = []
    physical_interfaces = {}
    for i in procnetdev:
        iface = re.match(r'^(.*):.*$', i)
        if iface:
            interface_found = iface.group(1).strip()
            if interface_found != 'lo':
                interface_list.append(interface_found)
    for interface in interface_list:
        perm_addr = subprocess.Popen(['ethtool', '-P', interface],
                                     stdout=subprocess.PIPE,
                                     stderr=DEVNULL).stdout.readlines()
        if not perm_addr:
            continue
        mac = re.match(r'^Permanent\saddress:\s(.*)$', perm_addr[0])
        if mac:
            if mac.group(1) != '00:00:00:00:00:00':
                physical_interfaces[interface] = {'perm_address': mac.group(1)}
    return physical_interfaces


def show_usage():
    """
    Show script usage
    """
    print("\nUsage:\nclone: Re-identify this server (write networking files)")
    print("check: Show available Name servers and NTP servers\n")
    sys.exit('Try: %s <check|clone>\n' % sys.argv[0])


def current_hostname(lookup):
    """
    Find current hostname of system via /etc/sysconfig/network
    """
    cur = open(network)
    cur = cur.readlines()
    for i in cur:
        if lookup in i:
            host = i.split('=')[1]
            return host


def current_mac(cfgfile):
    """
    Find current MAC address in given interface configuration
    :param cfgfile: interface configuration
    :return: Current MAC address
    """
    cur = open(cfgfile)
    cur = cur.readlines()
    for i in cur:
        if 'HWADDR' in i:
            return i.strip()[7:]


def backup_file(cfgfile):
    """
    Creates Backup of configuration file
    :param cfgfile: configuration file
    :return: creates backup if backup not already exists
    """
    backup_dir = script_path + '/cfg_backups/%s' % date
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    p, f = os.path.split(cfgfile)
    if os.path.isfile("%s%s" % (backup_dir, f)):
        pass
    else:
        if os.path.isfile(cfgfile):
            shutil.copy(cfgfile, backup_dir)
        else:
            print("Unable to backup %s. File does not exist." % cfgfile)


def findmac(iface):
    """
    Return permanent MAC address for interface
    """
    interfaces = get_interfaces()
    return interfaces[iface]['perm_address']


def valid_ip(ip):
    """
    Validate IP Addresses
    """
    valid = re.match(valip, ip)
    if valid:
        return True
    else:
        print("Invalid IP address...")


def replace(cfgfile, pattern, subst):
    """
    Matches a pattern in a file and replaces with provided substitution.
    """
    with open(cfgfile, 'r') as filein:
        filecont = filein.read()
    if re.search(pattern, filecont):
        filecont = (re.sub(pattern, subst, filecont))
        with open(cfgfile, 'w') as fileout:
            fileout.write(filecont)
    else:
        with open(cfgfile, 'a') as fileout:
            fileout.write('\n' + subst)


def gen_interface(cfgfile, iface):
    """
    Re-Generate ifcfg-eth<x> file with temporary network information
    :param cfgfile: full path to interface configuration
    :param iface: interface name (ie: eth0)
    :return:
    """
    newuuid = subprocess.Popen('uuidgen', stdout=subprocess.PIPE)
    newuuid = newuuid.stdout.readlines()[0].strip()
    print("Generating interface %s.." % iface)
    with open(cfgfile, 'w') as f:
        f.write('# This file was generated by vmclone.py on %s\n'
                % datetime.datetime.now())
        f.write('DEVICE=%s\n' % iface)
        f.write('HWADDR=%s\n' % findmac(iface))
        f.write('IPADDR=123.123.123.123\n')
        f.write('NETMASK=255.255.255.0\n')
        f.write('GATEWAY=123.123.123.123\n')
        f.write('BOOTPROTO=none\n')
        f.write('ONBOOT=yes\n')
        f.write('UUID=%s\n' % newuuid)
        f.write('NM_CONTROLLED=no\n')


def get_nameservers(write=None):
    """
    Display responsive nameservers outlined in the settings file
    :param write: Writes nameservers to resolv.conf
    :return: Nameservers found as reachable
    """
    print("\nChecking for available Name Servers..\n"
          "The following servers are reachable:\n")
    if write:
        with open(resolvconf, 'r') as f:
            lines = f.readlines()
        with open(resolvconf, 'w') as f:
            for line in lines:
                if "nameserver" in line:
                    pass
                else:
                    f.write(line)
    for ns in nameservers:
        if valid_ip(ns):
            r = subprocess.Popen(['nc', '-v', '-z', '%s' % ns, '53'],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
            if r.wait() == 0:
                print('nameserver %s' % ns)
                if write:
                    with open(resolvconf, 'a') as f:
                        f.write('\nnameserver %s' % ns)
    if write:
        print("The above servers have been written to %s" % resolvconf)


def get_ntpservers():
    """
    Display responsive NTP servers outlined in the settings file
    :return: NTP servers found as reachable
    """
    print("\nChecking for available NTP Servers..\n"
          "The following servers are reachable:\n")
    for ntp in ntpservers:
        r = subprocess.Popen(['ntpdate', '-u', '%s' % ntp],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        if r.wait() == 0:
            print('server %s' % ntp)


def clean_shutdown(option):
    """
    Removes udev net rules and ssh host files that are automatically generated
    on boot.
    This ensures that any new servers cloned from this 'template' will
    have unique MAC addresses and ssh host keys.
    """
    if int(get_release()) <= 6:
        if os.path.isfile(persistent):
            print("deleting %s" % persistent)
            os.remove(persistent)
    for sshfile in glob.glob('/etc/ssh/ssh_host_*'):
        if os.path.isfile(sshfile):
            print("deleting %s" % sshfile)
            os.remove(sshfile)
    for i_cfg in glob.glob('%s/ifcfg-*' % ifcfg_path):
        if re.match(r'^.*ifcfg-lo$', i_cfg):
            continue
        else:
            backup_file(i_cfg)
            os.remove(i_cfg)
    sleep(2)
    if option == 'halt':
        command = "/sbin/shutdown -h now"
    else:
        command = "/sbin/shutdown -r now"
    subprocess.Popen(command.split())


class ServerClone:
    """
    Main Configuration Object
    """
    def __init__(self, mode=0):
        self.runmode = mode
        self.old_serv = current_hostname('HOSTNAME')
        self.new_serv = None
        self.interfaces = dict()
        self.oldip = 'IPADDR=%s' % valip
        self.oldnm = 'NETMASK=%s' % valip
        self.oldgw = 'GATEWAY=%s' % valip
        self.oldmac = 'HWADDR=%s' % valmac
        self.proto_dhcp = 'BOOTPROTO=%s' % valproto
        self.proto_stat = 'BOOTPROTO=none'
        self.ip = None
        self.nm = None
        self.gw = None
        self.new_ip = None
        self.new_nm = None
        self.new_gw = None
        self.ntppos = None

    def set_hostname(self):
        """
        Prompt for new hostname
        :return: Set object hostname
        """
        while not self.new_serv:
            self.new_serv = raw_input('Enter NEW Server Name: ')

    def set_ntpservers(self):
        """
        Tests NTP servers outlined in settings and writes accessible servers
        to /etc/ntp.conf
        :return:
        """
        if not os.path.exists(ntpconf):
            sys.exit("Unable to open %s" % ntpconf)
        print("\nChecking for available NTP Servers..\n"
              "The following servers are reachable:\n")
        with open(ntpconf, 'r') as f:
            lines = f.readlines()
            self.ntppos = [i for i, item in enumerate(lines)
                           if re.search(r'\bserver\b', item)]
        with open(ntpconf, 'w') as f:
            for line in lines:
                if "server" in line:
                    pass
                else:
                    f.write(line)
        accessible = []
        for ntp in ntpservers:
            r = subprocess.Popen(['ntpdate', '-u', '%s' % ntp],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
            if r.wait() == 0:
                accessible.append(ntp)
                print('server %s' % ntp)
        if accessible:
            if self.ntppos:
                with open(ntpconf, 'r') as f:
                    lines = f.readlines()
                for i, a in enumerate(accessible):
                    if i == 0:
                        newline = '\nserver %s\n' % a
                        lines.insert(self.ntppos[0], newline)
                    else:
                        newline = '\nserver %s' % a
                        lines.insert(self.ntppos[0], newline)
                with open(ntpconf, 'w') as out:
                    out.writelines(lines)
            else:
                with open(ntpconf, 'a') as out:
                    for i, a in enumerate(accessible):
                        newline = '\nserver %s' % a
                        out.write(newline)
            print("The above servers have been written to %s" % ntpconf)
        else:
            print("Warning:\n"
                  "All servers specified by settings are inaccessible.")

    def show_settings(self):
        """
        Show proposed object configuration
        :return:
        """
        os.system('clear')
        print("Proposed Network Configuration:")
        print("Hostname: %s\n" % clone.new_serv)
        for i in sorted(self.interfaces):
            print('Interface %s\n' % i)
            print("IP: %s\nNetmask: %s\nGateway: %s\n"
                  % (self.interfaces[i]['ip'],
                     self.interfaces[i]['nm'],
                     self.interfaces[i]['gw']))

    def confirm_settings(self):
        """
        Prompts to confirm settings before writing configuration files
        :return:
        """
        applyconf = raw_input("Would you like apply the above "
                              "configuration?[y/N]")
        if 'y' in applyconf:
            self.commit_settings()
        else:
            print("\nOK.. No changes have been made to this system.\n"
                  "The configuration you have entered will be saved.")
            sys.exit()

    def commit_settings(self):
        """
        Write configuration files
        """
        try:
            for i in sorted(self.interfaces):
                cfg_file = ifcfg_path + '/ifcfg-%s' % i
                backup_file(cfg_file)
                gen_interface(cfg_file, i)
                replace(cfg_file, self.oldip, 'IPADDR=%s'
                        % self.interfaces[i]['ip'])
                replace(cfg_file, self.oldnm, 'NETMASK=%s'
                        % self.interfaces[i]['nm'])
                replace(cfg_file, self.oldgw, 'GATEWAY=%s'
                        % self.interfaces[i]['gw'])
                replace(cfg_file, self.oldmac, 'HWADDR=%s' % findmac(i))
                replace(cfg_file, self.proto_dhcp, self.proto_stat)
                print('Interface %s configured..' % i)
                sleep(1)
            if self.old_serv:
                backup_file(network)
                replace(network, self.old_serv, self.new_serv)
            # Hosts strings
            host_pattern = '%s%s%s %s.%s\n' % (valip, valtabs, self.old_serv,
                                               self.old_serv, domain)
            # hostfile replacements
            backup_file(hosts)
            for i in sorted(self.interfaces):
                ip = self.interfaces[i]['ip']
                host_record = '%s\t\t%s %s.%s\n' % (ip, self.new_serv,
                                                    self.new_serv, domain)
                replace(hosts, host_pattern, host_record)
            print("Restarting the network service...")
            if get_release() >= '7':
                subprocess.call(['systemctl', 'restart', 'network.service'])
            else:
                subprocess.call('start_udev')
                subprocess.call(['service', 'network', 'restart'])
        except Exception as e:
            sys.exit(e)


def config_interface(preconf, interface):
    """
    Function for configuring interface IP addresses.
    :param preconf:
    :param interface:
    :return:
    """
    print('\nConfiguring Interface: %s' % interface)
    while True:
        if preconf == 1:
            ip = vmconf[interface]['ip']
            clone.ip = raw_input('Primary IP Address[%s]: ' % ip) or ip
            if valid_ip(clone.ip):
                clone.new_ip = 'IPADDR=%s' % clone.ip
                break
        else:
            clone.ip = raw_input('Primary IP Address: ')
            if valid_ip(clone.ip):
                clone.new_ip = 'IPADDR=%s' % clone.ip
                break
    while True:
        if preconf == 1:
            nm = vmconf[interface]['nm']
            clone.nm = raw_input('Primary Netmask[%s]: ' % nm) or nm
            if valid_ip(clone.nm):
                clone.new_nm = 'NETMASK=%s' % clone.nm
                break
        else:
            clone.nm = raw_input('Primary Netmask: ')
            if valid_ip(clone.nm):
                clone.new_nm = 'NETMASK=%s' % clone.nm
                break
    # Calculate Gateway based on IP & Netmask
    prcidr = sum([bin(int(x)).count('1') for x in clone.nm.split('.')])
    if clone.runmode == 0:
        clone.gw = IPNetwork('%s/%s' % (clone.ip, prcidr))[1].format()
        while True:
            clone.gw = raw_input('Primary Gateway IP[%s]: '
                                 % clone.gw) or clone.gw
            if valid_ip(clone.gw):
                clone.new_gw = 'GATEWAY=%s' % clone.gw
                break
    else:
        while True:
            if preconf == 1:
                gw = vmconf[interface]['gw']
                clone.gw = raw_input('Primary Gateway IP[%s]: '
                                       % gw) or gw
                if valid_ip(clone.gw):
                    clone.new_gw = 'GATEWAY=%s' % clone.gw
                    break
            else:
                clone.gw = raw_input('Primary Gateway IP: ')
                if valid_ip(clone.gw):
                    clone.new_gw = 'GATEWAY=%s' % clone.gw
                    break
    clone.interfaces[interface] = {'ip': clone.ip,
                                   'nm': clone.nm,
                                   'gw': clone.gw}


def main(preconf):
    clone.set_hostname()
    # while True:
    for i in sorted(get_interfaces()):
        config_interface(preconf, i)
    print("\n" * 2 + "Saving configuration..")
    sleep(1)
    with open(script_path + '/vmconf.json', 'w') as j:
        json.dump(clone.interfaces, j, sort_keys=True,
                  indent=4, separators=(',', ': '))
    clone.show_settings()
    clone.confirm_settings()


if __name__ == "__main__":
    try:
        from netaddr import IPNetwork
    except ImportError:
        print('Installing python-netaddr library..')
        netmod = subprocess.Popen(['yum', 'install', 'python-netaddr', '-y'],
                                  stdout=DEVNULL, stderr=subprocess.STDOUT)
        if netmod.wait() == 0:
            from netaddr import IPNetwork
        else:
            minimal_mode = 1
    os.system("clear")
    if not os.geteuid() == 0:
        sys.exit("\nOnly root can run this script\n")
    if len(sys.argv) == 2:
        if sys.argv[1] == 'check':
            if minimal_mode == 0:
                if dependency_check():
                    get_nameservers()
                    get_ntpservers()
            else:
                raw_input('Unable to perform \'check\'\nPress the \'any\' key'
                          'to exit.')
                sys.exit()
        elif sys.argv[1] == 'clone':
            clone = ServerClone(minimal_mode)
            try:
                with open('vmconf.json', 'r') as data:
                    print("Previous Configuration Detected. Loading...\n")
                    vmconf = json.load(data)
                    main(1)
            except IOError:
                main(2)
            print('\n\n' + ('=' * 45))
            print("Would you like to prepare the server for cloning?\n"
                  "Answering \'yes\' will do the following:\n"
                  "Remove:\n"
                  "/etc/ssh/ssh_host_*\n"
                  "/etc/sysconfig/network-scripts/ifcfg-eth*\n"
                  "udev 70-persistent-net.rules (CentOS 6 Only)\n"
                  ".. followed by a shutdown (halt)\n\n")
            clean = raw_input("Prepare to Clone? [y/N]")
            if clean.lower() == 'y':
                clean_shutdown('halt')
            else:
                pass
        else:
            show_usage()
    else:
        current_interfaces = get_interfaces()
        print("Current detected interfaces:\n")
        for c_interface in sorted(current_interfaces):
            interface_mac = current_interfaces[c_interface]['perm_address']
            print("%s - %s" % (c_interface, interface_mac))
        print('\n')
        interface_prompt = raw_input("Are the above interfaces correct?[Y/n]")
        if interface_prompt.lower() == 'y':
            show_usage()
        else:
            reset_prompt = raw_input("Remove udev rules/ssh_host/ifcfg files "
                                     "and reboot?[y/N]")
            if reset_prompt.lower() == 'y':
                clean_shutdown('reboot')
