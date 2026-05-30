from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import text

from idp_asset_graph_registry.infrastructure.postgres.database import create_engine

pytestmark = pytest.mark.integration


def test_asset_graph_registry_persists_graph_and_binding_through_postgres(
    local_asset_graph_registry_stack,
) -> None:
    tenant_code = "tenant-asset-graph-it"
    point_code = f"{tenant_code}|asset-a|knx-main|temperature"
    _seed_config_registry(local_asset_graph_registry_stack, tenant_code, point_code)

    node = local_asset_graph_registry_stack.asset_graph_json(
        "POST",
        f"/internal/tenants/{tenant_code}/asset-graph/nodes",
        {
            "asset_graph_node_code": "ahu-1",
            "display_name": "AHU 1",
            "object_type": "equipment",
        },
    )
    attribute = local_asset_graph_registry_stack.asset_graph_json(
        "POST",
        f"/internal/tenants/{tenant_code}/asset-graph/nodes/ahu-1/attributes",
        {
            "attribute_key": "supply_temperature",
            "value_type": "number",
            "unit": "degC",
        },
    )
    catalog_node = local_asset_graph_registry_stack.asset_graph_json(
        "POST",
        f"/internal/tenants/{tenant_code}/catalog/default/nodes",
        {
            "node_code": "root",
            "node_type": "folder",
            "display_name": "Root",
        },
    )
    binding = local_asset_graph_registry_stack.asset_graph_json(
        "POST",
        f"/internal/tenants/{tenant_code}/asset-graph/telemetry-bindings",
        {
            "binding_code": "ahu-1-supply-temperature",
            "point_code": point_code,
            "asset_graph_node_code": "ahu-1",
            "attribute_key": "supply_temperature",
        },
    )
    counts = asyncio.run(
        _asset_graph_counts(
            local_asset_graph_registry_stack.database_url,
            tenant_code,
        )
    )

    assert node["asset_graph_node_code"] == "ahu-1"
    assert attribute["attribute_key"] == "supply_temperature"
    assert catalog_node["reference_status"] == "unknown"
    assert binding["reference_status"] == "valid"
    assert binding["display_snapshot_json"] == {
        "tenant_code": tenant_code,
        "point_code": point_code,
    }
    assert counts == {
        "asset_graph_nodes": 1,
        "asset_graph_node_attributes": 1,
        "asset_graph_telemetry_bindings": 1,
        "catalog_nodes": 1,
    }


def test_catalog_folder_rejects_missing_tenant_and_does_not_persist(
    local_asset_graph_registry_stack,
) -> None:
    tenant_code = "missing-tenant-it"

    status_code, payload = local_asset_graph_registry_stack.asset_graph_response(
        "POST",
        f"/internal/tenants/{tenant_code}/catalog/default/nodes",
        {
            "node_code": "root",
            "node_type": "folder",
            "display_name": "Root",
        },
    )
    node_count = asyncio.run(
        _catalog_node_count(
            local_asset_graph_registry_stack.database_url,
            tenant_code,
        )
    )

    assert status_code == 404
    assert "tenant" in str(payload["detail"])
    assert node_count == 0


def test_telemetry_binding_rejects_missing_config_registry_point(
    local_asset_graph_registry_stack,
) -> None:
    tenant_code = "tenant-missing-point-it"
    point_code = f"{tenant_code}|asset-a|knx-main|temperature"
    _seed_config_registry(local_asset_graph_registry_stack, tenant_code, point_code)
    local_asset_graph_registry_stack.asset_graph_json(
        "POST",
        f"/internal/tenants/{tenant_code}/asset-graph/nodes",
        {
            "asset_graph_node_code": "ahu-1",
            "display_name": "AHU 1",
            "object_type": "equipment",
        },
    )
    local_asset_graph_registry_stack.asset_graph_json(
        "POST",
        f"/internal/tenants/{tenant_code}/asset-graph/nodes/ahu-1/attributes",
        {
            "attribute_key": "supply_temperature",
            "value_type": "number",
            "unit": "degC",
        },
    )

    status_code, payload = local_asset_graph_registry_stack.asset_graph_response(
        "POST",
        f"/internal/tenants/{tenant_code}/asset-graph/telemetry-bindings",
        {
            "binding_code": "ahu-1-missing-point",
            "point_code": f"{tenant_code}|asset-a|knx-main|missing",
            "asset_graph_node_code": "ahu-1",
            "attribute_key": "supply_temperature",
        },
    )

    assert status_code == 404
    assert "point" in str(payload["detail"])


def test_config_registry_lookup_unavailability_returns_503(
    local_asset_graph_registry_stack,
) -> None:
    try:
        local_asset_graph_registry_stack.compose(
            "stop",
            "idp-config-registry",
            timeout=120,
        )
        status_code, payload = local_asset_graph_registry_stack.asset_graph_response(
            "POST",
            "/internal/tenants/tenant-dependency-down/catalog/default/nodes",
            {
                "node_code": "root",
                "node_type": "folder",
                "display_name": "Root",
            },
            timeout=15,
        )
    finally:
        local_asset_graph_registry_stack.compose(
            "start",
            "idp-config-registry",
            timeout=120,
        )
        local_asset_graph_registry_stack.wait_for_config_registry_api()

    assert status_code == 503
    assert "lookup is unavailable" in str(payload["detail"])


def _seed_config_registry(stack, tenant_code: str, point_code: str) -> None:
    stack.config_registry_json(
        "POST",
        "/tenants",
        {"tenant_code": tenant_code, "name": "Tenant IT"},
    )
    stack.config_registry_json(
        "POST",
        f"/tenants/{tenant_code}/assets",
        {"asset_code": "asset-a", "name": "Asset A"},
    )
    stack.config_registry_json(
        "POST",
        f"/tenants/{tenant_code}/assets/asset-a/agents",
        {"agent_code": "agent-a", "name": "Agent A"},
    )
    stack.config_registry_json(
        "POST",
        f"/tenants/{tenant_code}/assets/asset-a/agents/agent-a/sources",
        {
            "source_code": "knx-main",
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
    stack.config_registry_json(
        "POST",
        f"/tenants/{tenant_code}/assets/asset-a/agents/agent-a"
        "/sources/knx-main/points",
        {
            "point_code": point_code,
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


async def _asset_graph_counts(
    database_url: str,
    tenant_code: str,
) -> dict[str, int]:
    tables = (
        "asset_graph_nodes",
        "asset_graph_node_attributes",
        "asset_graph_telemetry_bindings",
        "catalog_nodes",
    )
    engine = create_engine(database_url)
    try:
        async with engine.connect() as connection:
            return {
                table: await _count_rows(connection, table, tenant_code)
                for table in tables
            }
    finally:
        await engine.dispose()


async def _catalog_node_count(database_url: str, tenant_code: str) -> int:
    engine = create_engine(database_url)
    try:
        async with engine.connect() as connection:
            return await _count_rows(connection, "catalog_nodes", tenant_code)
    finally:
        await engine.dispose()


async def _count_rows(connection: object, table_name: str, tenant_code: str) -> int:
    result = await connection.execute(
        text(f"select count(*) from {table_name} where tenant_code = :tenant_code"),
        {"tenant_code": tenant_code},
    )
    return int(result.scalar_one())
