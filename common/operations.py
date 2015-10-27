import vmwareapi
from pyVmomi import vim

VC_SECTION = 'vc_info'
DC_SECTION = 'dc_info'
CLUSTER_SECTION_PREFIX = 'cluster_info'
HOST_SECTION = 'host_info'
DVS_SECTION_PREFIX = 'dvs_info'
NFS_PREFIX = 'nfs_info'


def get_vcenter(cf):
    # Get VC Info
    vc_ip = cf.get(VC_SECTION, 'vc_ip')
    vc_user = cf.get(VC_SECTION, 'vc_user')
    vc_pwd = cf.get(VC_SECTION, 'vc_pwd')
    return vmwareapi.VirtualCenter(vc_ip, vc_user, vc_pwd)


def get_datacenter(vc, cf):
    # Get DC info
    dc_name = cf.get(DC_SECTION, 'dc')
    dc = vc.get_datacenter(dc_name)
    if dc is None:
        dc = vc.create_datacenter(dc_name)
    else:
        print 'Datacenter {} already exist.'.format(dc_name)
    return dc


def add_hosts_to_cluster(vc, dc, cf):
    # Get host accout info
    host_user = cf.get(HOST_SECTION, 'user')
    host_pwd = cf.get(HOST_SECTION, 'pwd')
    force_str = cf.get(HOST_SECTION, 'force')

    host_connect_spec = vim.host.ConnectSpec()
    host_connect_spec.userName = host_user
    host_connect_spec.password = host_pwd
    host_connect_spec.force = True
    if 'enable' != force_str.lower():
        host_connect_spec.force = False

    sections = cf.sections()
    all_hosts = vc.get_hosts()
    exist_hosts = []
    for host in all_hosts:
        exist_hosts.append(host.host_system.name)
    for section in sections:
        if section.startswith(CLUSTER_SECTION_PREFIX):
            # Get VC Cluster info
            cluster_name = cf.get(section, 'name')
            drs_flag = cf.get(section, 'drs').lower()
            ha_flag = cf.get(section, 'ha').lower()

            cluster = dc.get_cluster(cluster_name)
            if cluster is None:
                cluster = dc.create_cluster(cluster_name)
            print 'Cluster {} already exist'.format(cluster_name)

            if 'enable' == drs_flag:
                cluster.enable_drs()
            else:
                cluster.enable_drs(False)

            if 'enable' == ha_flag:
                cluster.enable_ha()
            else:
                cluster.enable_ha(False)

            target_hosts = cf.get(section, 'host_add_list')
            target_host_list = target_hosts.split(',')

            # Add hosts to the target cluster
            for host_name in target_host_list:
                host_name = host_name.strip()
                host_connect_spec.hostName = host_name
                # Only add non-exist hosts
                if host_name not in exist_hosts:
                    print 'Add host {} to VC cluster {}.'\
                        .format(host_name, cluster_name)
                    cluster.add_host(host_connect_spec)
                else:
                    print 'Host {} already exist in current VC'\
                        .format(host_name)


def config_hosts(vc, cf):
    # Get Host config info
    host_ntp = cf.get(HOST_SECTION, 'ntp')
    host_licensekey = cf.get(HOST_SECTION, 'license')
    host_ssh_flag = cf.get(HOST_SECTION, 'ssh')
    host_ssh = True
    if 'enable' != host_ssh_flag.lower():
        host_ssh = False
    # Config All Hosts
    all_hosts = vc.get_hosts()
    for host in all_hosts:
        host.enable_ssh(enable=host_ssh)
        host.enable_ntp(ntp=host_ntp)
        host.add_license(license_key=host_licensekey)


