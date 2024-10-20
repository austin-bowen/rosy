from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Optional, Union

Host = str
ServerHost = Union[Host, Sequence[Host], None]
Port = int


@dataclass
class Endpoint:
    host: Host
    port: Port


Topic = str
Data = Any
TopicCallback = Callable[[Topic, Data], None]


@dataclass(slots=True)
class Message:
    topic: Topic
    data: Optional[Data]
