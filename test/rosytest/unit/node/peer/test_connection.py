import socket
from unittest.mock import call, create_autospec, patch

import pytest

from rosy.asyncio import LockableWriter, Reader, Writer
from rosy.node.peer.connection import (
    PeerConnection,
    PeerConnectionBuilder,
    PeerConnectionManager,
)
from rosy.specs import IpConnectionSpec, UnixConnectionSpec
from rosytest.util import mock_node_spec


class TestPeerConnection:
    def setup_method(self):
        self.reader = create_autospec(Reader)
        self.writer = create_autospec(Writer)

        self.connection = PeerConnection(self.reader, self.writer)

    @pytest.mark.asyncio
    async def test_close(self):
        await self.connection.close()

        self.writer.close.assert_called_once()
        self.writer.wait_closed.assert_awaited_once()

    def test_is_closing(self):
        expected = True
        self.writer.is_closing.return_value = expected

        assert self.connection.is_closing() == expected

        self.writer.is_closing.assert_called_once()


class TestPeerConnectionBuilder:
    def setup_method(self):
        self.conn_builder = PeerConnectionBuilder(host="host")

    @pytest.mark.asyncio
    async def test_build_with_IPConnectionSpec(self, open_connection_mock):
        reader = create_autospec(Reader)
        writer = create_autospec(Writer)
        open_connection_mock.return_value = reader, writer

        conn_spec = IpConnectionSpec("host", 8080, family=socket.AF_INET)

        result = await self.conn_builder.build([conn_spec])

        assert result == (reader, writer)

        open_connection_mock.assert_awaited_once_with(
            host="host",
            port=8080,
            family=socket.AF_INET,
        )

    @pytest.mark.asyncio
    async def test_build_with_UnixConnectionSpec_on_same_host_succeeds(
        self, open_unix_connection_mock
    ):
        reader = create_autospec(Reader)
        writer = create_autospec(Writer)
        open_unix_connection_mock.return_value = reader, writer

        conn_spec = UnixConnectionSpec("path", "host")

        result = await self.conn_builder.build([conn_spec])

        assert result == (reader, writer)

        open_unix_connection_mock.assert_awaited_once_with(path="path")

    @pytest.mark.asyncio
    async def test_build_with_UnixConnectionSpec_on_different_host_fails(
        self, open_unix_connection_mock
    ):
        conn_spec = UnixConnectionSpec("path", "other-host")

        with pytest.raises(ConnectionError):
            await self.conn_builder.build([conn_spec])

        open_unix_connection_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_build_with_multiple_specs_uses_first_successful(
        self, open_connection_mock
    ):
        reader = create_autospec(Reader)
        writer = create_autospec(Writer)
        open_connection_mock.side_effect = [
            ConnectionError("Connection failed"),
            (reader, writer),  # Second spec succeeds
        ]

        conn_specs = [
            IpConnectionSpec("host1", 8080, family=socket.AF_INET),
            IpConnectionSpec("host2", 8080, family=socket.AF_INET6),
        ]

        result = await self.conn_builder.build(conn_specs)

        assert result == (reader, writer)

        assert open_connection_mock.call_args_list == [
            call(host="host1", port=8080, family=socket.AF_INET),
            call(host="host2", port=8080, family=socket.AF_INET6),
        ]

    @pytest.mark.asyncio
    async def test_build_raises_ConnectionError_if_no_specs_succeed(
        self, open_connection_mock
    ):
        open_connection_mock.side_effect = [
            ConnectionError("Connection failed"),
            ConnectionError("Connection failed"),
        ]

        conn_specs = [
            IpConnectionSpec("host1", 8080, family=socket.AF_INET),
            IpConnectionSpec("host2", 8080, family=socket.AF_INET6),
        ]

        with pytest.raises(
            ConnectionError, match="Could not connect to any connection spec"
        ):
            await self.conn_builder.build(conn_specs)

        assert open_connection_mock.call_args_list == [
            call(host="host1", port=8080, family=socket.AF_INET),
            call(host="host2", port=8080, family=socket.AF_INET6),
        ]

    @pytest.mark.asyncio
    async def test_build_raises_ValueError_if_unknown_connection_spec_given(self):
        with pytest.raises(ValueError, match="Unrecognized connection spec:"):
            not_a_connection_spec = object()
            await self.conn_builder._get_connection([not_a_connection_spec])

    @pytest.mark.asyncio
    async def test_build_raises_ConnectionError_if_no_specs_provided(self):
        with pytest.raises(
            ConnectionError, match="Could not connect to any connection spec"
        ):
            await self.conn_builder.build([])


@pytest.fixture
def open_connection_mock():
    with patch("rosy.node.peer.connection.open_connection") as mock:
        yield mock


@pytest.fixture
def open_unix_connection_mock():
    with patch("rosy.node.peer.connection.open_unix_connection") as mock:
        yield mock


class TestPeerConnectionManager:
    def setup_method(self):
        self.reader = create_autospec(Reader)

        self.writer = create_autospec(Writer)
        self.writer.is_closing.return_value = False

        self.conn_builder = create_autospec(PeerConnectionBuilder)
        self.conn_builder.build.return_value = self.reader, self.writer

        self.manager = PeerConnectionManager(self.conn_builder)

    @pytest.mark.asyncio
    async def test_get_connection_returns_new_connection_on_first_call(self):
        node = mock_node_spec("node")

        connection = await self.manager.get_connection(node)

        assert connection.reader is self.reader
        assert isinstance(connection.writer, LockableWriter)
        assert connection.writer.writer is self.writer

        self.conn_builder.build.assert_awaited_once_with(node.connection_specs)

    @pytest.mark.asyncio
    async def test_get_connection_returns_cached_connection_on_second_call(self):
        node = mock_node_spec("node")

        connection1 = await self.manager.get_connection(node)

        self.conn_builder.build.assert_awaited_once_with(node.connection_specs)

        connection2 = await self.manager.get_connection(node)

        assert connection2 is connection1

        self.conn_builder.build.assert_awaited_once_with(node.connection_specs)

    @pytest.mark.asyncio
    async def test_get_connection_returns_new_connection_on_second_call_when_cached_connection_closed(
        self,
    ):
        node = mock_node_spec("node")

        connection1 = await self.manager.get_connection(node)

        self.writer.is_closing.return_value = True

        connection2 = await self.manager.get_connection(node)

        assert connection2 is not connection1

        assert self.conn_builder.build.call_args_list == [
            call(node.connection_specs),
            call(node.connection_specs),
        ]
