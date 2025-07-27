import asyncio
import logging
from argparse import Namespace

from rosy import build_node_from_args
from rosy.argparse import get_node_arg_parser
from rosy.cli.utils import add_log_arg


async def main(args: Namespace):
    logging.basicConfig(level=args.log)

    node = await build_node_from_args(args=args)

    topic = node.get_topic(args.topic)

    data = eval(args.data) if args.eval else args.data

    while True:
        if not args.no_wait and not await topic.has_listeners():
            print(f'Waiting for listeners on topic {args.topic!r}...')
            await topic.wait_for_listener()

        print(f'Sending topic={args.topic!r} data={args.data!r}')

        await topic.send(data)

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

    parser.add_argument(
        '--no-wait',
        action='store_true',
        help='Send the message without waiting for any listeners',
    )

    add_log_arg(parser, default='INFO')

    return parser.parse_args()


if __name__ == '__main__':
    asyncio.run(main(parse_args()))
