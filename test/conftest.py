import pytest

from rosytest.integration.cli.utils import (
    TEST_AUTHKEY,
    TEST_COORDINATOR_PORT,
    rosy_cli,
)


@pytest.fixture(scope='session')
def coordinator():
    with rosy_cli(
            'coordinator',
            f'--port={TEST_COORDINATOR_PORT}',
            f'--authkey={TEST_AUTHKEY}',
            timeout=1,
    ) as process:
        process.expect_exact(
            f'Started rosy coordinator on :{TEST_COORDINATOR_PORT}\n',
        )

        yield process
