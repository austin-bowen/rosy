import logging

from rosy.node.codec import NodeMessageCodec
from rosy.node.peer.connection import PeerConnectionManager
from rosy.node.peer.selector import PeerSelector
from rosy.node.topic.types import TopicMessage
from rosy.node.types import Args, KWArgs
from rosy.specs import MeshNodeSpec
from rosy.types import Buffer, Topic
from rosy.utils import ALLOWED_EXCEPTIONS

logger = logging.getLogger(__name__)


class TopicSender:
    def __init__(
            self,
            peer_selector: PeerSelector,
            connection_manager: PeerConnectionManager,
            node_message_codec: NodeMessageCodec,
    ):
        self.peer_selector = peer_selector
        self.connection_manager = connection_manager
        self.node_message_codec = node_message_codec

    async def send(self, topic: Topic, args: Args, kwargs: KWArgs) -> None:
        # TODO handle case of self-sending more efficiently

        nodes = self.peer_selector.get_nodes_for_topic(topic)
        if not nodes:
            return

        message = TopicMessage(topic, args, kwargs)
        data = await self.node_message_codec.encode_topic_message(message)

        [
            await self._send_to_one(n, data)
            for n in nodes
        ]

    async def _send_to_one(self, node: MeshNodeSpec, data: Buffer) -> None:
        try:
            connection = await self.connection_manager.get_connection(node)

            async with connection.writer as writer:
                writer.write(data)
                await writer.drain()
        except ALLOWED_EXCEPTIONS:
            raise
        except Exception as e:
            logger.error(
                f'Error sending topic message to node={node.id}: {e!r}',
            )
