"""create IDP config registry baseline

Revision ID: 0001_idp_config_registry
Revises:
Create Date: 2026-05-10 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_idp_config_registry"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(code) > 0", name="ck_tenants_code_non_empty"),
        sa.CheckConstraint(
            "status in ('active', 'disabled')",
            name="ck_tenants_status",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tenants"),
        sa.UniqueConstraint("code", name="uq_tenants_code"),
    )

    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "code ~ '^[a-z0-9][a-z0-9_-]{0,127}$'",
            name="ck_assets_code_path_id",
        ),
        sa.CheckConstraint(
            "status in ('active', 'disabled')",
            name="ck_assets_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_assets_tenant",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_assets"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_assets_id_tenant"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_assets_tenant_code"),
    )
    op.create_index(
        "ix_assets_tenant_status",
        "assets",
        ["tenant_id", "status"],
    )

    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "bootstrap_hint_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "code ~ '^[a-z0-9][a-z0-9_-]{0,127}$'",
            name="ck_agents_code_path_id",
        ),
        sa.CheckConstraint(
            "status in ('active', 'disabled', 'retired')",
            name="ck_agents_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_agents_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id", "tenant_id"],
            ["assets.id", "assets.tenant_id"],
            name="fk_agents_asset",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agents"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_agents_id_tenant"),
        sa.UniqueConstraint("asset_id", "code", name="uq_agents_asset_code"),
    )
    op.create_index(
        "ix_agents_tenant_code",
        "agents",
        ["tenant_id", "code"],
    )

    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "connection_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "acquisition_defaults_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "publish_defaults_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "code ~ '^[a-z0-9][a-z0-9_-]{0,127}$'",
            name="ck_sources_code_path_id",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_sources_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["agent_id", "tenant_id"],
            ["agents.id", "agents.tenant_id"],
            name="fk_sources_agent",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sources"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_sources_id_tenant"),
        sa.UniqueConstraint(
            "id",
            "agent_id",
            "tenant_id",
            name="uq_sources_id_agent_tenant",
        ),
        sa.UniqueConstraint("agent_id", "code", name="uq_sources_agent_code"),
    )
    op.create_index(
        "ix_sources_tenant_type",
        "sources",
        ["tenant_id", "source_type"],
    )

    op.create_table(
        "points",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("point_key", sa.String(length=512), nullable=False),
        sa.Column("point_ref", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("value_type", sa.Text(), nullable=False),
        sa.Column("value_model", sa.Text(), nullable=False),
        sa.Column("signal_type", sa.Text(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column(
            "enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "acquisition_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "publish_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "tags_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "point_key ~ '^(?:[A-Za-z0-9._~-]|%[0-9A-F]{2})+$'",
            name="ck_points_point_key",
        ),
        sa.CheckConstraint(
            "signal_type in ('command', 'feedback', 'status', 'sensor')",
            name="ck_points_signal_type",
        ),
        sa.CheckConstraint(
            "value_type in ('boolean', 'number', 'string')",
            name="ck_points_value_type",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_points_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["source_id", "tenant_id"],
            ["sources.id", "sources.tenant_id"],
            name="fk_points_source",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_points"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_points_tenant_code"),
        sa.UniqueConstraint("source_id", "point_key", name="uq_points_point_key"),
        sa.UniqueConstraint("source_id", "point_ref", name="uq_points_point_ref"),
    )
    op.create_index(
        "ix_points_source_enabled",
        "points",
        ["source_id", "enabled"],
    )

    op.create_table(
        "agent_runtime_config_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "agent_runtime_payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status in ('draft', 'rendered', 'active', 'superseded', 'failed')",
            name="ck_agent_runtime_config_revisions_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_agent_runtime_config_revisions_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["agent_id", "tenant_id"],
            ["agents.id", "agents.tenant_id"],
            name="fk_agent_runtime_config_revisions_agent",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agent_runtime_config_revisions"),
        sa.UniqueConstraint(
            "id",
            "tenant_id",
            name="uq_agent_runtime_config_revisions_id_tenant",
        ),
        sa.UniqueConstraint(
            "agent_id",
            "code",
            name="uq_agent_runtime_config_revisions_agent_code",
        ),
    )
    op.create_index(
        "uq_agent_runtime_config_revisions_active",
        "agent_runtime_config_revisions",
        ["agent_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "source_config_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "agent_runtime_config_revision_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("config_revision", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "source_payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status in ('draft', 'rendered', 'active', 'superseded', 'failed')",
            name="ck_source_config_revisions_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_source_config_revisions_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["source_id", "tenant_id"],
            ["sources.id", "sources.tenant_id"],
            name="fk_source_config_revisions_source",
        ),
        sa.ForeignKeyConstraint(
            ["agent_runtime_config_revision_id", "tenant_id"],
            [
                "agent_runtime_config_revisions.id",
                "agent_runtime_config_revisions.tenant_id",
            ],
            name="fk_source_config_revisions_runtime",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_source_config_revisions"),
        sa.UniqueConstraint(
            "source_id",
            "code",
            name="uq_source_config_revisions_source_code",
        ),
    )
    op.create_index(
        "uq_source_config_revisions_active",
        "source_config_revisions",
        ["source_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "config_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("config_revision", sa.Text(), nullable=False),
        sa.Column("config_scope", sa.Text(), nullable=False),
        sa.Column("source_config_revision", sa.Text(), nullable=True),
        sa.Column("message_type", sa.Text(), nullable=False),
        sa.Column("kafka_topic", sa.Text(), nullable=False),
        sa.Column("kafka_key", sa.Text(), nullable=False),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status in ('pending', 'inflight', 'published', 'retry', 'dead_letter')",
            name="ck_config_outbox_status",
        ),
        sa.CheckConstraint(
            "(config_scope = 'agent_runtime' and source_id is null "
            "and source_config_revision is null) "
            "or (config_scope like 'source:%' and source_id is not null "
            "and source_config_revision is not null)",
            name="ck_config_outbox_scope_source_consistency",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_config_outbox_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["agent_id", "tenant_id"],
            ["agents.id", "agents.tenant_id"],
            name="fk_config_outbox_agent",
        ),
        sa.ForeignKeyConstraint(
            ["source_id", "agent_id", "tenant_id"],
            ["sources.id", "sources.agent_id", "sources.tenant_id"],
            name="fk_config_outbox_source",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_config_outbox"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_config_outbox_idempotency_key",
        ),
    )
    op.create_index(
        "ix_config_outbox_reservation",
        "config_outbox",
        ["status", "available_at"],
    )
    op.create_index(
        "ix_config_outbox_lease",
        "config_outbox",
        ["status", "lease_expires_at"],
    )
    op.create_index(
        "ix_config_outbox_config_scope",
        "config_outbox",
        ["agent_id", "config_revision", "config_scope"],
    )


def downgrade() -> None:
    op.drop_index("ix_config_outbox_config_scope", table_name="config_outbox")
    op.drop_index("ix_config_outbox_lease", table_name="config_outbox")
    op.drop_index("ix_config_outbox_reservation", table_name="config_outbox")
    op.drop_table("config_outbox")

    op.drop_index(
        "uq_source_config_revisions_active",
        table_name="source_config_revisions",
    )
    op.drop_table("source_config_revisions")
    op.drop_index(
        "uq_agent_runtime_config_revisions_active",
        table_name="agent_runtime_config_revisions",
    )
    op.drop_table("agent_runtime_config_revisions")

    op.drop_index("ix_points_source_enabled", table_name="points")
    op.drop_table("points")
    op.drop_index("ix_sources_tenant_type", table_name="sources")
    op.drop_table("sources")
    op.drop_index("ix_agents_tenant_code", table_name="agents")
    op.drop_table("agents")
    op.drop_index("ix_assets_tenant_status", table_name="assets")
    op.drop_table("assets")
    op.drop_table("tenants")
