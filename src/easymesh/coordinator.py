import asyncio
from abc import abstractmethod
from asyncio import StreamReader, open_connection
from codecs import StreamWriter
from collections.abc import Awaitable, Callable
from typing import Optional

from easymesh.asyncio import forever
from easymesh.objectstreamio import CodecObjectStreamIO
from easymesh.reqres import MeshTopologyBroadcast, RegisterNodeRequest, RegisterNodeResponse
from easymesh.rpc import ObjectStreamRPC, RPC
from easymesh.specs import MeshNodeSpec, MeshTopologySpec, NodeName

DEFAULT_COORDINATOR_PORT: int = 6374
"""Default coordinator port is 6374, which spells "MESH" on a telephone keypad :)"""


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

        self.node_clients: dict[RPC, Optional[NodeName]] = {}
        self.mesh_topology = MeshTopologySpec(nodes={})

    async def start(self) -> None:
        server = await self.start_stream_server(self._handle_connection)

    async def _handle_connection(self, reader: StreamReader, writer: StreamWriter) -> None:
        peer_name = writer.get_extra_info('peername')
        sock_name = writer.get_extra_info('sockname')
        print(f'New connection from: {peer_name or sock_name}')

        rpc = self.build_rpc(reader, writer)
        rpc.request_handler = lambda r: self._handle_request(r, rpc)
        self.node_clients[rpc] = None

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
            handler = self._handle_register_node
        else:
            raise Exception(f'Received invalid request object of type={type(request)}')

        return await handler(request, rpc)

    async def _handle_register_node(
            self,
            request: RegisterNodeRequest,
            rpc: RPC,
    ) -> RegisterNodeResponse:
        print(f'Got register node request: {request}')

        node_spec = request.node_spec
        self.node_clients[rpc] = node_spec.name
        self.mesh_topology.put_node(node_spec)

        # noinspection PyAsyncCall
        asyncio.create_task(self._broadcast_topology())

        return RegisterNodeResponse()

    async def _remove_node(self, rpc: RPC) -> None:
        node_name = self.node_clients.pop(rpc)
        self.mesh_topology.nodes.pop(node_name, None)

        # noinspection PyAsyncCall
        asyncio.create_task(self._broadcast_topology())

    async def _broadcast_topology(self) -> None:
        print(f'Broadcasting topology to {len(self.node_clients)} nodes...')
        print(f'mesh_topology={self.mesh_topology}')

        message = MeshTopologyBroadcast(self.mesh_topology)

        await asyncio.gather(*(
            node_client.send_message(message)
            for node_client in self.node_clients.keys()
        ))


MeshTopologyBroadcastHandler = Callable[[MeshTopologyBroadcast], Awaitable[None]]


class MeshCoordinatorClient:
    mesh_topology_broadcast_handler: MeshTopologyBroadcastHandler

    @abstractmethod
    async def send_heartbeat(self) -> None:
        ...

    @abstractmethod
    async def register_node(self, node_spec: MeshNodeSpec) -> None:
        ...


class RPCMeshCoordinatorClient(MeshCoordinatorClient):
    def __init__(self, rpc: RPC):
        self.rpc = rpc

        rpc.message_handler = self._handle_rpc_message

    async def send_heartbeat(self) -> None:
        response = await self.rpc.send_request(b'ping')
        if response != b'pong':
            raise Exception(f'Got unexpected response={response} from heartbeat.')

    async def register_node(self, node_spec: MeshNodeSpec) -> None:
        request = RegisterNodeRequest(node_spec)

        response = await self.rpc.send_request(request)

        if not isinstance(response, RegisterNodeResponse):
            raise Exception(f'Failed to register node; got response={response}')

    async def _handle_rpc_message(self, data) -> None:
        if isinstance(data, MeshTopologyBroadcast):
            await self.mesh_topology_broadcast_handler(data)
        else:
            print(f'Received unknown message={data}')


async def build_coordinator_client(
        host: str = 'localhost',
        port: int = DEFAULT_COORDINATOR_PORT,
) -> MeshCoordinatorClient:
    reader, writer = await open_connection(host, port)
    obj_io = CodecObjectStreamIO(reader, writer)
    rpc = ObjectStreamRPC(obj_io)
    client = RPCMeshCoordinatorClient(rpc)
    await rpc.start()

    return client


async def main() -> None:
    def build_rpc(reader, writer):
        return ObjectStreamRPC(CodecObjectStreamIO(reader, writer))

    server = RPCMeshCoordinatorServer(
        # start_stream_server=lambda cb: asyncio.start_unix_server(cb, path='./mesh.sock'),
        start_stream_server=lambda cb: asyncio.start_server(cb, host='', port=DEFAULT_COORDINATOR_PORT),
        build_rpc=build_rpc,
    )

    print('Starting server...')
    await server.start()
    print('Server started.')

    await forever()


if __name__ == '__main__':
    asyncio.run(main())
