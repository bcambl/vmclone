#!/usr/bin/env python
__description__ = """
This script assists with cloning Linux Virtual Machines.

Assumptions:
-----------
- Linux distribution is CentOS/RHEL 5/6 (script may require tweaks for others)
- The virtual machine is configured with two interfaces (Primary & Backup)
- Default gateway on your network is the first available ip in the range

The following files will be modified:

- /etc/hosts - PRIMARY IP, BACKUP IP, HOSTNAME, DOMAIN
- /etc/sysconfig/network - HOSTNAME
- /etc/sysconfig/network-scripts/ifcfg-eth0 - IP, NETMASK, GATEWAY, MAC, UUID
- /etc/sysconfig/network-scripts/ifcfg-eth1 - IP, NETMASK, GATEWAY, MAC, UUID

Un-Identify Host for Cloning
----------------------------
You will be prompted whether you would like to un-identify the server and
shutdown. This will remove the following files:
- /etc/udev/rules.d/70-persistent-net.rules
- /etc/ssh/ssh_host_*
This will allow the system to re-generate the files upon next (re)boot.

"""
__author__ = 'Blayne Campbell'
__date__ = '2014-01-29'
__version__ = '1.0.5'

from netaddr import IPNetwork
from time import sleep
import subprocess
import glob
import sys
import os
import re

# Import Settings
from settings import *

#### Validations #
valip = '\\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.)' \
        '{3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\b'
valmac = '\\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\\b'
valuuid = '\\b([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]' \
          '{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})\\b'
tabs = '\\b(\\t+)\\b'
#### Validations End #


def show_usage():
    print("\nUsage:\nclone: Re-identify this server (write networking files)")
    print("check: Show available Name servers and NTP servers\n")
    sys.exit('Try: %s <check|clone>\n' % sys.argv[0])


def curhost(lookup):
    """
    Find Current Hostname of system via /etc/sysconfig/network
    """
    cur = open(network)
    cur = cur.readlines()
    for i in cur:
        if lookup in i:
            host = i.split('=')[1]
            return host


def findmac(iface):
    """
    Find MAC address of interface via /etc/udev/rules.d/70-persistent-net.rules
    """
    pnet = open(persistent)
    pnet = pnet.readlines()
    for i in pnet:
        if iface in i:
            mac = i.index('ATTR{address}==')
            mac = i[mac + 16:mac + 33]
            return mac.upper()


def val(ip):
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
    filein = open(cfgfile, 'r')
    filecont = filein.read()
    filein.close()
    filecont = (re.sub(pattern, subst, filecont))
    filein = open(cfgfile, 'w')
    filein.write(filecont)
    filein.close()


def genuuid(cfgfile):
    """
    Generate a new random UUID for ifcfg-<interface>
    """
    cfg = open(cfgfile)
    cfg = cfg.readlines()
    for i in cfg:
        if 'UUID' in i:
            newuuid = subprocess.Popen('uuidgen', stdout=subprocess.PIPE)
            newuuid = newuuid.stdout.readlines()[0].strip()
            replace(cfgfile, 'UUID="%s"' % valuuid, 'UUID="%s"' % newuuid)
        else:
            pass


def get_nameservers(write=None):
    print("\nChecking for available Name Servers..")
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
        if val(ns):
            r = subprocess.Popen(['ping', '-c', '1', '-w2', '%s' % ns],
                                 stdout=subprocess.PIPE)
            if r.wait() == 0:
                print('nameserver %s' % ns)
                if write:
                    with open(resolvconf, 'a') as f:
                        f.write('\nnameserver %s' % ns)
    if write:
        print("The above servers have been written to %s" % resolvconf)


