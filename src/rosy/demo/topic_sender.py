import logging

from rosy.node.builder import build_node


def main():
    logging.basicConfig(level="WARNING")

    with build_node(name="topic_sender") as node:
        node.wait_for_listener("some-topic")
        node.send("some-topic", "hello", name="world")


if __name__ == "__main__":
    main()
