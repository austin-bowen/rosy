import asyncio
from abc import abstractmethod
from asyncio import StreamReader
from codecs import StreamWriter
from typing import Optional

from easymesh.coordinator.constants import DEFAULT_COORDINATOR_HOST, DEFAULT_COORDINATOR_PORT
from easymesh.objectstreamio import CodecObjectStreamIO
from easymesh.reqres import MeshTopologyBroadcast, RegisterNodeRequest, RegisterNodeResponse
from easymesh.rpc import ObjectStreamRPC, RPC
from easymesh.specs import MeshNodeSpec, MeshTopologySpec, NodeId
from easymesh.types import Port, ServerHost


class MeshCoordinatorServer:
    @abstractmethod
    async def start(self) -> None:
        ...


class RPCMeshCoordinatorServer(MeshCoordinatorServer):
    def __init__(
            self,
            start_stream_server,
            build_rpc,
    ):
        self.start_stream_server = start_stream_server
        self.build_rpc = build_rpc

        self._node_clients: dict[RPC, Optional[NodeId]] = {}
        self._nodes: dict[NodeId, MeshNodeSpec] = {}

    async def start(self) -> None:
        server = await self.start_stream_server(self._handle_connection)

    async def _handle_connection(self, reader: StreamReader, writer: StreamWriter) -> None:
        peer_name = writer.get_extra_info('peername')
        sock_name = writer.get_extra_info('sockname')
        print(f'New connection from: {peer_name or sock_name}')

        rpc = self.build_rpc(reader, writer)
        rpc.request_handler = lambda r: self._handle_request(r, rpc)
        self._node_clients[rpc] = None

        try:
            await rpc.run_forever()
        except EOFError:
            print('Client disconnected')
        finally:
            await self._remove_node(rpc)

            writer.close()
            await writer.wait_closed()

    async def _handle_request(self, request, rpc: RPC):
        if request == b'ping':
            print('Received heartbeat')
            return b'pong'
        elif isinstance(request, RegisterNodeRequest):
            return await self._handle_register_node(request, rpc)
        else:
            raise Exception(f'Received invalid request object of type={type(request)}')

    async def _handle_register_node(
            self,
            request: RegisterNodeRequest,
            rpc: RPC,
    ) -> RegisterNodeResponse:
        print(f'Got register node request: {request}')

        node_spec = request.node_spec
        self._node_clients[rpc] = node_spec.id
        self._nodes[node_spec.id] = node_spec

        # noinspection PyAsyncCall
        asyncio.create_task(self._broadcast_topology())

        return RegisterNodeResponse()

    async def _remove_node(self, rpc: RPC) -> None:
        node_id = self._node_clients.pop(rpc)
        self._nodes.pop(node_id, None)

        # noinspection PyAsyncCall
        asyncio.create_task(self._broadcast_topology())

    async def _broadcast_topology(self) -> None:
        print(f'\nBroadcasting topology to {len(self._nodes)} nodes...')

        nodes = sorted(self._nodes.values(), key=lambda n: n.id)
        print('Mesh nodes:')
        for node in nodes:
            print(f'- {node.id}: {node}')

        mesh_topology = MeshTopologySpec(nodes=nodes)
        message = MeshTopologyBroadcast(mesh_topology)

        await asyncio.gather(*(
            node_client.send_message(message)
            for node_client in self._node_clients.keys()
        ))


def build_mesh_coordinator_server(
        host: ServerHost = DEFAULT_COORDINATOR_HOST,
        port: Port = DEFAULT_COORDINATOR_PORT,
) -> MeshCoordinatorServer:
    async def start_stream_server(cb):
        return await asyncio.start_server(cb, host=host, port=port)

    def build_rpc(reader, writer):
        return ObjectStreamRPC(CodecObjectStreamIO(reader, writer))

    return RPCMeshCoordinatorServer(start_stream_server, build_rpc)
