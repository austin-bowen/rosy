import logging

from rosy import build_node
from rosy.types import Topic


def main():
    logging.basicConfig(level="WARNING")

    with build_node("topic_listener") as node:
        print("Listening...")
        node.listen("some-topic", callback)
        node.forever()


def callback(topic: Topic, message: str, name: str | None = None):
    print(f'Received "{message} {name}" on topic={topic}')


if __name__ == "__main__":
    main()
