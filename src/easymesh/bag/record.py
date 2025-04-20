from argparse import Namespace

from easymesh.node.node import MeshNode


async def record(node: MeshNode, args: Namespace) -> None:
    ...


def add_record_args(subparsers) -> None:
    parser = subparsers.add_parser('record', help='Record messages to file')

    parser.add_argument(
        '--output', '-o',
        help='Output file path. Default: record_<date>_<time>.bag',
    )

    parser.add_argument(
        'topics',
        nargs='+',
        help='Topics to record.',
    )
