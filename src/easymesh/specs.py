import socket
from dataclasses import dataclass
from typing import Union

from easymesh.types import Host, Port, Topic


@dataclass
class IpConnectionSpec:
    host: Host
    port: Port


@dataclass
class UnixConnectionSpec:
    path: str
    host: Host = socket.gethostname()


ConnectionSpec = Union[IpConnectionSpec, UnixConnectionSpec]

NodeName = str


@dataclass
class MeshNodeSpec:
    name: NodeName
    connections: list[ConnectionSpec]
    listening_to_topics: set[Topic]


@dataclass
class MeshTopologySpec:
    nodes: dict[NodeName, MeshNodeSpec]

    def put_node(self, node: MeshNodeSpec) -> None:
        self.nodes[node.name] = node
