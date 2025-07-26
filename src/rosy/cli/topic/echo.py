import logging
from argparse import ArgumentParser, Namespace
from datetime import datetime

from rosy import build_node_from_args
from rosy.argparse import add_node_args
from rosy.types import Topic


async def echo_main(args: Namespace):
    logging.basicConfig(level=args.log)

    node = await build_node_from_args(args=args)

    for topic in args.topics:
        await node.listen(topic, handle_message)

    print(f'Listening to topics: {args.topics}')
    await node.forever()


async def handle_message(topic: Topic, *args_, **kwargs_):
    now = datetime.now()
    print(f'[{now}]')

    print(f'topic={topic!r}')

    if args_:
        print('args:')
        for i, arg in enumerate(args_):
            print(f'  {i}: {arg!r}')

    if kwargs_:
        print('kwargs:')
        for key, value in kwargs_.items():
            print(f'  {key}={value!r}')

    print()


def add_echo_command(subparsers) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        'echo',
        description='Start a node that listens to topics and prints received messages.',
        help='listen to topics',
    )

    parser.add_argument(
        'topics',
        nargs='+',
        metavar='topic',
        help='The topic(s) to listen to.',
    )

    parser.add_argument(
        '--log',
        default='ERROR',
        help='Log level; DEBUG, INFO, ERROR, etc. Default: %(default)s'
    )

    add_node_args(
        parser,
        default_node_name='rosy topic echo',
    )
