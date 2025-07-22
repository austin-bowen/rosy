from rosy.types import Topic, TopicCallback


class TopicListenerManager:
    def __init__(self):
        self._listeners: dict[Topic, TopicCallback] = {}

    @property
    def topics(self) -> set[Topic]:
        return set(self._listeners.keys())

    def get_listener(self, topic: Topic) -> TopicCallback | None:
        return self._listeners.get(topic)

    def set_listener(self, topic: Topic, callback: TopicCallback) -> None:
        self._listeners[topic] = callback

    def remove_listener(self, topic: Topic) -> TopicCallback | None:
        return self._listeners.pop(topic, None)

    def has_listener(self, topic: Topic) -> bool:
        return topic in self._listeners
