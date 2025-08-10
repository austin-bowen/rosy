from abc import ABC, abstractmethod
from typing import Awaitable, Callable

from rosy.specs import MeshNodeSpec, MeshTopologySpec

TopologyChangedCallback = Callable[[MeshTopologySpec], Awaitable[None]]


class NodeDiscovery(ABC):
    topology_changed_callback: TopologyChangedCallback | None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.stop()

    @property
    @abstractmethod
    def topology(self) -> MeshTopologySpec: ...

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def register_node(self, node: MeshNodeSpec) -> None: ...

    @abstractmethod
    async def update_node(self, node: MeshNodeSpec) -> None: ...

    @abstractmethod
    async def unregister_node(self, node: MeshNodeSpec) -> None: ...

    async def _call_topology_changed_callback(self) -> None:
        if self.topology_changed_callback is not None:
            await self.topology_changed_callback(self.topology)
