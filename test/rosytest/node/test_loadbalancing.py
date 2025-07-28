import time
from random import Random
from unittest.mock import call, create_autospec

from rosy.node.loadbalancing import (
    GroupingTopicLoadBalancer,
    LeastRecentLoadBalancer,
    NoopTopicLoadBalancer,
    RandomLoadBalancer,
    RoundRobinLoadBalancer,
    ServiceLoadBalancer,
    TopicLoadBalancer,
    node_name_group_key,
)
from rosy.specs import MeshNodeSpec, NodeId
from rosy.types import Service, Topic


class TopicLoadBalancerTest:
    load_balancer: TopicLoadBalancer

    def test_choose_nodes_empty(self):
        assert self.load_balancer.choose_nodes([], 'any_topic') == []


class ServiceLoadBalancerTest:
    load_balancer: ServiceLoadBalancer

    def test_choose_node_empty(self):
        assert self.load_balancer.choose_node([], 'any_topic') is None


class TestNoopTopicLoadBalancer(TopicLoadBalancerTest):
    def setup_method(self):
        self.load_balancer = NoopTopicLoadBalancer()

    def test_choose_nodes_returns_all_nodes(self):
        nodes = [mock_node(), mock_node(), mock_node()]

        assert self.load_balancer.choose_nodes(nodes, 'any_topic') is nodes


class TestGroupingTopicLoadBalancer(TopicLoadBalancerTest):
    def setup_method(self):
        self.wrapped_load_balancer = create_autospec(TopicLoadBalancer)

        self.load_balancer = GroupingTopicLoadBalancer(
            group_key=node_name_group_key,
            load_balancer=self.wrapped_load_balancer,
        )

    def test_choose_nodes_picks_from_groups(self):
        self.wrapped_load_balancer.choose_nodes.side_effect = (
            lambda nodes_, topic_: [nodes_[0]]
        )

        nodes = [
            mock_node('a'),
            mock_node('a'),
            mock_node('b'),
            mock_node('b'),
        ]

        result = self.load_balancer.choose_nodes(nodes, 'any_topic')

        assert result == [
            nodes[0],
            nodes[2],
        ]

        self.wrapped_load_balancer.choose_nodes.assert_has_calls([
            call(nodes[:2], 'any_topic'),
            call(nodes[2:], 'any_topic'),
        ])


class TestRandomLoadBalancer(TopicLoadBalancerTest, ServiceLoadBalancerTest):
    load_balancer: RandomLoadBalancer

    def setup_method(self):
        self.nodes = [mock_node(), mock_node(), mock_node()]
        self.expected_node = self.nodes[1]

        # RNG that "randomly" picks the second item from the list
        rng = create_autospec(Random)
        rng.choice.side_effect = lambda items: items[1]

        self.load_balancer = RandomLoadBalancer(rng)

    def test_choose_nodes_returns_random_node(self):
        assert self.load_balancer.choose_nodes(
            self.nodes,
            'any_topic',
        ) == [self.expected_node]

    def test_choose_node_returns_random_node(self):
        assert self.load_balancer.choose_node(
            self.nodes,
            'any_service',
        ) is self.expected_node


class TestRoundRobinLoadBalancer(TopicLoadBalancerTest, ServiceLoadBalancerTest):
    load_balancer: RoundRobinLoadBalancer

    def setup_method(self):
        self.nodes = [mock_node(), mock_node(), mock_node()]

        self.load_balancer = RoundRobinLoadBalancer()

    def test_choose_nodes_returns_first_node(self):
        assert self._choose_nodes('topic0') == [self.nodes[0]]
        assert self._choose_nodes('topic0') == [self.nodes[1]]
        assert self._choose_nodes('topic1') == [self.nodes[0]]
        assert self._choose_nodes('topic0') == [self.nodes[2]]
        assert self._choose_nodes('topic0') == [self.nodes[0]]
        assert self._choose_nodes('topic1') == [self.nodes[1]]
        assert self._choose_nodes('topic1') == [self.nodes[2]]
        assert self._choose_nodes('topic1') == [self.nodes[0]]

    def _choose_nodes(self, topic: Topic) -> list[MeshNodeSpec]:
        return self.load_balancer.choose_nodes(self.nodes, topic)

    def test_choose_node_returns_first_node(self):
        assert self._choose_node('service0') is self.nodes[0]
        assert self._choose_node('service0') is self.nodes[1]
        assert self._choose_node('service1') is self.nodes[0]
        assert self._choose_node('service0') is self.nodes[2]
        assert self._choose_node('service0') is self.nodes[0]
        assert self._choose_node('service1') is self.nodes[1]
        assert self._choose_node('service1') is self.nodes[2]
        assert self._choose_node('service1') is self.nodes[0]

    def _choose_node(self, service: Service) -> MeshNodeSpec:
        return self.load_balancer.choose_node(self.nodes, service)


class TestLeastRecentLoadBalancer(TopicLoadBalancerTest, ServiceLoadBalancerTest):
    load_balancer: LeastRecentLoadBalancer

    def setup_method(self):
        self.nodes = [
            mock_node('node0'),
            mock_node('node1'),
            mock_node('node2'),
        ]

        self.load_balancer = LeastRecentLoadBalancer()

    def test_default_time_func_is_monotonic_ns(self):
        load_balancer = LeastRecentLoadBalancer()
        assert load_balancer.time_func is time.monotonic_ns

    def test_choose_methods_pick_least_recent(self):
        nodes = self.load_balancer.choose_nodes(self.nodes, 'any_topic')
        assert len(nodes) == 1
        node0 = nodes[0]

        node1 = self.load_balancer.choose_node(self.nodes, 'any_service')

        nodes = self.load_balancer.choose_nodes(self.nodes, 'any_topic')
        assert len(nodes) == 1
        node2 = nodes[0]

        selected_nodes = {node0, node1, node2}
        assert selected_nodes == set(self.nodes)

        assert self.load_balancer.choose_node(self.nodes, 'any_service') == node0
        assert self.load_balancer.choose_nodes(self.nodes, 'any_topic') == [node1]
        assert self.load_balancer.choose_node(self.nodes, 'any_service') == node2


def mock_node(name: str = None):
    node = create_autospec(MeshNodeSpec)

    if name is not None:
        node.id = NodeId(name)

    return node
