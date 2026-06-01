"""create Asset Graph Registry baseline

Revision ID: 0001_asset_graph_registry
Revises:
Create Date: 2026-05-24 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_asset_graph_registry"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PATH_CODE_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,127}$"


def upgrade() -> None:
    op.create_table(
        "asset_graph_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_code", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("object_type", sa.Text(), nullable=False),
        sa.Column("vocabulary_term", sa.Text(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            f"tenant_code ~ '{PATH_CODE_PATTERN}'",
            name="ck_asset_graph_nodes_tenant_code_path",
        ),
        sa.CheckConstraint(
            f"code ~ '{PATH_CODE_PATTERN}'",
            name="ck_asset_graph_nodes_code_path",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_code", "code", name="uq_asset_graph_nodes_tenant_code"),
    )
    op.create_index(
        "ix_asset_graph_nodes_tenant_object_type",
        "asset_graph_nodes",
        ["tenant_code", "object_type"],
    )

    op.create_table(
        "asset_graph_node_attributes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_code", sa.Text(), nullable=False),
        sa.Column("asset_graph_node_code", sa.Text(), nullable=False),
        sa.Column("attribute_key", sa.Text(), nullable=False),
        sa.Column("value_type", sa.Text(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("vocabulary_term", sa.Text(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "value_type in ('boolean', 'number', 'string')",
            name="ck_asset_graph_node_attributes_value_type",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_code",
            "asset_graph_node_code",
            "attribute_key",
            name="uq_asset_graph_node_attributes_key",
        ),
    )
    op.create_index(
        "ix_asset_graph_node_attributes_node",
        "asset_graph_node_attributes",
        ["tenant_code", "asset_graph_node_code"],
    )

    op.create_table(
        "asset_graph_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_code", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("source_asset_graph_node_code", sa.Text(), nullable=False),
        sa.Column("target_asset_graph_node_code", sa.Text(), nullable=False),
        sa.Column("relation_type", sa.Text(), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "relation_type in ('partOf', 'locatedIn', 'hasPoint', 'feeds', "
            "'measures', 'controls')",
            name="ck_asset_graph_relationships_relation_type",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_code",
            "code",
            name="uq_asset_graph_relationships_tenant_code",
        ),
    )
    op.create_index(
        "ix_asset_graph_relationships_source",
        "asset_graph_relationships",
        ["tenant_code", "source_asset_graph_node_code"],
    )
    op.create_index(
        "ix_asset_graph_relationships_target",
        "asset_graph_relationships",
        ["tenant_code", "target_asset_graph_node_code"],
    )

    op.create_table(
        "asset_graph_telemetry_bindings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_code", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("point_code", sa.Text(), nullable=False),
        sa.Column("asset_graph_node_code", sa.Text(), nullable=False),
        sa.Column("attribute_key", sa.Text(), nullable=False),
        sa.Column("reference_status", sa.Text(), nullable=False),
        sa.Column(
            "display_snapshot_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "reference_status in ('valid', 'stale', 'unknown')",
            name="ck_asset_graph_telemetry_bindings_reference_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_code",
            "code",
            name="uq_asset_graph_telemetry_bindings_tenant_code",
        ),
        sa.UniqueConstraint(
            "tenant_code",
            "point_code",
            name="uq_asset_graph_telemetry_bindings_point",
        ),
        sa.UniqueConstraint(
            "tenant_code",
            "asset_graph_node_code",
            "attribute_key",
            name="uq_asset_graph_telemetry_bindings_attribute",
        ),
    )

    op.create_table(
        "catalog_trees",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_code", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_code", "code", name="uq_catalog_trees_tenant_code"),
    )

    op.create_table(
        "catalog_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_code", sa.Text(), nullable=False),
        sa.Column("tree_code", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("parent_node_code", sa.Text(), nullable=True),
        sa.Column("node_type", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("target_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("reference_status", sa.Text(), nullable=False),
        sa.Column(
            "display_snapshot_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "node_type in ('folder', 'asset_ref', 'agent_ref', 'source_ref', "
            "'registry_point_ref', 'asset_graph_node_ref')",
            name="ck_catalog_nodes_node_type",
        ),
        sa.CheckConstraint(
            "reference_status in ('valid', 'stale', 'unknown')",
            name="ck_catalog_nodes_reference_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_code",
            "tree_code",
            "code",
            name="uq_catalog_nodes_tenant_tree_code",
        ),
    )
    op.create_index(
        "ix_catalog_nodes_parent",
        "catalog_nodes",
        ["tenant_code", "tree_code", "parent_node_code", "sort_order"],
    )


def downgrade() -> None:
    op.drop_index("ix_catalog_nodes_parent", table_name="catalog_nodes")
    op.drop_table("catalog_nodes")
    op.drop_table("catalog_trees")
    op.drop_table("asset_graph_telemetry_bindings")
    op.drop_index(
        "ix_asset_graph_relationships_target",
        table_name="asset_graph_relationships",
    )
    op.drop_index(
        "ix_asset_graph_relationships_source",
        table_name="asset_graph_relationships",
    )
    op.drop_table("asset_graph_relationships")
    op.drop_index(
        "ix_asset_graph_node_attributes_node",
        table_name="asset_graph_node_attributes",
    )
    op.drop_table("asset_graph_node_attributes")
    op.drop_index(
        "ix_asset_graph_nodes_tenant_object_type",
        table_name="asset_graph_nodes",
    )
    op.drop_table("asset_graph_nodes")
