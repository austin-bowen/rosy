from unittest.mock import create_autospec

import pytest

from rosy.asyncio import Writer, close_ignoring_errors, noop


class TestCloseIgnoringErrors:
    def setup_method(self):
        self.writer = create_autospec(Writer)

    @pytest.mark.asyncio
    async def test_no_errors(self):
        assert await close_ignoring_errors(self.writer) is None

        self.writer.close.assert_called_once()
        self.writer.wait_closed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_raises_ConnectionError(self):
        self.writer.close.side_effect = ConnectionError()
        assert await close_ignoring_errors(self.writer) is None

        self.writer.close.assert_called_once()
        self.writer.wait_closed.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_close_raises_ConnectionError(self):
        self.writer.wait_closed.side_effect = ConnectionError()
        assert await close_ignoring_errors(self.writer) is None

        self.writer.close.assert_called_once()
        self.writer.wait_closed.assert_awaited_once()


@pytest.mark.asyncio
async def test_noop():
    assert await noop() is None
