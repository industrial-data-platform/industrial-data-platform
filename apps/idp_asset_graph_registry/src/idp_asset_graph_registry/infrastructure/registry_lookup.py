from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

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

    async def tenant(self, tenant_code: str) -> RegistryReference:
        return self._get({"reference_type": "tenant", "tenant_code": tenant_code})

    async def asset(self, tenant_code: str, asset_code: str) -> RegistryReference:
        return self._get(
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
        return self._get(
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
        return self._get(
            {
                "reference_type": "source",
                "tenant_code": tenant_code,
                "asset_code": asset_code,
                "agent_code": agent_code,
                "source_code": source_code,
            }
        )

    async def point(self, tenant_code: str, point_code: str) -> RegistryReference:
        return self._get(
            {
                "reference_type": "point",
                "tenant_code": tenant_code,
                "point_code": point_code,
            }
        )

    def _get(self, query: dict[str, str]) -> RegistryReference:
        encoded = urllib.parse.urlencode(query)
        url = f"{self.base_url.rstrip('/')}/internal/registry/reference-lookup?{encoded}"
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                payload = json.loads(response.read().decode())
        except Exception:
            return RegistryReference(query["reference_type"], ReferenceStatus.UNKNOWN)
        return RegistryReference(
            reference_type=payload["reference_type"],
            status=ReferenceStatus(payload["status"]),
            display_name=payload.get("display_name"),
            snapshot_json=dict(payload.get("snapshot_json") or {}),
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
