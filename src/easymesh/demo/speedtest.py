import asyncio
import time
from argparse import ArgumentParser, Namespace
from typing import Optional

from easymesh.argparse import add_coordinator_arg
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
            await topic_sender.send(data)
            await noop()  # Yield to other tasks since this runs as fast as possible and can block other tasks
            message_count += 1

        true_duration = end_time - start_time

        return message_count / true_duration

    async def receive(self, topic: Topic) -> None:
        message_count = 0
        last_count = None

        async def handle_message(topic_, data):
            nonlocal message_count
            message_count += 1

        await self.node.add_listener(topic, handle_message)

        sleep_time = 1.
        while True:
            await asyncio.sleep(sleep_time)

            if message_count != last_count:
                mps = (message_count - (last_count or 0)) / sleep_time
                print(f'Received message count: {message_count}; mps={round(mps)}')
                last_count = message_count


async def main() -> None:
    args = _parse_args()

    node = await build_mesh_node(
        name=f'speed-test/{args.role}',
        coordinator_host=args.coordinator.host,
        coordinator_port=args.coordinator.port,
        allow_unix_connections=not args.disable_unix,
        allow_tcp_connections=not args.disable_tcp,
        load_balancer='default' if args.enable_load_balancer else None,
    )

    speed_tester = SpeedTest(node)

    topic = args.topic

    if args.role == 'recv':
        await speed_tester.receive(topic)
    elif args.role == 'send':
        data = None
        # data = b'helloworld' * 100000
        # data = dict(foo=list(range(100)), bar='bar' * 100, baz=dict(a=dict(b=dict(c='c'))))
        # data = (np.random.random_sample((3, 1280, 720)) * 255).astype(np.uint8)
        # data = torch.tensor(data)

        print('Waiting for listeners...')
        await node.wait_for_listener(topic)

        print(f'Running speed test for {args.seconds}s...')
        mps = await speed_tester.measure_mps(topic, data=data, duration=args.seconds)
        print(f'mps={round(mps)}')
    else:
        raise ValueError(f'Invalid role={args.role}')


def _parse_args() -> Namespace:
    parser = ArgumentParser()

    parser.add_argument(
        'role', choices=('send', 'recv'),
        help='Role of the node: sender or receiver.',
    )
    add_coordinator_arg(parser)
    parser.add_argument(
        '--seconds', type=float, default=10.,
        help='How long to run the speed test in seconds. Default: 10',
    )
    parser.add_argument(
        '--topic', default='speed-test',
        help='Topic to send/receive on. Default: speed-test',
    )
    parser.add_argument(
        '--enable-load-balancer', action='store_true',
        help='Enable the default load balancer. It is disabled for speed testing by default.',
    )
    parser.add_argument(
        '--disable-unix', action='store_true',
        help='Disable Unix domain sockets for inter-node connections.',
    )
    parser.add_argument(
        '--disable-tcp', action='store_true',
        help='Disable TCP sockets for inter-node connections.',
    )

    return parser.parse_args()


if __name__ == '__main__':
    asyncio.run(main())
