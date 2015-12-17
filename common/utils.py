CONFIG_FILE_PATH = '/usr/local/data/config.ini'
SCHEDULAR_FILE_PATH = '/usr/local/data/monkey.ini'

VC_SECTION = 'vc_info'
DC_SECTION = 'dc_info'
CLUSTER_SECTION_PREFIX = 'cluster_info'
HOST_SECTION = 'host_info'
DVS_SECTION_PREFIX = 'dvs_info'
NFS_PREFIX = 'nfs_info'

SCH_PREFIX = 'sch_'
SCH_GLOBAL = 'global'

# Firewall rule on ESXi
# cmmds: Virtual SAN Clustering Services
RULES = ['httpClient', 'syslog', 'nfsClient', 'ntpClient',
         'sshServer', 'sshClient', 'faultTolerance', 'vMotion',
         'vsanvp', 'rabbitmqproxy', 'dhcp', 'dns', 'cmmds',
         'activeDirectoryAll', 'webAccess']

# Services on ESXi
SERVICES = ['TSM-SSH', 'ntpd', 'snmpd']

# Storage Type
DS_TYPE = ['VMFS', 'NFS', 'VSAN']

# VM Status
VM_STATUS = ['poweredOn', 'poweredOff', 'suspended']


def init_ssl():
    import ssl
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        # Legacy Python that doesn't verify HTTPS certificates by default
        pass
    else:
        # Handle target environment that doesn't support HTTPS verification
        ssl._create_default_https_context = _create_unverified_https_context


def get_items(items_str):
    items_list = items_str.strip().split(',')
    return [item.strip() for item in items_list]


def get_randstr(size):
    import string
    import random
    chars = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
             'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
    len_chars = len(chars)
    if size > len_chars:
        size = len_chars
    return string.join(random.sample(chars, size)).replace(" ", "")