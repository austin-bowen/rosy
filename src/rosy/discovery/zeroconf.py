import asyncio
import gzip
import logging
import pickle
import socket
from abc import ABC, abstractmethod

from zeroconf import ServiceBrowser, ServiceInfo, ServiceStateChange, Zeroconf

from rosy.discovery.base import NodeDiscovery, TopologyChangedCallback
from rosy.specs import MeshNodeSpec, MeshTopologySpec

DEFAULT_SERVICE_TYPE = "_rosy._tcp.local."

logger = logging.getLogger(__name__)


class ZeroconfNodeDiscovery(NodeDiscovery):
    topology_changed_callback: TopologyChangedCallback | None

    def __init__(
        self,
        topology_changed_callback: TopologyChangedCallback = None,
        service_type: str = DEFAULT_SERVICE_TYPE,
        zc: Zeroconf = None,
        node_spec_codec: "NodeSpecCodec" = None,
    ) -> None:
        self.topology_changed_callback = topology_changed_callback
        self._service_type = service_type
        self._zc = zc or Zeroconf()
        self._node_spec_codec = node_spec_codec or GzipPickleNodeSpecCodec()

        self._service_name_to_node: dict[str, MeshNodeSpec] = {}

        self._browser: ServiceBrowser | None = None

    @property
    def topology(self) -> MeshTopologySpec:
        return MeshTopologySpec(nodes=self._service_name_to_node.values())

    async def start(self) -> None:
        self._browser = ServiceBrowser(
            self._zc,
            self._service_type,
            handlers=[self._on_service_state_change],
        )

    async def stop(self) -> None:
        try:
            await asyncio.to_thread(self._browser.cancel)
        finally:
            await asyncio.to_thread(self._zc.close)

    async def register_node(self, node: MeshNodeSpec) -> None:
        info = self._get_service_info(node)
        await (await self._zc.async_register_service(info))

    async def update_node(self, node: MeshNodeSpec) -> None:
        info = self._get_service_info(node)
        await (await self._zc.async_update_service(info))

    async def unregister_node(self, node: MeshNodeSpec) -> None:
        info = self._get_service_info(node)
        await (await self._zc.async_unregister_service(info))

    def _get_service_info(self, node: MeshNodeSpec) -> ServiceInfo:
        return ServiceInfo(
            type_=self._service_type,
            name=f"{node.id.uuid}.{self._service_type}",
            port=0,
            properties=self._node_spec_codec.encode(node),
            server=get_mdns_fqdn(),
        )

    def _on_service_state_change(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        """Called by the ServiceBrowser thread."""

        future = asyncio.run_coroutine_threadsafe(
            self._async_on_service_state_change(name, state_change),
            self._zc.loop,
        )
        future.result()

    async def _async_on_service_state_change(
        self,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        if state_change in (ServiceStateChange.Added, ServiceStateChange.Updated):
            await self._add_node(name)
        elif state_change == ServiceStateChange.Removed:
            await self._remove_node(name)

    async def _add_node(self, name: str) -> None:
        info = await self._zc.async_get_service_info(self._service_type, name)
        if info is None:
            logger.error(f"Failed to get service info for: {name!r}")
            await self._remove_node(name)
            return

        self._service_name_to_node[name] = self._node_spec_codec.decode(info.text)
        await self._call_topology_changed_callback()

    async def _remove_node(self, name: str) -> None:
        node = self._service_name_to_node.pop(name, None)
        if node is not None:
            await self._call_topology_changed_callback()


def get_mdns_fqdn() -> str:
    fqdn = socket.getfqdn()

    if fqdn.endswith(".local."):
        return fqdn
    elif fqdn.endswith(".local"):
        return fqdn + "."
    elif fqdn.endswith("."):
        return fqdn + "local."
    else:
        return fqdn + ".local."


class NodeSpecCodec(ABC):
    @abstractmethod
    def encode(self, node: MeshNodeSpec) -> bytes: ...

    @abstractmethod
    def decode(self, data: bytes) -> MeshNodeSpec: ...


class GzipPickleNodeSpecCodec(NodeSpecCodec):
    """
    Not a lot of space in the UDP payload, so compress as much as possible.
    """

    def __init__(
        self,
        protocol: int = pickle.HIGHEST_PROTOCOL,
        compresslevel: int = 9,
    ) -> None:
        self.protocol = protocol
        self.compresslevel = compresslevel

    def encode(self, node: MeshNodeSpec) -> bytes:
        data = pickle.dumps(node, protocol=self.protocol)
        return gzip.compress(data, compresslevel=self.compresslevel)

    def decode(self, data: bytes) -> MeshNodeSpec:
        data = gzip.decompress(data)
        return pickle.loads(data)
