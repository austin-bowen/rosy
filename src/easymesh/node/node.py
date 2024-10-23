import asyncio
import os
import sys
import time
from asyncio import StreamReader, StreamWriter
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import TypeVar

from easymesh.asyncio import MultiWriter, many
from easymesh.codec import Codec
from easymesh.coordinator.client import MeshCoordinatorClient, build_coordinator_client
from easymesh.coordinator.constants import DEFAULT_COORDINATOR_PORT
from easymesh.network import get_hostname, get_interface_ip_address, get_lan_hostname
from easymesh.node.loadbalancing import GroupingLoadBalancer, LoadBalancer, RoundRobinLoadBalancer, \
    node_name_group_key
from easymesh.node.peer import MeshPeer, PeerManager
from easymesh.node.serverprovider import (
    PortScanTcpServerProvider,
    ServerProvider,
    TmpUnixServerProvider,
    UnsupportedProviderError,
)
from easymesh.objectstreamio import MessageStreamIO, pickle_codec
from easymesh.reqres import MeshTopologyBroadcast
from easymesh.specs import MeshNodeSpec, NodeId
from easymesh.types import Data, Host, Message, Port, ServerHost, Topic

T = TypeVar('T')

ListenerCallback = Callable[[Topic, Data], Awaitable[None]]


class MeshNode:
    def __init__(
            self,
            id: NodeId,
            mesh_coordinator_client: MeshCoordinatorClient,
            server_providers: Iterable[ServerProvider],
            peer_manager: PeerManager,
            message_codec: Codec[Data],
            load_balancer: LoadBalancer,
    ):
        self._id = id
        self._mesh_coordinator_client = mesh_coordinator_client
        self._server_providers = server_providers
        self._peer_manager = peer_manager
        self._message_codec = message_codec
        self._load_balancer = load_balancer

        self._connection_specs = []

        self._listeners: dict[Topic, set[ListenerCallback]] = defaultdict(set)

        mesh_coordinator_client.mesh_topology_broadcast_handler = self._handle_topology_broadcast

    @property
    def id(self) -> NodeId:
        return self._id

    def __str__(self) -> str:
        return str(self.id)

    async def start(self) -> None:
        print('Starting node servers...')
        self._connection_specs = []
        for server_provider in self._server_providers:
            try:
                server, connection_spec = await server_provider.start_server(
                    self._handle_connection
                )
            except UnsupportedProviderError as e:
                print(e)
            else:
                print(f'Started node server with connection_spec={connection_spec}')
                self._connection_specs.append(connection_spec)

        if not self._connection_specs:
            raise RuntimeError('Unable to start any node servers')

        await self._register_node()

    async def _register_node(self) -> None:
        node_spec = MeshNodeSpec(
            id=self.id,
            connections=self._connection_specs,
            listening_to_topics=set(self._listeners.keys()),
        )

        print(f'node_spec={node_spec}')
        print('Registering node with server...')
        await self._mesh_coordinator_client.register_node(node_spec)

    async def _handle_connection(self, reader: StreamReader, writer: StreamWriter) -> None:
        peer_name = writer.get_extra_info('peername')
        sock_name = writer.get_extra_info('sockname')
        print(f'New connection from: {peer_name or sock_name}')

        obj_io = MessageStreamIO(reader, writer, codec=self._message_codec)

        async for message in obj_io.read_objects():
            if isinstance(message, Message):
                await self._handle_message(message)
            else:
                print(f'Received unknown message={message}')

    async def _handle_message(self, message: Message) -> None:
        await many([
            listener(message.topic, message.data)
            for listener in self._listeners[message.topic]
        ])

    async def send(self, topic: Topic, data: Data = None):
        peers = await self._get_peers_for_topic(topic)

        # TODO use this
        self_peer = next(filter(lambda p: p.id == self.id, peers), None)

        # TODO lock the writers
        writers = [await peer.connection.get_writer() for peer in peers]
        multi_writer = MultiWriter(writers)

        obj_io = MessageStreamIO(None, multi_writer, codec=self._message_codec)
        await obj_io.write_object(Message(topic, data), drain=False)

        to_close = []
        for peer, writer in zip(peers, writers):
            try:
                await writer.drain()
            except Exception as e:
                print(
                    f'Error sending message with topic={topic} '
                    f'to node {peer.id}: {e!r}'
                )

                to_close.append(peer.connection)

        for connection in to_close:
            await connection.close()

    async def send_result(
            self,
            topic: Topic,
            fn: Callable[[...], T],
            *args,
            **kwargs,
    ) -> tuple[bool, T]:
        """
        Send the result of a function to all listeners of a topic.

        This is "lazy" in that it will only call the function if there are
        listeners for the topic. This is useful in avoiding unnecessary
        computation when no one is listening.

        Returns a tuple of (did_send, result). If there were no listeners, then
        this returns (False, None).
        """

        if not await self.topic_has_listeners(topic):
            return False, None

        result = fn(*args, **kwargs)
        if asyncio.iscoroutine(result):
            result = await result

        await self.send(topic, result)

        return True, result

    async def topic_has_listeners(self, topic: Topic) -> bool:
        peers = await self._get_peers_for_topic(topic)
        return bool(peers)

    async def _get_peers_for_topic(self, topic: Topic) -> list[MeshPeer]:
        peers = await self._peer_manager.get_peers()

        all_is_listening = [await peer.is_listening_to(topic) for peer in peers]

        peers = [
            peer for peer, is_listening in zip(peers, all_is_listening)
            if is_listening
        ]

        return self._load_balancer.choose_nodes(peers, topic)

    def get_topic_sender(self, topic: Topic) -> 'TopicSender':
        return TopicSender(self, topic)

    async def add_listener(self, topic: Topic, callback: ListenerCallback) -> None:
        self._listeners[topic].add(callback)
        await self._register_node()

    async def _handle_topology_broadcast(self, broadcast: MeshTopologyBroadcast) -> None:
        print('Received mesh topology broadcast')
        topology = broadcast.mesh_topology
        await self._peer_manager.set_mesh_topology(topology)


