from argparse import Namespace

import pytest

from rosy.argparse import get_node_arg_parser


class TestGetNodeArgParser:
    @pytest.mark.parametrize(
        "args, expected",
        [
            (
                ["--name=name"],
                Namespace(name="name", domain_id="default"),
            ),
            (
                ["--name=name", "--domain-id=domain_id"],
                Namespace(name="name", domain_id="domain_id"),
            ),
        ],
    )
    def test_with_defaults(self, args: list[str], expected: Namespace):
        parser = get_node_arg_parser()
        parsed_args = parser.parse_args(args)
        assert parsed_args == expected

    @pytest.mark.parametrize(
        "args, expected",
        [
            (
                [],
                Namespace(name="default_name", domain_id="default_domain_id"),
            ),
            (
                ["--name=name", "--domain-id=domain_id"],
                Namespace(name="name", domain_id="domain_id"),
            ),
        ],
    )
    def test_with_overrides(self, args: list[str], expected: Namespace):
        parser = get_node_arg_parser(
            default_node_name="default_name",
            default_domain_id="default_domain_id",
        )
        parsed_args = parser.parse_args(args)
        assert parsed_args == expected
