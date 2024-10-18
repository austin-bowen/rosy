import time
from typing import Optional

from easymesh.asyncio import noop
from easymesh.node.node import MeshNode
from easymesh.types import Body, Topic


class SpeedTester:
    def __init__(self, node: MeshNode):
        self.node = node

    async def measure_mps(
            self,
            topic: Topic,
            body: Body = None,
            duration: float = 10.,
            warmup: Optional[float] = 1.,
    ) -> float:
        """Measure messages per second."""

        if warmup is not None and warmup > 0.:
            await self.measure_mps(topic, body=body, duration=warmup, warmup=None)

        topic_sender = self.node.get_topic_sender(topic)

        if not await topic_sender.has_listeners():
            raise ValueError(f'No listeners for topic={topic}')

        message_count = 0
        start_time = time.monotonic()

        while (end_time := time.monotonic()) - start_time < duration:
            message = (time.time(), body)
            await topic_sender.send(message)
            await noop()  # Yield to other tasks since this runs as fast as possible and can block other tasks
            message_count += 1

        true_duration = end_time - start_time

        return message_count / true_duration
