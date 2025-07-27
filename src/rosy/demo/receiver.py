import asyncio
import logging
from argparse import Namespace

from rosy import build_node_from_args
from rosy.argparse import get_node_arg_parser
from rosy.cli.utils import add_log_arg


async def main(args: Namespace):
    logging.basicConfig(level=args.log)

    node = await build_node_from_args(args=args)

    async def handle_message(topic, *args_, **kwargs_):
        print(f'Received topic={topic!r} args={args_!r} kwargs={kwargs_!r}')

    for topic in args.topics:
        await node.listen(topic, handle_message)

    print(f'Listening to topics: {args.topics}')
    await node.forever()


def parse_args() -> Namespace:
    parser = get_node_arg_parser(default_node_name='receiver')

    parser.add_argument(
        '--topics', '-t',
        nargs='+',
        default=['some-topic'],
        help='The topics to listen to. Default: %(default)s',
    )

    add_log_arg(parser, default='INFO')

    return parser.parse_args()


if __name__ == '__main__':
    asyncio.run(main(parse_args()))
