import ConfigParser
import operations

CONFIG_FILE_PATH = '/usr/local/data/config.ini'
VC_SECTION = 'vc_info'


def _get_vc():
    cf = ConfigParser.ConfigParser()
    cf.read(CONFIG_FILE_PATH)
    vc_ip = cf.get(VC_SECTION, 'vc_ip')
    vc_user = cf.get(VC_SECTION, 'vc_user')
    vc_pwd = cf.get(VC_SECTION, 'vc_pwd')
    return operations.get_vcenter(vc_ip, vc_user, vc_pwd)


def assign_role(args):
    vc = operations.get_vcenter(args.vc_ip, args.vc_user, args.vc_pwd)
    vc.assign_role(args.account, args.role)


def assign_role_parser(subparsers):
    parser = subparsers.add_parser(
        'assign-role',
        help='Assign global administrator role to the root account.'
    )
    parser.add_argument(
        '-i',
        '--ip',
        action='store',
        required=True,
        help='IP of target VC.',
        dest='vc_ip'
    )
    parser.add_argument(
        '-u',
        '--user',
        action='store',
        required=True,
        help='vSphere.local user of target VC.',
        dest='vc_user'
    )
    parser.add_argument(
        '-p',
        '--password',
        action='store',
        required=True,
        help='vSphere.local user password of target VC.',
        dest='vc_pwd'
    )
    parser.add_argument(
        '-a',
        '--account',
        action='store',
        required=True,
        help='Account the role to be assigned.',
        dest='account'
    )
    parser.add_argument(
        '-r',
        '--role',
        action='store',
        required=True,
        help='Role to be assigned to the account.',
        choices=['Admin', 'ReadOnly', 'View', 'NoAccess', 'Anonymous'],
        dest='role'
    )
    parser.set_defaults(func=assign_role)


def init_vc(args):
    cf = ConfigParser.ConfigParser()
    cf.read(CONFIG_FILE_PATH)
    cf.set(VC_SECTION, 'vc_ip', args.vc_ip)
    cf.set(VC_SECTION, 'vc_user', args.vc_user)
    cf.set(VC_SECTION, 'vc_pwd', args.vc_pwd)
    fh = open(CONFIG_FILE_PATH, 'w')
    cf.write(fh)
    fh.close()


def init_vc_parser(subparsers):
    parser = subparsers.add_parser(
        'init-vc',
        help='Init vc account info with vc ip, user name and password.'
    )
    parser.add_argument(
        '-i',
        '--ip',
        action='store',
        required=True,
        help='IP of target VC.',
        dest='vc_ip'
    )
    parser.add_argument(
        '-u',
        '--user',
        action='store',
        required=True,
        help='User of target VC.',
        dest='vc_user'
    )
    parser.add_argument(
        '-p',
        '--password',
        action='store',
        required=True,
        help='Password of target VC.',
        dest='vc_pwd'
    )
    parser.set_defaults(func=init_vc)


def add_dc(args):
    vc = _get_vc()
    dc_names = args.dc_names.strip().split(',')
    for dc_name in dc_names:
        operations.get_datacenter(vc, dc_name)


def add_dc_parser(subparsers):
    parser = subparsers.add_parser(
        'add-dc',
        help='Create Data Centers on VC if not exist.'
    )
    parser.add_argument(
        '--dc',
        action='store',
        required=True,
        help='Add Data Center by names. Separated by comma.',
        dest='dc_names'
    )
    parser.set_defaults(func=add_dc)


def add_cluster(args):
    vc = _get_vc()
    dc = operations.get_datacenter(vc, args.dc_name)
    cluster_names = args.cluster_names.strip().split(',')
    services = args.service_names
    for cluster_name in cluster_names:
        operations.create_cluster(dc, cluster_name.strip(), services)


def add_cluster_parser(subparsers):
    parser = subparsers.add_parser(
        'add-cluster',
        help='Create VC Clusters if not exist. Config services on clusters'
    )
    parser.add_argument(
        '--dc',
        action='store',
        required=True,
        help='Data Center Name that the clusters to be added.',
        dest='dc_name'
    )
    parser.add_argument(
        '--cluster',
        action='store',
        required=True,
        help='Cluster names to be added. Separated by comma.',
        dest='cluster_names'
    )
    parser.add_argument(
        '--service',
        action='store',
        help='[Optional] Service list enabled on cluster. '
             'E.g.drs,ha. Separated by comma.',
        default=None,
        dest='service_names'
    )
    parser.set_defaults(func=add_cluster)


def add_host(args):
    vc = _get_vc()
    dc = operations.get_datacenter(vc, args.dc_name)
    cluster = operations.create_cluster(dc, args.cluster_name)
    operations.add_hosts_to_cluster(vc, cluster, args.host_user, args.host_pwd,
                                    args.host_names)


