#!/usr/bin/env python
"""
vmclone.py
----------
Re-Identify a cloned Linux Virtual Machine (Hostname & Networking)

See README.md for usage and more information
"""
__author__ = 'Blayne Campbell'
__date__ = '2014-01-29'
__version__ = '1.0.8'

import subprocess
import glob
import sys
import os
import re


#### Dependency check for required utilities #
def dependancy_check():
    d = subprocess.Popen(['which', 'ntpdate'])
    if d.wait() != 0:
        d = subprocess.Popen(['yum', 'install', 'ntpdate', '-y'])
        if d.wait() != 0:
            sys.exit("Problem while installing dependancy: ntpdate")
    d = subprocess.Popen(['which', 'nc'])
    if d.wait() != 0:
        d = subprocess.Popen(['yum', 'install', 'nc', '-y'])
        if d.wait() != 0:
            sys.exit("Problem while installing dependancy: nc")
    d = subprocess.Popen(['which', 'ntpd'])
    if d.wait() != 0:
        d = subprocess.Popen(['yum', 'install', 'ntp', '-y'])
        if d.wait() != 0:
            sys.exit("Problem while installing dependancy: ntp")

#### Import Settings #
try:
    from settings import *
except ImportError:
    sys.exit("Unable to import settings..\n"
             "Try re-naming example-settings.py to settings.py")

#### Validations #
valip = '\\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.)' \
        '{3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\b'
valmac = '\\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\\b'
valuuid = '\\b([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]' \
          '{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})\\b'
tabs = '\\b(\\t+)\\b'
yesno = '\\b((?i)yes|(?i)no)\\b'
#### Validations End #


def show_usage():
    print("\nUsage:\nclone: Re-identify this server (write networking files)")
    print("check: Show available Name servers and NTP servers\n")
    sys.exit('Try: %s <check|clone>\n' % sys.argv[0])


def curhost(lookup):
    """
    Find current hostname of system via /etc/sysconfig/network
    """
    cur = open(network)
    cur = cur.readlines()
    for i in cur:
        if lookup in i:
            host = i.split('=')[1]
            return host


def curmac(cfgfile):
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
    with open(cfgfile, 'r') as filein:
        filecont = filein.read()
    if re.search(pattern, filecont):
        filecont = (re.sub(pattern, subst, filecont))
        with open(cfgfile, 'w') as fileout:
            fileout.write(filecont)
    else:
        with open(cfgfile, 'a') as fileout:
            fileout.write('\n' + subst)


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
            replace(cfgfile, 'UUID=%s' % valuuid, 'UUID=%s' % newuuid)
        else:
            pass


def mac_repair(cfgfile, iface):
    """
    Replace MAC address with new from re-generated persistent
    :return:
    """
    if curmac(cfgfile) != findmac(iface):
        replace(cfgfile, 'HWADDR=%s' % valmac, 'HWADDR=%s' % findmac(iface))
        print("MAC Address for %s has been repaired. "
              "Restarting networking.." % iface)
        subprocess.call(['service', 'network', 'restart'])
    # Ensure the interface is enabld on boot:
    replace(cfgfile, 'ONBOOT=%s' % yesno, 'ONBOOT=yes')


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
        if val(ns):
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
    """
    Main Configuration Object
    """
    def __init__(self):
        self.old_serv = curhost('HOSTNAME')
        self.new_serv = None
        self.new_prmac = 'HWADDR=%s' % findmac('eth0')
        self.new_bkmac = 'HWADDR=%s' % findmac('eth1')
        self.oldip = 'IPADDR=%s' % valip
        self.oldnm = 'NETMASK=%s' % valip
        self.oldgw = 'GATEWAY=%s' % valip
        self.oldmac = 'HWADDR=%s' % valmac
        self.proto_dhcp = 'BOOTPROTO=dhcp'
        self.proto_stat = 'BOOTPROTO=none'
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
        print("Proposed Network Configuration\n"
              "------------------------------\n\n"
              "Host Name: %s\n\n"
              "Primary IP: %s\n"
              "Primary NM: %s\n"
              "Primary GW: %s\n\n"
              "Backup IP: %s\n"
              "Backup NM: %s\n"
              "Backup GW: %s\n\n"
              % (self.new_serv, self.prip, self.prnm, self.prgw,
                 self.bkip, self.bknm, self.bkgw))

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
                  "The configuration you have entered will be saved for "
                  "next time (see vmconf.py)\n")
            sys.exit()

    def commit_settings(self):
        """
        Write configuration files
        :return:
        """
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
            print("Restarting the network service...")
            subprocess.call(['service', 'network', 'restart'])
        except Exception as e:
            sys.exit(e)


