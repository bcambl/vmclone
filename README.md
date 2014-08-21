# vmclone.py
This script assists with cloning Linux Virtual Machines.
(This script was written for CentOS/RHEL)

#### The following files will be modified:

/etc/hosts - PRIMARY IP, BACKUP IP, HOSTNAME, DOMAIN

/etc/sysconfig/network - HOSTNAME

/etc/sysconfig/network-scripts/ifcfg-eth0 - IP, NETMASK, GATEWAY, MAC, UUID

/etc/sysconfig/network-scripts/ifcfg-eth1 - IP, NETMASK, GATEWAY, MAC, UUID


#### Un-Identify Host for Cloning

You will be prompted whether you would like to un-identify the server and
shutdown. This will remove the following files:

/etc/udev/rules.d/70-persistent-net.rules

/etc/ssh/ssh_host_*

This will allow the system to re-generate the files upon next (re)boot.

##### Usage Notes

*The script requires root to execute.*

*Comment out the 'development' variables and uncomment the 'production' variables*
