from argparse import ArgumentParser, Namespace

from rosy.cli.topic.echo import add_echo_command, echo_main
from rosy.cli.topic.list import add_list_command, list_main
from rosy.cli.topic.send import add_send_command, send_main


async def topic_main(args: Namespace) -> None:
    if args.topic_command == 'list':
        await list_main(args)
    elif args.topic_command == 'echo':
        await echo_main(args)
    elif args.topic_command == 'send':
        await send_main(args)
    else:
        raise ValueError(f'Unknown topic command: {args.topic_command}')


def add_topic_command(subparsers) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        'topic',
        description='Topic commands.',
        help='Topic commands like send, echo, etc.',
    )

    subparsers = parser.add_subparsers(
        title='commands',
        dest='topic_command',
        required=True,
    )

    add_list_command(subparsers)
    add_echo_command(subparsers)
    add_send_command(subparsers)
