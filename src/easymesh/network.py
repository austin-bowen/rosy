import socket
from collections.abc import Container
from socket import AddressFamily

import psutil
from psutil._common import snicaddr

from easymesh.types import Host


def get_hostname() -> Host:
    """Return the current host name."""
    return socket.gethostname()


def get_lan_hostname(suffix: str = '.local') -> Host:
    """
    Return the mDNS hostname of this machine as seen on the local network,
    e.g. "<hostname>.local".
    """
    return get_hostname() + suffix


def get_interface_ip_address(
        interface_name: str,
        families: Container[AddressFamily] = None,
) -> str:
    """
    Get the IP address of the given interface.

    If ``families`` is not provided, then it defaults to {AF_INET, AF_INET6},
    returning the first IPv4 or IPv6 address found.
    """

    addresses = get_interface_addresses(interface_name)

    if not families:
        families = {AddressFamily.AF_INET, AddressFamily.AF_INET6}

    try:
        address = next(a for a in addresses if a.family in families)
    except StopIteration:
        raise ValueError(
            f'No address of family={families} found for interface={interface_name}. '
            f'Addresses found: {addresses}'
        )

    return address.address


def get_interface_addresses(interface_name: str) -> list[snicaddr]:
    interfaces = psutil.net_if_addrs()

    try:
        return interfaces[interface_name]
    except KeyError:
        raise ValueError(
            f'Interface with name={interface_name} not found. '
            f'Available interfaces: {list(interfaces.keys())}'
        )


def print_interfaces() -> None:
    for interface, addrs in psutil.net_if_addrs().items():
        print(interface)
        for addr in addrs:
            print(f'  {addr.family.name}: {addr.address}')


if __name__ == '__main__':
    print_interfaces()
