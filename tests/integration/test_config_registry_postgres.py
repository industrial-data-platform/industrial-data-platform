from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from idp_config_registry.application.use_cases.config_outbox import (
    MarkConfigOutboxPublished,
    ReleaseExpiredConfigOutboxLeases,
    ReserveConfigOutboxCommand,
    ReserveConfigOutboxRecords,
)
from idp_config_registry.application.use_cases.render_config import (
    RenderAgentRuntimeConfig,
    RenderAgentRuntimeConfigCommand,
    StoreRenderedAgentRuntimeConfig,
)
from idp_config_registry.domain.value_objects import ConfigOutboxStatus
from idp_config_registry.infrastructure.json_schema_validator import (
    JsonSchemaConfigPayloadValidator,
)
from idp_config_registry.infrastructure.postgres.unit_of_work import (
    PostgresUnitOfWorkFactory,
)
from idp_config_registry.main import create_app
from idp_config_registry.settings import ConfigRegistrySettings

pytestmark = pytest.mark.integration

CONTRACT_DIR = Path("docs/contracts/edge-telemetry-agent/schemas")

REGISTRY_TABLES = (
    "tenants",
    "assets",
    "agents",
    "sources",
    "points",
    "agent_runtime_config_revisions",
    "source_config_revisions",
    "config_outbox",
)

UUID_COLUMNS_BY_TABLE = {
    "tenants": {"id"},
    "assets": {"id", "tenant_id"},
    "agents": {"id", "tenant_id", "asset_id"},
    "sources": {"id", "tenant_id", "agent_id"},
    "points": {"id", "tenant_id", "source_id"},
    "agent_runtime_config_revisions": {"id", "tenant_id", "agent_id"},
    "source_config_revisions": {
        "id",
        "tenant_id",
        "source_id",
        "agent_runtime_config_revision_id",
    },
    "config_outbox": {"id", "tenant_id", "agent_id", "source_id"},
}

CODE_TABLES = {
    "tenants",
    "assets",
    "agents",
    "sources",
    "points",
    "agent_runtime_config_revisions",
    "source_config_revisions",
}


@pytest.mark.asyncio
async def test_config_registry_postgres_schema_uses_uuid_surrogates_and_code_columns(
    local_config_registry_postgres_stack,
) -> None:
    engine = create_async_engine(local_config_registry_postgres_stack.database_url)
    try:
        async with engine.connect() as connection:
            primary_key_rows = (
                (
                    await connection.execute(
                        text(
                            """
                        select c.relname as table_name,
                               array_agg(a.attname order by keys.ordinality) as columns
                        from pg_index i
                        join pg_class c on c.oid = i.indrelid
                        join pg_namespace n on n.oid = c.relnamespace
                        join unnest(i.indkey) with ordinality as keys(attnum, ordinality)
                          on true
                        join pg_attribute a
                          on a.attrelid = c.oid
                         and a.attnum = keys.attnum
                        where i.indisprimary
                          and n.nspname = 'public'
                          and c.relname in (
                            'tenants',
                            'assets',
                            'agents',
                            'sources',
                            'points',
                            'agent_runtime_config_revisions',
                            'source_config_revisions',
                            'config_outbox'
                          )
                        group by c.relname
                        """
                        )
                    )
                )
                .mappings()
                .all()
            )
            column_rows = (
                (
                    await connection.execute(
                        text(
                            """
                        select table_name,
                               column_name,
                               data_type,
                               column_default
                        from information_schema.columns
                        where table_schema = 'public'
                          and table_name in (
                            'tenants',
                            'assets',
                            'agents',
                            'sources',
                            'points',
                            'agent_runtime_config_revisions',
                            'source_config_revisions',
                            'config_outbox'
                          )
                        """
                        )
                    )
                )
                .mappings()
                .all()
            )
    finally:
        await engine.dispose()

    primary_keys = {
        row["table_name"]: tuple(row["columns"]) for row in primary_key_rows
    }
    columns = {(row["table_name"], row["column_name"]): row for row in column_rows}

    assert primary_keys == {table: ("id",) for table in REGISTRY_TABLES}

    for table_name, uuid_columns in UUID_COLUMNS_BY_TABLE.items():
        for column_name in uuid_columns:
            column = columns[(table_name, column_name)]
            assert column["data_type"] == "uuid"
            assert column["column_default"] is None

    for table_name in CODE_TABLES:
        assert columns[(table_name, "code")]["data_type"] == "text"


