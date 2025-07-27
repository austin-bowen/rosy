from argparse import ArgumentParser, Namespace

from rosy.cli.node.list import add_list_command, list_main


async def node_main(args: Namespace) -> None:
    if args.node_command == 'list':
        await list_main(args)
    else:
        raise ValueError(f'Unknown node command: {args.node_command}')


def add_node_command(subparsers) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        'node',
        description='Node commands.',
        help='Node commands like list',
    )

    subparsers = parser.add_subparsers(
        title='commands',
        dest='node_command',
        required=True,
    )

    add_list_command(subparsers)
