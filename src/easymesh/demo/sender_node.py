import asyncio

from easymesh.node import build_mesh_node


async def main():
    node = await build_mesh_node(name='sender')

    while True:
        await node.send('some-topic', 'Hello, world!')
        await asyncio.sleep(1)


if __name__ == '__main__':
    asyncio.run(main())