@pytest.mark.asyncio
async def test_config_registry_postgres_rejects_cross_tenant_uuid_links(
    local_config_registry_postgres_stack,
) -> None:
    tenant_a_id = uuid4()
    tenant_b_id = uuid4()
    asset_id = uuid4()
    agent_id = uuid4()
    now = datetime.now(tz=UTC)
    engine = create_async_engine(local_config_registry_postgres_stack.database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    insert into tenants (id, code, name, status, created_at, updated_at)
                    values (:tenant_a_id, 'tenant-link-a', 'Tenant A', 'active', :now, :now),
                           (:tenant_b_id, 'tenant-link-b', 'Tenant B', 'active', :now, :now)
                    """
                ),
                {
                    "tenant_a_id": tenant_a_id,
                    "tenant_b_id": tenant_b_id,
                    "now": now,
                },
            )
            await connection.execute(
                text(
                    """
                    insert into assets
                      (id, tenant_id, code, name, status, created_at, updated_at)
                    values
                      (:asset_id, :tenant_a_id, 'asset-link-a', 'Asset A',
                       'active', :now, :now)
                    """
                ),
                {
                    "asset_id": asset_id,
                    "tenant_a_id": tenant_a_id,
                    "now": now,
                },
            )

        async with engine.connect() as connection:
            transaction = await connection.begin()
            with pytest.raises(IntegrityError):
                await connection.execute(
                    text(
                        """
                        insert into agents
                          (id, tenant_id, asset_id, code, name, status,
                           bootstrap_hint_json, created_at, updated_at)
                        values
                          (:agent_id, :tenant_b_id, :asset_id, 'agent-a', null,
                           'active', '{}'::jsonb, :now, :now)
                        """
                    ),
                    {
                        "agent_id": agent_id,
                        "tenant_b_id": tenant_b_id,
                        "asset_id": asset_id,
                        "now": now,
                    },
                )
            await transaction.rollback()
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    delete from agents ag
                    using tenants t
                    where ag.tenant_id = t.id
                      and t.code in ('tenant-link-a', 'tenant-link-b')
                    """
                )
            )
            await connection.execute(
                text(
                    """
                    delete from assets a
                    using tenants t
                    where a.tenant_id = t.id
                      and t.code in ('tenant-link-a', 'tenant-link-b')
                    """
                )
            )
            await connection.execute(
                text(
                    """
                    delete from tenants
                    where code in ('tenant-link-a', 'tenant-link-b')
                    """
                )
            )
        await engine.dispose()


@pytest.mark.asyncio
async def test_config_registry_postgres_backoffice_accepts_sqladmin_uuid_ids(
    local_config_registry_postgres_stack,
) -> None:
    settings = ConfigRegistrySettings(
        database_url=local_config_registry_postgres_stack.database_url,
        internal_mode=True,
    )

    try:
        with TestClient(create_app(settings=settings)) as client:
            _create_uuid_backoffice_agent_graph(client)
            ids = await _uuid_backoffice_ids(settings.database_url)

            edit_response = client.post(
                f"/backoffice/asset-model/edit/{ids['asset_id']}",
                data={
                    "name": "Asset UUID Updated",
                    "description": "Updated through SQLAdmin UUID route",
                    "status": "active",
                    "save": "Save",
                },
                follow_redirects=False,
            )
            render_response = client.get(
                "/backoffice/agent-model/action/render-agent-config",
                params={"pks": str(ids["agent_id"])},
                headers={"referer": "http://testserver/backoffice/agent-model/list"},
            )
            delete_response = client.request(
                "DELETE",
                f"/backoffice/point-model/delete?pks={ids['point_id']}",
                headers={"referer": "http://testserver/backoffice/point-model/list"},
            )
            assets = client.get("/tenants/tenant-backoffice-uuid/assets").json()
            points = client.get(
                "/tenants/tenant-backoffice-uuid/assets/asset-a"
                "/agents/agent-a/sources/knx-main/points"
            ).json()
    finally:
        await _delete_uuid_backoffice_agent_graph(settings.database_url)

    assert edit_response.status_code == 302
    assert any(
        asset["asset_id"] == "asset-a" and asset["name"] == "Asset UUID Updated"
        for asset in assets
    )
    assert render_response.status_code == 200
    assert "Успешно обработано агентов: 1." in render_response.text
    assert "Создано записей в config_outbox: 2." in render_response.text
    assert delete_response.status_code == 200
    assert points == []


