import asyncio
import logging

from rosy import build_node
from rosy.types import Service


async def main():
    logging.basicConfig(level="WARNING")

    async with await build_node("service_provider") as node:
        await node.add_service("multiply", multiply)
        print("Started service...")
        await node.forever()


async def multiply(service: Service, a: int, b: int) -> int:
    return a * b


if __name__ == "__main__":
    asyncio.run(main())
