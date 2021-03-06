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


# VM site operations
def migrate(args):
    vc = _get_vc()
    dc = vc.get_datacenter_by_name(args.dc)
    if dc is None:
        print 'Data center {} not exist on VC'.format(args.dc)
        exit(1)
    operations.vmotion(dc, args.vm_reg, args.host, args.ds, args.concurrency)


def migrate_parser(subparsers):
    parser = subparsers.add_parser(
        'vm-migrate',
        help='Migrate vm to target datastore on target host.'
    )
    parser.add_argument(
        '--dc',
        action='store',
        required=True,
        help='Data center name',
        dest='dc'
    )
    parser.add_argument(
        '--vm-reg',
        action='store',
        required=True,
        help='Regular list of target vm name to be migrated. Separated by comma.',
        dest='vm_reg'
    )
    parser.add_argument(
        '--host',
        action='store',
        required=True,
        help='Target host the vm to be migrated',
        dest='host'
    )
    parser.add_argument(
        '--ds',
        action='store',
        required=True,
        help='Target datastore the vm to be migrated',
        dest='ds'
    )
    parser.add_argument(
        '--concurrency',
        action='store',
        type=int,
        help='[Optional] Concurrency number of migrate task '
             '10 by default.',
        default=10,
        dest='concurrency'
    )
    parser.set_defaults(func=migrate)


def power(args):
    vc = _get_vc()
    vm_names = utils.get_items(args.vm_names)
    vms = vc.get_vms_by_regex(vm_names, args.folder)
    for vm in vms:
        vm.power(args.action)


def power_parser(subparsers):
    parser = subparsers.add_parser(
        'vm-power',
        help='Power on/off target vms defined by regular or name.'
    )
    parser.add_argument(
        '--vm',
        action='store',
        required=True,
        help='Regular or name list of target vms. Separated by comma.',
        dest='vm_names'
    )
    parser.add_argument(
        '--action',
        action='store',
        required=True,
        help='Action for power status change. on/off',
        choices=['on', 'off'],
        dest='action'
    )
    parser.add_argument(
        '--folder',
        action='store',
        help='[Optional] Folder name where the vm inside. '
             'Find from root folder by default.',
        default=None,
        dest='folder'
    )
    parser.set_defaults(func=power)


def reset(args):
    vc = _get_vc()
    vm_names = args.vm_name.strip().split(',')
    for vm_name in vm_names:
        print 'Reset vm ' + vm_name
        vm = vc.get_vm_by_name(vm_name.strip(), args.folder)
        vm.reset()


def reset_parser(subparsers):
    parser = subparsers.add_parser(
        'vm-reset',
        help='Reset (power off then on) target vm from VC site.'
    )
    parser.add_argument(
        '--vm',
        action='store',
        required=True,
        help='Target vm name list. Separated by comma.',
        dest='vm_name'
    )
    parser.add_argument(
        '--folder',
        action='store',
        help='[Optional] Folder name where the vm inside. '
             'Find from root folder by default.',
        default=None,
        dest='folder'
    )
    parser.set_defaults(func=reset)


def reboot(args):
    vc = _get_vc()
    vm_names = args.vm_name.strip().split(',')
    for vm_name in vm_names:
        print 'Reboot vm ' + vm_name
        vm = vc.get_vm_by_name(vm_name.strip(), args.folder)
        vm.rebootvm()


def reboot_parser(subparsers):
    parser = subparsers.add_parser(
        'vm-reboot',
        help='Reboot target vm from OS site.'
    )
    parser.add_argument(
        '--vm',
        action='store',
        required=True,
        help='Target vm name list. Separated by comma.',
        dest='vm_name'
    )
    parser.add_argument(
        '--folder',
        action='store',
        help='[Optional] Folder name where the vm inside. '
             'Find from root folder by default.',
        default=None,
        dest='folder'
    )
    parser.set_defaults(func=reboot)


def snapshot(args):
    vc = _get_vc()
    vm_names = args.vm_name.strip().split(',')
    for vm_name in vm_names:
        print 'Snapshot vm ' + vm_name
        vm = vc.get_vm_by_name(vm_name.strip(), args.folder)
        vm.snapshot(args.snap_name)


def snapshot_parser(subparsers):
    parser = subparsers.add_parser(
        'vm-snap',
        help='Create a snapshot with the given name on target vm.'
    )
    parser.add_argument(
        '--vm',
        action='store',
        required=True,
        help='Target vm name list. Separated by comma.',
        dest='vm_name'
    )
    parser.add_argument(
        '--name',
        action='store',
        required=True,
        help='Snapshot name.',
        dest='snap_name'
    )
    parser.add_argument(
        '--folder',
        action='store',
        help='[Optional] Folder name where the vm inside. '
             'Find from root folder by default.',
        default=None,
        dest='folder'
    )
    parser.set_defaults(func=snapshot)


def destroy(args):
    vc = _get_vc()
    vm_lists = utils.get_items(args.vm_names)
    vms = []
    if args.path is None:
        vms = vc.get_vms_by_regex(vm_lists)
    else:
        items = utils.get_items(args.path, '/')
        len_path = len(items)
        dc = vc.get_datacenter_by_name(items[0])
        if dc is None:
            exit(1)
        if len_path == 1:
            vms = dc.get_vms_by_regex(vm_lists)
        elif len_path == 2:
            cluster = dc.get_cluster_by_name(items[1])
            if cluster is None:
                exit(1)
            hosts = cluster.get_hosts()
            for host in hosts:
                vms.extend(host.get_vms_by_regex(vm_lists))
        elif len_path == 3:
            cluster = dc.get_cluster_by_name(items[1])
            if cluster is None:
                exit(1)
            rp = cluster.get_resourcepool_by_name(items[2])
            if rp is None:
                exit(1)
            vms.extend(rp.get_vms_by_regex(vm_lists))
    for vm in vms:
        print 'Delete vm ' + vm.name()
        vm.destroy()


