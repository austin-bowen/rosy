from unittest.mock import AsyncMock, Mock

import pytest

from easymesh.authentication import NoAuthenticator


class TestNoAuthenticator:
    @pytest.mark.asyncio
    async def test_authenticate_should_do_nothing(self):
        auth = NoAuthenticator()

        reader = Mock()
        writer = AsyncMock()

        assert await auth.authenticate(reader, writer) is None

        assert not reader.mock_calls
        assert not writer.mock_calls
