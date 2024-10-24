import easymesh
from easymesh.demo.argparse import parse_args


async def main():
    args = parse_args(default_node_name='sender')

    node = await easymesh.build_mesh_node(
        name=args.name,
        coordinator_host=args.coordinator.host,
        coordinator_port=args.coordinator.port,
    )

    await node.wait_for_listener('some-topic')
    await node.send('some-topic', {'hello': 'world!'})


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
