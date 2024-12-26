import asyncio
from argparse import Namespace
from datetime import datetime

from easymesh import build_mesh_node_from_args
from easymesh.argparse import get_node_arg_parser


async def main(args: Namespace):
    node = await build_mesh_node_from_args(args=args)

    def log(msg_) -> None:
        now = datetime.now()
        print(f'[{now}] [{node.id.name}] {msg_}')

    topic_sender = node.get_topic_sender(args.topic)

    data = eval(args.data) if args.eval else args.data

    while True:
        log(f'Sending topic={args.topic!r} data={args.data!r}')

        if not await topic_sender.has_listeners():
            log(f'WARNING: No listeners on topic {args.topic!r}.')

        await topic_sender.send(data)

        if args.interval < 0:
            return
        await asyncio.sleep(args.interval)


def parse_args() -> Namespace:
    parser = get_node_arg_parser(default_node_name='sender')

    parser.add_argument(
        '--topic', '-t',
        default='some-topic',
        help='The topic to send to. Default: %(default)s',
    )

    parser.add_argument(
        '--data', '-d',
        default='Hello, world!',
        help='The data to send. By default, data is interpreted as a string. '
             'Use the `--eval` flag to interpret it as Python code. '
             'Default: %(default)s',
    )

    parser.add_argument(
        '--eval', '-e',
        action='store_true',
        help='Evaluate the data as Python code. Default: %(default)s',
    )

    parser.add_argument(
        '--interval', '-i',
        default=-1,
        type=float,
        help='The interval in seconds to send messages. A value < 0 will '
             'cause the message to be sent only once. Default: %(default)s',
    )

    return parser.parse_args()


if __name__ == '__main__':
    asyncio.run(main(parse_args()))
