import asyncio
import logging

from rosy import build_node


async def main():
    logging.basicConfig(level='WARNING')

    node = await build_node('receiver')
    await node.listen('some-topic', callback)
    await node.forever()


async def callback(topic, message: str, name: str = None):
    print(f'Received "{message} {name}" on topic={topic}')


if __name__ == '__main__':
    asyncio.run(main())
