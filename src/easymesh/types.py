from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Union

Host = str
ServerHost = Union[Host, Sequence[Host], None]
Port = int

Topic = str
Body = Any
TopicCallback = Callable[[Topic, Body], None]


@dataclass(slots=True)
class Message:
    topic: Topic
    body: Body
