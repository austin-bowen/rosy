from abc import abstractmethod
from asyncio import open_connection
from collections.abc import Awaitable, Callable

from easymesh.coordinator.constants import DEFAULT_COORDINATOR_PORT
from easymesh.objectio import CodecObjectReader, CodecObjectWriter, ObjectIO
from easymesh.reqres import MeshTopologyBroadcast, RegisterNodeRequest, RegisterNodeResponse
from easymesh.rpc import ObjectIORPC, RPC
from easymesh.specs import MeshNodeSpec
from easymesh.types import Host, Port

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
        host: Host = 'localhost',
        port: Port = DEFAULT_COORDINATOR_PORT,
) -> MeshCoordinatorClient:
    reader, writer = await open_connection(host, port)
    rpc = ObjectIORPC(ObjectIO(
        reader=CodecObjectReader(reader),
        writer=CodecObjectWriter(writer),
    ))
    client = RPCMeshCoordinatorClient(rpc)
    await rpc.start()

    return client
