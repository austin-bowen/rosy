from argparse import Namespace

import pytest

from rosy.argparse import get_node_arg_parser, server_host_arg
from rosy.types import Endpoint, ServerHost


class TestGetNodeArgParser:
    @pytest.mark.parametrize('args, expected', [
        (
                ['--name=name'],
                Namespace(name='name', coordinator=Endpoint('localhost', 7679), authkey=None),
        ),
        (
                ['--name=name', '--coordinator=host:1234', '--authkey=secret'],
                Namespace(name='name', coordinator=Endpoint('host', 1234), authkey=b'secret'),
        ),
    ])
    def test_with_defaults(self, args: list[str], expected: Namespace):
        parser = get_node_arg_parser()
        parsed_args = parser.parse_args(args)
        assert parsed_args == expected

    @pytest.mark.parametrize('args, expected', [
        (
                [],
                Namespace(name='default_name', coordinator=Endpoint('default_host', 4321), authkey=b'default_secret'),
        ),
        (
                ['--name=name', '--coordinator=host:1234', '--authkey=secret'],
                Namespace(name='name', coordinator=Endpoint('host', 1234), authkey=b'secret'),
        ),
    ])
    def test_with_overrides(self, args: list[str], expected: Namespace):
        parser = get_node_arg_parser(
            default_node_name='default_name',
            default_coordinator=Endpoint('default_host', 4321),
            default_authkey=b'default_secret',
        )
        parsed_args = parser.parse_args(args)
        assert parsed_args == expected


@pytest.mark.parametrize('arg, expected', [
    ('', ''),
    ('None', None),
    ('host', 'host'),
    ('host1,host2', ['host1', 'host2']),
])
def test_server_host_arg(arg: str, expected: ServerHost):
    assert server_host_arg(arg) == expected
