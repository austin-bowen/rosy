import pytest
from pexpect import EOF

from rosytest.integration.cli.utils import rosy_cli
from rosytest.integration.demo.utils import python_module


def test_demo_sender_and_listener(coordinator):
    with python_module('rosy.demo.topic_listener') as listener_proc:
        listener_proc.expect_exact('Listening...\n')

        with python_module('rosy.demo.topic_sender') as sender_proc:
            sender_proc.expect_exact(EOF)

        listener_proc.expect_exact(
            'Received "hello world" on topic=some-topic\n',
        )


@pytest.fixture
def coordinator():
    with rosy_cli('coordinator') as process:
        process.expect('Started rosy coordinator')
        yield process