def get_ntpservers(write=None):
    print("\nChecking for available NTP Servers..")
    if write:
        with open(ntpconf, 'r') as f:
            lines = f.readlines()
        with open(ntpconf, 'w') as f:
            for line in lines:
                if "server" in line:
                    pass
                else:
                    f.write(line)
    for ntp in ntpservers:
        r = subprocess.Popen(['ntpdate', '-u', '%s' % ntp],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        if r.wait() == 0:
            print('server %s' % ntp)
            if write:
                with open(ntpconf, 'a') as f:
                    f.write('\nserver %s' % ntp)
    if write:
        print("The above servers have been written to %s" % ntpconf)


def clean_shutdown():
    """
    Removes udev net rules and ssh host files that are automatically generated
    on boot.
    This ensures that any new servers cloned from this 'template' will
    have unique MAC addresses and ssh host keys.
    """
    print("deleting %s" % persistent)
    os.remove(persistent)
    for sshfile in glob.glob('/etc/ssh/ssh_host_*'):
        print("deleting %s" % sshfile)
        os.remove(sshfile)
    command = "/sbin/shutdown -h +1"
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output = process.communicate()[0]
    print(output)


class ServerClone:
    def __init__(self):
        self.old_serv = curhost('HOSTNAME')
        self.new_serv = None
        self.new_prmac = 'HWADDR="%s"' % findmac('eth0')
        self.new_bkmac = 'HWADDR="%s"' % findmac('eth1')
        self.oldip = 'IPADDR="%s"' % valip
        self.oldnm = 'NETMASK="%s"' % valip
        self.oldgw = 'GATEWAY="%s"' % valip
        self.oldmac = 'HWADDR="%s"' % valmac
        self.proto_dhcp = 'BOOTPROTO="dhcp"'
        self.proto_stat = 'BOOTPROTO="none"'
        self.prip = None
        self.bkip = None
        self.prnm = None
        self.prgw = None
        self.bknm = None
        self.bkgw = None
        self.new_prip = None
        self.new_prnm = None
        self.new_prgw = None
        self.new_bkip = None
        self.new_bknm = None
        self.new_bkgw = None

    def set_hostname(self):
        while not self.new_serv:
            self.new_serv = raw_input('Enter NEW Server Name: ')

    def show_settings(self):
        os.system('clear')
        print("Proposed Network Configuration\n"
              "------------------------------\n\n"
              "Host Name: %s\n\n"
              "Primary IP: %s\n"
              "Primary NM: %s\n"
              "Primary GW: %s\n\n"
              "Backup IP: %s\n"
              "Backup NM: %s\n"
              "Backup GW: %s\n\n"
              % (self.new_serv, self.prip, self.prnm, self.prnm,
                 self.bkip, self.bknm, self.bkgw))

    def confirm_settings(self):
        applyconf = raw_input("Would you like apply the above "
                              "configuration?[y/N]")
        if 'y' in applyconf:
            self.commit_settings()
        else:
            print("\nOK.. No changes have been made to this system.\n"
                  "The configuration you have entered will be saved for "
                  "next time (see vmconf.py)")
            sys.exit()

    def commit_settings(self):
        try:
            # Primary interface ifcfg
            replace(p_ifcfg, self.oldip, self.new_prip)
            replace(p_ifcfg, self.oldnm, self.new_prnm)
            replace(p_ifcfg, self.oldgw, self.new_prgw)
            replace(p_ifcfg, self.oldmac, self.new_prmac)
            replace(p_ifcfg, self.proto_dhcp, self.proto_stat)
            genuuid(p_ifcfg)
            # Backup interface ifcfg
            replace(b_ifcfg, self.oldip, self.new_bkip)
            replace(b_ifcfg, self.oldnm, self.new_bknm)
            replace(b_ifcfg, self.oldgw, self.new_bkgw)
            replace(b_ifcfg, self.oldmac, self.new_bkmac)
            replace(b_ifcfg, self.proto_dhcp, self.proto_stat)
            genuuid(b_ifcfg)
            # network file
            replace(network, self.old_serv, self.new_serv)
            # Hosts strings
            prhpat = '%s%s%s %s.%s\n' % (valip, tabs, self.old_serv,
                                         self.old_serv, domain)
            bkhpat = '%s%s%s-bkp\n' % (valip, tabs, self.old_serv)
            prhost = '%s\t\t%s %s.%s\n' % (self.prip, self.new_serv,
                                           self.new_serv, domain)
            bkhost = '%s\t\t%s-bkp\n' % (self.bkip, self.new_serv)
            # hostfile replacements
            replace(hosts, prhpat, prhost)
            replace(hosts, bkhpat, bkhost)
            # Restart the network service
            subprocess.Popen(['service', 'network', 'restart'])
            print("Wait 15 seconds while we restart the network service...")
            sleep(15)
        except Exception as e:
            sys.exit(e)


def main(preconf):
    clone = ServerClone()
    clone.set_hostname()
    while True:
        while True:
            if preconf == 1:
                clone.prip = raw_input('Primary IP Address[%s]: '
                                       % vmconf.prip) or vmconf.prip
                if val(clone.prip):
                    clone.new_prip = 'IPADDR="%s"' % clone.prip
                    break
            else:
                clone.prip = raw_input('Primary IP Address: ')
                if val(clone.prip):
                    clone.new_prip = 'IPADDR="%s"' % clone.prip
                    break
        while True:
            if preconf == 1:
                clone.prnm = raw_input('Primary Netmask[%s]: '
                                       % vmconf.prnm) or vmconf.prnm
                if val(clone.prnm):
                    clone.new_prnm = 'NETMASK="%s"' % clone.prnm
                    break
            else:
                clone.prnm = raw_input('Primary Netmask: ')
                if val(clone.prnm):
                    clone.new_prnm = 'NETMASK="%s"' % clone.prnm
                    break
        # Calculate Gateway based on IP & Netmask
        prcidr = sum([bin(int(x)).count('1') for x in clone.prnm.split('.')])
        clone.prgw = IPNetwork('%s/%s' % (clone.prip, prcidr))[1].format()
        while True:
            clone.prgw = raw_input('Primary Gateway IP[%s]: '
                                   % clone.prgw) or clone.prgw
            if val(clone.prgw):
                clone.new_prgw = 'GATEWAY="%s"' % clone.prgw
                break
        while True:
            if preconf == 1:
                clone.bkip = raw_input('Backup IP Address[%s]: '
                                       % vmconf.bkip) or vmconf.bkip
                if val(clone.bkip):
                    clone.new_bkip = 'IPADDR="%s"' % clone.bkip
                    break
            else:
                clone.bkip = raw_input('Backup IP Address: ')
                if val(clone.bkip):
                    clone.new_bkip = 'IPADDR="%s"' % clone.bkip
                    break
        while True:
            if preconf == 1:
                clone.bknm = raw_input('Backup Netmask[%s]: '
                                       % vmconf.bknm) or vmconf.bknm
                if val(clone.bknm):
                    clone.new_bknm = 'NETMASK="%s"' % clone.bknm
                    break
            else:
                clone.bknm = raw_input('Backup Netmask: ')
                if val(clone.bknm):
                    clone.new_bknm = 'NETMASK="%s"' % clone.bknm
                    break
        # Calculate Gateway based on IP & Netmask
        bkcidr = sum([bin(int(x)).count('1') for x in clone.bknm.split('.')])
        clone.bkgw = IPNetwork('%s/%s' % (clone.bkip, bkcidr))[1].format()
        while True:
            clone.bkgw = raw_input('Backup Gateway IP[%s]: '
                                   % clone.bkgw) or clone.bkgw
            if val(clone.bkgw):
                clone.new_bkgw = 'GATEWAY="%s"' % clone.bkgw
                break
        print("\n" * 2 + "Saving configuration (see vmconf.py)")
        with open('vmconf.py', 'w') as f:
            f.write('""" Rapid Deployment Server Configuration """' + '\n')
            f.write('\n')
            f.write('# Primary Interface (%s)' % p_ifcfg + '\n')
            f.write('prip = "%s"' % clone.prip + '  # Primary IP\n')
            f.write('prnm = "%s"' % clone.prnm + '  # Primary NetMask\n')
            f.write('prgw = "%s"' % clone.prgw + '  # Primary Gateway' + '\n')
            f.write('\n')
            f.write('# Backup Interface (%s)' % b_ifcfg + '\n')
            f.write('bkip = "%s"' % clone.bkip + '  # Backup IP\n')
            f.write('bknm = "%s"' % clone.bknm + '  # Backup NetMask\n')
            f.write('bkgw = "%s"' % clone.bkgw + '  # Backup Gateway\n')
            f.close()
        clone.show_settings()
        clone.confirm_settings()
        break

if __name__ == "__main__":
    os.system("clear")
    if not os.geteuid() == 0:
        sys.exit("\nOnly root can run this script\n")
    if len(sys.argv) == 2:
        if sys.argv[1] == 'check':
            get_nameservers()
            get_ntpservers()
        elif sys.argv[1] == 'clone':
            try:
                with open('vmconf.py'):
                    print("Previous Configuration Detected. Loading...\n")
                    import vmconf
                    main(1)
            except IOError:
                main(2)
            get_nameservers(write='yes')
            get_ntpservers(write='yes')
            clean = raw_input("Would you like to 'un-identify' the server"
                              " and shutdown? [y/N]")
            if 'y' in clean:
                clean_shutdown()
            else:
                pass
        else:
            show_usage()
    else:
        show_usage()
    print("Script exiting..")