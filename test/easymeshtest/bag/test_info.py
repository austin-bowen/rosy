import pytest

from easymesh.bag.info import get_human_readable_size


@pytest.mark.parametrize("size,expected", [
    (0, (0, 'B')),
    (1023, (1023, 'B')),
    (1 * 1024 ** 1, (1, 'KB')),
    (1023 * 1024 ** 1, (1023, 'KB')),
    (1 * 1024 ** 2, (1, 'MB')),
    (1023 * 1024 ** 2, (1023, 'MB')),
    (1 * 1024 ** 3, (1, 'GB')),
    (2000 * 1024 ** 3, (2000, 'GB')),
])
def test_get_human_readable_size(size: int, expected: tuple[int, str]):
    assert get_human_readable_size(size) == expected
