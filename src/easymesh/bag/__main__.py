import argparse
import asyncio
from argparse import Namespace


async def main(args: Namespace):
    print(args)


def parse_args() -> Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)

    record_parser = subparsers.add_parser('record', help='Record messages to file')
    record_parser.add_argument(
        '--output', '-o',
        help='Output file path. Default: record_<date>_<time>.bag',
    )
    record_parser.add_argument(
        'topics',
        nargs='+',
        help='Topics to record.',
    )

    play_parser = subparsers.add_parser('play', help='Playback recorded messages from file')
    play_parser.add_argument(
        '--input',
        type=str,
        help='Input file path. Default: The most recent '
             'record_*.bag file in the current directory.',
    )
    play_parser.add_argument(
        '--speed',
        type=float,
        default=1.0,
        help='Playback speed. Default: %(default)s',
    )

    return parser.parse_args()


if __name__ == '__main__':
    asyncio.run(main(parse_args()))
