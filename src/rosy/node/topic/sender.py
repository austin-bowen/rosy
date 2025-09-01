import logging

from rosy.node.codec import NodeMessageCodec
from rosy.node.peer.selector import PeerSelector
from rosy.node.topic.outbox import NodeOutboxManager
from rosy.node.topic.types import TopicMessage
from rosy.node.types import Args, KWArgs
from rosy.types import Topic

logger = logging.getLogger(__name__)


class TopicSender:
    def __init__(
        self,
        peer_selector: PeerSelector,
        node_message_codec: NodeMessageCodec,
        outbox_manager: NodeOutboxManager,
    ):
        self.peer_selector = peer_selector
        self.node_message_codec = node_message_codec
        self.outbox_manager = outbox_manager

    async def send(self, topic: Topic, args: Args, kwargs: KWArgs) -> None:
        # TODO handle case of self-sending more efficiently

        nodes = self.peer_selector.get_nodes_for_topic(topic)
        if not nodes:
            return

        message = TopicMessage(topic, args, kwargs)
        data = await self.node_message_codec.encode_topic_message(message)

        for node in nodes:
            outbox = self.outbox_manager.get_outbox(node)
            outbox.send(data)
