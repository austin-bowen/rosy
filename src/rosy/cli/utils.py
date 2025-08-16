import asyncio
from argparse import ArgumentParser, Namespace
from typing import Iterable

from rosy.discovery.zeroconf import ZeroconfNodeDiscovery
from rosy.specs import MeshTopologySpec


def add_log_arg(parser: ArgumentParser, default: str = 'WARNING') -> None:
    parser.add_argument(
        '--log',
        default=default,
        help='Log level; DEBUG, INFO, ERROR, etc. Default: %(default)s'
    )


async def get_mesh_topology(args: Namespace) -> MeshTopologySpec:
    async with ZeroconfNodeDiscovery(args.domain_id) as discovery:
        await asyncio.sleep(1)
        return discovery.topology


def print_args_and_kwargs(args: Iterable, kwargs: dict) -> None:
    if args:
        print('args:')
        for i, arg in enumerate(args):
            arg = arg_to_str(arg)
            print(f'  {i}: {arg}')

    if kwargs:
        print('kwargs:')
        for key, value in kwargs.items():
            value = arg_to_str(value)
            print(f'  {key}={value}')


def arg_to_str(arg) -> str:
    arg = repr(arg)

    if '\n' in arg:
        arg = f'```\n{arg}\n```'

    return arg
