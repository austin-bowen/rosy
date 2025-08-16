import asyncio
import logging

from rosy import build_node


async def main():
    logging.basicConfig(level="WARNING")

    async with await build_node(name="topic_sender") as node:
        await node.send("some-topic", "hello", name="world")


if __name__ == "__main__":
    asyncio.run(main())
