from __future__ import annotations

from fastapi.testclient import TestClient

from idp_asset_graph_registry.infrastructure.registry_lookup import (
    InMemoryRegistryReferenceLookup,
)
from idp_asset_graph_registry.main import create_app


def _client() -> TestClient:
    registry_lookup = InMemoryRegistryReferenceLookup(
        tenants={"tenant-a"},
        assets={("tenant-a", "asset-a")},
        agents={("tenant-a", "asset-a", "agent-a")},
        sources={("tenant-a", "asset-a", "agent-a", "source-a")},
        points={("tenant-a", "point-a")},
    )
    return TestClient(create_app(registry_lookup=registry_lookup))


def test_health_and_ready_endpoints() -> None:
    client = _client()

    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json() == {"status": "ready"}


def test_relation_vocabulary_is_adr_016_v1_set() -> None:
    client = _client()

    response = client.get("/internal/vocabulary/relation-types")

    assert response.status_code == 200
    assert response.json() == [
        "partOf",
        "locatedIn",
        "hasPoint",
        "feeds",
        "measures",
        "controls",
    ]


def test_create_asset_graph_node_attribute_and_binding() -> None:
    client = _client()

    node_response = client.post(
        "/internal/tenants/tenant-a/asset-graph/nodes",
        json={
            "asset_graph_node_code": "ahu-1",
            "display_name": "AHU 1",
            "object_type": "machine",
        },
    )
    attribute_response = client.post(
        "/internal/tenants/tenant-a/asset-graph/nodes/ahu-1/attributes",
        json={"attribute_key": "temperature", "value_type": "number", "unit": "degC"},
    )
    binding_response = client.post(
        "/internal/tenants/tenant-a/asset-graph/telemetry-bindings",
        json={
            "binding_code": "ahu-1-temperature",
            "point_code": "point-a",
            "asset_graph_node_code": "ahu-1",
            "attribute_key": "temperature",
        },
    )

    assert node_response.status_code == 201
    assert node_response.json()["asset_graph_node_code"] == "ahu-1"
    assert attribute_response.status_code == 201
    assert attribute_response.json()["attribute_key"] == "temperature"
    assert binding_response.status_code == 201
    assert binding_response.json()["reference_status"] == "valid"


def test_asset_graph_node_and_attribute_crud_with_delete_guards() -> None:
    client = _client()
    client.post(
        "/internal/tenants/tenant-a/asset-graph/nodes",
        json={
            "asset_graph_node_code": "ahu-1",
            "display_name": "AHU 1",
            "object_type": "machine",
        },
    )
    client.post(
        "/internal/tenants/tenant-a/asset-graph/nodes/ahu-1/attributes",
        json={"attribute_key": "temperature", "value_type": "number", "unit": "degC"},
    )
    client.post(
        "/internal/tenants/tenant-a/asset-graph/telemetry-bindings",
        json={
            "binding_code": "ahu-1-temperature",
            "point_code": "point-a",
            "asset_graph_node_code": "ahu-1",
            "attribute_key": "temperature",
        },
    )

    updated_node = client.patch(
        "/internal/tenants/tenant-a/asset-graph/nodes/ahu-1",
        json={
            "display_name": "AHU Supply",
            "object_type": "equipment",
            "metadata_json": {"area": "north"},
        },
    )
    updated_attribute = client.patch(
        "/internal/tenants/tenant-a/asset-graph/nodes/ahu-1/attributes/temperature",
        json={
            "value_type": "number",
            "unit": "K",
            "metadata_json": {"source": "manual"},
        },
    )
    guarded_attribute_delete = client.delete(
        "/internal/tenants/tenant-a/asset-graph/nodes/ahu-1/attributes/temperature"
    )
    guarded_node_delete = client.delete(
        "/internal/tenants/tenant-a/asset-graph/nodes/ahu-1"
    )
    client.delete(
        "/internal/tenants/tenant-a/asset-graph/telemetry-bindings/ahu-1-temperature"
    )
    attribute_delete = client.delete(
        "/internal/tenants/tenant-a/asset-graph/nodes/ahu-1/attributes/temperature"
    )
    node_delete = client.delete("/internal/tenants/tenant-a/asset-graph/nodes/ahu-1")
    missing_node = client.get("/internal/tenants/tenant-a/asset-graph/nodes/ahu-1")

    assert updated_node.status_code == 200
    assert updated_node.json()["display_name"] == "AHU Supply"
    assert updated_node.json()["metadata_json"] == {"area": "north"}
    assert updated_attribute.status_code == 200
    assert updated_attribute.json()["unit"] == "K"
    assert guarded_attribute_delete.status_code == 422
    assert guarded_node_delete.status_code == 422
    assert attribute_delete.status_code == 204
    assert node_delete.status_code == 204
    assert missing_node.status_code == 404


