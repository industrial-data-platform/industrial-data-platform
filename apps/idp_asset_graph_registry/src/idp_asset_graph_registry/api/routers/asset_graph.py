from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from idp_asset_graph_registry.api.dependencies import (
    UnitOfWorkFactory,
    get_registry_lookup,
    get_unit_of_work_factory,
)
from idp_asset_graph_registry.api.schemas import (
    AssetGraphNodeCreateRequest,
    AssetGraphNodeResponse,
    AssetGraphNodeUpdateRequest,
    AttributeCreateRequest,
    AttributeResponse,
    AttributeUpdateRequest,
    RelationshipCreateRequest,
    RelationshipResponse,
    RelationshipUpdateRequest,
    TelemetryBindingCreateRequest,
    TelemetryBindingResponse,
    TelemetryBindingUpdateRequest,
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
from idp_asset_graph_registry.application.use_cases.asset_graph import (
    CreateAssetGraphNode,
    CreateAssetGraphNodeAttribute,
    CreateAssetGraphNodeAttributeCommand,
    CreateAssetGraphNodeCommand,
    CreateAssetGraphRelationship,
    CreateAssetGraphRelationshipCommand,
    CreateTelemetryBinding,
    CreateTelemetryBindingCommand,
    DeleteAssetGraphNode,
    DeleteAssetGraphNodeAttribute,
    DeleteAssetGraphRelationship,
    DeleteTelemetryBinding,
    GetAssetGraphNode,
    GetAssetGraphNodeAttribute,
    GetAssetGraphRelationship,
    GetTelemetryBinding,
    ListAssetGraphNodeAttributes,
    ListAssetGraphNodes,
    ListAssetGraphRelationships,
    ListTelemetryBindings,
    UpdateAssetGraphNode,
    UpdateAssetGraphNodeAttribute,
    UpdateAssetGraphNodeAttributeCommand,
    UpdateAssetGraphNodeCommand,
    UpdateAssetGraphRelationship,
    UpdateAssetGraphRelationshipCommand,
    UpdateTelemetryBinding,
    UpdateTelemetryBindingCommand,
)
from idp_asset_graph_registry.domain.value_objects import DomainValidationError

router = APIRouter(
    prefix="/internal/tenants/{tenant_code}/asset-graph",
    tags=["asset-graph"],
)


@router.post(
    "/nodes",
    response_model=AssetGraphNodeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_asset_graph_node(
    tenant_code: str,
    request: AssetGraphNodeCreateRequest,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
    registry_lookup: RegistryReferenceLookup = Depends(get_registry_lookup),
) -> AssetGraphNodeResponse:
    try:
        node = await CreateAssetGraphNode(
            unit_of_work_factory(),
            registry_lookup,
        ).execute(
            CreateAssetGraphNodeCommand(
                tenant_code=tenant_code,
                asset_graph_node_code=request.asset_graph_node_code,
                display_name=request.display_name,
                object_type=request.object_type,
                vocabulary_term=request.vocabulary_term,
                metadata_json=request.metadata_json,
            )
        )
    except (ApplicationError, DomainValidationError) as exc:
        _raise_http_error(exc)
    return AssetGraphNodeResponse.from_domain(node)


@router.get("/nodes", response_model=list[AssetGraphNodeResponse])
async def list_asset_graph_nodes(
    tenant_code: str,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> list[AssetGraphNodeResponse]:
    nodes = await ListAssetGraphNodes(unit_of_work_factory()).execute(tenant_code)
    return [AssetGraphNodeResponse.from_domain(node) for node in nodes]


@router.get("/nodes/{asset_graph_node_code}", response_model=AssetGraphNodeResponse)
async def get_asset_graph_node(
    tenant_code: str,
    asset_graph_node_code: str,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> AssetGraphNodeResponse:
    try:
        node = await GetAssetGraphNode(unit_of_work_factory()).execute(
            tenant_code,
            asset_graph_node_code,
        )
    except (ApplicationError, DomainValidationError) as exc:
        _raise_http_error(exc)
    return AssetGraphNodeResponse.from_domain(node)


@router.patch("/nodes/{asset_graph_node_code}", response_model=AssetGraphNodeResponse)
async def update_asset_graph_node(
    tenant_code: str,
    asset_graph_node_code: str,
    request: AssetGraphNodeUpdateRequest,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> AssetGraphNodeResponse:
    try:
        node = await UpdateAssetGraphNode(unit_of_work_factory()).execute(
            UpdateAssetGraphNodeCommand(
                tenant_code=tenant_code,
                asset_graph_node_code=asset_graph_node_code,
                display_name=request.display_name,
                object_type=request.object_type,
                vocabulary_term=request.vocabulary_term,
                metadata_json=request.metadata_json,
            )
        )
    except (ApplicationError, DomainValidationError) as exc:
        _raise_http_error(exc)
    return AssetGraphNodeResponse.from_domain(node)


@router.delete(
    "/nodes/{asset_graph_node_code}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_asset_graph_node(
    tenant_code: str,
    asset_graph_node_code: str,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> None:
    try:
        await DeleteAssetGraphNode(unit_of_work_factory()).execute(
            tenant_code,
            asset_graph_node_code,
        )
    except (ApplicationError, DomainValidationError) as exc:
        _raise_http_error(exc)


@router.post(
    "/nodes/{asset_graph_node_code}/attributes",
    response_model=AttributeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_attribute(
    tenant_code: str,
    asset_graph_node_code: str,
    request: AttributeCreateRequest,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> AttributeResponse:
    try:
        attribute = await CreateAssetGraphNodeAttribute(
            unit_of_work_factory()
        ).execute(
            CreateAssetGraphNodeAttributeCommand(
                tenant_code=tenant_code,
                asset_graph_node_code=asset_graph_node_code,
                attribute_key=request.attribute_key,
                value_type=request.value_type,
                unit=request.unit,
                vocabulary_term=request.vocabulary_term,
                metadata_json=request.metadata_json,
            )
        )
    except (ApplicationError, DomainValidationError) as exc:
        _raise_http_error(exc)
    return AttributeResponse.from_domain(attribute)


@router.get(
    "/nodes/{asset_graph_node_code}/attributes/{attribute_key}",
    response_model=AttributeResponse,
)
async def get_attribute(
    tenant_code: str,
    asset_graph_node_code: str,
    attribute_key: str,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> AttributeResponse:
    try:
        attribute = await GetAssetGraphNodeAttribute(
            unit_of_work_factory()
        ).execute(tenant_code, asset_graph_node_code, attribute_key)
    except (ApplicationError, DomainValidationError) as exc:
        _raise_http_error(exc)
    return AttributeResponse.from_domain(attribute)


@router.get(
    "/nodes/{asset_graph_node_code}/attributes",
    response_model=list[AttributeResponse],
)
async def list_attributes(
    tenant_code: str,
    asset_graph_node_code: str,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> list[AttributeResponse]:
    attributes = await ListAssetGraphNodeAttributes(
        unit_of_work_factory()
    ).execute(tenant_code, asset_graph_node_code)
    return [AttributeResponse.from_domain(attribute) for attribute in attributes]


@router.patch(
    "/nodes/{asset_graph_node_code}/attributes/{attribute_key}",
    response_model=AttributeResponse,
)
async def update_attribute(
    tenant_code: str,
    asset_graph_node_code: str,
    attribute_key: str,
    request: AttributeUpdateRequest,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> AttributeResponse:
    try:
        attribute = await UpdateAssetGraphNodeAttribute(
            unit_of_work_factory()
        ).execute(
            UpdateAssetGraphNodeAttributeCommand(
                tenant_code=tenant_code,
                asset_graph_node_code=asset_graph_node_code,
                attribute_key=attribute_key,
                value_type=request.value_type,
                unit=request.unit,
                vocabulary_term=request.vocabulary_term,
                metadata_json=request.metadata_json,
            )
        )
    except (ApplicationError, DomainValidationError) as exc:
        _raise_http_error(exc)
    return AttributeResponse.from_domain(attribute)


@router.delete(
    "/nodes/{asset_graph_node_code}/attributes/{attribute_key}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_attribute(
    tenant_code: str,
    asset_graph_node_code: str,
    attribute_key: str,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> None:
    try:
        await DeleteAssetGraphNodeAttribute(unit_of_work_factory()).execute(
            tenant_code,
            asset_graph_node_code,
            attribute_key,
        )
    except (ApplicationError, DomainValidationError) as exc:
        _raise_http_error(exc)


@router.post(
    "/relationships",
    response_model=RelationshipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_relationship(
    tenant_code: str,
    request: RelationshipCreateRequest,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> RelationshipResponse:
    try:
        relationship = await CreateAssetGraphRelationship(
            unit_of_work_factory()
        ).execute(
            CreateAssetGraphRelationshipCommand(
                tenant_code=tenant_code,
                relationship_code=request.relationship_code,
                source_asset_graph_node_code=request.source_asset_graph_node_code,
                target_asset_graph_node_code=request.target_asset_graph_node_code,
                relation_type=request.relation_type,
                metadata_json=request.metadata_json,
            )
        )
    except (ApplicationError, DomainValidationError) as exc:
        _raise_http_error(exc)
    return RelationshipResponse.from_domain(relationship)


@router.get("/relationships/{relationship_code}", response_model=RelationshipResponse)
async def get_relationship(
    tenant_code: str,
    relationship_code: str,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> RelationshipResponse:
    try:
        relationship = await GetAssetGraphRelationship(
            unit_of_work_factory()
        ).execute(tenant_code, relationship_code)
    except (ApplicationError, DomainValidationError) as exc:
        _raise_http_error(exc)
    return RelationshipResponse.from_domain(relationship)


@router.get("/relationships", response_model=list[RelationshipResponse])
async def list_relationships(
    tenant_code: str,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> list[RelationshipResponse]:
    relationships = await ListAssetGraphRelationships(
        unit_of_work_factory()
    ).execute(tenant_code)
    return [
        RelationshipResponse.from_domain(relationship)
        for relationship in relationships
    ]


@router.patch(
    "/relationships/{relationship_code}",
    response_model=RelationshipResponse,
)
async def update_relationship(
    tenant_code: str,
    relationship_code: str,
    request: RelationshipUpdateRequest,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> RelationshipResponse:
    try:
        relationship = await UpdateAssetGraphRelationship(
            unit_of_work_factory()
        ).execute(
            UpdateAssetGraphRelationshipCommand(
                tenant_code=tenant_code,
                relationship_code=relationship_code,
                source_asset_graph_node_code=request.source_asset_graph_node_code,
                target_asset_graph_node_code=request.target_asset_graph_node_code,
                relation_type=request.relation_type,
                metadata_json=request.metadata_json,
            )
        )
    except (ApplicationError, DomainValidationError) as exc:
        _raise_http_error(exc)
    return RelationshipResponse.from_domain(relationship)


@router.delete(
    "/relationships/{relationship_code}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_relationship(
    tenant_code: str,
    relationship_code: str,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> None:
    try:
        await DeleteAssetGraphRelationship(unit_of_work_factory()).execute(
            tenant_code,
            relationship_code,
        )
    except (ApplicationError, DomainValidationError) as exc:
        _raise_http_error(exc)


@router.post(
    "/telemetry-bindings",
    response_model=TelemetryBindingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_telemetry_binding(
    tenant_code: str,
    request: TelemetryBindingCreateRequest,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
    registry_lookup: RegistryReferenceLookup = Depends(get_registry_lookup),
) -> TelemetryBindingResponse:
    try:
        binding = await CreateTelemetryBinding(
            unit_of_work_factory(),
            registry_lookup,
        ).execute(
            CreateTelemetryBindingCommand(
                tenant_code=tenant_code,
                binding_code=request.binding_code,
                point_code=request.point_code,
                asset_graph_node_code=request.asset_graph_node_code,
                attribute_key=request.attribute_key,
                metadata_json=request.metadata_json,
            )
        )
    except (ApplicationError, DomainValidationError) as exc:
        _raise_http_error(exc)
    return TelemetryBindingResponse.from_domain(binding)


@router.get(
    "/telemetry-bindings/{binding_code}",
    response_model=TelemetryBindingResponse,
)
async def get_telemetry_binding(
    tenant_code: str,
    binding_code: str,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> TelemetryBindingResponse:
    try:
        binding = await GetTelemetryBinding(unit_of_work_factory()).execute(
            tenant_code,
            binding_code,
        )
    except (ApplicationError, DomainValidationError) as exc:
        _raise_http_error(exc)
    return TelemetryBindingResponse.from_domain(binding)


@router.get("/telemetry-bindings", response_model=list[TelemetryBindingResponse])
async def list_telemetry_bindings(
    tenant_code: str,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> list[TelemetryBindingResponse]:
    bindings = await ListTelemetryBindings(unit_of_work_factory()).execute(tenant_code)
    return [TelemetryBindingResponse.from_domain(binding) for binding in bindings]


@router.patch(
    "/telemetry-bindings/{binding_code}",
    response_model=TelemetryBindingResponse,
)
async def update_telemetry_binding(
    tenant_code: str,
    binding_code: str,
    request: TelemetryBindingUpdateRequest,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
    registry_lookup: RegistryReferenceLookup = Depends(get_registry_lookup),
) -> TelemetryBindingResponse:
    try:
        binding = await UpdateTelemetryBinding(
            unit_of_work_factory(),
            registry_lookup,
        ).execute(
            UpdateTelemetryBindingCommand(
                tenant_code=tenant_code,
                binding_code=binding_code,
                point_code=request.point_code,
                asset_graph_node_code=request.asset_graph_node_code,
                attribute_key=request.attribute_key,
                metadata_json=request.metadata_json,
            )
        )
    except (ApplicationError, DomainValidationError) as exc:
        _raise_http_error(exc)
    return TelemetryBindingResponse.from_domain(binding)


@router.delete(
    "/telemetry-bindings/{binding_code}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_telemetry_binding(
    tenant_code: str,
    binding_code: str,
    unit_of_work_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> None:
    try:
        await DeleteTelemetryBinding(unit_of_work_factory()).execute(
            tenant_code,
            binding_code,
        )
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
    if isinstance(exc, (ResourceNotFoundError, InvalidReferenceError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, InvalidOperationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(exc),
    )
