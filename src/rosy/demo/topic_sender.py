import asyncio
import logging

from rosy import build_node


async def main():
    logging.basicConfig(level='WARNING')

    node = await build_node(name='topic_sender')
    await node.send('some-topic', 'hello', name='world')


if __name__ == '__main__':
    asyncio.run(main())
