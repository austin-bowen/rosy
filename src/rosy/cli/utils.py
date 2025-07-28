from argparse import ArgumentParser, Namespace

from rosy.authentication import optional_authkey_authenticator
from rosy.coordinator.client import build_coordinator_client
from rosy.specs import MeshTopologySpec


def add_log_arg(parser: ArgumentParser, default: str = 'WARNING') -> None:
    parser.add_argument(
        '--log',
        default=default,
        help='Log level; DEBUG, INFO, ERROR, etc. Default: %(default)s'
    )


async def get_mesh_topology(args: Namespace) -> MeshTopologySpec:
    authenticator = optional_authkey_authenticator(args.authkey)

    coordinator_client = await build_coordinator_client(
        host=args.coordinator.host,
        port=args.coordinator.port,
        authenticator=authenticator,
        reconnect_timeout=None,
    )

    return await coordinator_client.get_topology()