@pytest.mark.integration_smoke
def test_config_registry_persists_tenants_in_postgres(
    local_config_registry_postgres_stack,
) -> None:
    settings = ConfigRegistrySettings(
        database_url=local_config_registry_postgres_stack.database_url
    )

    with TestClient(create_app(settings=settings)) as client:
        create_response = client.post(
            "/tenants",
            json={"tenant_id": "tenant-a", "name": "Tenant A"},
        )
        duplicate_response = client.post(
            "/tenants",
            json={"tenant_id": "tenant-a", "name": "Tenant A"},
        )

    with TestClient(create_app(settings=settings)) as client:
        list_response = client.get("/tenants")

    assert create_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert list_response.status_code == 200
    assert [tenant["tenant_id"] for tenant in list_response.json()] == ["tenant-a"]


def test_config_registry_persists_assets_in_postgres(
    local_config_registry_postgres_stack,
) -> None:
    settings = ConfigRegistrySettings(
        database_url=local_config_registry_postgres_stack.database_url
    )

    with TestClient(create_app(settings=settings)) as client:
        client.post(
            "/tenants",
            json={"tenant_id": "tenant-assets", "name": "Tenant Assets"},
        )
        create_response = client.post(
            "/tenants/tenant-assets/assets",
            json={
                "asset_id": "asset-a",
                "name": "Asset A",
                "description": "Primary monitored asset",
            },
        )
        duplicate_response = client.post(
            "/tenants/tenant-assets/assets",
            json={"asset_id": "asset-a", "name": "Asset A"},
        )

    with TestClient(create_app(settings=settings)) as client:
        list_response = client.get("/tenants/tenant-assets/assets")

    assert create_response.status_code == 201
    assert create_response.json()["asset_id"] == "asset-a"
    assert create_response.json()["description"] == "Primary monitored asset"
    assert duplicate_response.status_code == 409
    assert list_response.status_code == 200
    assert [asset["asset_id"] for asset in list_response.json()] == ["asset-a"]


def test_config_registry_persists_agents_in_postgres(
    local_config_registry_postgres_stack,
) -> None:
    settings = ConfigRegistrySettings(
        database_url=local_config_registry_postgres_stack.database_url
    )

    with TestClient(create_app(settings=settings)) as client:
        client.post(
            "/tenants",
            json={"tenant_id": "tenant-agents", "name": "Tenant Agents"},
        )
        client.post(
            "/tenants/tenant-agents/assets",
            json={"asset_id": "asset-a", "name": "Asset A"},
        )
        create_response = client.post(
            "/tenants/tenant-agents/assets/asset-a/agents",
            json={
                "agent_id": "agent-a",
                "name": "Agent A",
                "bootstrap_hint_json": {"mqtt_profile": "local"},
            },
        )
        duplicate_response = client.post(
            "/tenants/tenant-agents/assets/asset-a/agents",
            json={"agent_id": "agent-a"},
        )

    with TestClient(create_app(settings=settings)) as client:
        list_response = client.get("/tenants/tenant-agents/assets/asset-a/agents")

    assert create_response.status_code == 201
    assert create_response.json()["agent_id"] == "agent-a"
    assert create_response.json()["bootstrap_hint_json"] == {"mqtt_profile": "local"}
    assert duplicate_response.status_code == 409
    assert list_response.status_code == 200
    assert [agent["agent_id"] for agent in list_response.json()] == ["agent-a"]


