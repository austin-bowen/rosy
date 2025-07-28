import time
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from itertools import chain, groupby
from random import Random
from typing import Any

from rosy.specs import MeshNodeSpec, NodeId
from rosy.types import Service, Topic

GroupKey = Callable[[MeshNodeSpec], Any]


class TopicLoadBalancer(ABC):
    @abstractmethod
    def choose_nodes(self, nodes: list[MeshNodeSpec], topic: Topic) -> list[MeshNodeSpec]:
        """
        Takes a list of nodes listening to the given topic
        and returns which nodes to send the message to.
        """
        ...  # pragma: no cover


class ServiceLoadBalancer(ABC):
    @abstractmethod
    def choose_node(self, nodes: list[MeshNodeSpec], service: Service) -> MeshNodeSpec | None:
        """
        Takes a list of nodes providing the given service
        and returns which node to send the request to.
        """
        ...  # pragma: no cover


class NoopTopicLoadBalancer(TopicLoadBalancer):
    """No load balancing. Sends to all nodes."""

    def choose_nodes(self, nodes: list[MeshNodeSpec], topic: Topic) -> list[MeshNodeSpec]:
        return nodes


def node_name_group_key(node: MeshNodeSpec) -> str:
    return node.id.name


class GroupingTopicLoadBalancer(TopicLoadBalancer):
    """
    Groups nodes according to ``group_key`` and applies
    the given load balancer to each group.
    """

    def __init__(
            self,
            group_key: GroupKey,
            load_balancer: TopicLoadBalancer,
    ):
        self.group_key = group_key
        self.load_balancer = load_balancer

    def choose_nodes(self, nodes: list[MeshNodeSpec], topic: Topic) -> list[MeshNodeSpec]:
        if not nodes:
            return []

        nodes = sorted(nodes, key=self.group_key)
        grouped_nodes = (list(group) for _, group in groupby(nodes, key=self.group_key))
        return list(chain.from_iterable(
            self.load_balancer.choose_nodes(group, topic)
            for group in grouped_nodes
        ))


class RandomLoadBalancer(TopicLoadBalancer, ServiceLoadBalancer):
    """Chooses a single node at random."""

    def __init__(self, rng: Random = None):
        self.rng = rng or Random()

    def choose_nodes(self, nodes: list[MeshNodeSpec], topic: Topic) -> list[MeshNodeSpec]:
        return [self.rng.choice(nodes)] if nodes else []

    def choose_node(self, nodes: list[MeshNodeSpec], service: Service) -> MeshNodeSpec | None:
        return self.rng.choice(nodes) if nodes else None


class LeastRecentLoadBalancer(TopicLoadBalancer, ServiceLoadBalancer):
    """Chooses the node that has been least recently chosen."""

    def __init__(
            self,
            time_func: Callable[[], float | int] = time.monotonic_ns,
            rng: Random = None,
    ):
        self.time_func = time_func
        self.rng = rng or Random()

        # By defaulting the last used time to a random value before the current time,
        # we ensure that any ties between new nodes will be broken randomly,
        # while still ensuring new nodes will be chosen first.
        t0 = time_func()
        self._last_used: defaultdict[NodeId, float | int] = defaultdict(
            lambda: t0 * self.rng.random(),
        )

    def choose_nodes(self, nodes: list[MeshNodeSpec], topic: Topic) -> list[MeshNodeSpec]:
        return [self._get_least_recent_node(nodes)] if nodes else []

    def choose_node(self, nodes: list[MeshNodeSpec], service: Service) -> MeshNodeSpec | None:
        return self._get_least_recent_node(nodes) if nodes else None

    def _get_least_recent_node(self, nodes: list[MeshNodeSpec]) -> MeshNodeSpec:
        last_used_times = (self._last_used[node.id] for node in nodes)

        node, _ = min(
            zip(nodes, last_used_times),
            key=lambda i: i[1],
        )

        self._last_used[node.id] = self.time_func()
        return node
