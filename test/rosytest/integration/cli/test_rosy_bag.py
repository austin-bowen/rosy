import signal
import tempfile
import time
from collections.abc import Generator
from threading import Thread

import pytest
from pexpect import EOF

from rosytest.integration.cli.utils import rosy_cli


class TestRosyBag:
    """NOTE: The tests in this class are order dependent!"""

    @pytest.fixture(scope="class")
    def bag_file(self) -> Generator[str, None, None]:
        with tempfile.NamedTemporaryFile(suffix=".bag") as f:
            f.close()
            yield f.name

    def test_record_no_messages(self, bag_file: str) -> None:
        with rosy_cli(
            "bag",
            "record",
            "--output",
            bag_file,
            "bag-test",
        ) as bag_proc:
            bag_proc.expect('Recording topics to ".*":\n')
            bag_proc.expect_exact("- 'bag-test'\n")

            def ctrl_c():
                time.sleep(1)
                bag_proc.kill(signal.SIGINT)

            Thread(target=ctrl_c).run()

            bag_proc.expect_exact("\n")
            bag_proc.expect_exact("Recording stopped.\n")
            bag_proc.expect_exact("No messages recorded.\n")
            bag_proc.expect_exact(EOF)

    def test_record(self, bag_file: str) -> None:
        with rosy_cli(
            "bag",
            "record",
            "--output",
            bag_file,
            "bag-test",
        ) as bag_proc:
            bag_proc.expect('Recording topics to ".*":\n')
            bag_proc.expect_exact("- 'bag-test'\n")

            with (
                rosy_cli("topic", "send", "bag-test") as send_proc1,
                rosy_cli("topic", "send", "bag-test") as send_proc2,
            ):
                send_proc1.wait()
                send_proc2.wait()

            bag_proc.expect("\.\.")

    def test_info(self, bag_file: str) -> None:
        with rosy_cli("bag", "info", "--input", bag_file) as bag_proc:
            bag_proc.expect(r"path:     [^\n]+\n")
            bag_proc.expect(r"duration: [^\n]+\n")
            bag_proc.expect(r"start:    [^\n]+\n")
            bag_proc.expect(r"end:      [^\n]+\n")
            bag_proc.expect(r"size:     [^\n]+\n")
            bag_proc.expect(r"messages: 2\n")
            bag_proc.expect(r"topics:\n")
            bag_proc.expect(r"- 'bag-test':\t2 \(100%\)\n")
            bag_proc.expect_exact(EOF)

    def test_play(self, bag_file: str) -> None:
        with rosy_cli("topic", "echo", "bag-test") as echo_proc:
            echo_proc.expect_exact("Listening to topics: ['bag-test']\n")

            with rosy_cli("bag", "play", "--input", bag_file) as bag_proc:
                bag_proc.expect('Playing back messages from ".*"\.\.\.\n')
                bag_proc.expect(r"\[.*\] topic='bag-test'\n")
                bag_proc.expect(r"\[.*\] topic='bag-test'\n")
                bag_proc.expect_exact(EOF)

            echo_proc.expect_exact("topic='bag-test'\n")
            echo_proc.expect_exact("topic='bag-test'\n")
