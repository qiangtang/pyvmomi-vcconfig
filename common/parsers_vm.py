import ConfigParser
import operations
import utils


def _get_vc():
    cf = ConfigParser.ConfigParser()
    cf.read(utils.CONFIG_FILE_PATH)
    vc_ip = cf.get(utils.VC_SECTION, 'vc_ip')
    vc_user = cf.get(utils.VC_SECTION, 'vc_user')
    vc_pwd = cf.get(utils.VC_SECTION, 'vc_pwd')
    return operations.get_vcenter(vc_ip, vc_user, vc_pwd)


# VM site operations
def migrate(args):
    vc = _get_vc()
    vmotion_vm = args.vmotion_vm
    dest_host = args.dest_host
    dest_datastore = args.dest_datastore
    operations.vmotion(vc, vmotion_vm, dest_host, dest_datastore, args.folder)


def migrate_parser(subparsers):
    parser = subparsers.add_parser(
        'vm-migrate',
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
    parser.add_argument(
        '--folder',
        action='store',
        help='[Optional] Folder name where the vm inside. '
             'Find from root folder by default.',
        default=None,
        dest='folder'
    )
    parser.set_defaults(func=migrate)


def power(args):
    vc = _get_vc()
    vm_names = args.vm_name.strip().split(',')
    for vm_name in vm_names:
        vm = vc.get_vm_by_name(vm_name.strip(), args.folder)
        vm.power(args.action)


def power_parser(subparsers):
    parser = subparsers.add_parser(
        'vm-power',
        help='Power on/off target vm.'
    )
    parser.add_argument(
        '--vm',
        action='store',
        required=True,
        help='Target vm name list. Separated by comma.',
        dest='vm_name'
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
    vm_names = args.vm_name.strip().split(',')
    for vm_name in vm_names:
        print 'Delete vm ' + vm_name
        vm = vc.get_vm_by_name(vm_name.strip(), args.folder)
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