from __future__ import annotations

import json

from knx_source_emulator.cli import main


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