def test_create_asset_graph_node_rejects_missing_tenant_reference() -> None:
    client = TestClient(create_app(registry_lookup=InMemoryRegistryReferenceLookup()))

    response = client.post(
        "/internal/tenants/tenant-a/asset-graph/nodes",
        json={
            "asset_graph_node_code": "ahu-1",
            "display_name": "AHU 1",
            "object_type": "machine",
        },
    )

    assert response.status_code == 404


def test_catalog_tree_supports_create_move_read_and_delete_leaf() -> None:
    client = _client()
    root_response = client.post(
        "/internal/tenants/tenant-a/catalog/default/nodes",
        json={
            "node_code": "root",
            "node_type": "folder",
            "display_name": "Root",
        },
    )
    child_response = client.post(
        "/internal/tenants/tenant-a/catalog/default/nodes",
        json={
            "node_code": "child",
            "parent_node_code": "root",
            "node_type": "asset_ref",
            "display_name": "Asset A",
            "target": {"asset_code": "asset-a"},
        },
    )
    move_response = client.post(
        "/internal/tenants/tenant-a/catalog/default/nodes/child/move",
        json={"parent_node_code": None, "sort_order": 1},
    )
    tree_response = client.get("/internal/tenants/tenant-a/catalog/default/tree")
    delete_response = client.delete(
        "/internal/tenants/tenant-a/catalog/default/nodes/child"
    )

    assert root_response.status_code == 201
    assert child_response.status_code == 201
    assert child_response.json()["reference_status"] == "valid"
    assert move_response.status_code == 200
    assert move_response.json()["parent_node_code"] is None
    assert [node["node_code"] for node in tree_response.json()["nodes"]] == [
        "root",
        "child",
    ]
    assert delete_response.status_code == 204


def test_catalog_node_rejects_missing_registry_reference() -> None:
    client = _client()

    response = client.post(
        "/internal/tenants/tenant-a/catalog/default/nodes",
        json={
            "node_code": "missing-point",
            "node_type": "registry_point_ref",
            "display_name": "Missing Point",
            "target": {"point_code": "missing-point"},
        },
    )

    assert response.status_code == 422


def test_catalog_move_rejects_cycles_and_delete_rejects_non_leaf() -> None:
    client = _client()
    client.post(
        "/internal/tenants/tenant-a/catalog/default/nodes",
        json={"node_code": "root", "node_type": "folder", "display_name": "Root"},
    )
    client.post(
        "/internal/tenants/tenant-a/catalog/default/nodes",
        json={
            "node_code": "child",
            "parent_node_code": "root",
            "node_type": "folder",
            "display_name": "Child",
        },
    )
    client.post(
        "/internal/tenants/tenant-a/catalog/default/nodes",
        json={
            "node_code": "grandchild",
            "parent_node_code": "child",
            "node_type": "folder",
            "display_name": "Grandchild",
        },
    )

    cycle_response = client.post(
        "/internal/tenants/tenant-a/catalog/default/nodes/root/move",
        json={"parent_node_code": "grandchild"},
    )
    delete_response = client.delete(
        "/internal/tenants/tenant-a/catalog/default/nodes/root"
    )

    assert cycle_response.status_code == 422
    assert delete_response.status_code == 422


