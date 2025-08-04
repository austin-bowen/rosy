from pexpect import EOF

from rosytest.integration.cli.utils import python_module


def test_demo_topic_sender_and_listener(coordinator):
    with python_module('rosy.demo.topic_listener') as listener_proc:
        listener_proc.expect_exact('Listening...\n')

        with python_module('rosy.demo.topic_sender') as sender_proc:
            sender_proc.expect_exact(EOF)

        listener_proc.expect_exact(
            'Received "hello world" on topic=some-topic\n',
        )


def test_demo_service_caller_and_provider(coordinator):
    with python_module('rosy.demo.service_provider') as provider_proc:
        provider_proc.expect_exact('Started service...\n')

        with python_module('rosy.demo.service_caller') as caller_proc:
            caller_proc.expect_exact([
                'Calculating 2 * 2...\n',
                'Result: 4\n',
                EOF,
            ])
