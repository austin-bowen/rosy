import asyncio

from easymesh import build_mesh_node_from_args
from easymesh.asyncio import forever


async def handle_message(topic, data):
    print(f'receiver got: topic={topic!r} data={data!r}')


async def main():
    node = await build_mesh_node_from_args(default_node_name='receiver')
    await node.listen('some-topic', handle_message)
    await forever()


if __name__ == '__main__':
    asyncio.run(main())
