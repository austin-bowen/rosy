import asyncio
import os
import sys
import tempfile
import time
from abc import abstractmethod
from asyncio import Server, StreamReader, StreamWriter, open_connection, open_unix_connection
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Optional, TypeVar

from easymesh.asyncio import noop
from easymesh.coordinator import MeshCoordinatorClient, RPCMeshCoordinatorClient
from easymesh.objectstreamio import AnyObjectStreamIO, MessageStreamIO, ObjectStreamIO
from easymesh.reqres import MeshTopologyBroadcast
from easymesh.rpc import ObjectStreamRPC
from easymesh.server import AUTHENTICATED_RESPONSE
from easymesh.specs import (
    ConnectionSpec,
    IpConnectionSpec,
    MeshNodeSpec,
    MeshTopologySpec,
    NodeName,
    UnixConnectionSpec,
)
from easymesh.utils import ephemeral_port_range
from easymesh.types import Body, Message, Topic

T = TypeVar('T')


class PeerConnection:
    @abstractmethod
    async def send(self, message: Message) -> None:
        ...


class ObjectStreamPeerConnection(PeerConnection):
    def __init__(self, obj_io: ObjectStreamIO[Message]):
        self.obj_io = obj_io

    async def send(self, message: Message) -> None:
        await self.obj_io.write_object(message)


class PeerConnectionBuilder:
    async def build(self, conn_spec: ConnectionSpec) -> PeerConnection:
        if isinstance(conn_spec, IpConnectionSpec):
            reader, writer = await open_connection(
                host=conn_spec.host,
                port=conn_spec.port,
            )
        elif isinstance(conn_spec, UnixConnectionSpec):
            reader, writer = await open_unix_connection(path=conn_spec.path)
        else:
            raise ValueError(f'Invalid connection spec: {conn_spec}')

        return ObjectStreamPeerConnection(
            obj_io=MessageStreamIO(reader, writer),
        )


class PeerConnectionPool:
    def __init__(self, connection_builder: PeerConnectionBuilder):
        self.connection_builder = connection_builder
        self._connections: dict[str, PeerConnection] = {}

    def clear(self) -> None:
        self._connections = {}

    async def get_connection_for(self, peer_spec: MeshNodeSpec) -> PeerConnection:
        conn = self._connections.get(peer_spec.name, None)

        if conn is None:
            conn = await self.connection_builder.build(peer_spec.connection)
            self._connections[peer_spec.name] = conn

        return conn


class LazyPeerConnection(PeerConnection):
    def __init__(
            self,
            peer_spec: MeshNodeSpec,
            peer_connection_pool: PeerConnectionPool,
    ):
        self.peer_spec = peer_spec
        self.connection_pool = peer_connection_pool

    async def send(self, message: Message) -> None:
        connection = await self.connection_pool.get_connection_for(self.peer_spec)
        return await connection.send(message)


class MeshPeer:
    def __init__(
            self,
            name: NodeName,
            topics: set[Topic],
            connection: PeerConnection,
    ):
        self.name = name
        self.topics = topics
        self.connection = connection

    async def send(self, message: Message) -> None:
        await self.connection.send(message)

    async def is_listening_to(self, topic: Topic) -> bool:
        return topic in self.topics


class PeerManager:
    def __init__(self):
        self._connection_pool = PeerConnectionPool(
            connection_builder=PeerConnectionBuilder(),
        )
        self._mesh_topology = MeshTopologySpec(nodes={})

    async def get_peers(self) -> list[MeshPeer]:
        return [
            MeshPeer(
                name=node.name,
                topics=node.listening_to_topics,
                connection=LazyPeerConnection(
                    peer_spec=node,
                    peer_connection_pool=self._connection_pool,
                ),
            ) for node in self._mesh_topology.nodes.values()
        ]

    def set_mesh_topology(self, mesh_topo: MeshTopologySpec) -> None:
        self._mesh_topology = mesh_topo


class ServerProvider:
    @abstractmethod
    async def start_server(
            self,
            client_connected_cb,
    ) -> tuple[Server, ConnectionSpec]:
        ...


class EphemeralPortTcpServerProvider(ServerProvider):
    """Starts a TCP server on the first available ephemeral port."""

    def __init__(self, host: str = 'localhost'):
        self.host = host

    async def start_server(
            self,
            client_connected_cb,
    ) -> tuple[Server, ConnectionSpec]:
        last_error = None

        for port in ephemeral_port_range():
            try:
                server = await asyncio.start_server(
                    client_connected_cb,
                    host=self.host,
                    port=port,
                )
            except OSError as last_error:
                pass
            else:
                conn_spec = IpConnectionSpec(self.host, port)
                return server, conn_spec

        raise OSError(
            f'Unable to start a server on any ephemeral ports. Last error: {last_error}'
        )


class TmpUnixServerProvider(ServerProvider):
    """Starts a Unix server on a tmp file."""

    def __init__(
            self,
            prefix: Optional[str] = 'mesh-node-server.',
            suffix: Optional[str] = '.sock',
            dir=None,
    ):
        self.prefix = prefix
        self.suffix = suffix
        self.dir = dir

    async def start_server(
            self,
            client_connected_cb,
    ) -> tuple[Server, ConnectionSpec]:
        with tempfile.NamedTemporaryFile(
                prefix=self.prefix,
                suffix=self.suffix,
                dir=self.dir,
        ) as file:
            path = file.name

        server = await asyncio.start_unix_server(client_connected_cb, path=path)
        conn_spec = UnixConnectionSpec(path=path)

        return server, conn_spec


