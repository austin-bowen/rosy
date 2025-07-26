import argparse
import asyncio
import sys

from rosy.bag.main import add_bag_command, bag_main
from rosy.coordinator.main import add_coordinator_command, coordinator_main
from rosy.launch.main import add_launch_command, launch_main

_command_to_main = {
    'coordinator': coordinator_main,
    'bag': bag_main,
    'launch': launch_main,
}

_add_command_functions = [
    add_coordinator_command,
    add_bag_command,
    add_launch_command,
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

    subparsers = parser.add_subparsers(
        dest='command',
        title='commands',
        required=True,
    )

    for add_command in _add_command_functions:
        add_command(subparsers)

    return parser


if __name__ == '__main__':
    main()
