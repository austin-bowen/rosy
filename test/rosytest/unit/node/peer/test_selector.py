from unittest.mock import create_autospec

from rosy.node.loadbalancing import ServiceLoadBalancer, TopicLoadBalancer
from rosy.node.peer.selector import PeerSelector
from rosy.node.topology import MeshTopologyManager


class TestPeerSelector:
    def setup_method(self):
        self.topology_manager = create_autospec(MeshTopologyManager)
        self.topic_load_balancer = create_autospec(TopicLoadBalancer)
        self.service_load_balancer = create_autospec(ServiceLoadBalancer)

        self.selector = PeerSelector(
            self.topology_manager,
            self.topic_load_balancer,
            self.service_load_balancer,
        )

    def test_get_nodes_for_topic(self):
        nodes = ["node0", "node1"]
        self.topology_manager.get_nodes_listening_to_topic.return_value = nodes
        self.topic_load_balancer.choose_nodes.return_value = ["node1"]

        topic = "topic"

        result = self.selector.get_nodes_for_topic(topic)

        assert result == ["node1"]

        self.topology_manager.get_nodes_listening_to_topic.assert_called_once_with(
            topic
        )
        self.topic_load_balancer.choose_nodes.assert_called_once_with(nodes, topic)
        self.service_load_balancer.choose_node.assert_not_called()

    def test_get_node_for_service(self):
        nodes = ["node0", "node1"]
        self.topology_manager.get_nodes_providing_service.return_value = nodes
        self.service_load_balancer.choose_node.return_value = "node1"

        service = "service"

        result = self.selector.get_node_for_service(service)

        assert result == "node1"

        self.topology_manager.get_nodes_providing_service.assert_called_once_with(
            service
        )
        self.service_load_balancer.choose_node.assert_called_once_with(nodes, service)
        self.topic_load_balancer.choose_nodes.assert_not_called()
