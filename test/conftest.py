import pytest

from rosytest.integration.cli.utils import (
    TEST_AUTHKEY,
    TEST_COORDINATOR_PORT,
    rosy_cli,
)


@pytest.fixture(scope='session')
def default_coordinator():
    with rosy_cli('coordinator') as process:
        process.expect('Started rosy coordinator')
        yield process


@pytest.fixture(scope='session')
def custom_coordinator():
    with rosy_cli(
            'coordinator',
            f'--port={TEST_COORDINATOR_PORT}',
            f'--authkey={TEST_AUTHKEY}',
    ) as process:
        process.expect('Started rosy coordinator')
        yield process
