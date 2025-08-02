from argparse import ArgumentParser
from collections.abc import Callable
from urllib.parse import urlparse

from rosy.coordinator.constants import DEFAULT_COORDINATOR_PORT
from rosy.types import Endpoint, Port


def get_node_arg_parser(
        default_node_name: str = None,
        default_coordinator: Endpoint = None,
        default_authkey: bytes = None,
        **kwargs,
) -> ArgumentParser:
    """
    Returns an argument parser with the following node-specific arguments:
    - `--name`
    - `--coordinator HOST[:PORT]`
    - `--authkey`

    Args:
        default_node_name:
            Default node name. If not given, the argument `--name` is required.
        default_coordinator:
            Default coordinator endpoint. If not given, the argument will
            default to `localhost:DEFAULT_COORDINATOR_PORT`.
        default_authkey:
            Default authentication key. If not given, the argument will
            default to `None` (i.e. no auth key).
        **kwargs:
            These are passed to the `ArgumentParser` constructor.
    """

    parser = ArgumentParser(**kwargs)
    add_node_args(parser, default_node_name, default_coordinator, default_authkey)
    return parser


def add_node_args(
        parser: ArgumentParser,
        default_node_name: str = None,
        default_coordinator: Endpoint = None,
        default_authkey: bytes = None,
) -> None:
    """
    Adds node-specific arguments to an argument parser:
    - `--name`
    - `--coordinator HOST[:PORT]`
    - `--authkey`

    Args:
        parser:
            Argument parser to which the arguments will be added.
        default_node_name:
            Default node name. If not given, the argument is required.
        default_coordinator:
            Default coordinator endpoint. If not given, the argument will
            default to `localhost:DEFAULT_COORDINATOR_PORT`.
        default_authkey:
            Default authentication key. If not given, the argument will
            default to `None` (i.e. no auth key).
    """

    add_node_name_arg(parser, default_node_name)
    add_coordinator_arg(parser, default_coordinator)
    add_authkey_arg(parser, default_authkey)


def add_node_name_arg(parser: ArgumentParser, default: str = None) -> None:
    """
    Adds a `--name` argument to an argument parser.

    Args:
        parser:
            Argument parser to which the argument will be added.
        default:
            Default node name. If not given, the argument will be required.
    """

    arg_args = dict(
        default=default,
        help='Node name. Default: %(default)s',
    ) if default is not None else dict(
        required=True,
        help='Node name.',
    )

    parser.add_argument('--name', **arg_args)


def add_coordinator_arg(
        parser: ArgumentParser,
        default: Endpoint = None,
) -> None:
    """
    Adds a `--coordinator HOST[:PORT]` argument to an argument parser.

    Args:
        parser:
            Argument parser to which the argument will be added.
        default:
            Default coordinator endpoint. If not given, the argument will
            default to `localhost:DEFAULT_COORDINATOR_PORT`.
    """

    if default is None:
        default = Endpoint('localhost', DEFAULT_COORDINATOR_PORT)

    parser.add_argument(
        '--coordinator',
        default=default,
        type=endpoint_arg(default_port=default.port),
        metavar='HOST[:PORT]',
        help=f'Coordinator host and port. Default: %(default)s',
    )


def add_authkey_arg(
        parser: ArgumentParser,
        default: bytes = None,
) -> None:
    """
    Adds an `--authkey` argument to an argument parser.

    Args:
        parser:
            Argument parser to which the argument will be added.
        default:
            Default authentication key. If not given, the argument will
            default to `None` (i.e. no auth key).
    """

    parser.add_argument(
        '--authkey',
        default=default,
        type=lambda arg: arg.encode(),
        help='Authentication key to use for new connections between all nodes in the mesh. '
             'Default: %(default)s',
    )


def endpoint_arg(default_port: Port = None) -> Callable[[str], Endpoint]:
    """
    Returns a function that parses a string of format ``host[:port]`` into an
    ``Endpoint`` object. If the port is not specified, it defaults to the
    provided ``default_port``.
    """

    def wrapped(arg: str) -> Endpoint:
        parsed = urlparse(f'//{arg}')
        host = parsed.hostname
        port = parsed.port or default_port
        return Endpoint(host, port)

    return wrapped
