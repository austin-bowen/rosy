import argparse
import asyncio
from argparse import Namespace

from easymesh.bag.play import add_play_args
from easymesh.bag.record import add_record_args


async def main(args: Namespace):
    print(args)


def parse_args() -> Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)

    add_record_args(subparsers)
    add_play_args(subparsers)

    return parser.parse_args()


if __name__ == '__main__':
    asyncio.run(main(parse_args()))
