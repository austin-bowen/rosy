from rosytest.integration.cli.utils import rosy_cli


class TestRosyTopic:
    def test_send_and_echo(self, custom_coordinator):
        with (
            rosy_cli('topic', 'echo', 'test') as echo_proc,
            rosy_cli('topic', 'send', 'test', "'arg'", "key='value'") as send_proc,
        ):
            echo_proc.expect_exact("Listening to topics: ['test']\n")

            send_proc.expect_exact([
                "Sending to topic='test'\n",
                "args:\n",
                "  0: 'arg'\n",
                "kwargs:\n",
                "  key='value'\n",
            ])

            echo_proc.expect_exact([
                "topic='test'\n",
                "args:\n",
                "  0: 'arg'\n",
                "kwargs:\n",
                "  key='value'\n",
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
