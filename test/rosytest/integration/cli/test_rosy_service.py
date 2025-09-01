from pexpect import EOF

from rosytest.integration.cli.utils import python_module, rosy_cli


class TestRosyService:
    def test_call(self):
        with rosy_cli(
            "service",
            "call",
            "multiply",
            "3",
            "4",
        ) as call_proc:
            call_proc.expect_exact("Waiting for providers...\n")

            with python_module("rosy.demo.service_provider") as provider_proc:
                provider_proc.expect_exact("Started service...\n")

                call_proc.expect(r"\[.*\]\n")  # Timestamp header
                call_proc.expect_exact(
                    [
                        "Calling service='multiply'\n",
                        "args:\n",
                        "  0: 3\n",
                        "  1: 4\n",
                        "Response: 12\n",
                        "\n",
                        EOF,
                    ]
                )

    def test_call_multiple(self):
        with (
            python_module("rosy.demo.service_provider"),
            rosy_cli(
                "service",
                "call",
                "--interval",
                "0.1",
                "multiply",
                "3",
                "4",
            ) as call_proc,
        ):
            for _ in range(2):
                call_proc.expect(r"\[.*\]\n")  # Timestamp header
                call_proc.expect_exact(
                    [
                        "Calling service='multiply'\n",
                        "args:\n",
                        "  0: 3\n",
                        "  1: 4\n",
                        "Response: 12\n",
                        "\n",
                    ]
                )

    def test_list(self):
        with python_module("rosy.demo.service_provider") as provider_proc:
            provider_proc.expect_exact("Started service...\n")

            with rosy_cli("service", "list") as list_proc:
                list_proc.expect_exact(
                    [
                        "multiply\n",
                    ]
                )

    def test_call_raises_ValueError_when_kwargs_before_args(self):
        with rosy_cli("service", "call", "test", "key='value'", "'arg'") as call_proc:
            call_proc.expect_exact(
                [
                    """ValueError: Positional argument "'arg'" must come before the keyword arguments.\n""",
                    EOF,
                ]
            )
