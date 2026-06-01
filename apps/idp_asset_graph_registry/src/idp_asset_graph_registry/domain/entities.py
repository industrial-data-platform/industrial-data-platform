from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from idp_asset_graph_registry.domain.value_objects import (
    CatalogNodeType,
    ReferenceStatus,
    RelationType,
    ValueType,
    require_non_empty,
    require_optional_path_code,
    require_path_code,
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True)
class AssetGraphNode:
    tenant_code: str
    asset_graph_node_code: str
    display_name: str
    object_type: str
    vocabulary_term: str | None = None
    metadata_json: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "tenant_code",
            require_path_code(self.tenant_code, field_name="tenant_code"),
        )
        object.__setattr__(
            self,
            "asset_graph_node_code",
            require_path_code(
                self.asset_graph_node_code,
                field_name="asset_graph_node_code",
            ),
        )
        object.__setattr__(
            self,
            "display_name",
            require_non_empty(self.display_name, field_name="display_name"),
        )
        object.__setattr__(
            self,
            "object_type",
            require_path_code(self.object_type, field_name="object_type"),
        )


@dataclass(frozen=True)
class AssetGraphNodeAttribute:
    tenant_code: str
    asset_graph_node_code: str
    attribute_key: str
    value_type: ValueType
    unit: str | None = None
    vocabulary_term: str | None = None
    metadata_json: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "tenant_code",
            require_path_code(self.tenant_code, field_name="tenant_code"),
        )
        object.__setattr__(
            self,
            "asset_graph_node_code",
            require_path_code(
                self.asset_graph_node_code,
                field_name="asset_graph_node_code",
            ),
        )
        object.__setattr__(
            self,
            "attribute_key",
            require_path_code(self.attribute_key, field_name="attribute_key"),
        )


@dataclass(frozen=True)
class AssetGraphRelationship:
    tenant_code: str
    relationship_code: str
    source_asset_graph_node_code: str
    target_asset_graph_node_code: str
    relation_type: RelationType
    metadata_json: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "tenant_code",
            require_path_code(self.tenant_code, field_name="tenant_code"),
        )
        object.__setattr__(
            self,
            "relationship_code",
            require_path_code(self.relationship_code, field_name="relationship_code"),
        )
        object.__setattr__(
            self,
            "source_asset_graph_node_code",
            require_path_code(
                self.source_asset_graph_node_code,
                field_name="source_asset_graph_node_code",
            ),
        )
        object.__setattr__(
            self,
            "target_asset_graph_node_code",
            require_path_code(
                self.target_asset_graph_node_code,
                field_name="target_asset_graph_node_code",
            ),
        )


@dataclass(frozen=True)
class TelemetryBinding:
    tenant_code: str
    binding_code: str
    point_code: str
    asset_graph_node_code: str
    attribute_key: str
    reference_status: ReferenceStatus = ReferenceStatus.VALID
    display_snapshot_json: dict[str, Any] = field(default_factory=dict)
    metadata_json: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "tenant_code",
            require_path_code(self.tenant_code, field_name="tenant_code"),
        )
        object.__setattr__(
            self,
            "binding_code",
            require_path_code(self.binding_code, field_name="binding_code"),
        )
        object.__setattr__(
            self,
            "point_code",
            require_non_empty(self.point_code, field_name="point_code"),
        )
        object.__setattr__(
            self,
            "asset_graph_node_code",
            require_path_code(
                self.asset_graph_node_code,
                field_name="asset_graph_node_code",
            ),
        )
        object.__setattr__(
            self,
            "attribute_key",
            require_path_code(self.attribute_key, field_name="attribute_key"),
        )


@dataclass(frozen=True)
class CatalogNode:
    tenant_code: str
    node_code: str
    node_type: CatalogNodeType
    display_name: str
    parent_node_code: str | None = None
    tree_code: str = "default"
    sort_order: int = 0
    target: dict[str, Any] | None = None
    metadata_json: dict[str, Any] = field(default_factory=dict)
    reference_status: ReferenceStatus = ReferenceStatus.UNKNOWN
    display_snapshot_json: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "tenant_code",
            require_path_code(self.tenant_code, field_name="tenant_code"),
        )
        object.__setattr__(
            self,
            "tree_code",
            require_path_code(self.tree_code, field_name="tree_code"),
        )
        object.__setattr__(
            self,
            "node_code",
            require_path_code(self.node_code, field_name="node_code"),
        )
        object.__setattr__(
            self,
            "parent_node_code",
            require_optional_path_code(
                self.parent_node_code,
                field_name="parent_node_code",
            ),
        )
        object.__setattr__(
            self,
            "display_name",
            require_non_empty(self.display_name, field_name="display_name"),
        )
