import argparse
import asyncio

import easymesh
from easymesh.asyncio import forever
from easymesh.types import Data, Topic


async def handle_message(topic: Topic, data: Data):
    print(f'Received: topic={topic!r} data={data!r}')


async def main():
    args = _parse_args()

    node = await easymesh.build_mesh_node(
        name=args.name,
        coordinator_host=args.coordinator_host,
    )

    await node.add_listener('some-topic', handle_message)
    await forever()


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='receiver')
    parser.add_argument('--coordinator-host', default='localhost')
    return parser.parse_args()


if __name__ == '__main__':
    asyncio.run(main())
