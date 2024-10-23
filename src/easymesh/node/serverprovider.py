import asyncio
import tempfile
from abc import abstractmethod
from asyncio import Server
from typing import Optional

from easymesh.specs import ConnectionSpec, IpConnectionSpec, UnixConnectionSpec
from easymesh.types import Host, Port, ServerHost


class ServerProvider:
    @abstractmethod
    async def start_server(
            self,
            client_connected_cb,
    ) -> tuple[Server, ConnectionSpec]:
        """Raises ``UnsupportedProviderError`` if not supported on the system."""
        ...


class PortScanTcpServerProvider(ServerProvider):
    """Starts a TCP server on the first available port."""

    def __init__(
            self,
            server_host: ServerHost,
            client_host: Host,
            start_port: Port = 49152,
            max_ports: Port = 1024,
            **kwargs,
    ):
        """
        Args:
            server_host:
                The interface(s) that the server will listen on.
            client_host:
                The host that clients will use to connect to the server.
            start_port:
                The port to start scanning for an open port.
            max_ports:
                Maximum number of ports to scan.
            kwargs:
                Additional keyword arguments will be passed to the
                ``asyncio.start_server`` call.
        """

        self.server_host = server_host
        self.client_host = client_host
        self.start_port = start_port
        self.max_ports = max_ports
        self.kwargs = kwargs

    @property
    def end_port(self) -> int:
        return self.start_port + self.max_ports - 1

    async def start_server(
            self,
            client_connected_cb,
    ) -> tuple[Server, ConnectionSpec]:
        last_error = None

        for port in range(self.start_port, self.end_port + 1):
            try:
                server = await asyncio.start_server(
                    client_connected_cb,
                    host=self.server_host,
                    port=port,
                    **self.kwargs,
                )
            except OSError as e:
                last_error = e
            else:
                conn_spec = IpConnectionSpec(self.client_host, port)
                return server, conn_spec

        raise OSError(
            f'Unable to start a server on any port in range '
            f'{self.start_port}-{self.end_port}. '
            f'Last error: {last_error!r}'
        )


class TmpUnixServerProvider(ServerProvider):
    """Starts a Unix server on a tmp file."""

    def __init__(
            self,
            prefix: Optional[str] = 'mesh-node-server.',
            suffix: Optional[str] = '.sock',
            dir=None,
            **kwargs,
    ):
        """
        Args:
            prefix:
                The prefix for the temporary Unix socket file.
            suffix:
                The suffix for the temporary Unix socket file.
            dir:
                The directory to create the temporary Unix socket file in.
                If not set, the system's default temporary directory will be used.
            kwargs:
                Additional keyword arguments will be passed to the
                ``asyncio.start_unix_server`` call.
        """

        self.prefix = prefix
        self.suffix = suffix
        self.dir = dir
        self.kwargs = kwargs

    async def start_server(
            self,
            client_connected_cb,
    ) -> tuple[Server, ConnectionSpec]:
        with tempfile.NamedTemporaryFile(
                prefix=self.prefix,
                suffix=self.suffix,
                dir=self.dir,
        ) as file:
            path = file.name

        try:
            server = await asyncio.start_unix_server(client_connected_cb, path=path, **self.kwargs)
        except NotImplementedError as e:
            raise UnsupportedProviderError(self, repr(e))

        conn_spec = UnixConnectionSpec(path=path)

        return server, conn_spec


class UnsupportedProviderError(Exception):
    """Raised when trying to start a server from an unsupported server provider."""

    def __init__(self, provider: ServerProvider, message: str):
        super().__init__(
            f'Unsupported server provider {provider.__class__}: {message}'
        )
