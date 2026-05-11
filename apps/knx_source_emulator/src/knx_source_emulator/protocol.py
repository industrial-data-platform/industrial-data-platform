from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

JsonObject = dict[str, Any]
EVENT_MESSAGE_TYPE = "knx_source_emulator.event.v1"
WRITE_MESSAGE_TYPE = "knx_source_emulator.write.v1"
WRITE_ACK_MESSAGE_TYPE = "knx_source_emulator.write_ack.v1"
ERROR_MESSAGE_TYPE = "knx_source_emulator.error.v1"


@dataclass(frozen=True)
class EmulatorEvent:
    source_id: str
    point_ref: str
    point_key: str
    observation_mode: str
    value: object
    value_raw: str
    quality: str
    ts: str
    name: str
    description: str | None
    signal_type: str
    value_model: str
    unit: str | None
    tags: dict[str, str]

    def to_payload(self) -> JsonObject:
        return {
            "message_type": EVENT_MESSAGE_TYPE,
            "source_id": self.source_id,
            "point_ref": self.point_ref,
            "point_key": self.point_key,
            "observation_mode": self.observation_mode,
            "value": self.value,
            "value_raw": self.value_raw,
            "quality": self.quality,
            "ts": self.ts,
            "name": self.name,
            "description": self.description,
            "signal_type": self.signal_type,
            "value_model": self.value_model,
            "unit": self.unit,
            "tags": dict(self.tags),
        }


@dataclass(frozen=True)
class WriteCommand:
    source_id: str
    point_ref: str | None
    point_key: str | None
    value: object
    request_id: str


def encode_json_line(payload: JsonObject) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    ) + b"\n"


def parse_json_line(line: bytes) -> JsonObject:
    parsed = json.loads(line.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("JSON line must contain an object")
    return parsed


def parse_write_command(payload: JsonObject) -> WriteCommand:
    if payload.get("message_type") != WRITE_MESSAGE_TYPE:
        raise ValueError(f"message_type must be {WRITE_MESSAGE_TYPE}")
    source_id = _required_string(payload, "source_id")
    point_ref = _optional_string(payload, "point_ref")
    point_key = _optional_string(payload, "point_key")
    if point_ref is None and point_key is None:
        raise ValueError("point_ref or point_key is required")
    return WriteCommand(
        source_id=source_id,
        point_ref=point_ref,
        point_key=point_key,
        value=payload.get("value"),
        request_id=_required_string(payload, "request_id"),
    )


def write_ack_payload(command: WriteCommand) -> JsonObject:
    return {
        "message_type": WRITE_ACK_MESSAGE_TYPE,
        "source_id": command.source_id,
        "point_ref": command.point_ref,
        "point_key": command.point_key,
        "request_id": command.request_id,
        "accepted": True,
    }


def write_error_payload(
    *,
    source_id: str | None,
    request_id: str | None,
    reason: str,
) -> JsonObject:
    return {
        "message_type": ERROR_MESSAGE_TYPE,
        "source_id": source_id,
        "request_id": request_id,
        "reason": reason,
    }


def _required_string(payload: JsonObject, field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _optional_string(payload: JsonObject, field_name: str) -> str | None:
    value = payload.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string or null")
    return value