def test_config_registry_persists_sources_in_postgres(
    local_config_registry_postgres_stack,
) -> None:
    settings = ConfigRegistrySettings(
        database_url=local_config_registry_postgres_stack.database_url
    )

    with TestClient(create_app(settings=settings)) as client:
        client.post(
            "/tenants",
            json={"tenant_id": "tenant-sources", "name": "Tenant Sources"},
        )
        client.post(
            "/tenants/tenant-sources/assets",
            json={"asset_id": "asset-a", "name": "Asset A"},
        )
        client.post(
            "/tenants/tenant-sources/assets/asset-a/agents",
            json={"agent_id": "agent-a"},
        )
        create_response = client.post(
            "/tenants/tenant-sources/assets/asset-a/agents/agent-a/sources",
            json={
                "source_id": "knx-main",
                "source_type": "knx",
                "connection_json": {"gateway": "127.0.0.1"},
            },
        )
        duplicate_response = client.post(
            "/tenants/tenant-sources/assets/asset-a/agents/agent-a/sources",
            json={"source_id": "knx-main", "source_type": "knx"},
        )

    with TestClient(create_app(settings=settings)) as client:
        list_response = client.get(
            "/tenants/tenant-sources/assets/asset-a/agents/agent-a/sources"
        )

    assert create_response.status_code == 201
    assert create_response.json()["source_id"] == "knx-main"
    assert create_response.json()["connection_json"] == {"gateway": "127.0.0.1"}
    assert duplicate_response.status_code == 409
    assert list_response.status_code == 200
    assert [source["source_id"] for source in list_response.json()] == ["knx-main"]


def test_config_registry_persists_points_in_postgres(
    local_config_registry_postgres_stack,
) -> None:
    settings = ConfigRegistrySettings(
        database_url=local_config_registry_postgres_stack.database_url
    )

    with TestClient(create_app(settings=settings)) as client:
        client.post(
            "/tenants",
            json={"tenant_id": "tenant-points", "name": "Tenant Points"},
        )
        client.post(
            "/tenants/tenant-points/assets",
            json={"asset_id": "asset-a", "name": "Asset A"},
        )
        client.post(
            "/tenants/tenant-points/assets/asset-a/agents",
            json={"agent_id": "agent-a"},
        )
        client.post(
            "/tenants/tenant-points/assets/asset-a/agents/agent-a/sources",
            json={"source_id": "knx-main", "source_type": "knx"},
        )
        create_response = client.post(
            "/tenants/tenant-points/assets/asset-a/agents/agent-a"
            "/sources/knx-main/points",
            json={
                "point_id": "tenant-points|asset-a|knx-main|lights.main",
                "point_key": "lights.main",
                "point_ref": "1/1/1",
                "name": "Main Light",
                "value_type": "boolean",
                "value_model": "1.001",
                "signal_type": "feedback",
                "tags_json": {"room": "hall"},
            },
        )
        duplicate_response = client.post(
            "/tenants/tenant-points/assets/asset-a/agents/agent-a"
            "/sources/knx-main/points",
            json={
                "point_id": "tenant-points|asset-a|knx-main|lights.main",
                "point_key": "lights.secondary",
                "point_ref": "1/1/2",
                "name": "Secondary Light",
                "value_type": "boolean",
                "value_model": "1.001",
                "signal_type": "feedback",
            },
        )

    with TestClient(create_app(settings=settings)) as client:
        list_response = client.get(
            "/tenants/tenant-points/assets/asset-a/agents/agent-a"
            "/sources/knx-main/points"
        )

    assert create_response.status_code == 201
    assert create_response.json()["point_key"] == "lights.main"
    assert create_response.json()["tags_json"] == {"room": "hall"}
    assert duplicate_response.status_code == 409
    assert list_response.status_code == 200
    assert [point["point_key"] for point in list_response.json()] == ["lights.main"]


