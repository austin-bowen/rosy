from collections import defaultdict

from easymesh.asyncio import many
from easymesh.node.node import ListenerCallback
from easymesh.types import Message, Topic


class ListenerManager:
    def __init__(self):
        self._listeners: dict[Topic, set[ListenerCallback]] = defaultdict(set)

    def add_listener(self, topic: Topic, callback: ListenerCallback) -> None:
        self._listeners[topic].add(callback)

    def remove_listener(self, topic: Topic, callback: ListenerCallback) -> None:
        self._listeners[topic].remove(callback)
        if not self._listeners[topic]:
            del self._listeners[topic]

    def get_topics(self) -> set[Topic]:
        return set(self._listeners.keys())

    async def handle_message(self, message: Message) -> None:
        await many(
            listener(message.topic, message.data)
            for listener in self._listeners[message.topic]
        )
