import asyncio
import hmac
import secrets
from abc import ABC, abstractmethod
from asyncio import IncompleteReadError
from collections.abc import Callable
from typing import Optional, Union

from easymesh.asyncio import Reader, Writer
from easymesh.utils import require

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


class HMACAuthenticator(Authenticator):
    """
    Authenticates using symmetric HMAC challenge-response with a shared secret key.
    """

    def __init__(
            self,
            authkey: AuthKey,
            challenge_length: int = 32,
            digest='sha256',
            timeout: Optional[float] = 10.,
            get_random_bytes: Callable[[int], bytes] = secrets.token_bytes,
    ):
        require(authkey, 'authkey must not be empty.')
        require(challenge_length > 0, 'challenge_length must be > 0.')

        self.authkey = authkey
        self.challenge_length = challenge_length
        self.digest = digest
        self.timeout = timeout
        self.get_random_bytes = get_random_bytes

    async def authenticate(self, reader: Reader, writer: Writer) -> None:
        sent_challenge = self.get_random_bytes(self.challenge_length)

        writer.write(sent_challenge)
        await writer.drain()

        received_challenge = await self._read_exactly(reader, self.challenge_length)

        hmac_digest = self._hmac_digest(received_challenge)

        writer.write(hmac_digest)
        await writer.drain()

        expected_hmac = self._hmac_digest(sent_challenge)

        received_hmac = await self._read_exactly(reader, len(expected_hmac))

        if not hmac.compare_digest(expected_hmac, received_hmac):
            raise AuthenticationError('Received HMAC digest does not match expected digest.')

    async def _read_exactly(self, reader: Reader, n: int) -> bytes:
        try:
            return await asyncio.wait_for(
                reader.readexactly(n),
                timeout=self.timeout,
            )
        except TimeoutError:
            raise AuthenticationError(f'Timeout after {self.timeout}s waiting for authkey.')
        except IncompleteReadError as e:
            raise AuthenticationError(e)

    def _hmac_digest(self, challenge: bytes) -> bytes:
        return hmac.digest(self.authkey, challenge, self.digest)


class AuthenticationError(Exception):
    pass


def optional_authkey_authenticator(
        authkey: Optional[AuthKey],
) -> Union[HMACAuthenticator, NoAuthenticator]:
    return HMACAuthenticator(authkey) if authkey else NoAuthenticator()
