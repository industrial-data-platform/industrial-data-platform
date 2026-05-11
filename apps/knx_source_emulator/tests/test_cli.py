from __future__ import annotations

import json
from argparse import Namespace

from idp_synthetic_config.generator import GeneratorOptions, generate_synthetic_config
from knx_source_emulator.cli import (
    _model_with_endpoint,
    _runtime_duration_seconds,
    main,
)


def test_plan_dry_run_outputs_json_summary(capsys) -> None:
    exit_code = main(
        [
            "plan",
            "--dry-run",
            "--devices",
            "1",
            "--tags-per-device",
            "4",
            "--seed",
            "123",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["source_id"] == "knx_synthetic"
    assert payload["stats"]["devices"] == 1
    assert payload["stats"]["points"] == 4
    assert "Периодический опрос" in payload["points"][0]["description"]


def test_run_command_starts_and_stops_with_duration(capsys) -> None:
    exit_code = main(
        [
            "run",
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--devices",
            "1",
            "--tags-per-device",
            "1",
            "--duration-seconds",
            "0.01",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["devices"] == 1
    assert payload["points"] == 1
    assert "events_sent" in payload
    assert payload["host"] == "127.0.0.1"
    assert isinstance(payload["port"], int)


def test_runtime_duration_accepts_explicit_forever() -> None:
    duration = _runtime_duration_seconds(
        Namespace(forever=True, duration_seconds=None)
    )

    assert duration is None


def test_run_command_rejects_forever_with_duration(capsys) -> None:
    exit_code = main(["run", "--forever", "--duration-seconds", "0.01"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "--forever cannot be combined with --duration-seconds" in captured.err


def test_seed_config_rejects_unbound_port(capsys) -> None:
    exit_code = main(["seed-config", "--port", "0"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "concrete --port" in captured.err


def test_seed_config_model_uses_bound_emulator_endpoint() -> None:
    model = generate_synthetic_config(
        GeneratorOptions(devices=1, tags_per_device=1, seed=123)
    )

    updated = _model_with_endpoint(model, host="127.0.0.1", port=45678)

    connection = updated.sources[0].connection_json
    assert connection["host"] == "127.0.0.1"
    assert connection["port"] == 45678
    assert connection["gateway_ip"] == "127.0.0.1"
    assert connection["gateway_port"] == 45678
