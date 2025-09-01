from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from rosy.cli.bag.record import get_bag_file_path


@patch("rosy.cli.bag.record.datetime")
def test_get_bag_file_path(datetime_mock):
    datetime_mock.now.return_value = datetime(2025, 1, 2, 12, 34, 56)

    result = get_bag_file_path()

    assert result == Path("record_2025-01-02-12-34-56.bag")

    datetime_mock.now.assert_called_once()
