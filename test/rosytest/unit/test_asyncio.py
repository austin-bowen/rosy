import pytest

from rosy.asyncio import noop


@pytest.mark.asyncio
async def test_noop():
    assert await noop() is None
