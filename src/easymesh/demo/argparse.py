import argparse

from easymesh.argparse import add_authkey_arg, add_coordinator_arg, add_node_name_arg


def parse_args(default_node_name: str):
    parser = argparse.ArgumentParser()
    add_node_name_arg(parser, default_node_name)
    add_coordinator_arg(parser)
    add_authkey_arg(parser)
    return parser.parse_args()
