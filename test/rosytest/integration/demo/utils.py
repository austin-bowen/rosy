import signal
from collections.abc import Generator
from contextlib import contextmanager

from pexpect.popen_spawn import PopenSpawn


@contextmanager
def python_module(*args: str, timeout: float | None = 3) -> Generator[PopenSpawn]:
    process = PopenSpawn(
        [
            'env',
            'PYTHONUNBUFFERED=1',
            'python',
            '-m',
            *args,
        ],
        timeout=timeout,
        encoding='utf-8',
    )

    try:
        yield process
    finally:
        if process.proc.poll() is None:
            # Emulate Ctrl+C
            process.kill(signal.SIGINT)

        process.wait()
