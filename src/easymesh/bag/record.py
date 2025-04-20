from argparse import Namespace
from datetime import datetime
from pathlib import Path

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


def get_bag_file_path() -> Path:
    now = datetime.now()
    now = now.strftime("%Y-%m-%d-%H-%M-%S")
    return Path(f'record_{now}.bag')
