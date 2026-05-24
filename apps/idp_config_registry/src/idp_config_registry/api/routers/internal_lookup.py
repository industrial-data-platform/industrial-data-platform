from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from idp_config_registry.api.dependencies import (
    UnitOfWorkFactory,
    get_unit_of_work_factory,
)
from idp_config_registry.api.schemas.reference_lookup import (
    RegistryReferenceLookupResponse,
)
from idp_config_registry.application.use_cases.reference_lookup import (
    RegistryReferenceLookupQuery,
    ResolveRegistryReference,
)

router = APIRouter(prefix="/internal/registry", tags=["internal-registry"])


@router.get("/reference-lookup", response_model=RegistryReferenceLookupResponse)
async def reference_lookup(
    reference_type: str = Query(
        pattern="^(tenant|asset|agent|source|point)$",
    ),
    tenant_code: str = Query(min_length=1),
    asset_code: str | None = Query(default=None),
    agent_code: str | None = Query(default=None),
    source_code: str | None = Query(default=None),
    point_code: str | None = Query(default=None),
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> RegistryReferenceLookupResponse:
    result = await ResolveRegistryReference(unit_of_work_factory()).execute(
        RegistryReferenceLookupQuery(
            reference_type=reference_type,
            tenant_code=tenant_code,
            asset_code=asset_code,
            agent_code=agent_code,
            source_code=source_code,
            point_code=point_code,
        )
    )
    return RegistryReferenceLookupResponse.from_result(result)
