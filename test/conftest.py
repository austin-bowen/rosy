import pytest

from rosytest.integration.cli.utils import rosy_cli


@pytest.fixture(scope='session')
def coordinator():
    with rosy_cli('coordinator') as process:
        process.expect('Started rosy coordinator')
        yield process
