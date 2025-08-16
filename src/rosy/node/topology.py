import logging
from collections import defaultdict

from rosy.node.peer.connection import PeerConnectionManager
from rosy.specs import MeshNodeSpec, MeshTopologySpec
from rosy.types import Service, Topic

logger = logging.getLogger(__name__)


class MeshTopologyManager:
    def __init__(self):
        self._topology: MeshTopologySpec
        self._topic_nodes: dict[Topic, list[MeshNodeSpec]]
        self._service_nodes: dict[Service, list[MeshNodeSpec]]

        self.set_topology(MeshTopologySpec(nodes=[]))

    @property
    def topology(self) -> MeshTopologySpec:
        return self._topology

    def set_topology(self, topology: MeshTopologySpec) -> None:
        self._topology = topology

        self._cache_topic_nodes()
        self._cache_service_nodes()

    def _cache_topic_nodes(self) -> None:
        topic_nodes = defaultdict(list)

        for node in self.topology.nodes:
            for topic in node.topics:
                topic_nodes[topic].append(node)

        self._topic_nodes_cache = topic_nodes

    def _cache_service_nodes(self) -> None:
        service_nodes = defaultdict(list)

        for node in self.topology.nodes:
            for service in node.services:
                service_nodes[service].append(node)

        self._service_nodes_cache = service_nodes

    def get_nodes_listening_to_topic(self, topic: Topic) -> list[MeshNodeSpec]:
        return self._topic_nodes_cache[topic]

    def get_nodes_providing_service(self, service: str) -> list[MeshNodeSpec]:
        return self._service_nodes_cache[service]

    def get_removed_nodes(
        self,
        new_topology: MeshTopologySpec,
    ) -> list[MeshNodeSpec]:
        """
        Returns a list of nodes that were removed in the new topology.
        """

        new_node_ids = {node.id for node in new_topology.nodes}

        return [node for node in self.topology.nodes if node.id not in new_node_ids]


class TopologyChangedHandler:
    def __init__(
        self,
        topology_manager: MeshTopologyManager,
        connection_manager: PeerConnectionManager,
    ):
        self.topology_manager = topology_manager
        self.connection_manager = connection_manager

    async def __call__(self, new_topology: MeshTopologySpec) -> None:
        logger.debug(
            f"Received mesh topology broadcast with "
            f"{len(new_topology.nodes)} nodes."
        )

        removed_nodes = self.topology_manager.get_removed_nodes(new_topology)
        logger.debug(
            f"Removed {len(removed_nodes)} nodes: "
            f"{[str(node.id) for node in removed_nodes]}"
        )

        self.topology_manager.set_topology(new_topology)

        for node in removed_nodes:
            await self.connection_manager.close_connection(node)
