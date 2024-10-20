import asyncio

import easymesh
from easymesh.asyncio import forever
from easymesh.demo.argparse import parse_args


async def handle_message(topic, data):
    print(f'Received: topic={topic!r} data={data!r}')


async def main():
    args = parse_args(default_node_name='receiver')

    node = await easymesh.build_mesh_node(
        name=args.name,
        coordinator_host=args.coordinator.host,
        coordinator_port=args.coordinator.port,
    )

    await node.add_listener('some-topic', handle_message)
    await forever()


if __name__ == '__main__':
    asyncio.run(main())
