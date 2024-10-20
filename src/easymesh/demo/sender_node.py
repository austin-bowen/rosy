import argparse
import asyncio
import time

import easymesh


async def main():
    args = _parse_args()

    node = await easymesh.build_mesh_node(
        name=args.name,
        coordinator_host=args.coordinator_host,
    )

    while True:
        data = (time.time(), f'Hello from node {node}!')
        await node.send('some-topic', data)
        await asyncio.sleep(1)


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='sender')
    parser.add_argument('--coordinator-host', default='localhost')
    return parser.parse_args()


if __name__ == '__main__':
    asyncio.run(main())
