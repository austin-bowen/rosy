import pytest
from pexpect import EOF

from rosytest.integration.cli.utils import python_module, rosy_cli


class TestRosyNode:
    def test_list(self, topic_listener, service_provider):
        with rosy_cli('node', 'list') as list_proc:
            list_proc.expect_exact([
                '2 nodes:\n',
                '\n',
            ])

            list_proc.expect(r"'rosy topic echo'@[^ ]+ \(\w+\)\n")
            list_proc.expect_exact([
                "- topics:\n",
                "  - 'test'\n",
                "- services: none\n",
                "\n",
            ])

            list_proc.expect(r"service_provider@[^ ]+ \(\w+\)\n")
            list_proc.expect_exact([
                "- topics: none\n",
                "- services:\n",
                "  - 'multiply'\n",
                "\n",
                EOF,
            ])

    @pytest.mark.parametrize('flag', ['--verbose', '-v'])
    def test_list_verbose(self, topic_listener, service_provider, flag: str):
        with rosy_cli('node', 'list', flag) as list_proc:
            list_proc.expect_exact([
                '2 nodes:\n',
                '\n',
            ])

            list_proc.expect(r"'rosy topic echo'@[^ ]+ \(\w+\)\n")
            list_proc.expect(r"- UUID: [0-9a-f-]+\n")
            list_proc.expect_exact([
                "- topics:\n",
                "  - 'test'\n",
                "- services: none\n",
                "- supported connection methods:\n",
            ])
            list_proc.expect(r"(  - \w+ConnectionSpec\([^\n]*\)\n)+")
            list_proc.expect_exact("\n")

            list_proc.expect(r"service_provider@[^ ]+ \(\w+\)\n")
            list_proc.expect(r"- UUID: [0-9a-f-]+\n")
            list_proc.expect_exact([
                "- topics: none\n",
                "- services:\n",
                "  - 'multiply'\n",
                "- supported connection methods:\n",
            ])
            list_proc.expect(r"(  - \w+ConnectionSpec\([^\n]*\)\n)+")
            list_proc.expect_exact(EOF)


@pytest.fixture(scope='class')
def topic_listener(coordinator):
    with rosy_cli('topic', 'echo', 'test') as echo_proc:
        echo_proc.expect_exact("Listening to topics: ['test']\n")
        yield


@pytest.fixture(scope='class')
def service_provider(coordinator):
    with python_module('rosy.demo.service_provider') as provider_proc:
        provider_proc.expect_exact('Started service...\n')
        yield
