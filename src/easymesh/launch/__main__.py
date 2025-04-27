import argparse
from dataclasses import dataclass
from pathlib import Path
from time import sleep
from typing import Union

import yaml

from easymesh.network import get_hostname
from easymesh.procman import ProcessManager


def main() -> None:
    args = parse_args()

    config = load_config(args.config)
    _print('Press Ctrl+C to stop all nodes.')

    with ProcessManager() as pm:
        node_args = start_coordinator(config, pm)

        nodes = config['nodes']
        for node_name, node_config in nodes.items():
            start_node(node_name, node_config, node_args, pm)

        try:
            pm.wait()
        except KeyboardInterrupt:
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch easymesh nodes together.",
    )

    parser.add_argument(
        '-c', '--config',
        default=Path('launch.yaml'),
        type=Path,
        help="Path to the configuration file. Default: %(default)s",
    )

    return parser.parse_args()


def load_config(path: Path) -> dict:
    _print(f"Using config: {path}")
    with path.open('r') as file:
        return yaml.safe_load(file)


def start_coordinator(config: dict, pm: ProcessManager) -> list[str]:
    """
    Start the coordinator (if not disabled), and return a list of coordinator
    arguments to pass to nodes.
    """

    node_args = []

    config = config.get('coordinator', {})

    if not is_enabled(config):
        _print('Not starting coordinator.')
        return []

    args = ['easymesh']

    host = config.get('host')
    if host is not None:
        args.extend(['--host', host])

    port = config.get('port')
    if port is not None:
        args.extend(['--port', str(port)])

    client_host = config.get('client_host')
    if client_host or port:
        coordinator_arg = (client_host or '')
        if port:
            coordinator_arg += f':{port}'

        node_args.extend(['--coordinator', coordinator_arg])

    authkey = config.get('authkey')
    if authkey is not None:
        authkey_arg = ['--authkey', authkey]
        args.extend(authkey_arg)
        node_args.extend(authkey_arg)

    log_heartbeats = config.get('log_heartbeats', False)
    if log_heartbeats:
        args.append('--log-heartbeats')

    _print(f"Starting coordinator: {args}")
    pm.popen(args)

    delay = config.get('post_delay', 1)
    sleep(delay)

    return node_args


def start_node(
        name: str,
        config: dict,
        coordinator_args: list[str],
        pm: ProcessManager,
) -> None:
    if not is_enabled(config):
        return

    delay = config.get('pre_delay', 0)
    sleep(delay)

    command = config['command']
    command = ProcessArgs(command)
    command.extend(['--name', name])
    command.extend(coordinator_args)
    command = command.args

    default_shell = isinstance(command, str)
    shell = config.get('shell', default_shell)

    number = config.get('number', 1)
    for i in range(number):
        _print(f'Starting node {name!r} ({i + 1}/{number}): {command}')
        pm.popen(command, shell=shell)

    delay = config.get('post_delay', 0)
    sleep(delay)


def is_enabled(config: dict) -> bool:
    disabled = config.get('disabled', False)
    return not disabled and is_enabled_on_host(config)


def is_enabled_on_host(config: dict) -> bool:
    hostname = get_hostname()
    on_host = config.get('on_host', hostname)
    return on_host == hostname


def _print(*args, **kwargs) -> None:
    print('[meshlaunch]', *args, **kwargs)


@dataclass
class ProcessArgs:
    args: Union[str, list[str]]

    def append(self, arg: str) -> None:
        if isinstance(self.args, str):
            if not arg:
                arg = '""'
            elif ' ' in arg and not (arg[0] == arg[-1] == '"'):
                arg = f'"{arg}"'

            self.args = f'{self.args} {arg}'
        else:
            self.args.append(arg)

    def extend(self, args: list[str]) -> None:
        for arg in args:
            self.append(arg)


if __name__ == '__main__':
    main()
