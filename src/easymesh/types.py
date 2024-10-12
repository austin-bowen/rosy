from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

Topic = str
TopicPattern = Topic

Body = Any

TopicCallback = Callable[[Topic, Body], None]


@dataclass(slots=True)
class Message:
    topic: Topic
    body: Body
