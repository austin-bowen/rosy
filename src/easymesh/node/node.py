import asyncio
from asyncio import StreamReader, StreamWriter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal, TypeVar, Union

from easymesh.asyncio import MultiWriter, close_ignoring_errors
from easymesh.codec import Codec, pickle_codec
from easymesh.coordinator.client import MeshCoordinatorClient, build_coordinator_client
from easymesh.coordinator.constants import DEFAULT_COORDINATOR_PORT
from easymesh.network import get_lan_hostname
from easymesh.node.listenermanager import ListenerCallback, ListenerManager, SerialTopicsListenerManager
from easymesh.node.loadbalancing import (
    GroupingLoadBalancer,
    LoadBalancer,
    NoopLoadBalancer,
    RoundRobinLoadBalancer,
    node_name_group_key,
)
from easymesh.node.peer import MeshPeer, PeerManager
from easymesh.node.serverprovider import (
    PortScanTcpServerProvider,
    ServerProvider,
    TmpUnixServerProvider,
    UnsupportedProviderError,
)
from easymesh.objectio import MessageReader, MessageWriter
from easymesh.reqres import MeshTopologyBroadcast
from easymesh.specs import MeshNodeSpec, NodeId
from easymesh.types import Data, Host, Message, Port, ServerHost, Topic

T = TypeVar('T')


class MeshNode:
    def __init__(
            self,
            id: NodeId,
            mesh_coordinator_client: MeshCoordinatorClient,
            server_providers: Iterable[ServerProvider],
            listener_manager: ListenerManager,
            peer_manager: PeerManager,
            message_codec: Codec[Data],
            load_balancer: LoadBalancer,
    ):
        self._id = id
        self._mesh_coordinator_client = mesh_coordinator_client
        self._server_providers = server_providers
        self._listener_manager = listener_manager
        self._peer_manager = peer_manager
        self._message_codec = message_codec
        self._load_balancer = load_balancer

        self._connection_specs = []

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
            listening_to_topics=self._listener_manager.get_topics(),
        )

        print(f'node_spec={node_spec}')
        print('Registering node with server...')
        await self._mesh_coordinator_client.register_node(node_spec)

    async def _handle_connection(self, reader: StreamReader, writer: StreamWriter) -> None:
        peer_name = writer.get_extra_info('peername') or writer.get_extra_info('sockname')
        print(f'New connection from: {peer_name}')

        # Don't need the writer
        writer.write_eof()

        message_reader = MessageReader(reader, codec=self._message_codec)

        try:
            async for message in message_reader:
                await self._listener_manager.handle_message(message)
        except EOFError:
            print(f'Closed connection from: {peer_name}')
        finally:
            await close_ignoring_errors(writer)

    async def send(self, topic: Topic, data: Data = None):
        peers = await self._get_peers_for_topic(topic)

        self_peer = next(filter(lambda p: p.id == self.id, peers), None)

        writers = [
            await peer.connection.get_writer() for peer in peers
            if peer is not self_peer
        ]

        multi_writer = MultiWriter(writers)
        message_writer = MessageWriter(multi_writer, codec=self._message_codec)
        message = Message(topic, data)

        [await writer.lock.acquire() for writer in writers]

        try:
            await message_writer.write(message, drain=False)

            # TODO This doesn't guarantee self-messages are processed in order
            send_to_self = (
                asyncio.create_task(self._listener_manager.handle_message(message))
                if self_peer is not None else None
            )

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
        finally:
            [writer.lock.release() for writer in writers]

        for connection in to_close:
            await connection.close()

        if send_to_self is not None:
            await send_to_self

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

    async def wait_for_listener(self, topic: Topic, poll_interval: float = 1.) -> None:
        while not await self.topic_has_listeners(topic):
            await asyncio.sleep(poll_interval)

    async def _get_peers_for_topic(self, topic: Topic) -> list[MeshPeer]:
        peers = self._peer_manager.get_peers()

        listening_peers = [p for p in peers if await p.is_listening_to(topic)]

        return self._load_balancer.choose_nodes(listening_peers, topic)

    def get_topic_sender(self, topic: Topic) -> 'TopicSender':
        return TopicSender(self, topic)

    async def add_listener(self, topic: Topic, callback: ListenerCallback) -> None:
        self._listener_manager.add_listener(topic, callback)
        await self._register_node()

    async def remove_listener(self, topic: Topic, callback: ListenerCallback) -> None:
        self._listener_manager.remove_listener(topic, callback)
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
        message_queue_maxsize: int = 10,
        message_codec: Codec[Data] = pickle_codec,
        load_balancer: Union[LoadBalancer, Literal['default'], None] = 'default',
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

        provider = PortScanTcpServerProvider(node_server_host, node_client_host)

        server_providers.append(provider)
    if not server_providers:
        raise ValueError('Must allow at least one type of connection')

    listener_manager = SerialTopicsListenerManager(message_queue_maxsize)
    peer_manager = PeerManager()

    if load_balancer == 'default':
        load_balancer = GroupingLoadBalancer(node_name_group_key, RoundRobinLoadBalancer())
    elif load_balancer is None:
        load_balancer = NoopLoadBalancer()

    node = MeshNode(
        NodeId(name),
        mesh_coordinator_client,
        server_providers,
        listener_manager,
        peer_manager,
        message_codec,
        load_balancer,
    )

    if start:
        await node.start()

    return node
