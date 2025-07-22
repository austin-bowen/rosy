import asyncio
from argparse import ArgumentParser, Namespace

from rosy.argparse import add_authkey_arg
from rosy.asyncio import forever
from rosy.coordinator.constants import DEFAULT_COORDINATOR_HOST, DEFAULT_COORDINATOR_PORT
from rosy.coordinator.server import build_mesh_coordinator_server
from rosy.types import ServerHost


async def main() -> None:
    args = _parse_args()

    server = build_mesh_coordinator_server(
        host=args.host,
        port=args.port,
        authkey=args.authkey,
        log_heartbeats=args.log_heartbeats,
    )

    try:
        await server.start()
    except:
        print(f'Failed to start rosy coordinator on {args.host}:{args.port}')
        raise
    else:
        print(f'Started rosy coordinator on {args.host}:{args.port}')

    await forever()


def _parse_args() -> Namespace:
    parser = ArgumentParser(
        description='Start the rosy coordinator.',
    )

    def server_host_arg(arg: str) -> ServerHost:
        if arg == 'None':
            return None

        hosts = arg.split(',')
        return hosts if len(hosts) > 1 else hosts[0]

    parser.add_argument(
        '--host', default=DEFAULT_COORDINATOR_HOST, type=server_host_arg,
        help='Comma-separated list of host(s) to bind to. '
             'Default is empty string, which means all available interfaces.',
    )

    parser.add_argument(
        '--port', default=DEFAULT_COORDINATOR_PORT, type=int,
        help=f'Port to bind to. Default is {DEFAULT_COORDINATOR_PORT}.',
    )

    add_authkey_arg(parser)

    parser.add_argument(
        '--log-heartbeats', action='store_true',
        help='Log heartbeats from nodes.',
    )

    return parser.parse_args()


if __name__ == '__main__':
    asyncio.run(main())
