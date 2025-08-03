import signal
from collections.abc import Generator
from contextlib import contextmanager

from pexpect.popen_spawn import PopenSpawn

TEST_COORDINATOR_PORT: int = 7680
TEST_AUTHKEY: str = 'testing'


@contextmanager
def rosy_cli(*args: str, timeout: float | None = 3) -> Generator[PopenSpawn]:
    process = PopenSpawn(
        [
            'env',
            'PYTHONUNBUFFERED=1',
            'rosy',
            f'--coordinator=:{TEST_COORDINATOR_PORT}',
            '--authkey=testing',
            *args,
        ],
        timeout=timeout,
        encoding='utf-8',
    )

    try:
        yield process
    finally:
        # Emulate Ctrl+C
        process.kill(signal.SIGINT)
