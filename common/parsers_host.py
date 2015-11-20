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
        choices=operations.get_esxi_services(),
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
        choices=operations.get_esxi_rules(),
        dest='rule'
    )
    parser.set_defaults(func=config_rule)