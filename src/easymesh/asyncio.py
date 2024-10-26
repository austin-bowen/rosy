import asyncio
import traceback
from asyncio import Task
from collections.abc import Awaitable, Iterable, Sized
from typing import Protocol, Type, TypeVar, Union

T = TypeVar('T')
E = TypeVar('E', bound=BaseException)


async def forever():
    """Never returns."""
    while True:
        await asyncio.sleep(60)


async def many(
        awaitables: Iterable[Awaitable[T]],
        base_exception: Type[E] = Exception,
) -> list[Union[T, E]]:
    """
    Await multiple awaitables in parallel and returns their results.

    Exceptions of type ``base_exception`` are caught and returned
    in the results list.

    This is a bit faster and nicer to use than ``asyncio.gather``.
    In the case there is only a single awaitable, it is awaited
    directly rather than creating and awaiting a new task.
    """

    if not isinstance(awaitables, Sized):
        awaitables = list(awaitables)

    if len(awaitables) == 1:
        try:
            return [await awaitables[0]]
        except base_exception as e:
            traceback.print_exc()
            return [e]

    tasks = [
        a if isinstance(a, Task) else asyncio.create_task(a)
        for a in awaitables
    ]

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
