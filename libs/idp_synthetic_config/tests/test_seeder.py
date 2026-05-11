from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import unquote

import pytest

from idp_synthetic_config.config_registry_seeder import (
    ConfigRegistryConflict,
    ConfigRegistrySeeder,
)
from idp_synthetic_config.generator import GeneratorOptions, generate_synthetic_config
from idp_synthetic_config.reset import ResetPolicy


class FakeConfigRegistryApi:
    def __init__(self) -> None:
        self.records: dict[str, list[dict[str, Any]]] = {}
        self.posted: list[tuple[str, dict[str, Any]]] = []
        self.deleted: list[str] = []
        self.conflict_paths: set[str] = set()

    def get_json(self, path: str) -> object:
        return self.records.get(path, [])

    def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.posted.append((path, payload))
        if path in self.conflict_paths:
            raise ConfigRegistryConflict(path=path, body="duplicate")
        return {"status": "created", **payload}

    def delete_json(self, path: str) -> dict[str, Any]:
        self.deleted.append(path)
        graph_path, _, _ = path.partition("?")
        if graph_path.endswith("/registry-graph"):
            prefix = graph_path[: -len("/registry-graph")]
            deleted_points = 0
            for record_path in tuple(self.records):
                if record_path.startswith(f"{prefix}/sources/") and record_path.endswith(
                    "/points"
                ):
                    deleted_points += len(self.records[record_path])
                    self.records[record_path] = []
            return {
                "tenant_id": "synthetic-tenant",
                "asset_id": "mall-synthetic-01",
                "agent_id": "edge-synthetic-01",
                "config_outbox_records_deleted": 2,
                "source_config_revisions_deleted": 1,
                "agent_runtime_config_revisions_deleted": 1,
                "points_deleted": deleted_points,
                "sources_deleted": 1,
                "agents_deleted": 1,
                "assets_deleted": 1,
                "tenants_deleted": 1,
            }
        list_path, _, raw_point_id = path.rpartition("/")
        point_id = unquote(raw_point_id)
        self.records[list_path] = [
            item
            for item in self.records.get(list_path, [])
            if item.get("point_id") != point_id
        ]
        return {"status": "deleted", "path": path}


def test_seeder_posts_registry_records_and_render_request() -> None:
    model = generate_synthetic_config(
        GeneratorOptions(seed=2, devices=1, tags_per_device=4)
    )
    client = FakeConfigRegistryApi()
    seeder = ConfigRegistrySeeder(client, reset_policy=ResetPolicy(enabled=False))

    summary = seeder.seed(
        model,
        config_registry_url="http://localhost:8000",
        config_revision="synthetic-test",
        issued_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
    )

    assert summary.ok is True
    assert summary.counts["created"] == 9
    render_path, render_payload = client.posted[-1]
    assert render_path.endswith("/render-config")
    assert render_payload["config_revision"] == "synthetic-test"
    assert render_payload["issued_at"] == "2026-05-10T12:00:00Z"
    assert render_payload["source_config_revisions"] == {
        "knx_synthetic": "synthetic-test-knx_synthetic"
    }


def test_seeder_treats_matching_conflicts_as_exists() -> None:
    model = generate_synthetic_config(
        GeneratorOptions(seed=2, devices=1, tags_per_device=1)
    )
    client = FakeConfigRegistryApi()
    client.conflict_paths = {"/tenants"}
    client.records["/tenants"] = [model.tenant.to_create_payload()]

    summary = ConfigRegistrySeeder(
        client,
        reset_policy=ResetPolicy(enabled=False),
    ).seed(
        model,
        config_registry_url="http://localhost:8000",
        config_revision="synthetic-test",
        issued_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
    )

    assert summary.ok is True
    assert summary.counts["exists"] == 1


def test_seeder_reports_drift_for_conflicting_existing_payload() -> None:
    model = generate_synthetic_config(
        GeneratorOptions(seed=2, devices=1, tags_per_device=1)
    )
    client = FakeConfigRegistryApi()
    client.conflict_paths = {"/tenants"}
    client.records["/tenants"] = [
        {**model.tenant.to_create_payload(), "name": "Другой tenant"}
    ]

    summary = ConfigRegistrySeeder(
        client,
        reset_policy=ResetPolicy(enabled=False),
    ).seed(
        model,
        config_registry_url="http://localhost:8000",
        config_revision="synthetic-test",
        issued_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
    )

    assert summary.ok is False
    assert summary.counts["drift"] == 1
    assert not any(path.endswith("/render-config") for path, _ in client.posted)


def test_render_conflict_is_not_silently_accepted() -> None:
    model = generate_synthetic_config(
        GeneratorOptions(seed=2, devices=1, tags_per_device=1)
    )
    client = FakeConfigRegistryApi()
    render_path = (
        "/tenants/synthetic-tenant/assets/mall-synthetic-01"
        "/agents/edge-synthetic-01/render-config"
    )
    client.conflict_paths = {render_path}

    summary = ConfigRegistrySeeder(
        client,
        reset_policy=ResetPolicy(enabled=False),
    ).seed(
        model,
        config_registry_url="http://localhost:8000",
        config_revision="synthetic-test",
        issued_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
    )

    assert summary.ok is False
    assert summary.counts["drift"] == 1
    assert "cannot verify" in summary.entries[-1].detail

    with pytest.raises(ConfigRegistryConflict):
        raise ConfigRegistryConflict(path=render_path, body="duplicate")


def test_default_reset_deletes_existing_generated_graph_before_seed() -> None:
    model = generate_synthetic_config(
        GeneratorOptions(seed=2, devices=1, tags_per_device=1)
    )
    client = FakeConfigRegistryApi()
    point_path = (
        "/tenants/synthetic-tenant/assets/mall-synthetic-01"
        "/agents/edge-synthetic-01/sources/knx_synthetic/points"
    )
    client.records[point_path] = [
        model.sources[0].points[0].to_create_payload(),
        {
            **model.sources[0].points[0].to_create_payload(),
            "point_id": "synthetic-tenant|mall-synthetic-01|knx_synthetic|stale",
        },
    ]

    summary = ConfigRegistrySeeder(client).seed(
        model,
        config_registry_url="http://localhost:8000",
        config_revision="synthetic-test",
        issued_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
    )

    config_registry_reset = next(
        target for target in summary.reset.targets if target.name == "config_registry"
    )
    assert summary.ok is True
    assert client.deleted == [
        "/tenants/synthetic-tenant/assets/mall-synthetic-01"
        "/agents/edge-synthetic-01/registry-graph"
        "?delete_empty_asset=true&delete_empty_tenant=true"
    ]
    assert config_registry_reset.status == "cleared"
    assert config_registry_reset.records_affected == 10
