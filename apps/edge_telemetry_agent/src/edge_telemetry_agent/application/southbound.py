from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from edge_telemetry_agent.application.delivery import DeliveryWorker
from edge_telemetry_agent.application.processing import ObservationProcessor
from edge_telemetry_agent.domain.config import AgentRuntimeConfig, SourceDefinition
from edge_telemetry_agent.domain.events import Observation
from edge_telemetry_agent.infrastructure.mqtt_publisher import connect_mqtt_publisher
from edge_telemetry_agent.infrastructure.sqlite_outbox import SQLiteOutbox
from edge_telemetry_agent.infrastructure.sqlite_point_state import SQLitePointStateCache


class Publisher(Protocol):
    def publish(self, publication: object) -> None: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class SouthboundIngestionResult:
    observations_read: int = 0
    events_enqueued: int = 0
    events_delivered: int = 0
    suppressed: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "observations_read": self.observations_read,
            "events_enqueued": self.events_enqueued,
            "events_delivered": self.events_delivered,
            "suppressed": self.suppressed,
        }


async def run_knx_source_emulator_ingestion(
    runtime_config: AgentRuntimeConfig,
    *,
    source_id: str | None = None,
    max_events: int | None = None,
    duration_seconds: float | None = None,
    publisher: Publisher | None = None,
) -> SouthboundIngestionResult:
    source = _select_source(runtime_config, source_id=source_id)
    host, port = _source_endpoint(source)
    state_cache = SQLitePointStateCache(runtime_config.storage.sqlite_path)
    state_cache.initialize()
    outbox = SQLiteOutbox(runtime_config.storage.sqlite_path)
    outbox.initialize()
    processor = ObservationProcessor(
        runtime_config,
        agent_id=runtime_config.agent_id,
        state_store=state_cache,
    )
    owned_publisher = publisher is None
    resolved_publisher = publisher or connect_mqtt_publisher(
        runtime_config.delivery.mqtt,
        agent_id=runtime_config.agent_id,
    )
    worker = DeliveryWorker(
        runtime_config=runtime_config,
        agent_id=runtime_config.agent_id,
        outbox=outbox,
        publisher=resolved_publisher,
    )

    try:
        return await _read_source(
            host=host,
            port=port,
            source_id=source.source_id,
            processor=processor,
            outbox=outbox,
            worker=worker,
            max_events=max_events,
            duration_seconds=duration_seconds,
        )
    finally:
        if owned_publisher or hasattr(resolved_publisher, "close"):
            resolved_publisher.close()


async def _read_source(
    *,
    host: str,
    port: int,
    source_id: str,
    processor: ObservationProcessor,
    outbox: SQLiteOutbox,
    worker: DeliveryWorker,
    max_events: int | None,
    duration_seconds: float | None,
) -> SouthboundIngestionResult:
    reader, writer = await asyncio.open_connection(host, port)
    deadline = None
    if duration_seconds is not None:
        deadline = asyncio.get_running_loop().time() + duration_seconds
    observations_read = 0
    events_enqueued = 0
    events_delivered = 0
    suppressed = 0
    try:
        while True:
            if max_events is not None and observations_read >= max_events:
                break
            timeout = None
            if deadline is not None:
                timeout = max(0.0, deadline - asyncio.get_running_loop().time())
                if timeout == 0.0:
                    break
            try:
                line = await asyncio.wait_for(reader.readline(), timeout=timeout)
            except TimeoutError:
                break
            if not line:
                break
            observation = _observation_from_emulator_payload(
                json.loads(line.decode("utf-8")),
                expected_source_id=source_id,
            )
            observations_read += 1
            result = processor.process(observation)
            if result.event is None:
                suppressed += 1
                continue
            outbox.append(result.event, available_at=observation.observed_at)
            events_enqueued += 1
            delivery = worker.deliver_once(now=observation.observed_at)
            events_delivered += delivery.published_count
    finally:
        writer.close()
        await writer.wait_closed()

    return SouthboundIngestionResult(
        observations_read=observations_read,
        events_enqueued=events_enqueued,
        events_delivered=events_delivered,
        suppressed=suppressed,
    )


def _select_source(
    runtime_config: AgentRuntimeConfig,
    *,
    source_id: str | None,
) -> SourceDefinition:
    if source_id is not None:
        try:
            return runtime_config.sources[source_id]
        except KeyError as exc:
            raise RuntimeError(f"source_id {source_id!r} not found") from exc
    for source in runtime_config.sources.values():
        if source.source_type == "knx" and source.enabled:
            return source
    raise RuntimeError("no enabled knx source found")


def _source_endpoint(source: SourceDefinition) -> tuple[str, int]:
    connection = source.connection
    host = connection.get("host") or connection.get("tcp_host") or connection.get("gateway_ip")
    port = connection.get("port") or connection.get("tcp_port") or connection.get("gateway_port")
    if not isinstance(host, str) or not host:
        raise RuntimeError(f"source {source.source_id} connection host is missing")
    if isinstance(port, bool) or not isinstance(port, int):
        raise RuntimeError(f"source {source.source_id} connection port is missing")
    return host, port


def _observation_from_emulator_payload(
    payload: object,
    *,
    expected_source_id: str,
) -> Observation:
    if not isinstance(payload, dict):
        raise RuntimeError("emulator payload must be a JSON object")
    if payload.get("message_type") != "knx_source_emulator.event.v1":
        raise RuntimeError("emulator payload message_type must be knx_source_emulator.event.v1")
    source_id = _required_string(payload, "source_id")
    if source_id != expected_source_id:
        raise RuntimeError(
            f"emulator source_id {source_id!r} does not match expected {expected_source_id!r}"
        )
    return Observation(
        source_id=source_id,
        point_ref=_required_string(payload, "point_ref"),
        observation_mode=_required_observation_mode(payload),
        value=payload.get("value"),
        value_raw=_optional_string(payload, "value_raw"),
        observed_at=_parse_ts(_required_string(payload, "ts")),
        quality=_required_quality(payload),
    )


def _required_observation_mode(payload: dict[str, object]) -> str:
    value = _required_string(payload, "observation_mode")
    if value not in {"read_on_start", "periodic_read", "listen"}:
        raise RuntimeError(f"unsupported observation_mode {value!r}")
    return value


def _required_quality(payload: dict[str, object]) -> str:
    value = _required_string(payload, "quality")
    if value not in {"good", "uncertain", "bad"}:
        raise RuntimeError(f"unsupported quality {value!r}")
    return value


def _parse_ts(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _required_string(payload: dict[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"emulator payload field {field_name} must be a non-empty string")
    return value


def _optional_string(payload: dict[str, object], field_name: str) -> str | None:
    value = payload.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise RuntimeError(f"emulator payload field {field_name} must be a string or null")
    return value
