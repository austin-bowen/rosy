from argparse import ArgumentParser
from collections.abc import Callable
from urllib.parse import urlparse

from easymesh.coordinator.constants import DEFAULT_COORDINATOR_PORT
from easymesh.types import Endpoint, Port


def add_node_name_arg(parser: ArgumentParser, default_node_name: str) -> None:
    parser.add_argument(
        '--name',
        default=default_node_name,
        help=f'Node name. Defaults to {default_node_name!r}.',
    )


def add_coordinator_arg(parser: ArgumentParser) -> None:
    parser.add_argument(
        '--coordinator',
        default=Endpoint('localhost', DEFAULT_COORDINATOR_PORT),
        type=endpoint_arg(default_port=DEFAULT_COORDINATOR_PORT),
        metavar='HOST[:PORT]',
        help=f'Coordinator host and port. Defaults to localhost:{DEFAULT_COORDINATOR_PORT}',
    )


def add_authkey_arg(parser: ArgumentParser) -> None:
    parser.add_argument(
        '--authkey',
        default=None,
        type=lambda arg: arg.encode(),
        help='Authentication key to use for new connections between all nodes in the mesh. '
             'Should ideally be >= 32 characters. Default is None.',
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
