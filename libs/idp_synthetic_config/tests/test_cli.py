from __future__ import annotations

import io
import json

from idp_synthetic_config.cli import main


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