@dataclass
class TopicSender:
    node: MeshNode
    topic: Topic

    async def send(self, data: Data = None) -> None:
        await self.node.send(self.topic, data)

    async def send_result(
            self,
            fn: Callable[[...], T],
            *args,
            **kwargs,
    ) -> tuple[bool, T]:
        return await self.node.send_result(self.topic, fn, *args, **kwargs)

    async def has_listeners(self) -> bool:
        return await self.node.topic_has_listeners(self.topic)


async def build_mesh_node(
        name: str,
        coordinator_host: Host = 'localhost',
        coordinator_port: Port = DEFAULT_COORDINATOR_PORT,
        allow_unix_connections: bool = True,
        allow_tcp_connections: bool = True,
        node_server_host: ServerHost = None,
        node_client_host: Host = None,
        node_host_interface: str = None,
        message_codec: Codec[Data] = pickle_codec,
        load_balancer: LoadBalancer = None,
        start: bool = True,
) -> MeshNode:
    mesh_coordinator_client = await build_coordinator_client(
        coordinator_host,
        coordinator_port,
    )

    server_providers = []
    if allow_unix_connections:
        server_providers.append(TmpUnixServerProvider())
    if allow_tcp_connections:
        if not node_client_host:
            node_client_host = get_lan_hostname()

        if node_host_interface:
            node_server_host = node_client_host = \
                get_interface_ip_address(node_host_interface)

        provider = PortScanTcpServerProvider(node_server_host, node_client_host)

        server_providers.append(provider)
    if not server_providers:
        raise ValueError('Must allow at least one type of connection')

    peer_manager = PeerManager()

    node = MeshNode(
        NodeId(name),
        mesh_coordinator_client,
        server_providers,
        peer_manager,
        message_codec,
        load_balancer=load_balancer or GroupingLoadBalancer(node_name_group_key, RoundRobinLoadBalancer()),
    )

    if start:
        await node.start()

    return node


async def test_mesh_node(role: str = None) -> None:
    role = role or sys.argv[1]
    assert role in {'send', 'recv'}

    interface = 'wlp0s20f3' if get_hostname() == 'austin-laptop' else 'eth0'

    node = await build_mesh_node(
        name=f'{role}-{os.getpid()}',
        coordinator_host='austin-laptop.local',
        node_host_interface=interface,
    )

    if role == 'send':
        async def expensive_task():
            await asyncio.sleep(1.)
            return time.time(), 'expensive task ran'

        test_topic = node.get_topic_sender('test')
        while True:
            result = await test_topic.send_result(
                expensive_task,
            )
            print(result)
            await asyncio.sleep(0.5)
    elif role == 'recv':
        reqs = 0
        last_reqs = -1
        t00 = None
        latencies = []

        async def handle_test(topic_, data_) -> None:
            nonlocal reqs, t00
            if t00 is None:
                t00 = time.monotonic()
            latencies.append(time.time() - data_[0])
            reqs += 1
            # print(f'Received test message: {message}')
            # print('Received test message')
            rps = reqs / (time.monotonic() - t00)
            # print(f'rps={rps}')

        await node.add_listener('', handle_test)
        await node.add_listener('t', handle_test)
        await node.add_listener('test', handle_test)

        while True:
            await asyncio.sleep(1.)

            if reqs != last_reqs:
                print(f'reqs={reqs}')
                last_reqs = reqs

                if latencies:
                    print('avg latency:', sum(latencies) / len(latencies))


async def main():
    await test_mesh_node()


if __name__ == '__main__':
    asyncio.run(main())
