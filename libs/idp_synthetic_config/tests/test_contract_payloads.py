from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from idp_synthetic_config.generator import GeneratorOptions, generate_synthetic_config

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = REPO_ROOT / "docs" / "contracts" / "edge-telemetry-agent" / "schemas"


def test_generated_payloads_match_existing_edge_config_contract_shapes() -> None:
    model = generate_synthetic_config(
        GeneratorOptions(seed=31, devices=2, tags_per_device=10)
    )
    config_revision = "synthetic-contract"
    issued_at = "2026-05-10T12:00:00Z"
    source_revisions = model.source_config_revisions(config_revision)

    agent_runtime_payload = model.agent_runtime_payload(
        config_revision=config_revision,
        issued_at=issued_at,
        source_config_revisions=source_revisions,
    )
    source_payloads = model.source_config_payloads(
        config_revision=config_revision,
        source_config_revisions=source_revisions,
    )

    _validate_json_schema_subset(
        agent_runtime_payload,
        _load_schema("idp.edge.agent-runtime-config.v1.schema.json"),
    )
    for payload in source_payloads:
        _validate_json_schema_subset(
            payload,
            _load_schema("idp.edge.source-config.v1.schema.json"),
        )


def _load_schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


def _validate_json_schema_subset(value: Any, schema: dict[str, Any]) -> None:
    _validate_node(value, schema, root=schema, path="$")


def _validate_node(
    value: Any,
    schema: dict[str, Any],
    *,
    root: dict[str, Any],
    path: str,
) -> None:
    if "$ref" in schema:
        ref = schema["$ref"]
        assert isinstance(ref, str) and ref.startswith("#/$defs/")
        _validate_node(value, root["$defs"][ref.removeprefix("#/$defs/")], root=root, path=path)
        return

    if "const" in schema:
        assert value == schema["const"], path
    if "enum" in schema:
        assert value in schema["enum"], path

    declared_type = schema.get("type")
    if declared_type is not None:
        allowed_types = (
            [declared_type] if isinstance(declared_type, str) else declared_type
        )
        assert _matches_json_type(value, allowed_types), path

    if isinstance(value, str):
        if "minLength" in schema:
            assert len(value) >= schema["minLength"], path
        if "pattern" in schema:
            assert re.fullmatch(schema["pattern"], value), path

    if isinstance(value, int | float) and not isinstance(value, bool):
        if "minimum" in schema:
            assert value >= schema["minimum"], path
        if "exclusiveMinimum" in schema:
            assert value > schema["exclusiveMinimum"], path

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            assert key in value, f"{path}.{key}"
        if schema.get("additionalProperties") is False:
            assert set(value).issubset(set(schema.get("properties", {}))), path
        properties = schema.get("properties", {})
        for key, item in value.items():
            if key in properties:
                _validate_node(item, properties[key], root=root, path=f"{path}.{key}")
            elif isinstance(schema.get("additionalProperties"), dict):
                _validate_node(
                    item,
                    schema["additionalProperties"],
                    root=root,
                    path=f"{path}.{key}",
                )

    if isinstance(value, list):
        if "minItems" in schema:
            assert len(value) >= schema["minItems"], path
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                _validate_node(item, item_schema, root=root, path=f"{path}[{index}]")


def _matches_json_type(value: Any, allowed_types: list[str]) -> bool:
    return any(
        (json_type == "null" and value is None)
        or (json_type == "object" and isinstance(value, dict))
        or (json_type == "array" and isinstance(value, list))
        or (json_type == "string" and isinstance(value, str))
        or (json_type == "boolean" and isinstance(value, bool))
        or (
            json_type == "number"
            and isinstance(value, int | float)
            and not isinstance(value, bool)
        )
        for json_type in allowed_types
    )

