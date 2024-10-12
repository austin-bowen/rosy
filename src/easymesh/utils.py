from collections.abc import Iterable


def ephemeral_port_range() -> Iterable[int]:
    return range(49152, 65535 + 1)
