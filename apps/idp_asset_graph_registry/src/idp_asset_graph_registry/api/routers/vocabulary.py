from __future__ import annotations

from fastapi import APIRouter

from idp_asset_graph_registry.domain.value_objects import RelationType

router = APIRouter(prefix="/internal/vocabulary", tags=["vocabulary"])


@router.get("/relation-types", response_model=list[str])
async def relation_types() -> list[str]:
    return [relation_type.value for relation_type in RelationType]
