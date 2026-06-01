from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from idp_asset_graph_registry.api.dependencies import (
    UnitOfWorkFactory,
    get_registry_lookup,
    get_unit_of_work_factory,
)
from idp_asset_graph_registry.api.schemas import (
    CatalogNodeCreateRequest,
    CatalogNodeMoveRequest,
    CatalogNodeResponse,
    CatalogNodeUpdateRequest,
    CatalogTreeResponse,
)
from idp_asset_graph_registry.application.errors import (
    ApplicationError,
    DuplicateResourceError,
    InvalidOperationError,
    InvalidReferenceError,
    RegistryLookupUnavailableError,
    ResourceNotFoundError,
)
from idp_asset_graph_registry.application.ports.registry_lookup import (
    RegistryReferenceLookup,
)
from idp_asset_graph_registry.application.use_cases.catalog import (
    CreateCatalogNode,
    CreateCatalogNodeCommand,
    DeleteCatalogNode,
    GetCatalogTree,
    MoveCatalogNode,
    MoveCatalogNodeCommand,
    UpdateCatalogNode,
    UpdateCatalogNodeCommand,
)
from idp_asset_graph_registry.domain.value_objects import DomainValidationError

router = APIRouter(
    prefix="/internal/tenants/{tenant_code}/catalog/default",
    tags=["catalog"],
)


@router.get("/tree", response_model=CatalogTreeResponse)
async def get_catalog_tree(
    tenant_code: str,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> CatalogTreeResponse:
    tree = await GetCatalogTree(unit_of_work_factory()).execute(tenant_code)
    return CatalogTreeResponse.from_domain(tree)


@router.post(
    "/nodes",
    response_model=CatalogNodeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_catalog_node(
    tenant_code: str,
    request: CatalogNodeCreateRequest,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
    registry_lookup: RegistryReferenceLookup = Depends(get_registry_lookup),
) -> CatalogNodeResponse:
    try:
        node = await CreateCatalogNode(
            unit_of_work_factory(),
            registry_lookup,
        ).execute(
            CreateCatalogNodeCommand(
                tenant_code=tenant_code,
                node_code=request.node_code,
                parent_node_code=request.parent_node_code,
                node_type=request.node_type,
                display_name=request.display_name,
                sort_order=request.sort_order,
                target=request.target,
                metadata_json=request.metadata_json,
            )
        )
    except (ApplicationError, DomainValidationError) as exc:
        _raise_http_error(exc)
    return CatalogNodeResponse.from_domain(node)


@router.patch("/nodes/{node_code}", response_model=CatalogNodeResponse)
async def update_catalog_node(
    tenant_code: str,
    node_code: str,
    request: CatalogNodeUpdateRequest,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
    registry_lookup: RegistryReferenceLookup = Depends(get_registry_lookup),
) -> CatalogNodeResponse:
    try:
        node = await UpdateCatalogNode(
            unit_of_work_factory(),
            registry_lookup,
        ).execute(
            UpdateCatalogNodeCommand(
                tenant_code=tenant_code,
                node_code=node_code,
                display_name=request.display_name,
                sort_order=request.sort_order,
                target=request.target,
                metadata_json=request.metadata_json,
            )
        )
    except (ApplicationError, DomainValidationError) as exc:
        _raise_http_error(exc)
    return CatalogNodeResponse.from_domain(node)


@router.post("/nodes/{node_code}/move", response_model=CatalogNodeResponse)
async def move_catalog_node(
    tenant_code: str,
    node_code: str,
    request: CatalogNodeMoveRequest,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> CatalogNodeResponse:
    try:
        node = await MoveCatalogNode(unit_of_work_factory()).execute(
            MoveCatalogNodeCommand(
                tenant_code=tenant_code,
                node_code=node_code,
                parent_node_code=request.parent_node_code,
                sort_order=request.sort_order,
            )
        )
    except (ApplicationError, DomainValidationError) as exc:
        _raise_http_error(exc)
    return CatalogNodeResponse.from_domain(node)


@router.delete("/nodes/{node_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_catalog_node(
    tenant_code: str,
    node_code: str,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> None:
    try:
        await DeleteCatalogNode(unit_of_work_factory()).execute(tenant_code, node_code)
    except (ApplicationError, DomainValidationError) as exc:
        _raise_http_error(exc)


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, RegistryLookupUnavailableError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    if isinstance(exc, DuplicateResourceError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, ResourceNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if (
        isinstance(exc, InvalidReferenceError)
        and exc.reference_type == "tenant"
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, (InvalidOperationError, InvalidReferenceError)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(exc),
    )
