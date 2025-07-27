import logging
from argparse import ArgumentParser, Namespace

from rosy.argparse import add_authkey_arg, add_coordinator_arg
from rosy.authentication import optional_authkey_authenticator
from rosy.cli.utils import add_log_arg, get_mesh_topology
from rosy.coordinator.client import build_coordinator_client


async def list_main(args: Namespace):
    logging.basicConfig(level=args.log)

    topology = await get_mesh_topology(args)

    services = sorted({
        service
        for node in topology.nodes
        for service in node.services
    })

    for service in services:
        print(service)


def add_list_command(subparsers) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        'list',
        description='List all services currently being provided by nodes.',
        help='list services being provided',
    )

    add_log_arg(parser)

    add_coordinator_arg(parser)
    add_authkey_arg(parser)
