from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from rosy.cli.bag.file import get_bag_file_messages, get_most_recent_bag_file_path


@patch('rosy.cli.bag.file.pickle')
@patch('rosy.cli.bag.file.open')
def test_get_bag_file_messages(open_mock, pickle_mock):
    file_path = Path('record.bag')

    messages = [
        (datetime(2025, 1, 2, 12, 34, 0), 'topic1', b'data1'),
        (datetime(2025, 1, 2, 12, 34, 1), 'topic2', b'data2'),
    ]

    pickle_mock.load.side_effect = [
        *messages,
        EOFError()
    ]

    results = get_bag_file_messages(file_path)

    assert isinstance(results, Iterator)
    assert list(results) == messages

    open_mock.assert_called_once_with(file_path, 'rb')
    assert pickle_mock.load.call_count == 3


class TestGetMostRecentBagFilePath:
    @patch('rosy.cli.bag.file.Path')
    def test_returns_most_recent_bag_file_path(self, Path_mock):
        Path_mock.return_value.glob.return_value = [
            Path('record_2025-01-02-12-34-00.bag'),
            Path('record_2025-01-02-12-34-01.bag'),
        ]

        result = get_most_recent_bag_file_path()

        assert result == Path('record_2025-01-02-12-34-01.bag')

        Path_mock.assert_called_once_with('.')
        Path_mock.return_value.glob.assert_called_once_with(
            'record_????-??-??-??-??-??.bag'
        )

    @patch('rosy.cli.bag.file.Path')
    def test_raises_FileNotFoundError_if_no_bag_file_found(self, Path_mock):
        Path_mock.return_value.glob.return_value = []

        with pytest.raises(FileNotFoundError):
            get_most_recent_bag_file_path()

        Path_mock.assert_called_once_with('.')
        Path_mock.return_value.glob.assert_called_once_with(
            'record_????-??-??-??-??-??.bag'
        )
