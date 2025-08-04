import signal
from collections.abc import Generator
from contextlib import AbstractContextManager, contextmanager
from subprocess import TimeoutExpired

from pexpect.popen_spawn import PopenSpawn


def rosy_cli(*args: str) -> AbstractContextManager[PopenSpawn]:
    """
    Runs the `rosy` command with args setup to use the custom test coordinator.
    """

    return run(
        'env',
        'PYTHONUNBUFFERED=1',
        'rosy',
        *args,
    )


def python_module(module: str, *args: str) -> AbstractContextManager[PopenSpawn]:
    return run(
        'python',
        '-u',
        '-m',
        module,
        *args,
    )


@contextmanager
def run(cmd: str, *args: str) -> Generator[PopenSpawn]:
    """
    Context manager for running a command with arguments.

    If the command is still running when the context exits,
    it will send a SIGINT (Ctrl+C) to terminate it gracefully.
    """

    process = PopenSpawn(
        [cmd, *args],
        timeout=10,
        encoding='utf-8',
    )

    try:
        yield process
    finally:
        if process.proc.poll() is None:
            # Emulate Ctrl+C
            process.kill(signal.SIGINT)

        try:
            process.proc.wait(timeout=3)
        except TimeoutExpired:
            process.kill(signal.SIGKILL)
            process.wait()
