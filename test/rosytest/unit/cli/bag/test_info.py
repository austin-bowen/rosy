import argparse
from datetime import datetime, timedelta
from pathlib import Path
from textwrap import dedent
from unittest.mock import call, create_autospec, patch

import pytest

from rosy.cli.bag.info import BagInfo, display_info, get_human_readable_size, get_info


class TestDisplayInfo:
    def setup_method(self):
        self.args = argparse.Namespace()
        self.args.input = "bag_file_path"

    @pytest.fixture
    def get_info_mock(self):
        with patch("rosy.cli.bag.info.get_info") as mock:
            yield mock

    @pytest.fixture
    def print_mock(self):
        with patch("rosy.cli.bag.info.print") as mock:
            yield mock

    def test_with_topics(self, get_info_mock, print_mock):
        get_info_mock.return_value = BagInfo(
            path=Path("bag_file_path"),
            start=datetime(2025, 1, 1, 0, 0, 0),
            end=datetime(2025, 1, 1, 0, 1, 0),
            size=100,
            size_unit="MB",
            messages=30,
            topics={
                "topic1": 10,
                "topic2": 20,
            },
        )

        display_info(self.args)

        get_info_mock.assert_called_once_with("bag_file_path")

        print_mock.assert_has_calls(
            [
                call(
                    dedent(
                        """
                        path:     bag_file_path
                        duration: 0:01:00
                        start:    2025-01-01 00:00:00
                        end:      2025-01-01 00:01:00
                        size:     100 MB
                        messages: 30
                        """
                    ).strip()
                ),
                call("topics:"),
                call("- 'topic1':\t10 (33%)"),
                call("- 'topic2':\t20 (67%)"),
            ]
        )

    def test_no_topics(self, get_info_mock, print_mock):
        get_info_mock.return_value = BagInfo(
            path=Path("bag_file_path"),
            start=datetime(2025, 1, 1, 0, 0, 0),
            end=datetime(2025, 1, 1, 0, 1, 0),
            size=0,
            size_unit="KB",
            messages=0,
            topics={},
        )

        display_info(self.args)

        get_info_mock.assert_called_once_with("bag_file_path")

        print_mock.assert_has_calls(
            [
                call(
                    dedent(
                        """
                        path:     bag_file_path
                        duration: 0:01:00
                        start:    2025-01-01 00:00:00
                        end:      2025-01-01 00:01:00
                        size:     0 KB
                        messages: 0
                        """
                    ).strip()
                ),
                call("topics:   none"),
            ]
        )


class TestGetInfo:
    @patch("rosy.cli.bag.info.get_bag_file_messages")
    def test_with_topics(self, get_bag_file_messages_mock) -> None:
        bag_file_path = create_autospec(Path)
        bag_file_path.stat.return_value.st_size = 100

        get_bag_file_messages_mock.return_value = [
            (
                datetime(2025, 1, 1, 0, 0, 0),
                "topic0",
            ),
            (
                datetime(2025, 1, 1, 0, 0, 1),
                "topic1",
            ),
            (
                datetime(2025, 1, 1, 0, 0, 2),
                "topic1",
            ),
        ]

        assert get_info(bag_file_path) == BagInfo(
            path=bag_file_path,
            start=datetime(2025, 1, 1, 0, 0, 0),
            end=datetime(2025, 1, 1, 0, 0, 2),
            size=100,
            size_unit="B",
            messages=3,
            topics={
                "topic0": 1,
                "topic1": 2,
            },
        )

    @patch("rosy.cli.bag.info.get_bag_file_messages")
    def test_no_topics(self, get_bag_file_messages_mock) -> None:
        bag_file_path = create_autospec(Path)
        bag_file_path.stat.return_value.st_size = 0

        get_bag_file_messages_mock.return_value = []

        assert get_info(bag_file_path) == BagInfo(
            path=bag_file_path,
            start=None,
            end=None,
            size=0,
            size_unit="B",
            messages=0,
            topics={},
        )


@pytest.mark.parametrize(
    "size,expected",
    [
        (0, (0, "B")),
        (1023, (1023, "B")),
        (1 * 1024**1, (1, "KB")),
        (1023 * 1024**1, (1023, "KB")),
        (1 * 1024**2, (1, "MB")),
        (1023 * 1024**2, (1023, "MB")),
        (1 * 1024**3, (1, "GB")),
        (2000 * 1024**3, (2000, "GB")),
    ],
)
def test_get_human_readable_size(size: int, expected: tuple[int, str]):
    assert get_human_readable_size(size) == expected


start = datetime(2025, 1, 1, 0, 0, 0)
end = datetime(2025, 1, 2, 0, 0, 0)
dt = timedelta(days=1)


@pytest.mark.parametrize(
    "start, end, expected",
    [
        (start, end, dt),
        (start, None, None),
        (None, end, None),
        (None, None, None),
    ],
)
def test_BagInfo_duration(
    start: datetime | None,
    end: datetime | None,
    expected: timedelta | None,
):
    bag_info = BagInfo(
        path=...,
        start=start,
        end=end,
        size=...,
        size_unit=...,
        messages=...,
        topics=...,
    )

    assert bag_info.duration == expected
