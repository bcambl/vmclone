# vmclone.py
This is a script that I use for creating multiple virtual machines clones.
Create a minimal CentOS VM and clone this project to your /root directory. Now
shutdown the VM and clone. Once the new clone has booted, execute the script to 
change the hostname and IP addresses.

Assumptions:
-----------
- Linux distribution is CentOS/RHEL 6/7 (script may require tweaks for others)

#### The following files will be modified:

/etc/hosts - PRIMARY IP, BACKUP IP, HOSTNAME, DOMAIN

/etc/sysconfig/network - HOSTNAME

/etc/sysconfig/network-scripts/ifcfg-<interface> - IP, NETMASK, GATEWAY, MAC, UUID

/etc/ntp.conf - NTP SERVERS (ntp servers specified in settings)

/ect/resolv.conf - NAMESERVERS (nameservers specified in settings)


#### Un-Identify Host for Cloning

You will be prompted whether you would like to un-identify the server and
shutdown. This will remove the following files:

/etc/udev/rules.d/70-persistent-net.rules (CentOS 6)

/etc/ssh/ssh_host_*

This will allow the system to re-generate the files upon next (re)boot.

##### Usage Notes

```
# sudo ./vmclone.py <check|clone>
```

**Available parameters:**

*none* - Display current interface names and associated MAC addresses

*check* - Tests Nameservers and NTP servers outlined in settings (no files written)

*clone* - Prompts for new Hostname and IP information, Checks available nameservers
and ntp servers, writes configuration files, and prompts for un-identify/shutdown.



*The script requires root or sudo to execute.*

*Comment out the 'development' variables and uncomment the 'production' variables 
in the settings.py file*
