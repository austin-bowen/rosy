from argparse import ArgumentParser, Namespace

from rosy.cli.bag.info import add_info_args, display_info
from rosy.cli.bag.play import add_play_args, play
from rosy.cli.bag.record import add_record_args, record


async def bag_main(args: Namespace):
    if args.bag_command == 'record':
        await record(args)
    elif args.bag_command == 'play':
        await play(args)
    elif args.bag_command == 'info':
        await display_info(args)
    else:
        raise ValueError(f'Unknown command: {args.bag_command}')


def add_bag_command(subparsers) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        'bag',
        description='Tool for recording and playing back topic messages. '
                    'Based on the `ros2 bag` ROS command line tool.',
        help='Record and play back topic messages',
    )

    subparsers = parser.add_subparsers(
        title='commands',
        dest='bag_command',
        required=True,
    )

    add_record_args(subparsers)
    add_play_args(subparsers)
    add_info_args(subparsers)
