from datetime import datetime, timedelta

import pytest

from rosy.cli.bag.info import BagInfo, get_human_readable_size


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
