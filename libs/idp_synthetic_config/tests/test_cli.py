from __future__ import annotations

import io
import json

import idp_synthetic_config.cli as cli
from idp_synthetic_config.cli import main


class _DeleteClient:
    deleted: list[str] = []

    def __init__(self, base_url: str, *, timeout_seconds: float) -> None:
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    def get_json(self, path: str) -> object:
        return []

    def post_json(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        return {"status": "created", **payload}

    def delete_json(self, path: str) -> dict[str, object]:
        self.deleted.append(path)
        return {
            "config_outbox_records_deleted": 2,
            "source_config_revisions_deleted": 1,
            "agent_runtime_config_revisions_deleted": 1,
            "points_deleted": 2,
            "sources_deleted": 1,
            "agents_deleted": 1,
            "assets_deleted": 1,
            "tenants_deleted": 1,
        }


def test_plan_cli_prints_generated_model_as_json() -> None:
    stdout = io.StringIO()

    exit_code = main(
        ["plan", "--format", "json", "--seed", "5", "--devices", "1"],
        stdout=stdout,
    )

    payload = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert payload["tenant"]["tenant_id"] == "synthetic-tenant"
    assert len(payload["devices"]) == 1
    assert payload["sources"][0]["points"][0]["point_key"]


def test_plan_cli_prints_generated_model_as_yaml_without_side_effects() -> None:
    stdout = io.StringIO()

    exit_code = main(
        ["plan", "--format", "yaml", "--seed", "5", "--devices", "1"],
        stdout=stdout,
    )

    output = stdout.getvalue()
    assert exit_code == 0
    assert "tenant_id: synthetic-tenant" in output
    assert "sources:" in output


def test_delete_cli_calls_config_registry_delete_endpoint(monkeypatch) -> None:
    stdout = io.StringIO()
    _DeleteClient.deleted = []
    monkeypatch.setattr(cli, "ConfigRegistryHttpClient", _DeleteClient)

    exit_code = main(
        [
            "delete",
            "--format",
            "json",
            "--devices",
            "1",
            "--tags-per-device",
            "2",
            "--config-registry-url",
            "http://localhost:8000",
        ],
        stdout=stdout,
    )

    payload = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["counts"] == {"deleted": 1}
    assert _DeleteClient.deleted == [
        "/tenants/synthetic-tenant/assets/mall-synthetic-01"
        "/agents/edge-synthetic-01/registry-graph"
        "?delete_empty_asset=true&delete_empty_tenant=true"
    ]
