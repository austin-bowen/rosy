from collections.abc import Collection
from dataclasses import dataclass, field
from socket import AddressFamily
from uuid import UUID, uuid1

from rosy.network import get_hostname
from rosy.types import Host, Port, Service, Topic


@dataclass
class IpConnectionSpec:
    host: Host
    port: Port
    family: AddressFamily


@dataclass
class UnixConnectionSpec:
    path: str
    host: Host = field(default_factory=get_hostname)


ConnectionSpec = IpConnectionSpec | UnixConnectionSpec

NodeName = str
NodeUUID = UUID


@dataclass(order=True, frozen=True)
class NodeId:
    name: NodeName
    hostname: Host = field(default_factory=get_hostname)
    uuid: NodeUUID = field(default_factory=uuid1)

    def __str__(self) -> str:
        name = repr(self.name) if ' ' in self.name else self.name
        short_uuid = str(self.uuid)[:4]
        return f'{name}@{self.hostname} ({short_uuid})'


@dataclass
class MeshNodeSpec:
    id: NodeId
    connection_specs: list[ConnectionSpec]
    topics: set[Topic]
    services: set[Service]


@dataclass
class MeshTopologySpec:
    nodes: Collection[MeshNodeSpec]