ListenerCallback = Callable[[Message], Awaitable[None]]


class MeshNode:
    def __init__(
            self,
            name: str,
            mesh_coordinator_client: MeshCoordinatorClient,
            server_provider: ServerProvider,
            peer_manager: PeerManager,
    ):
        self.name = name
        self.mesh_coordinator_client = mesh_coordinator_client
        self.server_provider = server_provider
        self.peer_manager = peer_manager

        self._connection_spec = None

        self._listeners: dict[Topic, set[ListenerCallback]] = defaultdict(set)

        mesh_coordinator_client.mesh_topology_broadcast_handler = self._handle_topology_broadcast

    async def start(self) -> None:
        print('Starting node server...')
        server, self._connection_spec = await self.server_provider.start_server(
            self._handle_connection
        )
        print(f'Started node server with connection_spec={self._connection_spec}')

        await self._register_node()

    async def _register_node(self) -> None:
        node_spec = MeshNodeSpec(
            name=self.name,
            connection=self._connection_spec,
            listening_to_topics=set(self._listeners.keys()),
        )

        print(f'node_spec={node_spec}')
        print('Registering node with server...')
        await self.mesh_coordinator_client.register_node(node_spec)

    async def _handle_connection(self, reader: StreamReader, writer: StreamWriter) -> None:
        print('New connection')
        obj_io = MessageStreamIO(reader, writer)

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
                    f'to {peer.name}: {result}'
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
        self.peer_manager.set_mesh_topology(topology)


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


class TestClient:
    def __init__(
            self,
            reader: StreamReader,
            writer: StreamWriter,
            auth_key: bytes = b'hellothere',
    ):
        self.reader = reader
        self.writer = writer
        self.auth_key = auth_key

        self.obj_io = AnyObjectStreamIO(reader, writer)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.writer.close()
        await self.writer.wait_closed()

    async def run(self) -> None:
        print('Authenticating...')
        await self.authenticate()
        print('Done!')

        await asyncio.gather(
            self._send_heartbeat(),
            self._receive_objects(),
        )

    async def authenticate(self) -> None:
        await self.obj_io.write_object(self.auth_key)

        response = await self.obj_io.read_object()

        if response != AUTHENTICATED_RESPONSE:
            raise response

    async def _send_heartbeat(self) -> None:
        while True:
            await self.obj_io.write_object(b'heartbeat')
            await asyncio.sleep(1.)

    async def _receive_objects(self) -> None:
        while True:
            print('Received from server:', await self.obj_io.read_object())


async def test_client():
    # reader, writer = await open_connection(host='localhost', port=8888)
    reader, writer = await open_unix_connection('./mesh.sock')
    # print(f'Connected to {reader.getpeername()}')

    async with TestClient(reader, writer) as client:
        await client.run()


class SpeedTester:
    def __init__(self, node: MeshNode):
        self.node = node

    async def measure_mps(
            self,
            topic: Topic,
            body: Body = None,
            duration: float = 10.,
            warmup: Optional[float] = 1.,
    ) -> float:
        """Measure messages per second."""

        if warmup is not None and warmup > 0.:
            await self.measure_mps(topic, body=body, duration=warmup, warmup=None)

        topic_sender = self.node.get_topic_sender(topic)

        if not await topic_sender.has_listeners():
            raise ValueError(f'No listeners for topic={topic}')

        message_count = 0
        start_time = time.monotonic()

        while (end_time := time.monotonic()) - start_time < duration:
            await topic_sender.send(body)
            await noop()  # Yield to other tasks since this runs as fast as possible and can block other tasks
            message_count += 1

        true_duration = end_time - start_time

        return message_count / true_duration


async def test_mesh_node() -> None:
    print('Connecting to mesh coordinator...')
    reader, writer = await open_unix_connection('./mesh.sock')
    obj_io = AnyObjectStreamIO(reader, writer)
    rpc = ObjectStreamRPC(obj_io)
    mesh_coordinator_client = RPCMeshCoordinatorClient(rpc)
    await rpc.start()

    # server_provider = EphemeralPortTcpServerProvider(host='austin-laptop')
    server_provider = TmpUnixServerProvider()

    peer_manager = PeerManager()

    node = MeshNode(
        f'test-{os.getpid()}',
        mesh_coordinator_client,
        server_provider,
        peer_manager,
    )

    await node.start()

    speed_tester = SpeedTester(node)

    role = sys.argv[1]
    assert role in {'send', 'recv', 'speed-test'}

    if role == 'send':
        async def expensive_task():
            await asyncio.sleep(1.)
            return 'expensive task ran'

        test_topic = node.get_topic_sender('test')
        while True:
            result = await test_topic.send_result(
                expensive_task,
            )
            print(result)
            await asyncio.sleep(0.5)
    elif role == 'speed-test':
        topic = 'test'
        body = None
        # body = b'helloworld' * 100000

        while not await node.topic_has_listeners(topic):
            print('Waiting for listeners...')
            await asyncio.sleep(0.1)

        print('Running speed test...')
        mps = await speed_tester.measure_mps(topic, body=body)
        print(f'mps={mps}')
    elif role == 'recv':
        reqs = 0
        last_reqs = -1
        t00 = None

        async def handle_test(message: Message) -> None:
            nonlocal reqs, t00
            if t00 is None:
                t00 = time.monotonic()
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


async def main():
    # await test_client()
    await test_mesh_node()


if __name__ == '__main__':
    asyncio.run(main())
