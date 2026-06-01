from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from idp_asset_graph_registry.application.use_cases.catalog import CatalogTree
from idp_asset_graph_registry.domain.entities import (
    AssetGraphNode,
    AssetGraphNodeAttribute,
    AssetGraphRelationship,
    CatalogNode,
    TelemetryBinding,
)
from idp_asset_graph_registry.domain.value_objects import (
    CatalogNodeType,
    ReferenceStatus,
    RelationType,
    ValueType,
)


class AssetGraphNodeCreateRequest(BaseModel):
    asset_graph_node_code: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    object_type: str = Field(min_length=1)
    vocabulary_term: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class AssetGraphNodeUpdateRequest(BaseModel):
    display_name: str = Field(min_length=1)
    object_type: str = Field(min_length=1)
    vocabulary_term: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class AssetGraphNodeResponse(BaseModel):
    tenant_code: str
    asset_graph_node_code: str
    display_name: str
    object_type: str
    vocabulary_term: str | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, node: AssetGraphNode) -> AssetGraphNodeResponse:
        return cls(**node.__dict__)


class AttributeCreateRequest(BaseModel):
    attribute_key: str = Field(min_length=1)
    value_type: ValueType
    unit: str | None = None
    vocabulary_term: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class AttributeUpdateRequest(BaseModel):
    value_type: ValueType
    unit: str | None = None
    vocabulary_term: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class AttributeResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    tenant_code: str
    asset_graph_node_code: str
    attribute_key: str
    value_type: ValueType
    unit: str | None
    vocabulary_term: str | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(
        cls,
        attribute: AssetGraphNodeAttribute,
    ) -> AttributeResponse:
        return cls(**attribute.__dict__)


class RelationshipCreateRequest(BaseModel):
    relationship_code: str = Field(min_length=1)
    source_asset_graph_node_code: str = Field(min_length=1)
    target_asset_graph_node_code: str = Field(min_length=1)
    relation_type: RelationType
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class RelationshipUpdateRequest(BaseModel):
    source_asset_graph_node_code: str = Field(min_length=1)
    target_asset_graph_node_code: str = Field(min_length=1)
    relation_type: RelationType
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class RelationshipResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    tenant_code: str
    relationship_code: str
    source_asset_graph_node_code: str
    target_asset_graph_node_code: str
    relation_type: RelationType
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(
        cls,
        relationship: AssetGraphRelationship,
    ) -> RelationshipResponse:
        return cls(**relationship.__dict__)


class TelemetryBindingCreateRequest(BaseModel):
    binding_code: str = Field(min_length=1)
    point_code: str = Field(min_length=1)
    asset_graph_node_code: str = Field(min_length=1)
    attribute_key: str = Field(min_length=1)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class TelemetryBindingUpdateRequest(BaseModel):
    point_code: str = Field(min_length=1)
    asset_graph_node_code: str = Field(min_length=1)
    attribute_key: str = Field(min_length=1)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class TelemetryBindingResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    tenant_code: str
    binding_code: str
    point_code: str
    asset_graph_node_code: str
    attribute_key: str
    reference_status: ReferenceStatus
    display_snapshot_json: dict[str, Any]
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, binding: TelemetryBinding) -> TelemetryBindingResponse:
        return cls(**binding.__dict__)


class CatalogNodeCreateRequest(BaseModel):
    node_code: str = Field(min_length=1)
    parent_node_code: str | None = None
    node_type: CatalogNodeType
    display_name: str = Field(min_length=1)
    sort_order: int = 0
    target: dict[str, Any] | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CatalogNodeUpdateRequest(BaseModel):
    display_name: str = Field(min_length=1)
    sort_order: int = 0
    target: dict[str, Any] | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CatalogNodeMoveRequest(BaseModel):
    parent_node_code: str | None = None
    sort_order: int = 0


class CatalogNodeResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    tenant_code: str
    tree_code: str
    node_code: str
    parent_node_code: str | None
    node_type: CatalogNodeType
    display_name: str
    sort_order: int
    target: dict[str, Any] | None
    metadata_json: dict[str, Any]
    reference_status: ReferenceStatus
    display_snapshot_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, node: CatalogNode) -> CatalogNodeResponse:
        return cls(**node.__dict__)


class CatalogTreeResponse(BaseModel):
    tenant_code: str
    tree_code: str
    nodes: list[CatalogNodeResponse]

    @classmethod
    def from_domain(cls, tree: CatalogTree) -> CatalogTreeResponse:
        return cls(
            tenant_code=tree.tenant_code,
            tree_code=tree.tree_code,
            nodes=[CatalogNodeResponse.from_domain(node) for node in tree.nodes],
        )
