import asyncio

from easymesh.asyncio import forever
from easymesh.node import build_mesh_node
from easymesh.types import Message


async def handle_some_topic_message(message: Message):
    print(f'Received: {message}')


async def main():
    node = await build_mesh_node(name='receiver')

    await node.add_listener('some-topic', handle_some_topic_message)
    await forever()


if __name__ == '__main__':
    asyncio.run(main())
