import asyncio
import traceback
from collections.abc import Awaitable, Iterable, Sequence
from typing import Protocol


async def forever():
    """Never returns."""
    while True:
        await asyncio.sleep(60)


async def many(coros: Sequence[Awaitable], base_exception=Exception) -> list:
    if len(coros) == 1:
        try:
            return [await coros[0]]
        except base_exception as e:
            traceback.print_exc()
            return [e]

    # TODO handle if coros are already tasks
    tasks = [asyncio.create_task(c) for c in coros]

    results = []
    for task in tasks:
        try:
            results.append(await task)
        except base_exception as e:
            traceback.print_exc()
            results.append(e)

    return results


def noop():
    """Does nothing. Use to return control to the event loop."""
    return asyncio.sleep(0)


class Writer(Protocol):
    def write(self, data: bytes) -> None:
        ...

    async def drain(self) -> None:
        ...

    async def close(self) -> None:
        ...


class MultiWriter(Writer):
    def __init__(self, writers: Iterable[Writer]):
        self.writers = writers

    def write(self, data: bytes) -> None:
        for writer in self.writers:
            writer.write(data)

    async def drain(self) -> None:
        for writer in self.writers:
            await writer.drain()

    async def close(self) -> None:
        for writer in self.writers:
            await writer.close()
