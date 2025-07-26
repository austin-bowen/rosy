from argparse import ArgumentParser, Namespace

from rosy import build_node_from_args
from rosy.argparse import add_node_args
from rosy.bag.info import add_info_args, display_info
from rosy.bag.play import add_play_args, play
from rosy.bag.record import add_record_args, record


async def bag_main(args: Namespace):
    print(args)
    if args.bag_command == 'record':
        node = await build_node_from_args(args=args)
        await record(node, args)
    elif args.bag_command == 'play':
        node = await build_node_from_args(args=args)
        await play(node, args)
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

    add_node_args(
        parser,
        default_node_name='rosy.bag',
    )

    subparsers = parser.add_subparsers(dest='bag_command', required=True)

    add_record_args(subparsers)
    add_play_args(subparsers)
    add_info_args(subparsers)