@pytest.mark.asyncio
async def test_config_registry_persists_and_reserves_outbox_records_in_postgres(
    local_config_registry_postgres_stack,
) -> None:
    settings = ConfigRegistrySettings(
        database_url=local_config_registry_postgres_stack.database_url
    )
    with TestClient(create_app(settings=settings)) as client:
        _create_renderable_agent_graph(client)

    unit_of_work_factory = PostgresUnitOfWorkFactory.from_url(settings.database_url)
    validator = JsonSchemaConfigPayloadValidator.from_contract_dir(CONTRACT_DIR)
    try:
        rendered = await RenderAgentRuntimeConfig(
            unit_of_work_factory(),
            validator,
        ).execute(
            RenderAgentRuntimeConfigCommand(
                tenant_id="tenant-outbox",
                asset_id="asset-a",
                agent_id="agent-a",
                config_revision="rev-outbox-001",
                issued_at=datetime(2026, 5, 3, 10, 0, tzinfo=UTC),
                source_config_revisions={"knx-main": "rev-outbox-001-knx-main"},
            )
        )
        await StoreRenderedAgentRuntimeConfig(
            unit_of_work_factory(), validator
        ).execute(rendered)

        now = datetime.now(tz=UTC) + timedelta(seconds=1)
        reserved = await ReserveConfigOutboxRecords(unit_of_work_factory()).execute(
            ReserveConfigOutboxCommand(
                limit=10,
                now=now,
                lease_duration=timedelta(seconds=30),
            )
        )
        published = await MarkConfigOutboxPublished(unit_of_work_factory()).execute(
            reserved[0].outbox_id, now=now + timedelta(seconds=5)
        )
        released = await ReleaseExpiredConfigOutboxLeases(
            unit_of_work_factory()
        ).execute(now=now + timedelta(seconds=31))
    finally:
        await unit_of_work_factory.dispose()

    assert [record.config_scope for record in reserved] == [
        "agent_runtime",
        "source:knx-main",
    ]
    assert all(record.status == ConfigOutboxStatus.INFLIGHT for record in reserved)
    assert published is not None
    assert published.status == ConfigOutboxStatus.PUBLISHED
    assert released == 1


def _create_renderable_agent_graph(client: TestClient) -> None:
    client.post(
        "/tenants",
        json={"tenant_id": "tenant-outbox", "name": "Tenant Outbox"},
    )
    client.post(
        "/tenants/tenant-outbox/assets",
        json={"asset_id": "asset-a", "name": "Asset A"},
    )
    client.post(
        "/tenants/tenant-outbox/assets/asset-a/agents",
        json={"agent_id": "agent-a"},
    )
    client.post(
        "/tenants/tenant-outbox/assets/asset-a/agents/agent-a/sources",
        json={
            "source_id": "knx-main",
            "source_type": "knx",
            "connection_json": {"gateway_ip": "127.0.0.1"},
            "acquisition_defaults_json": {
                "listen": True,
                "read_on_start": False,
                "periodic_interval_seconds": None,
            },
            "publish_defaults_json": {
                "enabled": True,
                "change_threshold": None,
            },
        },
    )
    client.post(
        "/tenants/tenant-outbox/assets/asset-a/agents/agent-a/sources/knx-main/points",
        json={
            "point_id": "tenant-outbox|asset-a|knx-main|temperature",
            "point_key": "temperature",
            "point_ref": "2/0/0",
            "name": "Temperature",
            "value_type": "number",
            "value_model": "knx.dpt.9.001",
            "signal_type": "sensor",
            "acquisition_json": {"read_on_start": True},
            "publish_json": {"change_threshold": 1.0},
            "tags_json": {"room": "demo"},
        },
    )


