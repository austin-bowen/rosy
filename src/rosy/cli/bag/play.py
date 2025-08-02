import asyncio
import logging
from argparse import Namespace
from datetime import datetime
from pathlib import Path

from rosy import build_node_from_args
from rosy.argparse import add_node_name_arg
from rosy.cli.bag.file import get_bag_file_messages, get_most_recent_bag_file_path
from rosy.cli.utils import add_log_arg, print_args_and_kwargs
from rosy.utils import require


async def play(args: Namespace) -> None:
    logging.basicConfig(level=args.log)

    node = await build_node_from_args(args=args)

    bag_file_path = args.input or get_most_recent_bag_file_path()

    print(f'Playing back messages from "{bag_file_path}"...')

    first_instant = None
    first_sent_instant = datetime.now()

    for instant, topic, args_, kwargs_ in get_bag_file_messages(bag_file_path):
        if not first_instant:
            first_instant = instant
        elif not args.immediate:
            await _wait_for_next_send(
                first_instant,
                first_sent_instant,
                instant,
                args.rate,
            )

        await node.send(topic, *args_, **kwargs_)

        if not args.no_log:
            print(f'[{instant}] topic={topic!r}')
            if not args.no_log_args:
                print_args_and_kwargs(args_, kwargs_)
                print()


def add_play_args(subparsers) -> None:
    parser = subparsers.add_parser('play', help='Playback recorded messages from file')

    parser.add_argument(
        '--input', '-i',
        type=Path,
        help='Input file path. Default: The most recent '
             'record_*.bag file in the current directory.',
    )

    parser.add_argument(
        '--rate', '-r',
        type=float,
        default=1.0,
        help='Playback rate. Default: %(default)s',
    )

    parser.add_argument(
        '--immediate',
        action='store_true',
        help='Send messages immediately without waiting for the next send time.',
    )

    parser.add_argument(
        '--no-log',
        action='store_true',
        help='Do not log sent messages to the console.',
    )

    parser.add_argument(
        '--no-log-args',
        action='store_true',
        help='Do not log args/kwargs from sent messages to the console.',
    )

    add_log_arg(parser)
    add_node_name_arg(parser, default='rosy bag play')


async def _wait_for_next_send(
        first_instant: datetime,
        first_sent_instant: datetime,
        instant: datetime,
        rate: float,
) -> None:
    require(rate > 0, f'Rate must be greater than 0; got {rate}')

    dt = (instant - first_instant) / rate
    send_instant = first_sent_instant + dt
    now = datetime.now()
    wait_time = (send_instant - now).total_seconds()

    await asyncio.sleep(wait_time)
