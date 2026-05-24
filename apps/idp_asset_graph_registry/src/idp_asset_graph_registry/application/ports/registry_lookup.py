from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from idp_asset_graph_registry.domain.value_objects import ReferenceStatus


@dataclass(frozen=True)
class RegistryReference:
    reference_type: str
    status: ReferenceStatus
    display_name: str | None = None
    snapshot_json: dict[str, Any] = field(default_factory=dict)


class RegistryReferenceLookup(Protocol):
    async def tenant(self, tenant_code: str) -> RegistryReference: ...

    async def asset(
        self,
        tenant_code: str,
        asset_code: str,
    ) -> RegistryReference: ...

    async def agent(
        self,
        tenant_code: str,
        asset_code: str,
        agent_code: str,
    ) -> RegistryReference: ...

    async def source(
        self,
        tenant_code: str,
        asset_code: str,
        agent_code: str,
        source_code: str,
    ) -> RegistryReference: ...

    async def point(
        self,
        tenant_code: str,
        point_code: str,
    ) -> RegistryReference: ...

