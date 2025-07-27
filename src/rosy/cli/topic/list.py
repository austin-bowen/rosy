import logging
from argparse import ArgumentParser, Namespace

from rosy.argparse import add_authkey_arg, add_coordinator_arg
from rosy.authentication import optional_authkey_authenticator
from rosy.coordinator.client import build_coordinator_client


async def list_main(args: Namespace):
    logging.basicConfig(level=args.log)

    authenticator = optional_authkey_authenticator(args.authkey)
    coordinator_client = await build_coordinator_client(
        host=args.coordinator.host,
        port=args.coordinator.port,
        authenticator=authenticator,
        reconnect_timeout=None,
    )

    topology = await coordinator_client.get_topology()

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

    parser.add_argument(
        '--log',
        default='ERROR',
        help='Log level; DEBUG, INFO, ERROR, etc. Default: %(default)s'
    )

    add_coordinator_arg(parser)
    add_authkey_arg(parser)
