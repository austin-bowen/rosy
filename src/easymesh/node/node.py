import asyncio
import os
import socket
import sys
import time
from asyncio import StreamReader, StreamWriter
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import TypeVar

from easymesh.codec import Codec
from easymesh.coordinator.client import MeshCoordinatorClient, build_coordinator_client
from easymesh.coordinator.constants import DEFAULT_COORDINATOR_PORT
from easymesh.network import get_interface_ip_address
from easymesh.node.peer import MeshPeer, PeerManager
from easymesh.node.serverprovider import (
    PortScanTcpServerProvider,
    ServerProvider,
    TmpUnixServerProvider,
    UnsupportedProviderError,
)
from easymesh.objectstreamio import MessageStreamIO, pickle_codec
from easymesh.reqres import MeshTopologyBroadcast
from easymesh.specs import MeshNodeSpec
from easymesh.types import Body, Message, Topic

T = TypeVar('T')

ListenerCallback = Callable[[Message], Awaitable[None]]


class MeshNode:
    def __init__(
            self,
            name: str,
            mesh_coordinator_client: MeshCoordinatorClient,
            server_providers: Iterable[ServerProvider],
            peer_manager: PeerManager,
            message_codec: Codec[Body],
    ):
        self.name = name
        self.mesh_coordinator_client = mesh_coordinator_client
        self.server_providers = server_providers
        self.peer_manager = peer_manager
        self.message_codec = message_codec

        self._connection_specs = []

        self._listeners: dict[Topic, set[ListenerCallback]] = defaultdict(set)

        mesh_coordinator_client.mesh_topology_broadcast_handler = self._handle_topology_broadcast

    async def start(self) -> None:
        print('Starting node servers...')
        self._connection_specs = []
        for server_provider in self.server_providers:
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
            name=self.name,
            connections=self._connection_specs,
            listening_to_topics=set(self._listeners.keys()),
        )

        print(f'node_spec={node_spec}')
        print('Registering node with server...')
        await self.mesh_coordinator_client.register_node(node_spec)

    async def _handle_connection(self, reader: StreamReader, writer: StreamWriter) -> None:
        print('New connection')
        obj_io = MessageStreamIO(reader, writer, codec=self.message_codec)

        async for message in obj_io.read_objects():
            if isinstance(message, Message):
                await self._handle_message(message)
            else:
                print(f'Received unknown message={message}')

    async def _handle_message(self, message: Message) -> None:
        await asyncio.gather(*(
            listener(message)
            for listener in self._listeners[message.topic]
        ))

    async def send(self, topic: Topic, body: Body = None):
        message = Message(topic, body)
        peers = await self._get_peers_for_topic(topic)

        self_peer = next(filter(lambda p: p.name == self.name, peers), None)

        results = await asyncio.gather(
            *(
                peer.send(message) if peer is not self_peer
                else self._handle_message(message)
                for peer in peers
            ),
            return_exceptions=True,
        )

        for peer, result in zip(peers, results):
            if isinstance(result, BaseException):
                print(
                    f'Error sending message with topic={message.topic} '
                    f'to {peer.name}: {result!r}'
                )

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
        peers = await self.peer_manager.get_peers()

        all_is_listening = await asyncio.gather(
            *(peer.is_listening_to(topic) for peer in peers)
        )

        return [
            peer for peer, is_listening in zip(peers, all_is_listening)
            if is_listening
        ]

    def get_topic_sender(self, topic: Topic) -> 'TopicSender':
        return TopicSender(self, topic)

    async def add_listener(self, topic: Topic, callback: ListenerCallback) -> None:
        self._listeners[topic].add(callback)
        await self._register_node()

    async def _handle_topology_broadcast(self, broadcast: MeshTopologyBroadcast) -> None:
        print(f'Received mesh topology broadcast: {broadcast}')
        topology = broadcast.mesh_topology
        await self.peer_manager.set_mesh_topology(topology)


@dataclass
class TopicSender:
    node: MeshNode
    topic: Topic

    async def send(self, body: Body = None) -> None:
        await self.node.send(self.topic, body)

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
        coordinator_host: str = 'localhost',
        coordinator_port: int = DEFAULT_COORDINATOR_PORT,
        allow_unix_connections: bool = True,
        allow_tcp_connections: bool = True,
        node_host: str = 'localhost',
        node_host_interface: str = None,
        message_codec: Codec[Body] = pickle_codec,
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
        if node_host_interface:
            node_host = get_interface_ip_address(node_host_interface)

        server_providers.append(PortScanTcpServerProvider(host=node_host))
    if not server_providers:
        raise ValueError('Must allow at least one type of connection')

    peer_manager = PeerManager(message_codec)

    node = MeshNode(
        name,
        mesh_coordinator_client,
        server_providers,
        peer_manager,
        message_codec
    )

    if start:
        await node.start()

    return node


async def test_mesh_node(role: str = None) -> None:
    role = role or sys.argv[1]
    assert role in {'send', 'recv'}

    interface = 'wlp0s20f3' if socket.gethostname() == 'austin-laptop' else 'eth0'

    node = await build_mesh_node(
        name=f'{role}-{os.getpid()}',
        coordinator_host='192.168.0.172',
        node_host=get_interface_ip_address(interface),
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

        async def handle_test(message: Message) -> None:
            nonlocal reqs, t00
            if t00 is None:
                t00 = time.monotonic()
            latencies.append(time.time() - message.body[0])
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
