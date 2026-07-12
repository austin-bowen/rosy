import logging
from argparse import ArgumentParser, Namespace
from datetime import datetime

from rosy import build_node_from_args
from rosy.argparse import add_node_name_arg
from rosy.cli.utils import add_log_arg, print_args_and_kwargs
from rosy.types import Topic


def echo_main(args: Namespace):
    logging.basicConfig(level=args.log)

    with build_node_from_args(args=args) as node:
        print(f"Listening to topics: {args.topics}")

        for topic in args.topics:
            node.listen(topic, handle_message)

        node.forever()


def handle_message(topic: Topic, *args, **kwargs):
    now = datetime.now()
    print(f"\n[{now}]")

    print(f"topic={topic!r}")
    print_args_and_kwargs(args, kwargs)


def add_echo_command(subparsers) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        "echo",
        description="Start a node that listens to topics and prints received messages.",
        help="listen to topics",
    )

    parser.add_argument(
        "topics",
        nargs="+",
        metavar="topic",
        help="The topic(s) to listen to.",
    )

    add_log_arg(parser)

    add_node_name_arg(
        parser,
        default="rosy topic echo",
    )
