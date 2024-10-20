import asyncio
import time
from typing import Optional

from easymesh.asyncio import noop
from easymesh.node.node import MeshNode, build_mesh_node
from easymesh.types import Data, Topic


class SpeedTest:
    def __init__(self, node: MeshNode):
        self.node = node

    async def measure_mps(
            self,
            topic: Topic,
            data: Data = None,
            duration: float = 10.,
            warmup: Optional[float] = 1.,
    ) -> float:
        """Measure messages per second."""

        if warmup is not None and warmup > 0.:
            await self.measure_mps(topic, data=data, duration=warmup, warmup=None)

        topic_sender = self.node.get_topic_sender(topic)

        if not await topic_sender.has_listeners():
            raise ValueError(f'No listeners for topic={topic}')

        message_count = 0
        start_time = time.monotonic()

        while (end_time := time.monotonic()) - start_time < duration:
            message = (time.time(), data)
            await topic_sender.send(message)
            await noop()  # Yield to other tasks since this runs as fast as possible and can block other tasks
            message_count += 1

        true_duration = end_time - start_time

        return message_count / true_duration


async def main() -> None:
    node = await build_mesh_node(name='speed-test')

    speed_tester = SpeedTest(node)

    topic = 'test'
    data = None
    # data = b'helloworld' * 100000
    # data = dict(foo=list(range(100)), bar='bar' * 100, baz=dict(a=dict(b=dict(c='c'))))
    # data = (np.random.random_sample((3, 1280, 720)) * 255).astype(np.uint8)
    # data = torch.tensor(data)

    while not await node.topic_has_listeners(topic):
        print('Waiting for listeners...')
        await asyncio.sleep(0.1)

    print('Running speed test...')
    mps = await speed_tester.measure_mps(topic, data=data)
    print(f'mps={mps}')


if __name__ == '__main__':
    asyncio.run(main())
