from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from idp_config_registry.application.ports.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class RegistryReferenceLookupQuery:
    reference_type: str
    tenant_code: str
    asset_code: str | None = None
    agent_code: str | None = None
    source_code: str | None = None
    point_code: str | None = None


@dataclass(frozen=True)
class RegistryReferenceLookupResult:
    reference_type: str
    status: str
    display_name: str | None = None
    snapshot_json: dict[str, Any] = field(default_factory=dict)


class ResolveRegistryReference:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: RegistryReferenceLookupQuery,
    ) -> RegistryReferenceLookupResult:
        async with self._unit_of_work as unit_of_work:
            if query.reference_type == "tenant":
                tenant = await unit_of_work.tenants.get(query.tenant_code)
                return _result(
                    query.reference_type,
                    tenant is not None,
                    {"tenant_code": query.tenant_code},
                    tenant.name if tenant is not None else None,
                )
            if query.reference_type == "asset" and query.asset_code is not None:
                asset = await unit_of_work.assets.get(query.tenant_code, query.asset_code)
                return _result(
                    query.reference_type,
                    asset is not None,
                    {"tenant_code": query.tenant_code, "asset_code": query.asset_code},
                    asset.name if asset is not None else None,
                )
            if (
                query.reference_type == "agent"
                and query.asset_code is not None
                and query.agent_code is not None
            ):
                agent = await unit_of_work.agents.get(
                    query.tenant_code,
                    query.asset_code,
                    query.agent_code,
                )
                return _result(
                    query.reference_type,
                    agent is not None,
                    {
                        "tenant_code": query.tenant_code,
                        "asset_code": query.asset_code,
                        "agent_code": query.agent_code,
                    },
                    agent.name if agent is not None else None,
                )
            if (
                query.reference_type == "source"
                and query.asset_code is not None
                and query.agent_code is not None
                and query.source_code is not None
            ):
                source = await unit_of_work.sources.get(
                    query.tenant_code,
                    query.asset_code,
                    query.agent_code,
                    query.source_code,
                )
                return _result(
                    query.reference_type,
                    source is not None,
                    {
                        "tenant_code": query.tenant_code,
                        "asset_code": query.asset_code,
                        "agent_code": query.agent_code,
                        "source_code": query.source_code,
                    },
                    source.name if source is not None else None,
                )
            if query.reference_type == "point" and query.point_code is not None:
                point = await unit_of_work.points.get_by_id(
                    query.tenant_code,
                    query.point_code,
                )
                return _result(
                    query.reference_type,
                    point is not None,
                    {"tenant_code": query.tenant_code, "point_code": query.point_code},
                    point.name if point is not None else None,
                )
        return RegistryReferenceLookupResult(
            reference_type=query.reference_type,
            status="stale",
        )


def _result(
    reference_type: str,
    exists: bool,
    snapshot: dict[str, Any],
    display_name: str | None,
) -> RegistryReferenceLookupResult:
    return RegistryReferenceLookupResult(
        reference_type=reference_type,
        status="valid" if exists else "stale",
        display_name=display_name,
        snapshot_json=snapshot if exists else {},
    )

