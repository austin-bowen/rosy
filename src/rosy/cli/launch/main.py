import os
from argparse import ArgumentParser, Namespace
from pathlib import Path
from time import sleep

from rosy.cli.launch.args import ProcessArgs
from rosy.cli.launch.config import is_enabled, load_config
from rosy.procman import ProcessManager
from rosy.types import DomainId


async def launch_main(args: Namespace) -> None:
    _print(f"Using config: {args.config}")
    config = load_config(args.config)

    if args.exclude:
        _print(f"Excluding nodes: {args.exclude}")

    _print('Press Ctrl+C to stop all nodes.')

    with ProcessManager() as pm:
        domain_id = config.get('domain_id')
        node_env = get_node_env(domain_id)

        nodes = config['nodes']
        for node_name, node_config in nodes.items():
            if node_name in args.exclude:
                continue

            start_node(node_name, node_config, node_env, pm)

        try:
            pm.wait()
        except KeyboardInterrupt:
            pass


def add_launch_command(subparsers) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        'launch',
        description="Launch rosy nodes together.",
        help="Launch rosy nodes together",
    )

    parser.add_argument(
        'config',
        nargs='?',
        default=Path('launch.yaml'),
        type=Path,
        help="Path to the configuration file. Default: %(default)s",
    )

    parser.add_argument(
        '-e', '--exclude',
        nargs='+',
        default=[],
        help='Nodes to exclude from starting',
    )


def get_node_env(domain_id: DomainId | None) -> dict[str, str]:
    env = dict(os.environ)

    if domain_id is not None:
        env["ROSY_DOMAIN_ID"] = domain_id

    return env


def start_node(
        name: str,
        config: dict,
        env: dict[str, str],
        pm: ProcessManager,
) -> None:
    if not is_enabled(config):
        return

    delay = config.get('pre_delay', 0)
    sleep(delay)

    command = config['command']
    command = ProcessArgs(command)
    command.extend(['--name', name])
    command = command.args

    default_shell = isinstance(command, str)
    shell = config.get('shell', default_shell)

    number = config.get('number', 1)
    for i in range(number):
        _print(f'Starting node {name!r} ({i + 1}/{number}): {command}')
        pm.popen(command, shell=shell, env=env)

    delay = config.get('post_delay', 0)
    sleep(delay)


def _print(*args, **kwargs) -> None:
    print('[rosy launch]', *args, **kwargs)
