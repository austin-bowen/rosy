import asyncio
from abc import ABC, abstractmethod
from asyncio import IncompleteReadError
from typing import Optional, Union

from easymesh.asyncio import Reader, Writer

AuthKey = bytes


class Authenticator(ABC):
    @abstractmethod
    async def authenticate(self, reader: Reader, writer: Writer) -> None:
        """Raises AuthenticationError if authentication fails."""
        ...


class NoAuthenticator(Authenticator):
    """Performs no authentication."""

    async def authenticate(self, reader: Reader, writer: Writer) -> None:
        pass


class PlaintextAuthkeyAuthenticator(Authenticator):
    def __init__(self, authkey: AuthKey, timeout: Optional[float] = 10.):
        if not authkey:
            raise ValueError('authkey must not be empty.')

        self.authkey = authkey
        self.timeout = timeout

    async def authenticate(self, reader: Reader, writer: Writer) -> None:
        await self._send_authkey(writer)
        await self._receive_and_check_authkey(reader)

    async def _send_authkey(self, writer: Writer) -> None:
        writer.write(self.authkey)
        await writer.drain()

    async def _receive_and_check_authkey(self, reader: Reader) -> None:
        try:
            received_authkey = await asyncio.wait_for(
                reader.readexactly(len(self.authkey)),
                timeout=self.timeout,
            )
        except TimeoutError:
            raise AuthenticationError(f'Timeout after {self.timeout}s waiting for authkey.')
        except IncompleteReadError as e:
            raise AuthenticationError(e)

        if received_authkey != self.authkey:
            raise AuthenticationError(
                f'Received authkey={received_authkey} does not '
                f'match expected authkey={self.authkey}.'
            )


class AuthenticationError(Exception):
    pass


def optional_authkey_authenticator(
        authkey: Optional[AuthKey],
) -> Union[PlaintextAuthkeyAuthenticator, NoAuthenticator]:
    return PlaintextAuthkeyAuthenticator(authkey) if authkey else NoAuthenticator()
