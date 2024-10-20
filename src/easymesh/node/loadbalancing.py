from abc import abstractmethod
from collections import Counter
from collections.abc import Callable
from itertools import chain, groupby
from random import Random
from typing import Any

from easymesh.node.peer import MeshPeer
from easymesh.types import Topic

GroupKey = Callable[[MeshPeer], Any]


class LoadBalancer:
    @abstractmethod
    def choose_nodes(self, nodes: list[MeshPeer], topic: Topic) -> list[MeshPeer]:
        """
        Takes a list of nodes listening to the given topic
        and returns which nodes to send the message to.
        """
        ...


def node_name_group_key(peer: MeshPeer) -> str:
    return peer.id.name


def node_name_and_hostname_group_key(peer: MeshPeer) -> tuple[str, str]:
    return peer.id.name, peer.id.hostname


class GroupingLoadBalancer(LoadBalancer):
    """
    Groups nodes according to ``group_key`` and applies
    the given load balancer to each group.
    """

    def __init__(
            self,
            group_key: GroupKey,
            load_balancer: LoadBalancer,
    ):
        self.group_key = group_key
        self.load_balancer = load_balancer

    def choose_nodes(self, nodes: list[MeshPeer], topic: Topic) -> list[MeshPeer]:
        nodes = sorted(nodes, key=self.group_key)
        grouped_nodes = (list(group) for _, group in groupby(nodes, key=self.group_key))
        return list(chain.from_iterable(
            self.load_balancer.choose_nodes(group, topic)
            for group in grouped_nodes
        ))


class NoopLoadBalancer(LoadBalancer):
    def choose_nodes(self, nodes: list[MeshPeer], topic: Topic) -> list[MeshPeer]:
        return nodes


class RandomLoadBalancer(LoadBalancer):
    """Chooses a single node at random."""

    def __init__(self, rng: Random = None):
        self.rng = rng or Random()

    def choose_nodes(self, nodes: list[MeshPeer], topic: Topic) -> list[MeshPeer]:
        return [self.rng.choice(nodes)]


class RoundRobinLoadBalancer(LoadBalancer):
    """
    Chooses a single node in a round-robin fashion, based on
    the number of times a message is sent on the topic.
    """

    def __init__(self):
        self._topic_counter: Counter[Topic] = Counter()

    def choose_nodes(self, nodes: list[MeshPeer], topic: Topic) -> list[MeshPeer]:
        i = self._topic_counter[topic] % len(nodes)
        self._topic_counter[topic] += 1
        return [nodes[i]]
