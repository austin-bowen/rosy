import asyncio
import tempfile
from abc import abstractmethod
from asyncio import Server
from typing import Optional

from easymesh.specs import ConnectionSpec, IpConnectionSpec, UnixConnectionSpec
from easymesh.utils import require


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
            host: str = 'localhost',
            start_port: int = 49152,
            max_ports: int = 1024,
    ):
        require(1 <= start_port <= 65535, 'start_port must be in range 1-65535')
        require(1 <= max_ports <= 65534, 'max_ports must be in range 1-65534')

        self.host = host
        self.start_port = start_port
        self.max_ports = max_ports

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
                    host=self.host,
                    port=port,
                )
            except OSError as e:
                last_error = e
            else:
                conn_spec = IpConnectionSpec(self.host, port)
                return server, conn_spec

        raise OSError(
            f'Unable to start a server on any port in range '
            f'{self.start_port}-{self.end_port}. '
            f'Last error: {last_error}'
        )


class TmpUnixServerProvider(ServerProvider):
    """Starts a Unix server on a tmp file."""

    def __init__(
            self,
            prefix: Optional[str] = 'mesh-node-server.',
            suffix: Optional[str] = '.sock',
            dir=None,
    ):
        self.prefix = prefix
        self.suffix = suffix
        self.dir = dir

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
            server = await asyncio.start_unix_server(client_connected_cb, path=path)
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
