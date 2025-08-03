import logging
from argparse import ArgumentParser, Namespace

from rosy.argparse import add_authkey_arg, add_coordinator_arg
from rosy.cli.utils import add_log_arg, get_mesh_topology
from rosy.specs import MeshNodeSpec


async def list_main(args: Namespace):
    logging.basicConfig(level=args.log)

    topology = await get_mesh_topology(args)

    nodes = sorted(topology.nodes, key=lambda n: n.id)

    print(f'{len(nodes)} nodes:')
    for node in nodes:
        print()
        print_node(node, args.verbose)


def print_node(node: MeshNodeSpec, verbose: bool) -> None:
    print(node.id)

    if verbose:
        print(f'- UUID: {node.id.uuid}')

    if node.topics:
        print('- topics:')
        for topic in sorted(node.topics):
            print(f'  - {topic!r}')
    else:
        print('- topics: none')

    if node.services:
        print('- services:')
        for service in sorted(node.services):
            print(f'  - {service!r}')
    else:
        print('- services: none')

    if verbose:
        print('- supported connection methods:')
        for conn in node.connection_specs:
            print(f'  - {conn}')


def add_list_command(subparsers) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        'list',
        description='List all nodes in the mesh.',
        help='list nodes in the mesh',
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print all info about each node, including UUIDs and connection methods.',
    )

    add_log_arg(parser)
