import asyncio

import easymesh
from easymesh.asyncio import forever
from easymesh.types import Data, Topic


async def handle_message(topic: Topic, data: Data):
    print(f'Received: topic={topic!r} data={data!r}')


async def main():
    node = await easymesh.build_mesh_node(name='receiver')

    await node.add_listener('some-topic', handle_message)
    await forever()


if __name__ == '__main__':
    asyncio.run(main())
