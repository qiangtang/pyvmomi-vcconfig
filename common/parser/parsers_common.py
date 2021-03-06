import ConfigParser
from common import operations
from common import utils


def _get_vc():
    cf = ConfigParser.ConfigParser()
    cf.read(utils.CONFIG_FILE_PATH)
    vc_ip = cf.get(utils.INFO_VC, 'opt_vc')
    vc_user = cf.get(utils.INFO_VC, 'vc_user')
    vc_pwd = cf.get(utils.INFO_VC, 'vc_pwd')
    return operations.get_vcenter(vc_ip, vc_user, vc_pwd)


# VC site operations
def assign_role(args):
    vc = operations.get_vcenter(args.vc_ip, args.vc_user, args.vc_pwd)
    vc.assign_role(args.account, args.role)


def assign_role_parser(subparsers):
    parser = subparsers.add_parser(
        'assign-role',
        help='Assign role to the target account.'
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
    cf.read(utils.CONFIG_FILE_PATH)
    cf.set(utils.INFO_VC, 'opt_vc', args.vc_ip)
    cf.set(utils.INFO_VC, 'vc_user', args.vc_user)
    cf.set(utils.INFO_VC, 'vc_pwd', args.vc_pwd)
    fh = open(utils.CONFIG_FILE_PATH, 'w')
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


# DC site operations
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
        help='[Optional] Hosts added to the dvs. Support single ip/fqdn or '
             'ip-range. Ignore this if all hosts to be added. '
             'Separated by comma.',
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


# Cluster site operations
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


# Host site operations
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


def remove_datastore(args):
    vc = _get_vc()
    operations.remove_dc_datastore(vc, args.dc, args.dss)


def remove_datastore_parser(subparsers):
    parser = subparsers.add_parser(
        'remove-ds',
        help='Remove datastore from the target data center.'
    )
    parser.add_argument(
        '--dc',
        action='store',
        required=True,
        help='Target data center name',
        dest='dc'
    )
    parser.add_argument(
        '--ds',
        action='store',
        required=True,
        help='Name list of datastores to be removed. Separated by comma.',
        dest='dss'
    )
    parser.set_defaults(func=remove_datastore)


def power_vapp(args):
    vc = _get_vc()
    regular_list = utils.get_items(args.vapp_names)
    vapps = vc.get_vapps_by_regex(regular_list)
    for vapp in vapps:
        if args.action == 'on':
            vapp.poweron()
        else:
            vapp.poweroff()


def power_vapp_parser(subparsers):
    parser = subparsers.add_parser(
        'vapp-power',
        help='Power on/off target vapp.'
    )
    parser.add_argument(
        '--vapp',
        action='store',
        required=True,
        help='Regular list of the target vapp name. Separated by comma.',
        dest='vapp_names'
    )
    parser.add_argument(
        '--action',
        action='store',
        required=True,
        help='Action for power status change. on/off',
        choices=['on', 'off'],
        dest='action'
    )
    parser.set_defaults(func=power_vapp)


def destroy_vapp(args):
    vc = _get_vc()
    regular_list = utils.get_items(args.vapp_names)
    vapps = vc.get_vapps_by_regex(regular_list)
    for vapp in vapps:
        vapp.destroy()


def destroy_vapp_parser(subparsers):
    parser = subparsers.add_parser(
        'vapp-destroy',
        help='Destroy target vapp.'
    )
    parser.add_argument(
        '--vapp',
        action='store',
        required=True,
        help='Regular list of the target vapp name. Separated by comma.',
        dest='vapp_names'
    )
    parser.set_defaults(func=destroy_vapp)


def rename(args):
    vc = _get_vc()
    if args.type == 'vapp':
        vapp = vc.get_vapp_by_name(args.name)
        if vapp:
            vapp.rename(args.new_name)
    elif args.type == 'vm':
        vm = vc.get_vm_by_name(args.name)
        if vm:
            vm.rename(args.new_name)


def rename_parser(subparsers):
    parser = subparsers.add_parser(
        'rename',
        help='Rename the target object.'
    )
    parser.add_argument(
        '--type',
        action='store',
        required=True,
        help='Object type of target. e.g. vapp, vm',
        choices=utils.OBJ_TYPE,
        dest='type'
    )
    parser.add_argument(
        '--name',
        action='store',
        required=True,
        help='Name of the target object',
        dest='name'
    )
    parser.add_argument(
        '--new',
        action='store',
        required=True,
        help='Mew name of the target object',
        dest='new_name'
    )
    parser.set_defaults(func=rename)