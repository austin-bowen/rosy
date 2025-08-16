import logging
from argparse import ArgumentParser, Namespace

from rosy.cli.utils import add_log_arg, get_mesh_topology


async def list_main(args: Namespace):
    logging.basicConfig(level=args.log)

    topology = await get_mesh_topology(args)

    topics = sorted({
        topic
        for node in topology.nodes
        for topic in node.topics
    })

    for topic in topics:
        print(topic)


def add_list_command(subparsers) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        'list',
        description='List all topics currently being listened to by nodes.',
        help='list topics being listened to',
    )

    add_log_arg(parser)
