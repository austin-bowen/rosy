import socket

from rosy.types import Host


def get_hostname() -> Host:
    """Return the current host name."""
    return socket.gethostname()


def get_lan_hostname(suffix: str = '.local') -> Host:
    """
    Return the mDNS hostname of this machine as seen on the local network,
    e.g. "<hostname>.local".
    """
    return get_hostname() + suffix