def create_dvs(vc, dc, cf):
    hosts = vc.get_hosts()
    sections = cf.sections()
    for section in sections:
        if section.startswith(DVS_SECTION_PREFIX):
            dvs_name = cf.get(section, 'name')
            target_hosts_str = cf.get(section, 'host_list')
            nic_index = int(cf.get(section, 'nic_item'))
            if '' != target_hosts_str:
                target_hosts = target_hosts_str.split(',')
                hosts = [vc.get_host_by_name(host_name.strip())
                         for host_name in target_hosts]

            dvs = dc.get_dvs_by_name(dvs_name)
            if dvs is None:
                dvs_spec = vim.DistributedVirtualSwitch.CreateSpec()
                dvs_config =\
                    vim.dvs.VmwareDistributedVirtualSwitch.ConfigSpec()
                dvs_config.name = dvs_name
                dvs_config.host =\
                    [get_host_member_spec(host, nic_index) for host in hosts]
                dvs_spec.configSpec = dvs_config
                dvs = dc.create_dvs(dvs_spec)
            else:
                dvs_config_spec = vim.DistributedVirtualSwitch.ConfigSpec()
                dvs_config = dvs.config()
                for host_mem in dvs_config.host:
                    host_name = host_mem.config.host.name
                    for host in hosts:
                        if host_name == host.host_system.name:
                            hosts.remove(host)
                if hosts:
                    dvs_config_spec.configVersion = dvs_config.configVersion
                    dvs_config_spec.host = [get_host_member_spec(
                        host, nic_index) for host in hosts]
                    dvs.reconfig_dvs(dvs_config_spec)
                else:
                    print 'All target hosts already in dvs {}'.format(dvs_name)

            pgs_pair = cf.get(section, 'pg_pair_list').split(',')
            for pg_pair in pgs_pair:
                pg_pair_list = pg_pair.split(':')
                pg_name = pg_pair_list[0]
                vlan_id = pg_pair_list[1]
                # create non-existing portgroup
                if dvs.get_portgroup(pg_name):
                    print 'PortGroup {} already exist'.format(pg_name)
                else:
                    dvs.add_portgroup(get_port_group_spec(pg_name, vlan_id))


def get_host_member_spec(host, nic_index):
    host_member_spec = vim.dvs.HostMember.ConfigSpec()
    host_member_spec.host = host.host_system
    host_member_spec.operation = vim.ConfigSpecOperation.add

    backing = vim.dvs.HostMember.PnicBacking()
    backing.pnicSpec = [vim.dvs.HostMember.PnicSpec(
        pnicDevice=host.host_system.config.network.pnic[nic_index].device)]
    host_member_spec.backing = backing

    return host_member_spec


def get_port_group_spec(pg_name, vlan_id):
    spec = vim.dvs.DistributedVirtualPortgroup.ConfigSpec()
    spec.name = pg_name
    spec.type = 'earlyBinding'
    spec.numPorts = 128
    port_config =\
        vim.dvs.VmwareDistributedVirtualSwitch.VmwarePortConfigPolicy()
    port_config.securityPolicy =\
        vim.dvs.VmwareDistributedVirtualSwitch.SecurityPolicy()
    port_config.securityPolicy.allowPromiscuous = vim.BoolPolicy(value=True)

    vlan_spec = vim.dvs.VmwareDistributedVirtualSwitch.VlanIdSpec()
    vlan_spec.vlanId = int(vlan_id)

    port_config.vlan = vlan_spec
    spec.defaultPortConfig = port_config
    return spec


def add_nfs_to_host(vc, cf):
    sections = cf.sections()
    for section in sections:
        if section.startswith(NFS_PREFIX):
            ds_name = cf.get(section, 'local_name')
            if vc.get_datastore(ds_name):
                print 'The datastore named {} already exist.'.format(ds_name)
            else:
                ds_spec = vim.host.NasVolume.Specification()
                ds_spec.localPath = ds_name
                ds_spec.remoteHost = cf.get(section, 'remote_host')
                ds_spec.remotePath = cf.get(section, 'remote_path')
                ds_spec.accessMode = "readWrite"
                host_name = cf.get(section, 'target_host')
                target_host = vc.get_host_by_name(host_name)
                if target_host:
                    target_host.add_nfs_datastore(ds_spec)
                else:
                    print 'Target host {} not exist in the current VC.'\
                        .format(host_name)