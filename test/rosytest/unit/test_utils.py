import pytest

from rosy.utils import require


def test_require_returns_None_given_True():
    assert require(True) is None
    assert require(True, message="foo") is None


def test_require_raises_ValueError_given_False():
    with pytest.raises(ValueError):
        require(False)

    with pytest.raises(ValueError, match="foo"):
        require(False, message="foo")
