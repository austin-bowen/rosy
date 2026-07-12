import logging

from rosy import build_node
from rosy.types import Service


def main():
    logging.basicConfig(level="WARNING")

    with build_node("service_provider") as node:
        node.add_service("multiply", multiply)
        print("Started service...")
        node.forever()


def multiply(service: Service, a: int, b: int) -> int:
    return a * b


if __name__ == "__main__":
    main()
