from argparse import ArgumentParser
from collections.abc import Callable
from urllib.parse import urlparse

from easymesh.coordinator.constants import DEFAULT_COORDINATOR_PORT
from easymesh.types import Endpoint, Port


def get_node_arg_parser(default_node_name: str = None, **kwargs) -> ArgumentParser:
    """
    Returns an argument parser with node-specific arguments added.

    Args:
        default_node_name:
            Default node name. If not given, the argument is required.
        **kwargs:
            These are passed to the `ArgumentParser` constructor.
    """

    parser = ArgumentParser(**kwargs)
    add_node_args(parser, default_node_name)
    return parser


def add_node_args(parser: ArgumentParser, default_node_name: str = None) -> None:
    """
    Adds node-specific arguments to an argument parser.

    Args:
        parser:
            Argument parser to which the arguments will be added.
        default_node_name:
            Default node name. If not given, the argument is required.
    """

    add_node_name_arg(parser, default_node_name)
    add_coordinator_arg(parser)
    add_authkey_arg(parser)


def add_node_name_arg(parser: ArgumentParser, default_node_name: str = None) -> None:
    """
    Adds a `--name` argument to an argument parser.

    Args:
        parser:
            Argument parser to which the argument will be added.
        default_node_name:
            Default node name. If not given, the argument will be required.
    """

    arg_args = dict(
        default=default_node_name,
        help='Node name. Default: %(default)',
    ) if default_node_name is not None else dict(
        required=True,
        help='Node name.',
    )

    parser.add_argument('--name', **arg_args)


def add_coordinator_arg(parser: ArgumentParser) -> None:
    """
    Adds a `--coordinator HOST[:PORT]` argument to an argument parser.
    """

    parser.add_argument(
        '--coordinator',
        default=Endpoint('localhost', DEFAULT_COORDINATOR_PORT),
        type=endpoint_arg(default_port=DEFAULT_COORDINATOR_PORT),
        metavar='HOST[:PORT]',
        help=f'Coordinator host and port. Defaults to localhost:{DEFAULT_COORDINATOR_PORT}',
    )


def add_authkey_arg(parser: ArgumentParser) -> None:
    """
    Adds an `--authkey` argument to an argument parser.
    """

    parser.add_argument(
        '--authkey',
        default=None,
        type=lambda arg: arg.encode(),
        help='Authentication key to use for new connections between all nodes in the mesh. '
             'Should ideally be >= 32 characters. Default: %(default)s',
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
