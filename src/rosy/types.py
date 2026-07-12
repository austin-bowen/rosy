from collections.abc import Sequence
from typing import Any, Awaitable, Callable, Protocol

Data = Any

Topic = str


class TopicCallback(Protocol):
    def __call__(self, topic: Topic, *args, **kwargs) -> None: ...


Service = str


class ServiceCallback(Protocol):
    def __call__(self, service: Service, *args, **kwargs) -> Data: ...


Host = str
ServerHost = Host | Sequence[Host] | None
Port = int

DomainId = str


class Buffer(Protocol):
    """Not available in std lib until Python 3.12."""

    def __buffer__(self, *args, **kwargs): ...  # pragma: no cover
