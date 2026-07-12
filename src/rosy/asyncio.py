import asyncio
import threading
from abc import ABC, abstractmethod
from asyncio import IncompleteReadError, Lock
from asyncio.runners import _cancel_all_tasks
from io import BytesIO
from threading import Thread
from typing import Protocol

from rosy.types import Buffer


async def cancel_task(task: asyncio.Task, *, timeout: float | None = 10) -> None:
    """Cancels the task and safely waits for it to complete."""

    if task.done():
        return

    done = asyncio.Event()
    cb = lambda _: done.set()
    task.add_done_callback(cb)
    try:
        task.cancel()
        await asyncio.wait_for(done.wait(), timeout=timeout)
    finally:
        task.remove_done_callback(cb)


async def close_ignoring_errors(writer: "Writer") -> None:
    """Closes the writer ignoring any ConnectionErrors."""
    try:
        writer.close()
        await writer.wait_closed()
    except ConnectionError:
        pass


async def forever():
    """Never returns."""
    await asyncio.Future()  # pragma: no cover


def loop_time() -> float:
    return asyncio.get_running_loop().time()


def noop():
    """Does nothing. Use to return control to the event loop."""
    return asyncio.sleep(0)


class Reader(Protocol):
    async def readexactly(self, n: int) -> bytes: ...

    async def readuntil(self, separator: bytes) -> bytes: ...


class Writer(Protocol):
    def write(self, data: bytes) -> None: ...

    async def drain(self) -> None: ...

    def close(self) -> None: ...

    def is_closing(self) -> bool: ...

    async def wait_closed(self) -> None: ...

    def get_extra_info(self, name: str, default=None): ...


class LockableWriter(Writer):
    def __init__(self, writer: Writer):
        self.writer = writer
        self._lock = Lock()

    @property
    def lock(self) -> Lock:
        return self._lock

    async def __aenter__(self) -> "LockableWriter":
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
            raise RuntimeError("Writer must be locked before writing")


class BufferReader(Reader):
    def __init__(self, data: bytes):
        self._data = BytesIO(data)

    async def readexactly(self, n: int) -> bytes:
        data = self._data.read(n)

        if len(data) < n:
            raise IncompleteReadError(data, n)

        return data

    async def readuntil(self, separator: bytes) -> bytes:
        raise NotImplementedError()


class BufferWriter(bytearray, Buffer, Writer):
    def write(self, data: bytes) -> None:
        self.extend(data)

    async def drain(self) -> None:
        pass

    def close(self) -> None:
        raise NotImplementedError()

    def is_closing(self) -> bool:
        raise NotImplementedError()

    async def wait_closed(self) -> None:
        raise NotImplementedError()

    def get_extra_info(self, name: str, default=None):
        raise NotImplementedError()


class LoopRunner(ABC):
    @property
    @abstractmethod
    def loop(self) -> asyncio.AbstractEventLoop: ...

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...


class NewThreadLoopRunner(Thread, LoopRunner):
    """Runs an event loop in a new thread."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop | None = None,
        name: str | None = "NewThreadLoopRunner",
        daemon: bool = True,
    ):
        Thread.__init__(self, name=name, daemon=daemon)

        self._loop = loop or asyncio.new_event_loop()
        self._started = threading.Event()

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    def start(self, timeout: float | None = None) -> None:
        Thread.start(self)
        self._started.wait(timeout)

    def run(self) -> None:
        loop = self.loop
        asyncio.set_event_loop(loop)

        # Based on the implementation of `asyncio.run()`
        try:
            loop.call_soon(self._started.set)
            loop.run_forever()
        finally:
            self._shutdown()

    def _shutdown(self) -> None:
        loop = self.loop

        try:
            _cancel_all_tasks(loop)
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.run_until_complete(loop.shutdown_default_executor())
        finally:
            loop.close()

    def stop(self, timeout: float | None = None) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.join(timeout=timeout)
