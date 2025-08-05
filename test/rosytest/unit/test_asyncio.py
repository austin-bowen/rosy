from asyncio import IncompleteReadError
from unittest.mock import create_autospec

import pytest

from rosy.asyncio import BufferReader, LockableWriter, Writer, close_ignoring_errors, noop


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


class TestLockableWriter:
    def setup_method(self):
        self.writer = create_autospec(Writer)
        self.lockable_writer = LockableWriter(self.writer)

    def test_constructor(self):
        assert self.lockable_writer.writer is self.writer

    @pytest.mark.asyncio
    async def test_write_succeeds_when_locked(self):
        async with self.lockable_writer:
            self.lockable_writer.write(b'test')

        self.writer.write.assert_called_once_with(b'test')

    @pytest.mark.asyncio
    async def test_write_fails_when_not_locked(self):
        with pytest.raises(
                RuntimeError,
                match="Writer must be locked before writing",
        ):
            self.lockable_writer.write(b'test')

        self.writer.write.assert_not_called()

    @pytest.mark.asyncio
    async def test_drain(self):
        await self.lockable_writer.drain()
        self.writer.drain.assert_awaited_once()

    def test_close(self):
        self.lockable_writer.close()
        self.writer.close.assert_called_once()

    def test_is_closing(self):
        self.writer.is_closing.return_value = True
        assert self.lockable_writer.is_closing() is True
        self.writer.is_closing.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_closed(self):
        await self.lockable_writer.wait_closed()
        self.writer.wait_closed.assert_awaited_once()

    def test_get_extra_info(self):
        self.writer.get_extra_info.return_value = 'info'
        assert self.lockable_writer.get_extra_info('name') == 'info'
        self.writer.get_extra_info.assert_called_once_with('name', None)


class TestBufferReader:
    def setup_method(self):
        self.reader = BufferReader(b'test data')

    @pytest.mark.asyncio
    async def test_readexactly(self):
        assert await self.reader.readexactly(4) == b'test'
        assert await self.reader.readexactly(4) == b' dat'

        with pytest.raises(IncompleteReadError) as exc:
            await self.reader.readexactly(10)

        assert exc.value.partial == b'a'
        assert exc.value.expected == 10

    @pytest.mark.asyncio
    async def test_readuntil_is_not_implemented(self):
        with pytest.raises(NotImplementedError):
            await self.reader.readuntil(b' ')
