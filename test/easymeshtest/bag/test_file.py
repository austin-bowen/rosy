from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from easymesh.bag.file import get_bag_file_messages


@patch('easymesh.bag.file.pickle')
@patch('easymesh.bag.file.open')
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
