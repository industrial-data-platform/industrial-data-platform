from __future__ import annotations

import json

from knx_source_emulator.protocol import (
    EmulatorEvent,
    WriteCommand,
    encode_json_line,
    parse_write_command,
    write_ack_payload,
    write_error_payload,
)


def test_tcp_event_payload_has_versioned_message_type() -> None:
    event = EmulatorEvent(
        source_id="knx_synthetic",
        point_ref="1/0/1",
        point_key="1%2F0%2F1",
        observation_mode="periodic_read",
        value=23.5,
        value_raw="23.5",
        quality="good",
        ts="2026-05-11T07:00:00Z",
        name="Температура воздуха: Фудкорт, этаж 2",
        description="Контроль температуры воздуха.",
        signal_type="sensor",
        value_model="knx.dpt.9.001",
        unit="C",
        tags={"zone": "Фудкорт"},
    )

    payload = event.to_payload()
    line = encode_json_line(payload)

    assert payload["message_type"] == "knx_source_emulator.event.v1"
    assert line.endswith(b"\n")
    assert json.loads(line)["point_ref"] == "1/0/1"


def test_write_command_parses_point_ref_or_point_key_and_acknowledges() -> None:
    command = parse_write_command(
        {
            "message_type": "knx_source_emulator.write.v1",
            "source_id": "knx_synthetic",
            "point_key": "1%2F0%2F4",
            "value": True,
            "request_id": "req-1",
        }
    )

    assert command == WriteCommand(
        source_id="knx_synthetic",
        point_ref=None,
        point_key="1%2F0%2F4",
        value=True,
        request_id="req-1",
    )
    assert write_ack_payload(command)["message_type"] == "knx_source_emulator.write_ack.v1"
    assert write_ack_payload(command)["request_id"] == "req-1"


def test_invalid_write_payload_returns_versioned_error() -> None:
    error = write_error_payload(
        source_id="knx_synthetic",
        request_id="req-2",
        reason="point is not writable",
    )

    assert error == {
        "message_type": "knx_source_emulator.error.v1",
        "source_id": "knx_synthetic",
        "request_id": "req-2",
        "reason": "point is not writable",
    }
