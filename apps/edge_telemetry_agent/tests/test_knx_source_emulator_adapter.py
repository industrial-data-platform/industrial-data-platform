from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

from edge_telemetry_agent.application.configuration import build_agent_runtime_config
from edge_telemetry_agent.application.delivery import DeliveryWorker
from edge_telemetry_agent.application.processing import ObservationProcessor
from edge_telemetry_agent.application.southbound import (
    run_knx_source_emulator_ingestion,
)
from edge_telemetry_agent.domain.events import MqttPublication
from edge_telemetry_agent.infrastructure.sqlite_outbox import SQLiteOutbox
from edge_telemetry_agent.infrastructure.sqlite_point_state import SQLitePointStateCache


class FakePublisher:
    def __init__(self) -> None:
        self.publications: list[MqttPublication] = []
        self.closed = False

    def publish(self, publication: MqttPublication) -> None:
        self.publications.append(publication)

    def close(self) -> None:
        self.closed = True


def test_edge_agent_reads_tcp_emulator_events_through_outbox_and_delivery(
    tmp_path: Path,
) -> None:
    asyncio.run(_run_edge_adapter_smoke(tmp_path))


async def _run_edge_adapter_smoke(tmp_path: Path) -> None:
    server = await asyncio.start_server(
        _write_one_emulator_event,
        host="127.0.0.1",
        port=0,
    )
    host, port = server.sockets[0].getsockname()[:2]
    publisher = FakePublisher()
    runtime = _runtime_config(tmp_path, host=host, port=port)
    state_cache = SQLitePointStateCache(runtime.storage.sqlite_path)
    state_cache.initialize()
    outbox = SQLiteOutbox(runtime.storage.sqlite_path)
    outbox.initialize()
    processor = ObservationProcessor(
        runtime,
        agent_id=runtime.agent_id,
        state_store=state_cache,
    )
    worker = DeliveryWorker(
        runtime_config=runtime,
        agent_id=runtime.agent_id,
        outbox=outbox,
        publisher=publisher,
    )

    async with server:
        try:
            result = await run_knx_source_emulator_ingestion(
                runtime,
                processor=processor,
                outbox=outbox,
                worker=worker,
                source_id="knx_synthetic",
                max_events=1,
            )
        finally:
            publisher.close()

    assert result.observations_read == 1
    assert result.events_enqueued == 1
    assert result.events_delivered == 1
    assert publisher.closed is True
    assert publisher.publications[0].payload["message_type"] == (
        "idp.edge.telemetry.event.v1"
    )
    assert publisher.publications[0].payload["tenant_id"] == "tenant-001"
    assert publisher.publications[0].payload["source_config_revision"] == (
        "rev-2026-05-11-001-knx"
    )

    sqlite_path = runtime.storage.sqlite_path
    with sqlite3.connect(sqlite_path) as connection:
        outbox_row = connection.execute(
            "SELECT status, attempt_count FROM outbox"
        ).fetchone()
        state_row = connection.execute(
            """
            SELECT last_observed_value_json, last_published_value_json, sequence
            FROM point_state_cache
            WHERE source_id = 'knx_synthetic' AND point_ref = '1/0/1'
            """
        ).fetchone()
    assert outbox_row == ("sent", 1)
    assert state_row == ("23.5", "23.5", 1)


async def _write_one_emulator_event(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    _ = reader
    writer.write(
        json.dumps(
            {
                "message_type": "knx_source_emulator.event.v1",
                "source_id": "knx_synthetic",
                "point_ref": "1/0/1",
                "point_key": "1%2F0%2F1",
                "observation_mode": "periodic_read",
                "value": 23.5,
                "value_raw": "23.5",
                "quality": "good",
                "ts": "2026-05-11T07:00:00Z",
                "name": "Температура воздуха: Фудкорт, этаж 2",
                "description": "Контроль температуры воздуха.",
                "signal_type": "sensor",
                "value_model": "knx.dpt.9.001",
                "unit": "C",
                "tags": {"zone": "Фудкорт"},
            }
        ).encode()
        + b"\n"
    )
    await writer.drain()
    writer.close()


def _runtime_config(tmp_path: Path, *, host: str, port: int):
    return build_agent_runtime_config(
        bootstrap_data={
            "agent_id": "edge-synthetic-01",
            "delivery": {
                "transport": "mqtt",
                "mqtt": {
                    "enabled": True,
                    "version": "5.0",
                    "broker": "mqtt://127.0.0.1:1883",
                    "topic_root": "idp/v1",
                    "client_id_prefix": "edge-telemetry-agent",
                    "username_env": None,
                    "password_env": None,
                    "qos": 1,
                    "clean_start": True,
                    "session_expiry_seconds": 0,
                    "telemetry_message_expiry_seconds": 86400,
                    "connect_timeout_seconds": 5,
                    "retry_backoff_seconds": [1, 2, 5],
                },
            },
            "storage": {
                "sqlite_path": str(tmp_path / "state" / "edge.db"),
                "retention_days": 7,
                "dead_letter_after_attempts": 3,
            },
            "observability": {
                "log_level": "INFO",
                "emit_health_events": True,
                "metrics_bind": None,
            },
        },
        agent_runtime_data={
            "message_type": "idp.edge.agent-runtime-config.v1",
            "tenant_id": "tenant-001",
            "asset_id": "mall-synthetic-01",
            "agent_id": "edge-synthetic-01",
            "config_revision": "rev-2026-05-11-001",
            "issued_at": "2026-05-11T07:00:00Z",
            "sources": [
                {
                    "source_id": "knx_synthetic",
                    "source_config_revision": "rev-2026-05-11-001-knx",
                    "enabled": True,
                }
            ],
        },
        source_documents=[
            {
                "message_type": "idp.edge.source-config.v1",
                "tenant_id": "tenant-001",
                "asset_id": "mall-synthetic-01",
                "agent_id": "edge-synthetic-01",
                "config_revision": "rev-2026-05-11-001",
                "source_id": "knx_synthetic",
                "source_config_revision": "rev-2026-05-11-001-knx",
                "source_type": "knx",
                "enabled": True,
                "connection": {
                    "mode": "synthetic",
                    "host": host,
                    "port": port,
                    "gateway_ip": host,
                    "gateway_port": port,
                },
                "acquisition_defaults": {
                    "listen": True,
                    "read_on_start": False,
                    "periodic_interval_seconds": 60,
                },
                "publish_defaults": {
                    "enabled": True,
                    "change_threshold": None,
                },
                "points": [
                    {
                        "point_key": "1%2F0%2F1",
                        "point_ref": "1/0/1",
                        "name": "Температура воздуха: Фудкорт, этаж 2",
                        "description": "Контроль температуры воздуха.",
                        "value_type": "number",
                        "value_model": "knx.dpt.9.001",
                        "signal_type": "sensor",
                        "unit": "C",
                        "acquisition": {
                            "listen": True,
                            "read_on_start": True,
                            "periodic_interval_seconds": 60,
                        },
                        "publish": {
                            "enabled": True,
                            "change_threshold": 0.5,
                        },
                        "tags": {"zone": "Фудкорт"},
                    }
                ],
            }
        ],
    )
