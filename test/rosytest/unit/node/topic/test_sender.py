from unittest.mock import AsyncMock, Mock

import pytest

from rosy.asyncio import LockableWriter
from rosy.node.codec import NodeMessageCodec
from rosy.node.peer.connection import PeerConnection
from rosy.node.peer.selector import PeerSelector
from rosy.node.topic.outbox import NodeOutbox, NodeOutboxManager
from rosy.node.topic.sender import TopicSender
from rosy.node.topic.types import TopicMessage
from rosy.specs import MeshNodeSpec


class TestTopicSender:
    def setup_method(self) -> None:
        self.connection = AsyncMock(spec=PeerConnection)
        self.connection.writer = AsyncMock(spec=LockableWriter)
        self.connection.writer.__aenter__.return_value = self.connection.writer

        self.nodes = [
            Mock(spec=MeshNodeSpec),
            Mock(spec=MeshNodeSpec),
        ]

        self.peer_selector = AsyncMock(spec=PeerSelector)
        self.peer_selector.get_nodes_for_topic.return_value = self.nodes

        self.encoded_data = b"encoded data"
        self.node_message_codec = AsyncMock(spec=NodeMessageCodec)
        self.node_message_codec.encode_topic_message.return_value = self.encoded_data

        self.outboxes = [
            AsyncMock(spec=NodeOutbox),
            AsyncMock(spec=NodeOutbox),
        ]
        self.outbox_manager = AsyncMock(spec=NodeOutboxManager)
        self.outbox_manager.get_outbox.side_effect = lambda n: {
            self.nodes[0]: self.outboxes[0],
            self.nodes[1]: self.outboxes[1],
        }[n]

        self.topic_sender = TopicSender(
            self.peer_selector,
            self.node_message_codec,
            self.outbox_manager,
        )

    @pytest.mark.asyncio
    async def test_send(self):
        message = TopicMessage("topic", ["arg"], {"key": "value"})

        await self.topic_sender.send(message.topic, message.args, message.kwargs)

        self.peer_selector.get_nodes_for_topic.assert_called_once_with(message.topic)
        self.node_message_codec.encode_topic_message.assert_awaited_once_with(message)

        assert self.outbox_manager.get_outbox.call_count == 2
        self.outboxes[0].send.assert_called_once_with(self.encoded_data)
        self.outboxes[1].send.assert_called_once_with(self.encoded_data)

    @pytest.mark.asyncio
    async def test_send_with_no_listening_nodes(self):
        self.peer_selector.get_nodes_for_topic.return_value = []

        message = TopicMessage("topic", ["arg"], {"key": "value"})

        await self.topic_sender.send(message.topic, message.args, message.kwargs)

        self.peer_selector.get_nodes_for_topic.assert_called_once_with(message.topic)
        self.node_message_codec.encode_topic_message.assert_not_awaited()
        self.outbox_manager.get_outbox.assert_not_called()
        self.outboxes[0].send.assert_not_called()
        self.outboxes[1].send.assert_not_called()
