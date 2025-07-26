from argparse import ArgumentParser, Namespace

from rosy.cli.topic.echo import add_echo_command, echo_main


async def topic_main(args: Namespace) -> None:
    if args.topic_command == 'echo':
        await echo_main(args)
    else:
        raise ValueError(f'Unknown topic command: {args.topic_command}')


def add_topic_command(subparsers) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        'topic',
        description='Topic commands.',
        help='topic commands like send, echo, etc.',
    )

    subparsers = parser.add_subparsers(
        title='commands',
        dest='topic_command',
        required=True,
    )

    add_echo_command(subparsers)
