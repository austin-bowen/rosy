from argparse import ArgumentParser, Namespace

from rosy.cli.service.call import add_call_command, call_main
from rosy.cli.service.list import add_list_command, list_main


async def service_main(args: Namespace) -> None:
    if args.service_command == 'list':
        await list_main(args)
    elif args.service_command == 'call':
        await call_main(args)
    else:
        raise ValueError(f'Unknown service command: {args.service_command}')


def add_service_command(subparsers) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        'service',
        description='Service commands.',
        help='Service commands like list and call',
    )

    subparsers = parser.add_subparsers(
        title='commands',
        dest='service_command',
        required=True,
    )

    add_list_command(subparsers)
    add_call_command(subparsers)
