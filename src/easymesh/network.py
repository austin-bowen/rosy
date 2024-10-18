from socket import AddressFamily

import psutil
from psutil._common import snicaddr


def get_interface_ip_address(
        interface_name: str,
        family: AddressFamily = AddressFamily.AF_INET,
) -> str:
    addresses = get_interface_addresses(interface_name)

    try:
        address = next(a for a in addresses if a.family == family)
    except StopIteration:
        raise ValueError(
            f'No address of family={family} found for interface={interface_name}. '
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
