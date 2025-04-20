import asyncio
from argparse import Namespace

from easymesh import build_mesh_node_from_args
from easymesh.argparse import get_node_arg_parser
from easymesh.bag.play import add_play_args, play
from easymesh.bag.record import add_record_args, record


async def main(args: Namespace):
    node = await build_mesh_node_from_args(args=args)

    if args.command == 'record':
        await record(node, args)
    elif args.command == 'play':
        await play(node, args)
    else:
        raise ValueError(f'Unknown command: {args.command}')


def parse_args() -> Namespace:
    parser = get_node_arg_parser(default_node_name='bag')

    subparsers = parser.add_subparsers(dest='command', required=True)

    add_record_args(subparsers)
    add_play_args(subparsers)

    return parser.parse_args()


if __name__ == '__main__':
    asyncio.run(main(parse_args()))
