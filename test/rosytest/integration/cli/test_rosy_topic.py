from pexpect import EOF

from rosytest.integration.cli.utils import rosy_cli


class TestRosyTopic:
    def test_send_once_and_echo(self, custom_coordinator):
        with rosy_cli(
                'topic',
                'send',
                'test',
                "'arg'",
                "timestamp=call:time.time()",
        ) as send_proc:
            send_proc.expect_exact('Waiting for listeners...\n')

            with rosy_cli('topic', 'echo', 'test') as echo_proc:
                echo_proc.expect_exact("Listening to topics: ['test']\n")

                send_proc.expect(r'\[.*\]\n')  # Timestamp header
                send_proc.expect_exact([
                    "Sending to topic='test'\n",
                    "args:\n",
                    "  0: 'arg'\n",
                    "kwargs:\n",
                ])
                send_proc.expect(r"  timestamp=\d+\.\d+\n")
                send_proc.expect_exact(EOF)

                echo_proc.expect(r'\[.*\]\n')  # Timestamp header
                echo_proc.expect_exact([
                    "topic='test'\n",
                    "args:\n",
                    "  0: 'arg'\n",
                    "kwargs:\n",
                ])
                echo_proc.expect(r"  timestamp\=\d+\.\d+\n")

    def test_send_multiple(self, custom_coordinator):
        with (
            rosy_cli('topic', 'echo', 'test'),
            rosy_cli(
                'topic',
                'send',
                '--interval',
                '0.1',
                'test',
            ) as send_proc,
        ):
            for _ in range(2):
                send_proc.expect(r'\[.*\]\n')  # Timestamp header
                send_proc.expect_exact([
                    "Sending to topic='test'\n",
                    "\n",
                ])

    def test_list(self, custom_coordinator):
        with (
            rosy_cli('topic', 'echo', 'test1', 'test2') as echo_proc1,
            rosy_cli('topic', 'echo', 'test2', 'test3') as echo_proc2,
        ):
            echo_proc1.expect_exact("Listening to topics: ['test1', 'test2']\n")
            echo_proc2.expect_exact("Listening to topics: ['test2', 'test3']\n")

            with rosy_cli('topic', 'list') as list_proc:
                list_proc.expect_exact([
                    'test1\n',
                    'test2\n',
                    'test3\n',
                ])

    def test_send_raises_ValueError_when_kwargs_before_args(self):
        with rosy_cli('topic', 'send', 'test', "key='value'", "'arg'") as send_proc:
            send_proc.expect_exact([
                """ValueError: Positional argument "'arg'" must come before the keyword arguments.\n""",
                EOF,
            ])
