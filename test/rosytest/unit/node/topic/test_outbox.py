import asyncio
from unittest.mock import AsyncMock, Mock, create_autospec, patch

import pytest

from rosy.asyncio import LockableWriter
from rosy.node.peer.connection import PeerConnectionManager
from rosy.node.topic.outbox import NodeOutbox, NodeOutboxManager
from rosytest.util import mock_node_spec


class TestNodeOutboxManager:
    def setup_method(self) -> None:
        self.connection_manager = AsyncMock(spec=PeerConnectionManager)

        self.outbox_manager = NodeOutboxManager(self.connection_manager)

    @pytest.mark.asyncio
    async def test_get_new_outbox(self):
        node = mock_node_spec()

        outbox = self.outbox_manager.get_outbox(node)

        assert outbox.node is node
        assert outbox.connection_manager is self.connection_manager

    @pytest.mark.asyncio
    async def test_get_existing_outbox(self):
        node = mock_node_spec()

        outbox0 = self.outbox_manager.get_outbox(node)
        outbox1 = self.outbox_manager.get_outbox(node)

        assert outbox0 is outbox1

    @pytest.mark.asyncio
    async def test_get_different_node_outboxes(self):
        node0 = mock_node_spec()
        node1 = mock_node_spec()

        outbox0 = self.outbox_manager.get_outbox(node0)
        outbox1 = self.outbox_manager.get_outbox(node1)

        assert outbox0 is not outbox1
        assert outbox0.node is node0
        assert outbox1.node is node1

    @pytest.mark.asyncio
    @patch("rosy.node.topic.outbox.NodeOutbox")
    async def test_stop_outbox(self, NodeOutbox):
        node = mock_node_spec()

        outbox = AsyncMock()
        NodeOutbox.return_value = outbox

        assert self.outbox_manager.get_outbox(node) is outbox

        assert await self.outbox_manager.stop_outbox(node) is None

        outbox.stop.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("rosy.node.topic.outbox.NodeOutbox")
    async def test_stop_nonexistent_outbox(self, NodeOutbox):
        node = mock_node_spec()

        assert await self.outbox_manager.stop_outbox(node) is None

        assert NodeOutbox.not_called()


class TestNodeOutbox:
    def setup_method(self) -> None:
        self.node = mock_node_spec()

        self.writer = create_autospec(LockableWriter)
        self.writer.__aenter__.return_value = self.writer

        self.connection_manager = AsyncMock(spec=PeerConnectionManager)
        self.connection_manager.get_connection.return_value.writer = self.writer

    def get_outbox(self, ttl: float = None, maxsize: int = None):
        kwargs = {}
        if ttl is not None:
            kwargs["ttl"] = ttl
        if maxsize is not None:
            kwargs["maxsize"] = maxsize

        return NodeOutbox(self.node, self.connection_manager, **kwargs)

    @pytest.mark.asyncio
    async def test_defaults(self):
        outbox = self.get_outbox()
        assert outbox.ttl == 5
        assert outbox._queue.maxsize == 100

    @pytest.mark.asyncio
    async def test_send(self):
        outbox = self.get_outbox()

        assert outbox.send(b"data") is None

        await asyncio.wait_for(outbox._queue.join(), timeout=1)
        self.connection_manager.get_connection.assert_awaited_once_with(self.node)
        self.writer.write.assert_called_once_with(b"data")
        self.writer.drain.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_skips_expired_messages(self):
        # ttl=0 forces all messages to expire
        outbox = self.get_outbox(ttl=0)

        assert outbox.send(b"data") is None

        await asyncio.wait_for(outbox._queue.join(), timeout=1)
        self.writer.write.assert_not_called()
        self.writer.drain.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_send_drops_oldest_message_when_queue_is_full(self):
        outbox = self.get_outbox(maxsize=1)

        outbox.send(b"data1")  # This will be dropped
        outbox.send(b"data2")

        await asyncio.wait_for(outbox._queue.join(), timeout=1)
        self.writer.write.assert_called_once_with(b"data2")
        self.writer.drain.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_keeps_working_when_exception_occurs(self):
        outbox = self.get_outbox()

        connection = Mock()
        connection.writer = self.writer
        self.connection_manager.get_connection.side_effect = [
            ConnectionError(),
            connection,
        ]

        outbox.send(b"data1")  # ConnectionError will cause this to be skipped
        outbox.send(b"data2")

        await asyncio.wait_for(outbox._queue.join(), timeout=1)
        assert self.connection_manager.get_connection.await_count == 2
        self.writer.write.assert_called_once_with(b"data2")
        self.writer.drain.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stop(self):
        outbox = self.get_outbox()
        await outbox.stop()

        with pytest.raises(RuntimeError):
            outbox.send(b"data")

        self.connection_manager.get_connection.assert_not_awaited()
        self.writer.write.assert_not_called()
        self.writer.drain.assert_not_awaited()
