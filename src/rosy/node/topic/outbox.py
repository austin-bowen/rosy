import asyncio
import logging

from rosy.asyncio import LockableWriter, cancel_task, loop_time
from rosy.node.peer.connection import PeerConnectionManager
from rosy.specs import MeshNodeSpec, NodeId
from rosy.types import Buffer
from rosy.utils import ALLOWED_EXCEPTIONS

logger = logging.getLogger(__name__)


class NodeOutboxManager:
    def __init__(self, connection_manager: PeerConnectionManager):
        self.connection_manager = connection_manager
        self._outboxes: dict[NodeId, NodeOutbox] = {}

    def get_outbox(self, node: MeshNodeSpec) -> "NodeOutbox":
        if node.id not in self._outboxes:
            self._outboxes[node.id] = NodeOutbox(node, self.connection_manager)

        return self._outboxes[node.id]

    async def stop_outbox(self, node: MeshNodeSpec) -> None:
        outbox = self._outboxes.pop(node.id, None)
        if outbox is not None:
            await outbox.stop()


class NodeOutbox:
    def __init__(
        self,
        node: MeshNodeSpec,
        connection_manager: PeerConnectionManager,
        ttl: float = 5,
        maxsize: int = 100,
    ):
        self.node = node
        self.connection_manager = connection_manager
        self.ttl = ttl

        self._queue = asyncio.Queue(maxsize)
        self._task = asyncio.create_task(self._run())

    def send(self, data: Buffer) -> None:
        if self._task.done():
            raise RuntimeError(
                f"Outbox task unexpectedly completed for node={self.node.id}"
            )

        deadline = loop_time() + self.ttl

        if self._queue.full():
            self._queue.get_nowait()
            self._queue.task_done()
            logger.warning(
                f"Dropped topic message for node={self.node.id}; outbox queue full",
            )

        self._queue.put_nowait((deadline, data))

    async def stop(self) -> None:
        await cancel_task(self._task)

    async def _run(self) -> None:
        while True:
            item = await self._queue.get()
            try:
                await self._send_once(*item)
            except ALLOWED_EXCEPTIONS:
                raise
            except Exception as e:
                logger.error(
                    f"Error sending topic message to node={self.node.id}: {e!r}",
                )
            finally:
                self._queue.task_done()

    async def _send_once(self, deadline: float, data: Buffer) -> None:
        if self._expired(deadline):
            return

        async with await self._get_writer() as writer:
            if self._expired(deadline):
                return

            writer.write(data)
            await writer.drain()

    def _expired(self, deadline: float) -> bool:
        if loop_time() >= deadline:
            logger.warning(
                f"Topic message expired waiting to send to node={self.node.id}",
            )
            return True
        return False

    async def _get_writer(self) -> LockableWriter:
        connection = await self.connection_manager.get_connection(self.node)
        return connection.writer
