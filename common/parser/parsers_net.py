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


# Net site operations
def pg_moid(args):
    vc = _get_vc()
    pg_id = operations.get_pg_id(vc, args.dc, args.vds, args.pg)
    if pg_id:
        print pg_id
        exit(0)
    else:
        exit(1)


def pg_moid_parser(subparsers):
    parser = subparsers.add_parser(
        'net-pgid',
        help='Get vds portgroup id.'
    )
    parser.add_argument(
        '--dc',
        action='store',
        required=True,
        help='Data center name.',
        dest='dc'
    )
    parser.add_argument(
        '--vds',
        action='store',
        required=True,
        help='vDS name which the portgroup in.',
        dest='vds'
    )
    parser.add_argument(
        '--pg',
        action='store',
        required=True,
        help='Port group name',
        dest='pg'
    )
    parser.set_defaults(func=pg_moid)
