from argparse import Namespace


async def play(args: Namespace) -> None:
    ...


def add_play_args(subparsers) -> None:
    parser = subparsers.add_parser('play', help='Playback recorded messages from file')
    parser.add_argument(
        '--input',
        type=str,
        help='Input file path. Default: The most recent '
             'record_*.bag file in the current directory.',
    )
    parser.add_argument(
        '--speed',
        type=float,
        default=1.0,
        help='Playback speed. Default: %(default)s',
    )
