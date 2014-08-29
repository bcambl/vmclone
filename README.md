# vmclone.py
This script assists with cloning Linux Virtual Machines.
(This script was written for CentOS/RHEL)

Assumptions:
-----------
- Linux distribution is CentOS/RHEL 5/6 (script may require tweaks for others)
- The virtual machine is configured with two interfaces (Primary & Backup)
- Default gateway on your network is the first available ip in the range

#### The following files will be modified:

/etc/hosts - PRIMARY IP, BACKUP IP, HOSTNAME, DOMAIN

/etc/sysconfig/network - HOSTNAME

/etc/sysconfig/network-scripts/ifcfg-eth0 - IP, NETMASK, GATEWAY, MAC, UUID

/etc/sysconfig/network-scripts/ifcfg-eth1 - IP, NETMASK, GATEWAY, MAC, UUID

/etc/ntp.conf - NTP SERVERS (ntp servers specified in settings)

/ect/resolv.conf - NAMESERVERS (nameservers specified in settings)


#### Un-Identify Host for Cloning

You will be prompted whether you would like to un-identify the server and
shutdown. This will remove the following files:

/etc/udev/rules.d/70-persistent-net.rules

/etc/ssh/ssh_host_*

This will allow the system to re-generate the files upon next (re)boot.

##### Usage Notes

```
# sudo ./vmclone.py <check|clone>
```

**Available parameters:**

*check* - Tests Nameservers and NTP servers outlined in settings (no files written)

*clone* - Prompts for new Hostname and IP information, Checks available nameservers
and ntp servers, writes configuration files, and prompts for un-identify/shutdown.



*The script requires root or sudo to execute.*

*Comment out the 'development' variables and uncomment the 'production' variables 
in the settings.py file*