def test_relationship_requires_existing_nodes() -> None:
    client = _client()
    client.post(
        "/internal/tenants/tenant-a/asset-graph/nodes",
        json={
            "asset_graph_node_code": "site-a",
            "display_name": "Site A",
            "object_type": "site",
        },
    )
    client.post(
        "/internal/tenants/tenant-a/asset-graph/nodes",
        json={
            "asset_graph_node_code": "ahu-1",
            "display_name": "AHU 1",
            "object_type": "machine",
        },
    )

    response = client.post(
        "/internal/tenants/tenant-a/asset-graph/relationships",
        json={
            "relationship_code": "ahu-1-part-of-site-a",
            "source_asset_graph_node_code": "ahu-1",
            "target_asset_graph_node_code": "site-a",
            "relation_type": "partOf",
        },
    )

    assert response.status_code == 201
    assert response.json()["relation_type"] == "partOf"


def test_relationship_and_binding_crud() -> None:
    client = _client()
    for node_code, object_type in [("site-a", "site"), ("ahu-1", "machine")]:
        client.post(
            "/internal/tenants/tenant-a/asset-graph/nodes",
            json={
                "asset_graph_node_code": node_code,
                "display_name": node_code,
                "object_type": object_type,
            },
        )
    client.post(
        "/internal/tenants/tenant-a/asset-graph/nodes/ahu-1/attributes",
        json={"attribute_key": "temperature", "value_type": "number", "unit": "degC"},
    )
    client.post(
        "/internal/tenants/tenant-a/asset-graph/relationships",
        json={
            "relationship_code": "ahu-1-part-of-site-a",
            "source_asset_graph_node_code": "ahu-1",
            "target_asset_graph_node_code": "site-a",
            "relation_type": "partOf",
        },
    )
    client.post(
        "/internal/tenants/tenant-a/asset-graph/telemetry-bindings",
        json={
            "binding_code": "ahu-1-temperature",
            "point_code": "point-a",
            "asset_graph_node_code": "ahu-1",
            "attribute_key": "temperature",
        },
    )

    relationship_get = client.get(
        "/internal/tenants/tenant-a/asset-graph/relationships/ahu-1-part-of-site-a"
    )
    relationship_update = client.patch(
        "/internal/tenants/tenant-a/asset-graph/relationships/ahu-1-part-of-site-a",
        json={
            "source_asset_graph_node_code": "site-a",
            "target_asset_graph_node_code": "ahu-1",
            "relation_type": "locatedIn",
            "metadata_json": {"verified": True},
        },
    )
    binding_get = client.get(
        "/internal/tenants/tenant-a/asset-graph/telemetry-bindings/ahu-1-temperature"
    )
    binding_update = client.patch(
        "/internal/tenants/tenant-a/asset-graph/telemetry-bindings/ahu-1-temperature",
        json={
            "point_code": "point-a",
            "asset_graph_node_code": "ahu-1",
            "attribute_key": "temperature",
            "metadata_json": {"consumer": "monitoring"},
        },
    )
    relationship_delete = client.delete(
        "/internal/tenants/tenant-a/asset-graph/relationships/ahu-1-part-of-site-a"
    )
    binding_delete = client.delete(
        "/internal/tenants/tenant-a/asset-graph/telemetry-bindings/ahu-1-temperature"
    )

    assert relationship_get.status_code == 200
    assert relationship_update.status_code == 200
    assert relationship_update.json()["relation_type"] == "locatedIn"
    assert relationship_update.json()["metadata_json"] == {"verified": True}
    assert binding_get.status_code == 200
    assert binding_update.status_code == 200
    assert binding_update.json()["metadata_json"] == {"consumer": "monitoring"}
    assert relationship_delete.status_code == 204
    assert binding_delete.status_code == 204
