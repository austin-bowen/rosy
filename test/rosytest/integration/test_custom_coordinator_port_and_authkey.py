from rosytest.integration.cli.utils import rosy_cli


def test_custom_coordinator_port_and_authkey():
    with rosy_cli(
            'coordinator',
            '--port=7680',
            '--authkey=testing',
    ) as coordinator_proc:
        coordinator_proc.expect_exact('Started rosy coordinator on :7680\n')

        with rosy_cli(
                '--coordinator=:7680',
                '--authkey=testing',
                'topic', 'send', 'test',
        ) as send_proc:
            send_proc.expect_exact('Waiting for listeners...\n')

            with rosy_cli(
                    '--coordinator=:7680',
                    '--authkey=testing',
                    'topic', 'echo', 'test',
            ) as echo_proc:
                coordinator_proc.expect('Total nodes: 2\n')

                echo_proc.expect_exact("Listening to topics: ['test']\n")

                send_proc.expect_exact("Sending to topic='test'\n")

                echo_proc.expect_exact("topic='test'\n")
