import logging
from abc import ABC, abstractmethod
from typing import Awaitable, Callable

from rosy.specs import MeshNodeSpec, MeshTopologySpec
from rosy.utils import ALLOWED_EXCEPTIONS

TopologyChangedCallback = Callable[[MeshTopologySpec], Awaitable[None]]

logger = logging.getLogger(__name__)


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

    async def _call_topology_changed_callback(self) -> None:
        if self.topology_changed_callback is None:
            return

        try:
            await self.topology_changed_callback(self.topology)
        except ALLOWED_EXCEPTIONS:
            raise
        except Exception as e:
            logger.exception(
                "Error calling topology changed callback",
                exc_info=e,
            )
