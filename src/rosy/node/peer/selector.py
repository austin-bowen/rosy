from rosy.node.loadbalancing import ServiceLoadBalancer, TopicLoadBalancer
from rosy.node.topology import MeshTopologyManager
from rosy.specs import MeshNodeSpec
from rosy.types import Service, Topic


class PeerSelector:
    def __init__(
        self,
        topology_manager: MeshTopologyManager,
        topic_load_balancer: TopicLoadBalancer,
        service_load_balancer: ServiceLoadBalancer,
    ):
        self.topology_manager = topology_manager
        self.topic_load_balancer = topic_load_balancer
        self.service_load_balancer = service_load_balancer

    def get_nodes_for_topic(self, topic: Topic) -> list[MeshNodeSpec]:
        peers = self.topology_manager.get_nodes_listening_to_topic(topic)
        return self.topic_load_balancer.choose_nodes(peers, topic)

    def get_node_for_service(self, service: Service) -> MeshNodeSpec | None:
        peers = self.topology_manager.get_nodes_providing_service(service)
        return self.service_load_balancer.choose_node(peers, service)
