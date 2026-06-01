from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from idp_asset_graph_registry.application.errors import (
    RegistryLookupUnavailableError,
)
from idp_asset_graph_registry.application.ports.registry_lookup import (
    RegistryReference,
)
from idp_asset_graph_registry.domain.value_objects import ReferenceStatus


@dataclass(frozen=True)
class PermissiveRegistryReferenceLookup:
    async def tenant(self, tenant_code: str) -> RegistryReference:
        return _valid("tenant", {"tenant_code": tenant_code})

    async def asset(self, tenant_code: str, asset_code: str) -> RegistryReference:
        return _valid("asset", {"tenant_code": tenant_code, "asset_code": asset_code})

    async def agent(
        self,
        tenant_code: str,
        asset_code: str,
        agent_code: str,
    ) -> RegistryReference:
        return _valid(
            "agent",
            {
                "tenant_code": tenant_code,
                "asset_code": asset_code,
                "agent_code": agent_code,
            },
        )

    async def source(
        self,
        tenant_code: str,
        asset_code: str,
        agent_code: str,
        source_code: str,
    ) -> RegistryReference:
        return _valid(
            "source",
            {
                "tenant_code": tenant_code,
                "asset_code": asset_code,
                "agent_code": agent_code,
                "source_code": source_code,
            },
        )

    async def point(self, tenant_code: str, point_code: str) -> RegistryReference:
        return _valid("point", {"tenant_code": tenant_code, "point_code": point_code})


@dataclass
class InMemoryRegistryReferenceLookup:
    tenants: set[str] = field(default_factory=set)
    assets: set[tuple[str, str]] = field(default_factory=set)
    agents: set[tuple[str, str, str]] = field(default_factory=set)
    sources: set[tuple[str, str, str, str]] = field(default_factory=set)
    points: set[tuple[str, str]] = field(default_factory=set)

    async def tenant(self, tenant_code: str) -> RegistryReference:
        return _status("tenant", tenant_code in self.tenants, {"tenant_code": tenant_code})

    async def asset(self, tenant_code: str, asset_code: str) -> RegistryReference:
        return _status(
            "asset",
            (tenant_code, asset_code) in self.assets,
            {"tenant_code": tenant_code, "asset_code": asset_code},
        )

    async def agent(
        self,
        tenant_code: str,
        asset_code: str,
        agent_code: str,
    ) -> RegistryReference:
        return _status(
            "agent",
            (tenant_code, asset_code, agent_code) in self.agents,
            {
                "tenant_code": tenant_code,
                "asset_code": asset_code,
                "agent_code": agent_code,
            },
        )

    async def source(
        self,
        tenant_code: str,
        asset_code: str,
        agent_code: str,
        source_code: str,
    ) -> RegistryReference:
        return _status(
            "source",
            (tenant_code, asset_code, agent_code, source_code) in self.sources,
            {
                "tenant_code": tenant_code,
                "asset_code": asset_code,
                "agent_code": agent_code,
                "source_code": source_code,
            },
        )

    async def point(self, tenant_code: str, point_code: str) -> RegistryReference:
        return _status(
            "point",
            (tenant_code, point_code) in self.points,
            {"tenant_code": tenant_code, "point_code": point_code},
        )


@dataclass(frozen=True)
class ConfigRegistryHttpReferenceLookup:
    base_url: str
    timeout_seconds: float = 5.0

    async def tenant(self, tenant_code: str) -> RegistryReference:
        return await self._get(
            {"reference_type": "tenant", "tenant_code": tenant_code}
        )

    async def asset(self, tenant_code: str, asset_code: str) -> RegistryReference:
        return await self._get(
            {
                "reference_type": "asset",
                "tenant_code": tenant_code,
                "asset_code": asset_code,
            }
        )

    async def agent(
        self,
        tenant_code: str,
        asset_code: str,
        agent_code: str,
    ) -> RegistryReference:
        return await self._get(
            {
                "reference_type": "agent",
                "tenant_code": tenant_code,
                "asset_code": asset_code,
                "agent_code": agent_code,
            }
        )

    async def source(
        self,
        tenant_code: str,
        asset_code: str,
        agent_code: str,
        source_code: str,
    ) -> RegistryReference:
        return await self._get(
            {
                "reference_type": "source",
                "tenant_code": tenant_code,
                "asset_code": asset_code,
                "agent_code": agent_code,
                "source_code": source_code,
            }
        )

    async def point(self, tenant_code: str, point_code: str) -> RegistryReference:
        return await self._get(
            {
                "reference_type": "point",
                "tenant_code": tenant_code,
                "point_code": point_code,
            }
        )

    async def _get(self, query: dict[str, str]) -> RegistryReference:
        reference_type = query["reference_type"]
        url = f"{self.base_url.rstrip('/')}/internal/registry/reference-lookup"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, params=query)
                response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise TypeError("lookup response must be a JSON object")
            payload_reference_type = payload["reference_type"]
            payload_status = payload["status"]
            if not isinstance(payload_reference_type, str):
                raise TypeError("lookup response reference_type must be a string")
            display_name = payload.get("display_name")
            if display_name is not None and not isinstance(display_name, str):
                raise TypeError("lookup response display_name must be a string")
            snapshot_json = payload.get("snapshot_json") or {}
            if not isinstance(snapshot_json, dict):
                raise TypeError("lookup response snapshot_json must be an object")
            status = ReferenceStatus(payload_status)
        except httpx.HTTPStatusError as exc:
            raise RegistryLookupUnavailableError(
                reference_type,
                f"HTTP {exc.response.status_code}",
            ) from exc
        except httpx.TimeoutException as exc:
            raise RegistryLookupUnavailableError(reference_type, "timeout") from exc
        except httpx.RequestError as exc:
            raise RegistryLookupUnavailableError(
                reference_type,
                exc.__class__.__name__,
            ) from exc
        except (KeyError, TypeError, ValueError) as exc:
            raise RegistryLookupUnavailableError(
                reference_type,
                "invalid response",
            ) from exc
        return RegistryReference(
            reference_type=payload_reference_type,
            status=status,
            display_name=display_name,
            snapshot_json=dict(snapshot_json),
        )


def _valid(reference_type: str, snapshot: dict[str, Any]) -> RegistryReference:
    return RegistryReference(
        reference_type=reference_type,
        status=ReferenceStatus.VALID,
        snapshot_json=snapshot,
    )


def _status(
    reference_type: str,
    exists: bool,
    snapshot: dict[str, Any],
) -> RegistryReference:
    if exists:
        return _valid(reference_type, snapshot)
    return RegistryReference(reference_type, ReferenceStatus.STALE)