def destroy_parser(subparsers):
    parser = subparsers.add_parser(
        'vm-destroy',
        help='Delete the target vm from disk.'
    )
    parser.add_argument(
        '--vm',
        action='store',
        required=True,
        help='Target vm name/regular list. Separated by comma.',
        dest='vm_names'
    )
    parser.add_argument(
        '--path',
        action='store',
        help='[Optional] Resource path where the vm inside. '
             'DataCenter/Cluster/ResourcePool.',
        default=None,
        dest='path'
    )
    parser.set_defaults(func=destroy)


def unregister(args):
    vc = _get_vc()
    vm_names = args.vm_name.strip().split(',')
    for vm_name in vm_names:
        print 'Unregister vm ' + vm_name
        vm = vc.get_vm_by_name(vm_name.strip(), args.folder)
        vm.unregister()


def unregister_parser(subparsers):
    parser = subparsers.add_parser(
        'vm-unregister',
        help='Remove the target vm from inventory site.'
    )
    parser.add_argument(
        '--vm',
        action='store',
        required=True,
        help='Target vm name list. Separated by comma.',
        dest='vm_name'
    )
    parser.add_argument(
        '--folder',
        action='store',
        help='[Optional] Folder name where the vm inside. '
             'Find from root folder by default.',
        default=None,
        dest='folder'
    )
    parser.set_defaults(func=unregister)


def clone(args):
    vc = _get_vc()
    print 'Clone vm {} from {}'.format(args.clone_name, args.vm_name)
    vm = vc.get_vm_by_name(args.vm_name.strip(), args.src_folder)
    vm.clone(args.clone_name.strip())


def clone_parser(subparsers):
    parser = subparsers.add_parser(
        'vm-clone',
        help='Clone a new vm from the source vm. '
             'Same location and resources using as the source VM.'
    )
    parser.add_argument(
        '--vm',
        action='store',
        required=True,
        help='Source vm which the new vm cloned from.',
        dest='vm_name'
    )
    parser.add_argument(
        '--name',
        action='store',
        required=True,
        help='Name of the new created vm.',
        dest='clone_name'
    )
    parser.add_argument(
        '--src-folder',
        action='store',
        help='[Optional] Folder name where the source vm inside. '
             'Find from root folder by default.',
        default=None,
        dest='src_folder'
    )
    parser.set_defaults(func=clone)


def delete_file(args):
    vc = _get_vc()
    vm_name = args.vm_name.strip()
    vm = None
    if args.vm_path is not None:
        items = utils.get_items(args.vm_path, '/')
        dc = vc.get_datacenter_by_name(items[0])
        if dc:
            cluster = dc.get_cluster_by_name(items[1])
            if cluster:
                vm = cluster.get_vm_by_name(vm_name)
        if vm is None:
            print 'VM {} not exist under the path {}'.format(vm_name, args.vm_path)
            exit(1)
    else:
        vm = vc.get_vm_by_name(vm_name)
    if vm:
        if vm.search_file(args.file_name):
            vm.delete_file(args.file_name)
        exit(0)
    else:
        print 'File {} not exist on VM {}'.format(args.file_name, vm_name)
        exit(1)


def delete_file_parser(subparsers):
    parser = subparsers.add_parser(
        'vm-del-file',
        help='Delete the target file of the given VM'
    )
    parser.add_argument(
        '--vm',
        action='store',
        required=True,
        help='Name of target VM.',
        dest='vm_name'
    )
    parser.add_argument(
        '--file',
        action='store',
        required=True,
        help='Name of target file to be deleted.',
        dest='file_name'
    )
    parser.add_argument(
        '--vm-path',
        action='store',
        help='[Optional] VM path as DataCenter/Cluster on VC. '
             'Find from VC global by default.',
        default=None,
        dest='vm_path'
    )
    parser.set_defaults(func=delete_file)


def path(args):
    vc = _get_vc()
    vm = vc.get_vm_by_name(args.vm_name.strip(), args.src_folder)
    if vm:
        host_name = vm.get_host().name()
        path_str = vm.vm.config.files.logDirectory
        path_str = path_str.replace(' ', '').replace('[', '/').replace(']', '/')
        vm_path = '{}:/vmfs/volumes{}'.format(host_name, path_str)
        print vm_path
        exit(0)
    else:
        print 'VM {} not exist on vc'.format(args.vm_name)
        exit(1)


def path_parser(subparsers):
    parser = subparsers.add_parser(
        'vm-path',
        help='Get the vm folder path on ESXi. Return as <host>:/<vm_path>'
    )
    parser.add_argument(
        '--vm',
        action='store',
        required=True,
        help='Name of target VM.',
        dest='vm_name'
    )
    parser.add_argument(
        '--src-folder',
        action='store',
        help='[Optional] Folder name where the target vm inside on VC. '
             'Find from root folder by default.',
        default=None,
        dest='src_folder'
    )
    parser.set_defaults(func=path)