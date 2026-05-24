from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

PATH_CODE_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,127}$"


class Base(DeclarativeBase):
    pass


class AssetGraphNodeModel(Base):
    __tablename__ = "asset_graph_nodes"
    __table_args__ = (
        UniqueConstraint(
            "tenant_code",
            "code",
            name="uq_asset_graph_nodes_tenant_code",
        ),
        CheckConstraint(
            f"tenant_code ~ '{PATH_CODE_PATTERN}'",
            name="ck_asset_graph_nodes_tenant_code_path",
        ),
        CheckConstraint(
            f"code ~ '{PATH_CODE_PATTERN}'",
            name="ck_asset_graph_nodes_code_path",
        ),
        Index("ix_asset_graph_nodes_tenant_object_type", "tenant_code", "object_type"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tenant_code: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    object_type: Mapped[str] = mapped_column(Text, nullable=False)
    vocabulary_term: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AssetGraphNodeAttributeModel(Base):
    __tablename__ = "asset_graph_node_attributes"
    __table_args__ = (
        UniqueConstraint(
            "tenant_code",
            "asset_graph_node_code",
            "attribute_key",
            name="uq_asset_graph_node_attributes_key",
        ),
        CheckConstraint(
            "value_type in ('boolean', 'number', 'string')",
            name="ck_asset_graph_node_attributes_value_type",
        ),
        Index(
            "ix_asset_graph_node_attributes_node",
            "tenant_code",
            "asset_graph_node_code",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tenant_code: Mapped[str] = mapped_column(Text, nullable=False)
    asset_graph_node_code: Mapped[str] = mapped_column(Text, nullable=False)
    attribute_key: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str | None] = mapped_column(Text)
    vocabulary_term: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AssetGraphRelationshipModel(Base):
    __tablename__ = "asset_graph_relationships"
    __table_args__ = (
        UniqueConstraint(
            "tenant_code",
            "code",
            name="uq_asset_graph_relationships_tenant_code",
        ),
        CheckConstraint(
            "relation_type in ('partOf', 'locatedIn', 'hasPoint', 'feeds', "
            "'measures', 'controls')",
            name="ck_asset_graph_relationships_relation_type",
        ),
        Index(
            "ix_asset_graph_relationships_source",
            "tenant_code",
            "source_asset_graph_node_code",
        ),
        Index(
            "ix_asset_graph_relationships_target",
            "tenant_code",
            "target_asset_graph_node_code",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tenant_code: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    source_asset_graph_node_code: Mapped[str] = mapped_column(Text, nullable=False)
    target_asset_graph_node_code: Mapped[str] = mapped_column(Text, nullable=False)
    relation_type: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TelemetryBindingModel(Base):
    __tablename__ = "asset_graph_telemetry_bindings"
    __table_args__ = (
        UniqueConstraint(
            "tenant_code",
            "code",
            name="uq_asset_graph_telemetry_bindings_tenant_code",
        ),
        UniqueConstraint(
            "tenant_code",
            "point_code",
            name="uq_asset_graph_telemetry_bindings_point",
        ),
        UniqueConstraint(
            "tenant_code",
            "asset_graph_node_code",
            "attribute_key",
            name="uq_asset_graph_telemetry_bindings_attribute",
        ),
        CheckConstraint(
            "reference_status in ('valid', 'stale', 'unknown')",
            name="ck_asset_graph_telemetry_bindings_reference_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tenant_code: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    point_code: Mapped[str] = mapped_column(Text, nullable=False)
    asset_graph_node_code: Mapped[str] = mapped_column(Text, nullable=False)
    attribute_key: Mapped[str] = mapped_column(Text, nullable=False)
    reference_status: Mapped[str] = mapped_column(Text, nullable=False)
    display_snapshot_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CatalogTreeModel(Base):
    __tablename__ = "catalog_trees"
    __table_args__ = (
        UniqueConstraint(
            "tenant_code",
            "code",
            name="uq_catalog_trees_tenant_code",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tenant_code: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CatalogNodeModel(Base):
    __tablename__ = "catalog_nodes"
    __table_args__ = (
        UniqueConstraint(
            "tenant_code",
            "tree_code",
            "code",
            name="uq_catalog_nodes_tenant_tree_code",
        ),
        CheckConstraint(
            "node_type in ('folder', 'asset_ref', 'agent_ref', 'source_ref', "
            "'registry_point_ref', 'asset_graph_node_ref')",
            name="ck_catalog_nodes_node_type",
        ),
        CheckConstraint(
            "reference_status in ('valid', 'stale', 'unknown')",
            name="ck_catalog_nodes_reference_status",
        ),
        Index(
            "ix_catalog_nodes_parent",
            "tenant_code",
            "tree_code",
            "parent_node_code",
            "sort_order",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tenant_code: Mapped[str] = mapped_column(Text, nullable=False)
    tree_code: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    parent_node_code: Mapped[str | None] = mapped_column(Text)
    node_type: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0)
    target_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    reference_status: Mapped[str] = mapped_column(Text, nullable=False)
    display_snapshot_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
