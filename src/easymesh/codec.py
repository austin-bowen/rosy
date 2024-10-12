import pickle
from abc import abstractmethod
from typing import Any, Generic, TypeVar, Union

try:
    import msgpack
except ImportError:
    msgpack = None

T = TypeVar('T')


class Codec(Generic[T]):
    @abstractmethod
    def encode(self, obj: T) -> bytes:
        ...

    @abstractmethod
    def decode(self, data: bytes) -> T:
        ...


class PickleCodec(Codec[Any]):
    def __init__(self, protocol: int = pickle.HIGHEST_PROTOCOL):
        self.protocol = protocol

    def encode(self, obj: Any) -> bytes:
        return pickle.dumps(obj, protocol=self.protocol)

    def decode(self, data: bytes) -> Any:
        return pickle.loads(data)


if msgpack:
    MsgpackTypes = Union[None, bool, int, float, str, bytes, bytearray, list, tuple, dict]


    class MsgpackCodec(Codec[MsgpackTypes]):
        def encode(self, obj: MsgpackTypes) -> bytes:
            return msgpack.packb(obj)

        def decode(self, data: bytes) -> MsgpackTypes:
            return msgpack.unpackb(data)
