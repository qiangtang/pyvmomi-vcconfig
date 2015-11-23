import ConfigParser
from common import operations
from common import utils


def _get_vc():
    cf = ConfigParser.ConfigParser()
    cf.read(utils.CONFIG_FILE_PATH)
    vc_ip = cf.get(utils.VC_SECTION, 'vc_ip')
    vc_user = cf.get(utils.VC_SECTION, 'vc_user')
    vc_pwd = cf.get(utils.VC_SECTION, 'vc_pwd')
    return operations.get_vcenter(vc_ip, vc_user, vc_pwd)


def config_service(args):
    vc = _get_vc()
    operations.cfg_esxi_service(vc, args.hosts, args.service, args.action)


def config_service_parser(subparsers):
    parser = subparsers.add_parser(
        'host-service',
        help='Start/stop service on target host.'
    )
    parser.add_argument(
        '--host-name',
        action='store',
        required=True,
        help='Target host list. Support single ip/fqdn or ip-range. '
             'Separated by comma',
        dest='hosts'
    )
    parser.add_argument(
        '--action',
        action='store',
        required=True,
        help='Action for the service. start/stop',
        choices=['start', 'stop'],
        dest='action'
    )
    parser.add_argument(
        '--service',
        action='store',
        required=True,
        help='Service to be config',
        choices=utils.SERVICES,
        dest='service'
    )
    parser.set_defaults(func=config_service)


def config_rule(args):
    vc = _get_vc()
    operations.cfg_esxi_fw_rule(vc, args.hosts, args.rule, args.action)


def config_rule_parser(subparsers):
    parser = subparsers.add_parser(
        'host-rule',
        help='Enable/disable firewall rule on target host.'
    )
    parser.add_argument(
        '--host-name',
        action='store',
        required=True,
        help='Target host list. Support single ip/fqdn or ip-range. '
             'Separated by comma',
        dest='hosts'
    )
    parser.add_argument(
        '--action',
        action='store',
        required=True,
        help='Action for the rule. enable/disable',
        choices=['enable', 'disable'],
        dest='action'
    )
    parser.add_argument(
        '--rule',
        action='store',
        required=True,
        help='Rule to be config',
        choices=utils.RULES,
        dest='rule'
    )
    parser.set_defaults(func=config_rule)


def maintenance(args):
    vc = _get_vc()
    host = vc.get_host_by_name(args.host_name.strip())
    host.maintenance(args.action)


def maintenance_parser(subparsers):
    parser = subparsers.add_parser(
        'host-maintain',
        help='Enter/exit maintenance mode on target host.'
    )
    parser.add_argument(
        '--host',
        action='store',
        required=True,
        help='Name of host to enter/exit maintenance mode',
        dest='host_name'
    )
    parser.add_argument(
        '--action',
        action='store',
        required=True,
        help='Action for the host. enter/exit',
        choices=['enter', 'exit'],
        dest='action'
    )
    parser.set_defaults(func=maintenance)