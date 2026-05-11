from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from idp_config_registry.main import create_app
from idp_synthetic_config.config_registry_seeder import (
    ConfigRegistryConflict,
    ConfigRegistryError,
    ConfigRegistryNotFound,
    ConfigRegistrySeeder,
)
from idp_synthetic_config.generator import GeneratorOptions, generate_synthetic_config
from idp_synthetic_config.models import JsonObject
from idp_synthetic_config.reset import ResetPolicy


class _TestClientConfigRegistryApi:
    def __init__(self, client: TestClient) -> None:
        self._client = client

    def get_json(self, path: str) -> object:
        return self._request_json("GET", path)

    def post_json(self, path: str, payload: JsonObject) -> JsonObject:
        parsed = self._request_json("POST", path, payload)
        if not isinstance(parsed, dict):
            raise ConfigRegistryError(
                f"Config Registry response for {path} must be an object"
            )
        return parsed

    def delete_json(self, path: str) -> JsonObject:
        parsed = self._request_json("DELETE", path)
        if not isinstance(parsed, dict):
            raise ConfigRegistryError(
                f"Config Registry response for {path} must be an object"
            )
        return parsed

    def _request_json(
        self,
        method: str,
        path: str,
        payload: JsonObject | None = None,
    ) -> object:
        response = self._client.request(method, path, json=payload)
        response_text = response.text
        if response.status_code == 409:
            raise ConfigRegistryConflict(path=path, body=response_text)
        if response.status_code == 404:
            raise ConfigRegistryNotFound(path=path, body=response_text)
        if response.status_code >= 400:
            raise ConfigRegistryError(
                "Config Registry request failed: "
                f"method={method} path={path} status={response.status_code} "
                f"body={response_text}"
            )
        return response.json() if response.content else {}


def test_generator_seeds_and_deletes_generated_graph_through_config_registry_api() -> None:
    client = TestClient(create_app())
    api = _TestClientConfigRegistryApi(client)
    model = generate_synthetic_config(
        GeneratorOptions(seed=2, devices=1, tags_per_device=2)
    )
    point_path = (
        "/tenants/synthetic-tenant/assets/mall-synthetic-01"
        "/agents/edge-synthetic-01/sources/knx_synthetic/points"
    )

    seed_summary = ConfigRegistrySeeder(
        api,
        reset_policy=ResetPolicy(enabled=False),
    ).seed(
        model,
        config_registry_url="http://localhost:8000",
        config_revision="synthetic-acceptance",
        issued_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
    )

    points_after_seed = client.get(point_path)
    delete_summary = ConfigRegistrySeeder(api).delete_generated(
        model,
        config_registry_url="http://localhost:8000",
    )
    points_after_delete = client.get(point_path)
    tenants_after_delete = client.get("/tenants")

    assert seed_summary.ok is True
    assert points_after_seed.status_code == 200
    assert len(points_after_seed.json()) == 2
    assert delete_summary.ok is True
    assert delete_summary.reset.targets[0].records_affected == 10
    assert points_after_delete.status_code == 404
    assert tenants_after_delete.json() == []
