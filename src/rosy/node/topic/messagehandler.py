import logging

from rosy.node.topic.listenermanager import TopicListenerManager
from rosy.node.topic.types import TopicMessage
from rosy.utils import ALLOWED_EXCEPTIONS

logger = logging.getLogger(__name__)


class TopicMessageHandler:
    def __init__(
            self,
            listener_manager: TopicListenerManager,
    ):
        self.listener_manager = listener_manager

    async def handle_message(self, message: TopicMessage) -> None:
        callback = self.listener_manager.get_callback(message.topic)

        if not callback:
            logger.warning(
                f'Received message for topic={message.topic!r} '
                f'but no listener is registered.'
            )

        try:
            await callback(message.topic, *message.args, **message.kwargs)
        except ALLOWED_EXCEPTIONS:
            raise
        except Exception as e:
            logger.exception(
                f'Error calling callback={callback} '
                f'for topic={message.topic!r} '
                f'with args={message.args!r} '
                f'and kwargs={message.kwargs!r}',
                exc_info=e,
            )
