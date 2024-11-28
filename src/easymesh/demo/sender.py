import asyncio

from easymesh import build_mesh_node_from_args


async def main():
    node = await build_mesh_node_from_args(default_node_name='sender')

    while True:
        await node.send('some-topic', {'hello': 'world!'})
        await asyncio.sleep(1)


if __name__ == '__main__':
    asyncio.run(main())
