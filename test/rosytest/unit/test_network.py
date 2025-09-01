from unittest.mock import patch

import pytest

from rosy.network import get_hostname, get_lan_hostname


def test_get_hostname(socket_mock):
    assert get_hostname() == "hostname"


def test_get_lan_hostname_default_suffix_is_local(socket_mock):
    assert get_lan_hostname() == "hostname.local"


def test_get_lan_hostname_uses_custom_suffix(socket_mock):
    assert get_lan_hostname(".suffix") == "hostname.suffix"


@pytest.fixture
def socket_mock():
    with patch("rosy.network.socket") as mock_socket:
        mock_socket.gethostname.return_value = "hostname"
        yield mock_socket
