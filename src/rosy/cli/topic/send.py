import argparse
import asyncio
import importlib
import logging
import re
from argparse import ArgumentParser, Namespace
from ast import literal_eval
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from rosy import Node, build_node_from_args
from rosy.argparse import add_node_name_arg
from rosy.cli.utils import add_log_arg, print_args_and_kwargs


async def send_main(args: Namespace):
    logging.basicConfig(level=args.log)

    # Sanity check
    parse_args_and_kwargs(args.args)

    async with await build_node_from_args(args=args) as node:
        await _send_main(args, node)


async def _send_main(args: Namespace, node: Node) -> None:
    topic = node.get_topic(args.topic)

    async def send_once():
        if not args.no_wait and not await topic.has_listeners():
            print("Waiting for listeners...")
            await topic.wait_for_listener()
            print()

        topic_args, topic_kwargs = parse_args_and_kwargs(args.args)

        now = datetime.now()
        print(f"[{now}]")
        print(f"Sending to topic={args.topic!r}")
        print_args_and_kwargs(topic_args, topic_kwargs)

        await topic.send(*topic_args, **topic_kwargs)

    await send_once()

    while args.interval >= 0:
        await asyncio.sleep(args.interval)
        print()
        await send_once()


def parse_args_and_kwargs(args: Iterable[str]) -> tuple[list[Any], dict[str, Any]]:
    topic_args = []
    topic_kwargs = {}

    for arg in args:
        key, value = key_value_from_str(arg)

        if key is None:
            if topic_kwargs:
                raise ValueError(
                    f'Positional argument {arg!r} must come '
                    f'before the keyword arguments.'
                )

            topic_args.append(value)
        else:
            topic_kwargs[key] = value

    return topic_args, topic_kwargs


def key_value_from_str(value: str) -> tuple[str | None, Any]:
    match = re.match(
        r'^([A-Za-z_][\w_]*)=(.*)$',
        value,
    )

    if match:
        key, value = match.groups()
        return key, value_from_str(value)
    else:
        return None, value_from_str(value)


def value_from_str(value: str) -> Any:
    match = re.match(
        # prefix
        r'^call:'
        # module name
        r'([\w.]+)\.'
        # callable name
        r'(\w+)'
        # args
        r'\((.*)\)'
        r'$',
        value
    )

    if not match:
        return literal_eval(value)

    module, callable_, args = match.groups()
    module = importlib.import_module(module)
    callable_ = getattr(module, callable_)
    result = eval(f'callable({args})', {}, dict(callable=callable_))
    return result


def add_send_command(subparsers) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        'send',
        description='''
Start a node that sends messages to a topic.

---

Simple example:
    rosy topic send my-topic "'hello world'" 42 pi=3.14

This will send a message to the topic `my-topic` with args `'hello world'` and 42, and keyword arg `pi=3.14`.

---

Intermediate example:
    rosy topic send my-topic "{'key': 'value', 'data': [1, 2, 3]}"

This will send a message with a dictionary as an argument.

---

Advanced example:
    rosy topic send my-topic "call:myproj.MyData('data', pi=3.14)" "send_time=call:time.time()"

This will call the specified class/function to populate the arguments.

---
'''.strip(),
        help='send messages to a topic',
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        'topic',
        help='The topic to send to.',
    )

    parser.add_argument(
        'args',
        nargs='*',
        metavar='arg/kwarg',
        help='''
Arg(s) and/or kwarg(s) to send to the topic.
Each arg must be a valid Python expression,
or follow the format:
`call:module.callable(*args, **kwargs)`
'''.strip(),
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

    add_log_arg(parser)

    add_node_name_arg(
        parser,
        default='rosy topic send',
    )
