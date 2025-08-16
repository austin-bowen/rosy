import asyncio
import logging

from rosy import build_node


async def main():
    logging.basicConfig(level="WARNING")

    async with await build_node(name="service_caller") as node:
        print("Calculating 2 * 2...")
        result = await node.call("multiply", 2, 2)
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
