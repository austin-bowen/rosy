import asyncio
from asyncio import Lock
from io import BytesIO
from typing import Protocol, TypeVar

from rosy.types import Buffer

T = TypeVar('T')
E = TypeVar('E', bound=BaseException)


async def close_ignoring_errors(writer: 'Writer') -> None:
    """Closes the writer ignoring any ConnectionErrors."""
    try:
        writer.close()
        await writer.wait_closed()
    except ConnectionError:
        pass


async def forever():
    """Never returns."""
    await asyncio.Future()  # pragma: no cover


def noop():
    """Does nothing. Use to return control to the event loop."""
    return asyncio.sleep(0)


class Reader(Protocol):
    async def readexactly(self, n: int) -> bytes:
        ...

    async def readuntil(self, separator: bytes) -> bytes:
        ...


class Writer(Protocol):
    def write(self, data: bytes) -> None:
        ...

    async def drain(self) -> None:
        ...

    def close(self) -> None:
        ...

    def is_closing(self) -> bool:
        ...

    async def wait_closed(self) -> None:
        ...

    def get_extra_info(self, name: str, default=None):
        ...


class LockableWriter(Writer):
    def __init__(self, writer: Writer):
        self.writer = writer
        self._lock = Lock()

    @property
    def lock(self) -> Lock:
        return self._lock

    async def __aenter__(self) -> 'LockableWriter':
        await self.lock.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self._lock.release()

    def write(self, data: bytes) -> None:
        self.require_locked()
        self.writer.write(data)

    async def drain(self) -> None:
        await self.writer.drain()

    def close(self) -> None:
        self.writer.close()

    def is_closing(self) -> bool:
        return self.writer.is_closing()

    async def wait_closed(self) -> None:
        await self.writer.wait_closed()

    def get_extra_info(self, name: str, default=None):
        return self.writer.get_extra_info(name, default)

    def require_locked(self) -> None:
        if not self._lock.locked():
            raise RuntimeError('Writer must be locked before writing')


class BufferReader(Reader):
    def __init__(self, data: bytes):
        self._data = BytesIO(data)

    async def readexactly(self, n: int) -> bytes:
        data = self._data.read(n)
        assert len(data) == n
        return data

    async def readuntil(self, separator: bytes) -> bytes:
        raise NotImplementedError()


class BufferWriter(bytearray, Buffer, Writer):
    def write(self, data: bytes) -> None:
        self.extend(data)

    async def drain(self) -> None:
        pass

    def close(self) -> None:
        pass

    def is_closing(self) -> bool:
        pass

    async def wait_closed(self) -> None:
        pass

    def get_extra_info(self, name: str, default=None):
        raise NotImplementedError()