def main(preconf):
    clone.set_hostname()
    while True:
        while True:
            if preconf == 1:
                clone.prip = raw_input('Primary IP Address[%s]: '
                                       % vmconf.prip) or vmconf.prip
                if val(clone.prip):
                    clone.new_prip = 'IPADDR=%s' % clone.prip
                    break
            else:
                clone.prip = raw_input('Primary IP Address: ')
                if val(clone.prip):
                    clone.new_prip = 'IPADDR=%s' % clone.prip
                    break
        while True:
            if preconf == 1:
                clone.prnm = raw_input('Primary Netmask[%s]: '
                                       % vmconf.prnm) or vmconf.prnm
                if val(clone.prnm):
                    clone.new_prnm = 'NETMASK=%s' % clone.prnm
                    break
            else:
                clone.prnm = raw_input('Primary Netmask: ')
                if val(clone.prnm):
                    clone.new_prnm = 'NETMASK=%s' % clone.prnm
                    break
        # Calculate Gateway based on IP & Netmask
        prcidr = sum([bin(int(x)).count('1') for x in clone.prnm.split('.')])
        clone.prgw = IPNetwork('%s/%s' % (clone.prip, prcidr))[1].format()
        while True:
            clone.prgw = raw_input('Primary Gateway IP[%s]: '
                                   % clone.prgw) or clone.prgw
            if val(clone.prgw):
                clone.new_prgw = 'GATEWAY=%s' % clone.prgw
                break
        while True:
            if preconf == 1:
                clone.bkip = raw_input('Backup IP Address[%s]: '
                                       % vmconf.bkip) or vmconf.bkip
                if val(clone.bkip):
                    clone.new_bkip = 'IPADDR=%s' % clone.bkip
                    break
            else:
                clone.bkip = raw_input('Backup IP Address: ')
                if val(clone.bkip):
                    clone.new_bkip = 'IPADDR=%s' % clone.bkip
                    break
        while True:
            if preconf == 1:
                clone.bknm = raw_input('Backup Netmask[%s]: '
                                       % vmconf.bknm) or vmconf.bknm
                if val(clone.bknm):
                    clone.new_bknm = 'NETMASK=%s' % clone.bknm
                    break
            else:
                clone.bknm = raw_input('Backup Netmask: ')
                if val(clone.bknm):
                    clone.new_bknm = 'NETMASK=%s' % clone.bknm
                    break
        # Calculate Gateway based on IP & Netmask
        bkcidr = sum([bin(int(x)).count('1') for x in clone.bknm.split('.')])
        clone.bkgw = IPNetwork('%s/%s' % (clone.bkip, bkcidr))[1].format()
        while True:
            clone.bkgw = raw_input('Backup Gateway IP[%s]: '
                                   % clone.bkgw) or clone.bkgw
            if val(clone.bkgw):
                clone.new_bkgw = 'GATEWAY=%s' % clone.bkgw
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
        get_nameservers(write=True)
        clone.set_ntpservers()
        break

if __name__ == "__main__":
    mac_repair(p_ifcfg, 'eth0')
    mac_repair(b_ifcfg, 'eth1')
    try:
        from netaddr import IPNetwork
    except ImportError:
        netmod = subprocess.Popen(['yum', 'install', 'python-netaddr', '-y'])
        if netmod.wait() == 0:
            from netaddr import IPNetwork
        else:
            sys.exit("Problem while installing dependancy: python-netaddr")
    dependancy_check()
    os.system("clear")
    if not os.geteuid() == 0:
        sys.exit("\nOnly root can run this script\n")
    if len(sys.argv) == 2:
        if sys.argv[1] == 'check':
            get_nameservers()
            get_ntpservers()
        elif sys.argv[1] == 'clone':
            clone = ServerClone()
            try:
                with open('vmconf.py'):
                    print("Previous Configuration Detected. Loading...\n")
                    import vmconf
                    main(1)
            except IOError:
                main(2)
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
