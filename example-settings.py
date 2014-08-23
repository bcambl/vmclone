#### Development/Test Variables #
domain = 'example.com'
hosts = 'test_files/hosts-sample'  # hosts
network = 'test_files/network-sample'  # network
p_ifcfg = 'test_files/p_ifcfg-sample'  # ifcfg-eth0
b_ifcfg = 'test_files/b_ifcfg-sample'  # ifcfg-eth1
persistent = 'test_files/persistent-sample'  # 70-persistent-net.rules
resolvconf = 'test_files/resolv-sample'  # resolve.conf
#### Development End #

#### Production Variables #
# domain = 'example.com'
# hosts = '/etc/hosts'
# network = '/etc/sysconfig/network'
# p_ifcfg = '/etc/sysconfig/network-scripts/ifcfg-eth0'
# b_ifcfg = '/etc/sysconfig/network-scripts/ifcfg-eth1'
# persistent = '/etc/udev/rules.d/70-persistent-net.rules'
# resolvconf = '/etc/resolv.conf'  # resolve.conf

#### Production End #

#### List of possible nameservers #
nameservers = ['4.4.4.4',  # google
               '8.8.8.8',  # google
               '208.67.222.222',  # opendns
               '208.67.220.220']  # opendns
#### Nameservers End #