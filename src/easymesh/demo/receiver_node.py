import asyncio

import easymesh
from easymesh.asyncio import forever


async def handle_some_topic_message(message):
    print(f'Received: {message}')


async def main():
    node = await easymesh.build_mesh_node(name='receiver')

    await node.add_listener('some-topic', handle_some_topic_message)
    await forever()


if __name__ == '__main__':
    asyncio.run(main())
