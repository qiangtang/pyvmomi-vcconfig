CONFIG_FILE_PATH = '/usr/local/data/config.ini'

VC_SECTION = 'vc_info'
DC_SECTION = 'dc_info'
CLUSTER_SECTION_PREFIX = 'cluster_info'
HOST_SECTION = 'host_info'
DVS_SECTION_PREFIX = 'dvs_info'
NFS_PREFIX = 'nfs_info'

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