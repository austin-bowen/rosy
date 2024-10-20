import asyncio

import easymesh


async def main():
    node = await easymesh.build_mesh_node(name='sender')

    while True:
        await node.send('some-topic', f'Hello from node {node}!')
        await asyncio.sleep(1)


if __name__ == '__main__':
    asyncio.run(main())
