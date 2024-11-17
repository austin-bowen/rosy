import asyncio
from abc import ABC, abstractmethod
from asyncio import Queue, Task
from typing import Awaitable, Callable

from easymesh.types import Data, Message, Topic

ListenerCallback = Callable[[Topic, Data], Awaitable[None]]


class ListenerManager(ABC):
    @abstractmethod
    def set_listener(self, topic: Topic, callback: ListenerCallback) -> None:
        ...

    @abstractmethod
    def remove_listener(self, topic: Topic) -> None:
        ...

    @abstractmethod
    def has_listener(self, topic: Topic) -> bool:
        ...

    @abstractmethod
    def get_topics(self) -> set[Topic]:
        ...

    @abstractmethod
    async def handle_message(self, message: Message) -> None:
        ...


class SerialTopicsListenerManager(ListenerManager):
    """Ensures messages are processed in order for each topic."""

    def __init__(self, queue_maxsize: int):
        self._queue_maxsize = queue_maxsize
        self._listeners: dict[Topic, ListenerCallback] = {}
        self._topic_queues: dict[Topic, tuple[Queue[Data], Task]] = {}

    def set_listener(self, topic: Topic, callback: ListenerCallback) -> None:
        self._listeners[topic] = callback

    def remove_listener(self, topic: Topic) -> None:
        self._listeners.pop(topic, None)

    def has_listener(self, topic: Topic) -> bool:
        return topic in self._listeners

    def get_topics(self) -> set[Topic]:
        return set(self._listeners.keys())

    async def handle_message(self, message: Message) -> None:
        if self.has_listener(message.topic):
            queue = self._get_topic_queue(message.topic)
            await queue.put(message.data)

    def _get_topic_queue(self, topic: Topic) -> Queue[Data]:
        queue, queue_task = self._topic_queues.get(topic, (None, None))
        if queue is not None and not queue_task.done():
            return queue

        if queue is None:
            queue = Queue(self._queue_maxsize)

        assert queue_task is None or queue_task.done()
        queue_task = asyncio.create_task(
            self._process_queue(topic, queue),
            name=f'queue processor for topic={topic}',
        )

        self._topic_queues[topic] = (queue, queue_task)

        return queue

    async def _process_queue(self, topic: Topic, queue: Queue[Data]):
        while True:
            data = await queue.get()
            try:
                callback = self._listeners.get(topic, None)
                if callback is not None:
                    await callback(topic, data)
            finally:
                queue.task_done()