def _create_uuid_backoffice_agent_graph(client: TestClient) -> None:
    client.post(
        "/tenants",
        json={"tenant_id": "tenant-backoffice-uuid", "name": "Tenant Backoffice UUID"},
    )
    client.post(
        "/tenants/tenant-backoffice-uuid/assets",
        json={"asset_id": "asset-a", "name": "Asset A"},
    )
    client.post(
        "/tenants/tenant-backoffice-uuid/assets/asset-a/agents",
        json={"agent_id": "agent-a"},
    )
    client.post(
        "/tenants/tenant-backoffice-uuid/assets/asset-a/agents/agent-a/sources",
        json={
            "source_id": "knx-main",
            "source_type": "knx",
            "connection_json": {"host": "127.0.0.1", "port": 3671},
            "acquisition_defaults_json": {
                "listen": True,
                "read_on_start": False,
                "periodic_interval_seconds": None,
            },
            "publish_defaults_json": {
                "enabled": True,
                "change_threshold": None,
            },
        },
    )
    client.post(
        "/tenants/tenant-backoffice-uuid/assets/asset-a/agents/agent-a"
        "/sources/knx-main/points",
        json={
            "point_id": "tenant-backoffice-uuid|asset-a|knx-main|temperature",
            "point_key": "temperature",
            "point_ref": "2/0/0",
            "name": "Temperature",
            "value_type": "number",
            "value_model": "knx.dpt.9.001",
            "signal_type": "sensor",
            "acquisition_json": {"read_on_start": True},
            "publish_json": {"change_threshold": 1.0},
        },
    )


async def _uuid_backoffice_ids(database_url: str) -> dict[str, str]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            """
                        select a.id as asset_id,
                               ag.id as agent_id,
                               p.id as point_id
                        from tenants t
                        join assets a on a.tenant_id = t.id
                        join agents ag on ag.asset_id = a.id
                        join sources s on s.agent_id = ag.id
                        join points p on p.source_id = s.id
                        where t.code = 'tenant-backoffice-uuid'
                          and a.code = 'asset-a'
                          and ag.code = 'agent-a'
                          and s.code = 'knx-main'
                          and p.code = 'tenant-backoffice-uuid|asset-a|knx-main|temperature'
                        """
                        )
                    )
                )
                .mappings()
                .one()
            )
    finally:
        await engine.dispose()
    return {key: str(value) for key, value in row.items()}


async def _delete_uuid_backoffice_agent_graph(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    delete from config_outbox co
                    using tenants t
                    where co.tenant_id = t.id
                      and t.code = 'tenant-backoffice-uuid'
                    """
                )
            )
            await connection.execute(
                text(
                    """
                    delete from source_config_revisions scr
                    using tenants t
                    where scr.tenant_id = t.id
                      and t.code = 'tenant-backoffice-uuid'
                    """
                )
            )
            await connection.execute(
                text(
                    """
                    delete from agent_runtime_config_revisions acr
                    using tenants t
                    where acr.tenant_id = t.id
                      and t.code = 'tenant-backoffice-uuid'
                    """
                )
            )
            await connection.execute(
                text(
                    """
                    delete from points p
                    using tenants t
                    where p.tenant_id = t.id
                      and t.code = 'tenant-backoffice-uuid'
                    """
                )
            )
            await connection.execute(
                text(
                    """
                    delete from sources s
                    using tenants t
                    where s.tenant_id = t.id
                      and t.code = 'tenant-backoffice-uuid'
                    """
                )
            )
            await connection.execute(
                text(
                    """
                    delete from agents ag
                    using tenants t
                    where ag.tenant_id = t.id
                      and t.code = 'tenant-backoffice-uuid'
                    """
                )
            )
            await connection.execute(
                text(
                    """
                    delete from assets a
                    using tenants t
                    where a.tenant_id = t.id
                      and t.code = 'tenant-backoffice-uuid'
                    """
                )
            )
            await connection.execute(
                text("delete from tenants where code = 'tenant-backoffice-uuid'")
            )
    finally:
        await engine.dispose()
