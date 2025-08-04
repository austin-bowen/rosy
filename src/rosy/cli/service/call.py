import argparse
import asyncio
import logging
from argparse import ArgumentParser, Namespace
from datetime import datetime

from rosy import build_node_from_args
from rosy.argparse import add_node_name_arg
from rosy.cli.topic.send import parse_args_and_kwargs
from rosy.cli.utils import add_log_arg, print_args_and_kwargs


async def call_main(args: Namespace):
    logging.basicConfig(level=args.log)

    # Sanity check
    parse_args_and_kwargs(args.args)

    node = await build_node_from_args(args=args)

    service = node.get_service(args.service)

    async def call_once():
        if not args.no_wait and not await service.has_providers():
            print(f'Waiting for providers...')
            await service.wait_for_provider()

        service_args, service_kwargs = parse_args_and_kwargs(args.args)

        now = datetime.now()
        print(f'[{now}]')
        print(f'Calling service={args.service!r}')
        print_args_and_kwargs(service_args, service_kwargs)

        response = await service.call(*service_args, **service_kwargs)
        print(f'Response: {response!r}')
        print()

    if args.interval < 0:
        await call_once()
        return

    while True:
        await call_once()
        await asyncio.sleep(args.interval)


def add_call_command(subparsers) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        'call',
        description='''
Start a node that calls a service with the given arguments.

---

Simple example:
    rosy service call my-service "'hello world'" 42 pi=3.14

This will call service `my-service` with args `'hello world'` and 42, and keyword arg `pi=3.14`.

---

Intermediate example:
    rosy service call my-service "{'key': 'value', 'data': [1, 2, 3]}"

This will call the service with a dictionary as an argument.

---

Advanced example:
    rosy service call my-service "call:myproj.MyData('data', pi=3.14)" "send_time=call:time.time()"

This will call the specified class/function to populate the arguments.

---
'''.strip(),
        help='call a service',
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        'service',
        help='The service to call.',
    )

    parser.add_argument(
        'args',
        nargs='*',
        metavar='arg/kwarg',
        help='''
Arg(s) and/or kwarg(s) to call the service with.
Each arg must be a valid Python expression,
or follow the format:
`call:module.callable(*args, **kwargs)`
'''.strip(),
    )

    parser.add_argument(
        '--interval', '-i',
        default=-1,
        type=float,
        help='The interval in seconds to make calls. A value < 0 will '
             'cause the call to be made only once. Default: %(default)s',
    )

    parser.add_argument(
        '--no-wait',
        action='store_true',
        help='Send the message without waiting for any listeners',
    )

    add_log_arg(parser)

    add_node_name_arg(
        parser,
        default='rosy service call',
    )
