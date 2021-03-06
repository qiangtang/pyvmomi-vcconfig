import commands
import re
import vmwareapi
from pyVmomi import vim
import utils


def get_vcenter(vc_ip, vc_user, vc_pwd):
    return vmwareapi.VirtualCenter(vc_ip, vc_user, vc_pwd)


def get_datacenter(vc, dc_name):
    # Get DC info
    dc = vc.get_datacenter_by_name(dc_name)
    if dc is None:
        dc = vc.create_datacenter(dc_name)
    else:
        print 'Datacenter {} already exist.'.format(dc_name)
    return dc


def create_cluster(dc, cluster_name, services_str=None):
    cluster = dc.get_cluster_by_name(cluster_name)
    if cluster is None:
        print 'Create VC Cluster {}.'.format(cluster_name)
        cluster = dc.create_cluster(cluster_name)
    if services_str:
        services = services_str.strip().lower().split(',')
        for service in services:
            service = service.strip()
            if service == 'drs':
                cluster.enable_drs()
                continue
            if service == 'ha':
                cluster.enable_ha()
                continue
    return cluster


def add_hosts_to_cluster(vc, cluster, host_user, host_pwd, host_names_str):
    # Get host accout info
    host_connect_spec = vim.host.ConnectSpec()
    host_connect_spec.userName = host_user
    host_connect_spec.password = host_pwd
    host_connect_spec.force = True
    all_hosts = vc.get_hosts()
    exist_hosts = []
    for host in all_hosts:
        exist_hosts.append(host.host_system.name)
    host_names = get_host_list(host_names_str)
    for host_name in host_names:
        host_name = host_name.strip()
        host_connect_spec.sslThumbprint = get_fingerprint(host_name)
        host_connect_spec.hostName = host_name
        # Only add non-exist hosts
        if host_name not in exist_hosts:
            print 'Add host {} to VC cluster {}.'.format(host_name,
                                                         cluster.name)
            cluster.add_host(host_connect_spec)
        else:
            print 'Host {} already exist in current VC'.format(host_name)


def get_fingerprint(host_name):
    cmd = "echo -n | openssl s_client -connect {}:443 2>/dev/null " \
          "| openssl x509 -noout -fingerprint -sha1"
    result = commands.getoutput(cmd.format(host_name)).split('=')
    return result[1] if result else None


def is_ip_range(range_str):
    reg_iprange = '^\d+\.\d+\.\d+\.\d+-\d+\.\d+\.\d+\.\d+$'
    result = re.match(reg_iprange, range_str)
    return True if result else False


def ip2num(ip):
    ip = [int(x) for x in ip.split('.')]
    return ip[0] << 24 | ip[1] << 16 | ip[2] << 8 | ip[3]


def num2ip(num):
    return '%s.%s.%s.%s' % ((num & 0xff000000) >> 24,
                            (num & 0x00ff0000) >> 16,
                            (num & 0x0000ff00) >> 8,
                            num & 0x000000ff)


def get_ips(ip_range):
    start, end = [ip2num(x) for x in ip_range.split('-')]
    return [num2ip(num) for num in range(start, end+1) if num & 0xff]


def get_host_list(host_names):
    target_host_list = host_names.split(',')
    host_names = []
    for host_name_str in target_host_list:
        host_name_str = host_name_str.strip()
        if is_ip_range(host_name_str):
            # Host IP range
            host_names.extend(get_ips(host_name_str))
        else:
            # Single Host IP
            host_names.append(host_name_str)
    return host_names


def config_hosts(vc, services_str, ntp=None, licensekey=None, fw_rule=None):
    # Config All Hosts
    services = utils.get_items(services_str)
    rules = utils.get_items(fw_rule)
    all_hosts = vc.get_hosts()
    for host in all_hosts:
        if ntp:
            host.enable_ntp(ntp=ntp)
        if licensekey:
            host.add_license(license_key=licensekey)
        for service in services:
            if service == 'ssh':
                host.enable_ssh()
                continue
            if service == 'vmotion':
                # Config default vMotion network
                host.config_vmotion()
                continue
        for rule in rules:
            host.config_firewall(rule)


def create_dvs(vc, dc, dvs_name, nic_index=1, target_hosts_str=None,
               pgs_pair=None):
    hosts = vc.get_hosts()
    if target_hosts_str and '' != target_hosts_str:
        host_names = get_host_list(target_hosts_str)
        hosts = [vc.get_host_by_name(host_name.strip())
                 for host_name in host_names]

    dvs = dc.get_dvs_by_name(dvs_name)
    if dvs is None:
        dvs_spec = vim.DistributedVirtualSwitch.CreateSpec()
        dvs_config = vim.dvs.VmwareDistributedVirtualSwitch.ConfigSpec()
        dvs_config.name = dvs_name
        dvs_config.host =\
            [get_host_member_spec(host, nic_index) for host in hosts]
        dvs_spec.configSpec = dvs_config
        print 'Create DVS {}.'.format(dvs_name)
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

    for pg_pair in pgs_pair:
        pg_pair_list = pg_pair.split(':')
        pg_name = pg_pair_list[0].strip()
        vlan_id = pg_pair_list[1].strip()
        # create non-existing portgroup
        if dvs.get_portgroup(pg_name):
            print 'PortGroup {} already exist in DVS {}'\
                .format(pg_name, dvs_name)
        else:
            print 'Add portgroup {} to DVS {}.'.format(pg_name, dvs_name)
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


