import asyncio
from argparse import ArgumentParser, Namespace

from easymesh.asyncio import forever
from easymesh.coordinator.constants import DEFAULT_COORDINATOR_PORT
from easymesh.coordinator.server import build_mesh_coordinator_server


async def main() -> None:
    args = _parse_args()

    server = build_mesh_coordinator_server(args.host, args.port)

    try:
        await server.start()
    except:
        print(f'Failed to start coordinator on {args.host!r}:{args.port}')
        raise
    else:
        print(f'Started coordinator on {args.host!r}:{args.port}')

    await forever()


def _parse_args() -> Namespace:
    parser = ArgumentParser()

    parser.add_argument(
        '--host', default='',
        help='Host to bind to. Default is empty string, which means all available interfaces.',
    )

    parser.add_argument(
        '--port', default=DEFAULT_COORDINATOR_PORT, type=int,
        help=f'Port to bind to. Default is {DEFAULT_COORDINATOR_PORT}.',
    )

    return parser.parse_args()


if __name__ == '__main__':
    asyncio.run(main())
