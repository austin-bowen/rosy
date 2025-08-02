import asyncio
import time
from argparse import ArgumentParser, Namespace

from rosy import Node, build_node
from rosy.types import Topic


async def speedtest_main(args: Namespace) -> None:
    load_balancer = 'default' if args.enable_load_balancer else None

    node = await build_node(
        name=f'speed-test/{args.role}',
        coordinator_host=args.coordinator.host,
        coordinator_port=args.coordinator.port,
        allow_unix_connections=not args.disable_unix,
        allow_tcp_connections=not args.disable_tcp,
        data_codec=args.codec,
        authkey=args.authkey,
        topic_load_balancer=load_balancer,
        service_load_balancer=load_balancer,
    )

    speed_tester = SpeedTest(node)

    topic = args.topic

    if args.role == 'recv':
        await speed_tester.receive(topic)
    elif args.role == 'send':
        print('Waiting for listeners...')
        await node.wait_for_listener(topic)

        print(f'Running speed test for {args.seconds}s '
              f'with message_size={args.message_size}...')
        mps = await speed_tester.measure_mps(
            topic,
            message_size=args.message_size,
            duration=args.seconds,
        )
        print(f'[{node}] mps={round(mps)}')
    else:
        raise ValueError(f'Invalid role={args.role}')


class SpeedTest:
    def __init__(self, node: Node):
        self.node = node

    async def measure_mps(
            self,
            topic: Topic,
            message_size: int = 0,
            duration: float = 10.,
            warmup: float | None = 1.,
    ) -> float:
        """Measure messages per second."""

        topic_sender = self.node.get_topic(topic)

        if not await topic_sender.has_listeners():
            raise ValueError(f'No listeners for topic={topic}')

        dummy_data = 'A' * message_size

        if warmup is not None and warmup > 0.:
            end_time = time.monotonic() + warmup
            while time.monotonic() < end_time:
                await self.node.send('warmup')

        message_count = 0
        start_time = time.monotonic()

        while (end_time := time.monotonic()) - start_time < duration:
            send_time = time.time()
            data = send_time, dummy_data
            await topic_sender.send(data)
            message_count += 1

        true_duration = end_time - start_time

        await self.node.send('stop')

        return message_count / true_duration

    async def receive(self, topic: Topic) -> None:
        message_count = 0
        last_count = None
        avg_latency = 0.
        stop_signal = asyncio.locks.Event()

        async def handle_warmup(topic_):
            pass

        async def handle_message(topic_, data_):
            nonlocal message_count, avg_latency

            now = time.time()
            send_time = data_[0]
            dt = now - send_time

            message_count += 1
            avg_latency += (dt - avg_latency) / message_count

        async def handle_stop(topic_):
            print(f'[{self.node}] Received stop signal')
            stop_signal.set()

        await self.node.listen('warmup', handle_warmup)
        await self.node.listen(topic, handle_message)
        await self.node.listen('stop', handle_stop)

        sleep_time = 1.
        while not stop_signal.is_set():
            await asyncio.sleep(sleep_time)

            if message_count != last_count:
                mps = (message_count - (last_count or 0)) / sleep_time
                print(f'[{self.node}] Received message count: {message_count}; mps={round(mps)}')
                last_count = message_count

                print(f'[{self.node}] Avg latency: {avg_latency}s')


def add_speedtest_command(subparsers) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        'speedtest',
        description='Run a speed test between two nodes.',
        help='Run a speed test',
    )

    parser.add_argument(
        'role', choices=('send', 'recv'),
        help='Role of the node: sender or receiver.',
    )
    parser.add_argument(
        '--seconds', type=float, default=10.,
        help='How long to run the speed test in seconds. Default: %(default)s',
    )
    parser.add_argument(
        '--topic', default='t',
        help='Topic to send/receive on. Default: %(default)s',
    )
    parser.add_argument(
        '--message-size', type=int, default=0,
        help='Size of the message to send in bytes. Default: 0 (no data).',
    )
    parser.add_argument(
        '--codec',
        choices=('pickle', 'json', 'msgpack'),
        default='pickle',
        help='Codec to use for encoding/decoding messages. Default: %(default)s.',
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