def add_host_parser(subparsers):
    parser = subparsers.add_parser(
        'add-host',
        help='Add hosts to the target cluster.'
    )
    parser.add_argument(
        '--dc',
        action='store',
        required=True,
        help='Data Center Name that the cluster under.',
        dest='dc_name'
    )
    parser.add_argument(
        '--cluster',
        action='store',
        required=True,
        help='Cluster name the hosts to be added.',
        dest='cluster_name'
    )
    parser.add_argument(
        '--host',
        action='store',
        required=True,
        help='Host name list to be added. Support single ip/fqdn or '
             'ip-range. Separated by comma.',
        dest='host_names'
    )
    parser.add_argument(
        '--host-user',
        action='store',
        required=True,
        help='Host user name.',
        dest='host_user'
    )
    parser.add_argument(
        '--host-pwd',
        action='store',
        required=True,
        help='Host password',
        dest='host_pwd'
    )
    parser.set_defaults(func=add_host)


def config_host(args):
    vc = _get_vc()
    operations.config_hosts(vc, args.services, args.ntp, args.license)


def config_host_parser(subparsers):
    parser = subparsers.add_parser(
        'config-host',
        help='Config services on all hosts in VC.'
    )
    parser.add_argument(
        '--service',
        action='store',
        help='[Optional] Services on hosts.E.g. ssh. Separated by comma.',
        default=None,
        dest='services'
    )
    parser.add_argument(
        '--ntp',
        action='store',
        help='[Optional] Ntp config on hosts. Separated by comma.',
        default=None,
        dest='ntp'
    )
    parser.add_argument(
        '--license',
        action='store',
        help='[Optional] License key to be assigned to hosts',
        default=None,
        dest='license'
    )
    parser.set_defaults(func=config_host)


def add_nfs(args):
    vc = _get_vc()
    ds_name = args.local_name
    remote_host = args.remote_host
    remote_path = args.remote_path
    target_hosts = args.target_hosts
    operations.add_nfs_to_host(vc, remote_host, remote_path, ds_name,
                               target_hosts)


def add_nfs_parser(subparsers):
    parser = subparsers.add_parser(
        'add-nfs',
        help='Mount nfs datastore to targets hosts.'
    )
    parser.add_argument(
        '--ds-name',
        action='store',
        required=True,
        help='Local name of nfs datastore.',
        dest='ds_name'
    )
    parser.add_argument(
        '--remote-host',
        action='store',
        required=True,
        help='Remote host IP which the nfs on.',
        dest='remote_host'
    )
    parser.add_argument(
        '--remote-path',
        action='store',
        required=True,
        help='Remote folder path of the nfs.',
        dest='remote_path'
    )
    parser.add_argument(
        '--host',
        action='store',
        required=True,
        help='Target hosts the nfs mounted. Separated by comma.',
        dest='target_hosts'
    )
    parser.set_defaults(func=add_nfs)


def add_dvs(args):
    vc = _get_vc()
    dc = operations.get_datacenter(vc, args.dc_name)
    dvs_name = args.dvs_name
    target_hosts_str = args.target_hosts
    nic_index = args.nic_item
    pgs_pair = args.pg_pairs.split(',')
    operations.create_dvs(vc, dc, dvs_name, nic_index, target_hosts_str,
                          pgs_pair)


def add_dvs_parser(subparsers):
    parser = subparsers.add_parser(
        'add-dvs',
        help='Add dv switch to the target Data Center with port groups. '
             'Or config existing dv switch'
    )
    parser.add_argument(
        '--dc',
        action='store',
        required=True,
        help='Data Center Name.',
        dest='dc_name'
    )
    parser.add_argument(
        '--dvs',
        action='store',
        required=True,
        help='Dvs name',
        dest='dvs_name'
    )
    parser.add_argument(
        '--nic',
        action='store',
        type=int,
        required=True,
        help='Nic number used for hosts added. E.g. 1',
        dest='nic_item'
    )
    parser.add_argument(
        '--host',
        action='store',
        help='[Optional] Hosts added to the dvs. Ignore this if all hosts to '
             'be added. Separated by comma.',
        default=None,
        dest='target_hosts'
    )
    parser.add_argument(
        '--pg-pair',
        action='store',
        help='[Optional] Port group pairs to be added in the dvs. '
             '<pg_name:vlan_id> E.g. pg1:100. Separated by comma.',
        default=None,
        dest='pg_pairs'
    )
    parser.set_defaults(func=add_dvs)


def migrate(args):
    vc = _get_vc()
    vmotion_vm = args.vmotion_vm
    dest_host = args.dest_host
    dest_datastore = args.dest_datastore
    operations.vmotion(vc, vmotion_vm, dest_host, dest_datastore)


def vmotion_parser(subparsers):
    parser = subparsers.add_parser(
        'migrate',
        help='Migrate vm to target datastore on target host.'
    )
    parser.add_argument(
        '--vm',
        action='store',
        required=True,
        help='Target vm name to be migrated.',
        dest='vmotion_vm'
    )
    parser.add_argument(
        '--host',
        action='store',
        required=True,
        help='Target host the vm to be migrated',
        dest='dest_host'
    )
    parser.add_argument(
        '--datastore',
        action='store',
        required=True,
        help='Target datastore the vm to be migrated',
        dest='dest_datastore'
    )
    parser.set_defaults(func=migrate)
