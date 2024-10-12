import pickle
from abc import abstractmethod
from asyncio import Lock, StreamReader, StreamWriter
from collections.abc import AsyncIterable
from typing import Any, Generic, Literal, TypeVar

from easymesh.codec import Codec, PickleCodec
from easymesh.types import Body, Message

ByteOrder = Literal['big', 'little']
DEFAULT_BYTE_ORDER: ByteOrder = 'little'
T = TypeVar('T')

pickle_codec = PickleCodec()


def default_bytes_to_obj(data: bytes) -> T:
    return pickle.loads(data)


def default_obj_to_bytes(obj: T) -> bytes:
    return pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)


class ObjectStreamIO(Generic[T]):
    lock: Lock
    """For users to lock the whole object."""

    def __init__(self, reader: StreamReader, writer: StreamWriter):
        self.reader = reader
        self.writer = writer

        self.lock = Lock()
        self._read_lock = Lock()
        self._write_lock = Lock()
        self._drain_lock = Lock()

    async def read_object(self) -> T:
        async with self._read_lock:
            return await self._read_object()

    @abstractmethod
    async def _read_object(self) -> T:
        ...

    async def _read_data_with_len_header(
            self,
            header_len: int,
            byte_order: ByteOrder,
    ) -> bytes:
        header = await self.reader.readexactly(header_len)
        data_len = int.from_bytes(
            header,
            byteorder=byte_order,
            signed=False,
        )

        return await self.reader.readexactly(data_len)

    async def read_objects(self) -> AsyncIterable[T]:
        while True:
            yield await self.read_object()

    async def write_object(self, obj: T, drain: bool = True) -> None:
        async with self._write_lock:
            await self._write_object(obj)
            if drain:
                await self.drain()

    @abstractmethod
    async def _write_object(self, obj: T) -> None:
        ...

    def _write_data_with_len_header(
            self,
            data: bytes,
            header_len: int,
            header_byte_order: ByteOrder,
    ) -> None:
        header = len(data).to_bytes(
            length=header_len,
            byteorder=header_byte_order,
            signed=False,
        )
        self.writer.write(header)
        self.writer.write(data)

    async def drain(self) -> None:
        async with self._drain_lock:
            await self.writer.drain()


class AnyObjectStreamIO(ObjectStreamIO[Any]):
    def __init__(
            self,
            reader: StreamReader,
            writer: StreamWriter,
            codec: Codec[Any] = pickle_codec,
            header_len: int = 4,
            header_byte_order: ByteOrder = DEFAULT_BYTE_ORDER,
    ):
        super().__init__(reader, writer)

        self.codec = codec
        self.header_len = header_len
        self.header_byte_order = header_byte_order

    async def _read_object(self) -> T:
        data = await self._read_data_with_len_header(
            self.header_len,
            self.header_byte_order,
        )

        return self.codec.decode(data)

    async def _write_object(self, obj: T) -> None:
        data = self.codec.encode(obj)

        self._write_data_with_len_header(
            data,
            self.header_len,
            self.header_byte_order,
        )


class MessageStreamIO(ObjectStreamIO[Message]):
    """ObjectStreamIO that reads and writes only Message objects."""

    def __init__(
            self,
            reader: StreamReader,
            writer: StreamWriter,
            codec: Codec[Body] = pickle_codec,
            topic_header_len: int = 1,
            topic_encoding: str = 'utf-8',
            body_header_len: int = 4,
            header_byte_order: ByteOrder = DEFAULT_BYTE_ORDER,
    ):
        super().__init__(reader, writer)

        self.codec = codec
        self.topic_header_len = topic_header_len
        self.topic_encoding = topic_encoding
        self.body_header_len = body_header_len
        self.header_byte_order = header_byte_order

    async def _read_object(self) -> Message:
        topic = await self._read_data_with_len_header(
            self.topic_header_len,
            self.header_byte_order,
        )
        topic = topic.decode(self.topic_encoding)

        body = await self._read_data_with_len_header(
            self.body_header_len,
            self.header_byte_order,
        )
        body = self.codec.decode(body) if body else None

        return Message(topic, body)

    async def _write_object(self, message: Message) -> None:
        topic = message.topic.encode(self.topic_encoding)
        self._write_data_with_len_header(
            topic,
            self.topic_header_len,
            self.header_byte_order,
        )

        data = self.codec.encode(message.body) if message.body is not None else b''
        self._write_data_with_len_header(
            data,
            self.body_header_len,
            self.header_byte_order,
        )
