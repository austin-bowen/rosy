import asyncio
import gzip
import hashlib
import logging
import pickle
import socket
from abc import ABC, abstractmethod
from random import Random
from typing import cast

from zeroconf import ServiceBrowser, ServiceInfo, ServiceStateChange, Zeroconf

from rosy.asyncio import cancel_task
from rosy.discovery.base import NodeDiscovery, TopologyChangedCallback
from rosy.specs import MeshNodeSpec, MeshTopologySpec
from rosy.types import DomainId

DEFAULT_TTL: int = 30

logger = logging.getLogger(__name__)


class ZeroconfNodeDiscovery(NodeDiscovery):
    def __init__(
        self,
        domain_id: DomainId,
        topology_changed_callback: TopologyChangedCallback = None,
        zc: Zeroconf = None,
        node_spec_codec: "NodeSpecCodec" = None,
        ttl: int = DEFAULT_TTL,
        rng: Random = None,
    ) -> None:
        self._service_type = build_service_type(domain_id)
        self.topology_changed_callback = topology_changed_callback
        self._zc = zc or Zeroconf()
        self._node_spec_codec = node_spec_codec or GzipPickleNodeSpecCodec()
        self._ttl = ttl
        self._rng = rng or Random()

        self._service_name_to_node: dict[str, MeshNodeSpec] = {}
        self._topology_changed_caller_task: asyncio.Task | None = None
        self._browser: ServiceBrowser | None = None
        self._node_monitors: dict[str, asyncio.Task] = {}
        self._topology_changed = asyncio.Event()
        self._service_info_lock = asyncio.Lock()

    @property
    def topology(self) -> MeshTopologySpec:
        nodes = list(self._service_name_to_node.values())
        return MeshTopologySpec(nodes)

    async def start(self) -> None:
        self._topology_changed_caller_task = asyncio.create_task(
            self._monitor_for_topology_changes()
        )

        self._browser = ServiceBrowser(
            self._zc,
            self._service_type,
            handlers=[self._on_service_state_change],
        )

    async def stop(self, timeout: float | None = 10) -> None:
        exceptions = []

        try:
            await cancel_task(self._topology_changed_caller_task, timeout=timeout)
        except Exception as e:
            exceptions.append(e)

        try:
            await asyncio.wait_for(asyncio.to_thread(self._browser.cancel), timeout)
        except Exception as e:
            exceptions.append(e)

        tasks = list(self._node_monitors.values())
        for task in tasks:
            try:
                await cancel_task(task, timeout=timeout)
            except Exception as e:
                exceptions.append(e)

        try:
            await asyncio.wait_for(asyncio.to_thread(self._zc.close), timeout)
        except Exception as e:
            exceptions.append(e)

        if exceptions:
            # TODO Replace with ExceptionGroup when we drop Python 3.10
            raise Exception(
                "Exceptions occurred while stopping ZeroconfNodeDiscovery",
                exceptions,
            )

    async def register_node(self, node: MeshNodeSpec) -> None:
        logger.debug(f"Registering node: {node}")
        info = self._build_service_info(node)
        await (await self._zc.async_register_service(info))

    async def update_node(self, node: MeshNodeSpec) -> None:
        logger.debug(f"Updating node: {node}")
        info = self._build_service_info(node)
        await (await self._zc.async_update_service(info))

    def _build_service_info(self, node: MeshNodeSpec) -> ServiceInfo:
        return ServiceInfo(
            type_=self._service_type,
            name=f"{node.id.uuid}.{self._service_type}",
            port=0,
            properties=self._node_spec_codec.encode(node),
            server=get_mdns_fqdn(),
            host_ttl=self._ttl,
            other_ttl=self._ttl,
        )

    async def _monitor_for_topology_changes(self) -> None:
        while True:
            await self._topology_changed.wait()
            self._topology_changed.clear()
            await self._call_topology_changed_callback()

    def _on_service_state_change(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        """Called by the ServiceBrowser thread."""

        logger.debug(f"Service state change: {state_change.name} {name!r}")

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
            await self._start_monitoring_node(name)
        elif state_change == ServiceStateChange.Removed:
            await self._remove_node(name)

    async def _start_monitoring_node(self, name: str) -> None:
        """
        Why do we need to monitor the node? Why not just rely on the service
        state change events?

        Under normal circumstances, when a node exits, it will broadcast a
        notification, in which case a service state change event will be
        triggered immediately, and all is well.

        However, if a node dies unexpectedly and does not perform this cleanup
        step, or if there is a network failure between the nodes, `zeroconf`
        will not "pick this up" for a long time, like up to 18 minutes.
        Unfortunately, this is by design, and cannot be changed.

        To work around this, we periodically retrieve the node's service info,
        shortly after its TTL period. If the node is still alive, it should've
        already re-broadcast itself; otherwise, the TTL will have expired, and
        when we try to retrieve the service info again, it will be `None`,
        thus indicating that the node has left the mesh.
        """

        await self._stop_monitoring_node(name)
        self._node_monitors[name] = asyncio.create_task(self._monitor_node(name))

    async def _stop_monitoring_node(self, name: str) -> None:
        if name in self._node_monitors:
            await cancel_task(self._node_monitors[name])
            self._node_monitors.pop(name)

    async def _monitor_node(self, name: str) -> None:
        while await self._check_node(name):
            sleep_time = self._ttl + 1 + self._rng.random()
            await asyncio.sleep(sleep_time)

    async def _check_node(self, name: str) -> bool:
        self._check_this_task_is_current_monitor(name)

        logger.debug(f"Getting service info for: {name!r}")
        info = await asyncio.shield(self._get_service_info(name))

        if info is None:
            logger.error(f"Failed to get service info for: {name!r}")
            asyncio.create_task(self._remove_node(name))
            return False

        text = cast(bytes, info.text)
        node = self._node_spec_codec.decode(text)

        existing_node = self._service_name_to_node.get(name)
        if node != existing_node:
            if existing_node is None:
                logger.debug(f"Discovered node on mesh: {node}")
            else:
                logger.debug(f"Node updated: {node}")

            self._service_name_to_node[name] = node
            self._topology_changed.set()

        return True

    def _check_this_task_is_current_monitor(self, name: str) -> None:
        this_task = asyncio.current_task()
        monitor_task = self._node_monitors[name]
        if this_task is not monitor_task:
            raise RuntimeError(
                f"This task is not the current node monitor task. "
                f"this_task={this_task}; monitor_task={monitor_task}"
            )

    async def _get_service_info(self, name: str) -> ServiceInfo | None:
        async with self._service_info_lock:
            return await self._zc.async_get_service_info(self._service_type, name)

    async def _remove_node(self, name: str) -> None:
        await self._stop_monitoring_node(name)

        node = self._service_name_to_node.pop(name, None)
        if node is not None:
            logger.debug(f"Node left mesh: {node.id}")
            self._topology_changed.set()


def build_service_type(domain_id: DomainId) -> str:
    domain_id = hash_domain_id(domain_id)
    return f"_rosy-{domain_id}._tcp.local."


def hash_domain_id(domain_id: str, digest_size: int = 5) -> str:
    domain_id = domain_id.encode()
    domain_id = hashlib.blake2b(
        domain_id,
        digest_size=digest_size,
        usedforsecurity=False,
    )
    return domain_id.hexdigest()


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
