import logging
from argparse import ArgumentParser, Namespace
from datetime import datetime

from rosy import build_node_from_args
from rosy.argparse import add_node_args
from rosy.cli.topic.utils import print_args_and_kwargs
from rosy.types import Topic


async def echo_main(args: Namespace):
    logging.basicConfig(level=args.log)

    node = await build_node_from_args(args=args)

    for topic in args.topics:
        await node.listen(topic, handle_message)

    async def echo(service, *args, **kwargs):
        return (service, args, kwargs)
    await node.add_service('my-service', echo)

    print(f'Listening to topics: {args.topics}')
    await node.forever()


async def handle_message(topic: Topic, *args, **kwargs):
    now = datetime.now()
    print(f'[{now}]')

    print(f'topic={topic!r}')
    print_args_and_kwargs(args, kwargs)
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
