import asyncio
import logging
from abc import ABC, abstractmethod
from asyncio import StreamReader
from codecs import StreamWriter

from rosy.asyncio import close_ignoring_errors, many
from rosy.authentication import AuthKey, Authenticator, optional_authkey_authenticator
from rosy.coordinator.constants import DEFAULT_COORDINATOR_HOST, DEFAULT_COORDINATOR_PORT
from rosy.objectio import CodecObjectReader, CodecObjectWriter, ObjectIO
from rosy.reqres import MeshTopologyBroadcast, RegisterNodeRequest, RegisterNodeResponse
from rosy.rpc import ObjectIORPC, RPC
from rosy.specs import MeshNodeSpec, MeshTopologySpec, NodeId
from rosy.types import Port, ServerHost

logger = logging.getLogger(__name__)


class MeshCoordinatorServer(ABC):
    @abstractmethod
    async def start(self) -> None:
        ...


class RPCMeshCoordinatorServer(MeshCoordinatorServer):
    def __init__(
            self,
            start_stream_server,
            build_rpc,
            authenticator: Authenticator,
    ):
        self.start_stream_server = start_stream_server
        self.build_rpc = build_rpc
        self.authenticator = authenticator

        self._node_clients: dict[RPC, NodeId | None] = {}
        self._nodes: dict[NodeId, MeshNodeSpec] = {}

    async def start(self) -> None:
        server = await self.start_stream_server(self._handle_connection)

    async def _handle_connection(self, reader: StreamReader, writer: StreamWriter) -> None:
        peer_name = writer.get_extra_info('peername') or writer.get_extra_info('sockname')
        logger.debug(f'New connection from: {peer_name}')

        await self.authenticator.authenticate(reader, writer)

        rpc = self.build_rpc(reader, writer)
        rpc.request_handler = lambda r: self._handle_request(r, rpc, peer_name)
        self._node_clients[rpc] = None

        try:
            await rpc.run_forever()
        except (ConnectionResetError, EOFError):
            logger.debug(f'Client disconnected: {peer_name}')
        finally:
            try:
                await self._remove_node(rpc)
            finally:
                await close_ignoring_errors(writer)

    async def _handle_request(self, request, rpc: RPC, peer_name: str):
        if request == b'get_topology':
            return self._get_mesh_topology()
        elif request == b'ping':
            logger.debug(f'Received heartbeat from: {peer_name}')
            return b'pong'
        elif isinstance(request, RegisterNodeRequest):
            return await self._handle_register_node(request, rpc)
        else:
            raise Exception(f'Received invalid request object of type={type(request)}')

    def _get_mesh_topology(self) -> MeshTopologySpec:
        nodes = sorted(self._nodes.values(), key=lambda n: n.id)
        return MeshTopologySpec(nodes=nodes)

    async def _handle_register_node(
            self,
            request: RegisterNodeRequest,
            rpc: RPC,
    ) -> RegisterNodeResponse:
        logger.debug(f'Got register node request: {request}')

        node_spec = request.node_spec
        node_is_new = node_spec.id not in self._nodes
        self._node_clients[rpc] = node_spec.id
        self._nodes[node_spec.id] = node_spec

        if node_is_new:
            logger.info(f'Node registered: {node_spec.id}')
            logger.info(f'Total nodes: {len(self._nodes)}')
        else:
            logger.debug(f'Node re-registered: {node_spec.id}')

        await self._broadcast_topology()

        return RegisterNodeResponse()

    async def _remove_node(self, rpc: RPC) -> None:
        node_id = self._node_clients.pop(rpc)
        if node_id is None:
            return

        self._nodes.pop(node_id, None)
        logger.info(f'Node removed: {node_id}')
        logger.info(f'Total nodes: {len(self._nodes)}')

        await self._broadcast_topology()

    async def _broadcast_topology(self) -> None:
        logger.debug(f'Broadcasting topology to {len(self._nodes)} nodes...')
        if not self._nodes:
            return

        mesh_topology = self._get_mesh_topology()
        for node in mesh_topology.nodes:
            logger.debug(f'- {node.id}: {node}')

        message = MeshTopologyBroadcast(mesh_topology)

        await many(
            node_client.send_message(message)
            for node_client in self._node_clients.keys()
        )


def build_mesh_coordinator_server(
        host: ServerHost = DEFAULT_COORDINATOR_HOST,
        port: Port = DEFAULT_COORDINATOR_PORT,
        authkey: AuthKey = None,
        authenticator: Authenticator = None,
) -> MeshCoordinatorServer:
    async def start_stream_server(cb):
        return await asyncio.start_server(cb, host=host, port=port)

    def build_rpc(reader, writer):
        return ObjectIORPC(ObjectIO(
            reader=CodecObjectReader(reader),
            writer=CodecObjectWriter(writer),
        ))

    authenticator = authenticator or optional_authkey_authenticator(authkey)

    return RPCMeshCoordinatorServer(
        start_stream_server,
        build_rpc,
        authenticator,
    )
