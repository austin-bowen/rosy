import asyncio
import time

import easymesh
from easymesh.demo.argparse import parse_args


async def main():
    args = parse_args(default_node_name='sender')

    node = await easymesh.build_mesh_node(
        name=args.name,
        coordinator_host=args.coordinator.host,
        coordinator_port=args.coordinator.port,
    )

    while True:
        data = (time.time(), f'Hello from node {node}!')
        await node.send('some-topic', data)
        await asyncio.sleep(1)


if __name__ == '__main__':
    asyncio.run(main())
