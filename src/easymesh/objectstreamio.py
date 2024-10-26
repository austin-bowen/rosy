from abc import abstractmethod
from asyncio import Lock, StreamReader
from collections.abc import AsyncIterable
from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

from easymesh.asyncio import Writer
from easymesh.codec import Codec, PickleCodec
from easymesh.types import Data, Message

ByteOrder = Literal['big', 'little']
DEFAULT_BYTE_ORDER: ByteOrder = 'little'
T = TypeVar('T')

pickle_codec = PickleCodec()


class ObjectReader(Generic[T]):
    def __aiter__(self):
        return self

    async def __anext__(self) -> T:
        return await self.read()

    @abstractmethod
    async def read(self) -> T:
        ...


class ObjectWriter(Generic[T]):
    async def write_and_drain(self, obj: T) -> None:
        await self.write(obj)
        await self.drain()

    @abstractmethod
    async def write(self, obj: T) -> None:
        ...

    @abstractmethod
    async def drain(self) -> None:
        ...


@dataclass
class ObjectIO(Generic[T]):
    reader: ObjectReader[T]
    writer: ObjectWriter[T]


class ObjectStreamReader(ObjectReader[T]):
    def __init__(self, reader: StreamReader, byte_order: ByteOrder):
        self.reader = reader
        self.byte_order = byte_order

        self._read_lock = Lock()

    async def read(self) -> T:
        async with self._read_lock:
            return await self._read()

    @abstractmethod
    async def _read(self) -> T:
        ...

    async def _read_data_with_len_header(self) -> bytes:
        header_len = (await self.reader.readexactly(1))[0]

        if not header_len:
            return b''

        header = await self.reader.readexactly(header_len)
        data_len = self._bytes_to_int(header)

        return await self.reader.readexactly(data_len)

    def _bytes_to_int(self, data: bytes) -> int:
        return int.from_bytes(data, byteorder=self.byte_order, signed=False)


class ObjectStreamWriter(ObjectWriter[T]):
    def __init__(self, writer: Writer, byte_order: ByteOrder):
        self.writer = writer
        self.byte_order = byte_order

        self._write_lock = Lock()
        self._drain_lock = Lock()

    async def write(self, obj: T) -> None:
        async with self._write_lock:
            await self._write(obj)

    @abstractmethod
    async def _write(self, obj: T) -> None:
        ...

    def _write_data_with_len_header(self, data: bytes) -> None:
        data_len = len(data)

        header_len = (data_len.bit_length() + 7) // 8
        self.writer.write(self._int_to_bytes(header_len, length=1))

        if not data_len:
            return

        header = self._int_to_bytes(data_len, length=header_len)

        self.writer.write(header)
        self.writer.write(data)

    def _int_to_bytes(self, value: int, length: int) -> bytes:
        return value.to_bytes(length, byteorder=self.byte_order, signed=False)

    async def drain(self) -> None:
        async with self._drain_lock:
            await self.writer.drain()


class CodecObjectStreamReader(ObjectStreamReader[T]):
    def __init__(
            self,
            reader: StreamReader,
            codec: Codec[T] = pickle_codec,
            byte_order: ByteOrder = DEFAULT_BYTE_ORDER,
    ):
        super().__init__(reader, byte_order)
        self.codec = codec

    async def _read(self) -> T:
        data = await self._read_data_with_len_header()
        return self.codec.decode(data)


class CodecObjectStreamWriter(ObjectStreamWriter[T]):
    def __init__(
            self,
            writer: Writer,
            codec: Codec[T] = pickle_codec,
            byte_order: ByteOrder = DEFAULT_BYTE_ORDER,
    ):
        super().__init__(writer, byte_order)
        self.codec = codec

    async def _write(self, obj: T) -> None:
        data = self.codec.encode(obj)
        self._write_data_with_len_header(data)


class ObjectStreamIO(Generic[T]):
    lock: Lock
    """For users to lock the whole object."""

    def __init__(
            self,
            reader: StreamReader,
            writer: Writer,
            byte_order: ByteOrder,
    ):
        self.reader = reader
        self.writer = writer
        self.byte_order = byte_order

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

    async def _read_data_with_len_header(self) -> bytes:
        header_len = (await self.reader.readexactly(1))[0]

        if not header_len:
            return b''

        header = await self.reader.readexactly(header_len)
        data_len = self._bytes_to_int(header)

        return await self.reader.readexactly(data_len)

    def _bytes_to_int(self, data: bytes) -> int:
        return int.from_bytes(data, byteorder=self.byte_order, signed=False)

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

    def _write_data_with_len_header(self, data: bytes) -> None:
        data_len = len(data)

        header_len = (data_len.bit_length() + 7) // 8
        self.writer.write(self._int_to_bytes(header_len, length=1))

        if not data_len:
            return

        header = self._int_to_bytes(data_len, length=header_len)

        self.writer.write(header)
        self.writer.write(data)

    def _int_to_bytes(self, value: int, length: int) -> bytes:
        return value.to_bytes(length, byteorder=self.byte_order, signed=False)

    async def drain(self) -> None:
        async with self._drain_lock:
            await self.writer.drain()


class MessageStreamIO(ObjectStreamIO[Message]):
    """ObjectStreamIO that reads and writes only Message objects."""

    def __init__(
            self,
            reader: StreamReader,
            writer: Writer,
            codec: Codec[Data] = pickle_codec,
            topic_encoding: str = 'utf-8',
            byte_order: ByteOrder = DEFAULT_BYTE_ORDER,
    ):
        super().__init__(reader, writer, byte_order)

        self.codec = codec
        self.topic_encoding = topic_encoding

    async def _read_object(self) -> Message:
        topic = await self._read_data_with_len_header()
        topic = topic.decode(self.topic_encoding)

        data = await self._read_data_with_len_header()
        data = self.codec.decode(data) if data else None

        return Message(topic, data)

    async def _write_object(self, message: Message) -> None:
        topic = message.topic.encode(self.topic_encoding)
        self._write_data_with_len_header(topic)

        data = self.codec.encode(message.data) if message.data is not None else b''
        self._write_data_with_len_header(data)
