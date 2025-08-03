import asyncio
import logging

from rosy import build_node
from rosy.types import Topic


async def main():
    logging.basicConfig(level='WARNING')

    node = await build_node('topic_listener')
    await node.listen('some-topic', callback)
    print('Listening...')
    await node.forever()


async def callback(topic: Topic, message: str, name: str = None):
    print(f'Received "{message} {name}" on topic={topic}')


if __name__ == '__main__':
    asyncio.run(main())