def add_nfs_to_host(vc, remote_host, remote_path, ds_name, target_hosts):
    ds_spec = vim.host.NasVolume.Specification()
    ds_spec.localPath = ds_name
    ds_spec.remoteHost = remote_host
    ds_spec.remotePath = remote_path
    ds_spec.accessMode = "readWrite"
    hosts = get_host_list(target_hosts)
    for host_name in hosts:
        target_host = vc.get_host_by_name(host_name)
        if target_host:
            ds = target_host.get_datastore_by_name(ds_name)
            if ds is None:
                target_host.add_nfs_datastore(ds_spec)
            else:
                print 'Datastore {} already in host {}'.format(ds_name, host_name)
        else:
            print 'Target host {} not exist in the current VC.'\
                .format(host_name)


def call_func(instance, name, args=(), kwargs=None):
    if kwargs is None:
        kwargs = {}
    return getattr(instance, name)(*args, **kwargs)


def vmotion(dc, vm_reg, host_name, ds_name, concurrency=10):
    host = dc.get_host_by_name(host_name)
    ds = dc.get_datastore_by_name(ds_name)
    if host is None:
        print 'Host {} not exist on DC.'.format(host_name)
        exit(1)
    if ds is None:
        print 'Datastore {} not exist on DC.'.format(ds_name)
        exit(1)
    vms = dc.get_vms_by_regex(utils.get_items(vm_reg))
    vm_num = len(vms)
    import threadpool
    size = concurrency if concurrency < vm_num else vm_num
    pool = threadpool.ThreadPool(size)
    reqs = [threadpool.WorkRequest(call_func, args=(vm, 'migrate', (host, ds)))
            for vm in vms]
    for req in reqs:
        pool.putRequest(req)
    pool.wait()
    exit(0)


def cfg_esxi_service(vc, hosts, service, action):
    host_list = get_host_list(hosts)
    for host_name in host_list:
        host = vc.get_host_by_name(host_name)
        if host:
            host.config_services(service, action)
        else:
            print 'Host {} not exist in VC'.format(host_name)


def cfg_esxi_fw_rule(vc, hosts, rule, action):
    host_list = get_host_list(hosts)
    for host_name in host_list:
        host = vc.get_host_by_name(host_name)
        if host:
            host.config_firewall(rule, action)
        else:
            print 'Host {} not exist in VC'.format(host_name)


def cfg_esxi_vmotion(vc, hosts, nic_num=0):
    host_list = get_host_list(hosts)
    for host_name in host_list:
        host = vc.get_host_by_name(host_name)
        if host:
            host.config_vmotion(nic_num)
        else:
            print 'Host {} not exist in VC'.format(host_name)


def cfg_autostart(vc, host_name, vms):
    vm_list = [vm.strip() for vm in vms.strip().split(',')]
    host = vc.get_host_by_name(host_name)
    host.config_autostart(vm_list)


def remove_host_datastore(vc, host_name, datastores):
    host = vc.get_host_by_name(host_name)
    if host is None:
        print 'Host {} not exist in VC'.format(host_name)
        return
    dss = utils.get_items(datastores)
    dss_names = [ds.name() for ds in host.get_datastores()]
    for ds_name in dss:
        if ds_name not in dss_names:
            print 'Datastore {} not on host {}'.format(ds_name, host_name)
        else:
            ds = host.get_datastore_by_name(ds_name)
            host.remove_datastore(ds)


def remove_dc_datastore(vc, dc_name, datastores):
    dc = vc.get_datacenter_by_name(dc_name)
    if dc is None:
        print 'Data Center {} not found on VC'.format(dc_name)
        return
    target_names = utils.get_items(datastores)
    ds_names = [ds.name() for ds in dc.get_datastores()]
    target_names = [ds_name for ds_name in target_names if ds_name in ds_names]
    for ds_name in target_names:
        ds = dc.get_datastore_by_name(ds_name)
        for host in ds.get_hosts():
            host.remove_datastore(ds)


def get_pg_id(vc, dc_name, vds_name, pg_name):
    dc = vc.get_datacenter_by_name(dc_name)
    if dc is None:
        print 'Data Center {} not found on VC'.format(dc_name)
        return None
    vds = dc.get_dvs_by_name(vds_name)
    if vds is None:
        print 'vDS {} not exist on data center {}'.format(vds_name, dc_name)
        return None
    pg = vds.get_portgroup(pg_name)
    if pg:
        return pg.key
    else:
        print 'Portgroup {} not exist on vds {}'.format(pg_name, vds_name)
        return None