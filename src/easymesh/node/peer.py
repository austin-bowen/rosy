from abc import abstractmethod
from asyncio import open_connection, open_unix_connection
from dataclasses import dataclass
from typing import Iterable, Optional

from easymesh.asyncio import Writer, many
from easymesh.network import get_hostname
from easymesh.specs import (
    ConnectionSpec,
    IpConnectionSpec,
    MeshNodeSpec,
    MeshTopologySpec,
    NodeId,
    UnixConnectionSpec,
)
from easymesh.types import Host, Topic


class PeerWriterBuilder:
    def __init__(self, host: Host = None):
        self.host = host or get_hostname()

    async def build(self, conn_specs: Iterable[ConnectionSpec]) -> Writer:
        writer = None
        for conn_spec in conn_specs:
            try:
                _, writer = await self._get_connection(conn_spec)
            except ConnectionError as e:
                print(f'Error connecting to {conn_spec}: {e}')
                continue
            else:
                break

        if not writer:
            raise ConnectionError('Could not connect to any connection spec')

        return writer

    async def _get_connection(self, conn_spec: ConnectionSpec):
        if isinstance(conn_spec, IpConnectionSpec):
            return await open_connection(
                host=conn_spec.host,
                port=conn_spec.port,
            )
        elif isinstance(conn_spec, UnixConnectionSpec):
            if conn_spec.host != self.host:
                raise ConnectionError(
                    f'Unix connection host={conn_spec.host} '
                    f'does not match local host={self.host}'
                )

            return await open_unix_connection(path=conn_spec.path)
        else:
            raise ValueError(f'Invalid connection spec: {conn_spec}')


class PeerWriterPool:
    def __init__(self, writer_builder: PeerWriterBuilder):
        self.writer_builder = writer_builder
        self._writers: dict[NodeId, Writer] = {}

    def clear(self) -> None:
        self._writers = {}

    async def get_writer_for(self, peer_spec: MeshNodeSpec) -> Writer:
        writer = self._writers.get(peer_spec.id, None)
        if writer is not None:
            return writer

        try:
            writer = await self.writer_builder.build(peer_spec.connections)
        except Exception as e:
            raise ConnectionError(f'Error connecting to {peer_spec.id}: {e!r}')

        print(f'Connected to {peer_spec.id}')
        self._writers[peer_spec.id] = writer

        return writer

    def get_node_ids_with_writers(self) -> set[NodeId]:
        return set(self._writers.keys())

    def remove_writer_for(self, node_id: NodeId) -> Optional[Writer]:
        return self._writers.pop(node_id, None)


class PeerConnection:
    @abstractmethod
    async def get_writer(self) -> Writer:
        ...

    @abstractmethod
    async def close(self) -> None:
        ...


class LazyPeerConnection(PeerConnection):
    def __init__(
            self,
            peer_spec: MeshNodeSpec,
            peer_connection_pool: PeerWriterPool,
    ):
        self.peer_spec = peer_spec
        self.connection_pool = peer_connection_pool

    async def get_writer(self) -> Writer:
        return await self.connection_pool.get_writer_for(self.peer_spec)

    async def close(self) -> None:
        # TODO use this
        writer = self.connection_pool.remove_writer_for(self.peer_spec.id)
        if writer is not None:
            await writer.close()


@dataclass
class MeshPeer:
    id: NodeId
    topics: set[Topic]
    connection: PeerConnection

    async def is_listening_to(self, topic: Topic) -> bool:
        return topic in self.topics


class PeerManager:
    def __init__(self):
        self._connection_pool = PeerWriterPool(
            writer_builder=PeerWriterBuilder(),
        )
        self._peers: list[MeshPeer] = []

    def get_peers(self) -> list[MeshPeer]:
        return self._peers

    async def set_mesh_topology(self, mesh_topology: MeshTopologySpec) -> None:
        self._set_peers(mesh_topology)

        old_nodes_with_conns = self._connection_pool.get_node_ids_with_writers()
        new_nodes = set(node.id for node in mesh_topology.nodes)
        nodes_to_remove = old_nodes_with_conns - new_nodes

        connections_to_close = (
            self._connection_pool.remove_writer_for(node_id)
            for node_id in nodes_to_remove
        )

        await many([conn.close() for conn in connections_to_close])

    def _set_peers(self, mesh_topology: MeshTopologySpec) -> None:
        self._peers = [
            MeshPeer(
                id=node.id,
                topics=node.listening_to_topics,
                connection=LazyPeerConnection(
                    peer_spec=node,
                    peer_connection_pool=self._connection_pool,
                ),
            ) for node in mesh_topology.nodes
        ]
