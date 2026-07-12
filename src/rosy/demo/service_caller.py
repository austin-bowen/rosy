import asyncio
import logging

from rosy import build_node


async def main():
    logging.basicConfig(level="WARNING")

    with build_node(name="service_caller") as node:
        print("Waiting for a service provider...")
        node.wait_for_service_provider("multiply")
        print("Calculating 2 * 2...")
        result = node.call("multiply", 2, 2)
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
