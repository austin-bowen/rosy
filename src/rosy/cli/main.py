import argparse
import asyncio
import sys

from rosy.argparse import add_authkey_arg, add_coordinator_arg
from rosy.cli.bag.main import add_bag_command, bag_main
from rosy.cli.coordinator import add_coordinator_command, coordinator_main
from rosy.cli.launch.main import add_launch_command, launch_main
from rosy.cli.node.main import add_node_command, node_main
from rosy.cli.service.main import add_service_command, service_main
from rosy.cli.speedtest import add_speedtest_command, speedtest_main
from rosy.cli.topic.main import add_topic_command, topic_main
from rosy.version import __version__

_command_to_main = {
    'coordinator': coordinator_main,
    'bag': bag_main,
    'launch': launch_main,
    'node': node_main,
    'topic': topic_main,
    'service': service_main,
    'speedtest': speedtest_main,
}

_add_command_functions = [
    add_coordinator_command,
    add_bag_command,
    add_launch_command,
    add_node_command,
    add_topic_command,
    add_service_command,
    add_speedtest_command,
]


def main() -> None:
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        pass


async def _main():
    parser = get_arg_parser()

    args = sys.argv[1:] or ['coordinator']
    args = parser.parse_args(args)

    command_main = _command_to_main.get(args.command)
    await command_main(args)


def get_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='rosy CLI',
    )

    add_coordinator_arg(parser)
    add_authkey_arg(parser)

    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'%(prog)s {__version__}',
    )

    subparsers = parser.add_subparsers(
        title='commands',
        dest='command',
        required=True,
    )

    for add_command in _add_command_functions:
        add_command(subparsers)

    return parser
