import asyncio
import logging

from rosy.node.builder import build_async_node


async def main():
    logging.basicConfig(level="WARNING")

    async with build_async_node(name="topic_sender") as node:
        await node.wait_for_listener("some-topic")
        await node.send("some-topic", "hello", name="world")


if __name__ == "__main__":
    asyncio.run(main())
