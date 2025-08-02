import asyncio
import logging
import pickle
from argparse import Namespace
from datetime import datetime
from pathlib import Path

from rosy import build_node_from_args
from rosy.argparse import add_node_name_arg
from rosy.cli.utils import add_log_arg


async def record(args: Namespace) -> None:
    logging.basicConfig(level=args.log)

    node = await build_node_from_args(args=args)

    bag_file_path = args.output or get_bag_file_path()

    with open(bag_file_path, 'wb') as bag_file:
        message_counter = 0

        async def callback(topic, *args_, **kwargs_) -> None:
            nonlocal message_counter

            now = datetime.now()
            pickle.dump((now, topic, args_, kwargs_), bag_file)

            message_counter += 1
            if not args.no_dots:
                print('.', end='', flush=True)

        for topic in args.topics:
            await node.listen(topic, callback)

        print(f'Recording topics to "{bag_file_path}":')
        for topic in args.topics:
            print(f'- {topic}')

        try:
            await node.forever()
        except asyncio.CancelledError:
            print('\nRecording stopped.')

    if message_counter == 0:
        print('No messages recorded.')
        bag_file_path.unlink()
    else:
        print(f'Recorded {message_counter} messages to "{bag_file_path}".')


def add_record_args(subparsers) -> None:
    parser = subparsers.add_parser('record', help='Record messages to file')

    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Output file path. Default: record_<YYYY-MM-DD>-<HH-MM-SS>.bag',
    )

    parser.add_argument(
        '--no-dots',
        action='store_true',
        help='Disable logging of "." when a new message is received.'
    )

    add_log_arg(parser)
    add_node_name_arg(parser, default='rosy bag record')

    parser.add_argument(
        'topics',
        nargs='+',
        help='Topics to record.',
    )


def get_bag_file_path() -> Path:
    now = datetime.now()
    now = now.strftime("%Y-%m-%d-%H-%M-%S")
    return Path(f'record_{now}.bag')
