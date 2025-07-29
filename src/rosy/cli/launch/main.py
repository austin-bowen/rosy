from argparse import ArgumentParser, Namespace
from pathlib import Path
from time import sleep

from rosy.cli.launch.args import ProcessArgs
from rosy.cli.launch.config import is_enabled, load_config
from rosy.procman import ProcessManager


async def launch_main(args: Namespace) -> None:
    _print(f"Using config: {args.config}")
    config = load_config(args.config)

    if args.exclude:
        _print(f"Excluding nodes: {args.exclude}")

    _print('Press Ctrl+C to stop all nodes.')

    with ProcessManager() as pm:
        node_args = start_coordinator(config, args.no_coordinator, pm)

        nodes = config['nodes']
        for node_name, node_config in nodes.items():
            if node_name in args.exclude:
                continue

            start_node(node_name, node_config, node_args, pm)

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
        '--no-coordinator',
        action='store_true',
        help="Don't start the coordinator",
    )

    parser.add_argument(
        '-e', '--exclude',
        nargs='+',
        default=[],
        help='Nodes to exclude from starting',
    )


def start_coordinator(
        config: dict,
        disabled: bool,
        pm: ProcessManager,
) -> list[str]:
    """
    Start the coordinator (if not disabled), and return a list of coordinator
    arguments to pass to nodes.
    """

    node_args = []

    config = config.get('coordinator', {})

    args = ['rosy', 'coordinator']

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

    if not disabled and is_enabled(config):
        _print(f"Starting coordinator: {args}")
        pm.popen(args)

        delay = config.get('post_delay', 1)
        sleep(delay)
    else:
        _print('Not starting coordinator.')

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


def _print(*args, **kwargs) -> None:
    print('[rosy launch]', *args, **kwargs)
