from __future__ import annotations

import asyncio
import contextlib
import json

import pytest

from idp_synthetic_config.generator import GeneratorOptions, generate_synthetic_config
from knx_source_emulator.plan import build_emulator_plan
from knx_source_emulator.server import KnxSourceEmulatorServer

pytestmark = pytest.mark.asyncio


async def test_tcp_server_supports_multiple_clients_and_streams_non_command_points() -> None:
    model = generate_synthetic_config(
        GeneratorOptions(devices=1, tags_per_device=6, seed=17)
    )
    plan = build_emulator_plan(
        model,
        host="127.0.0.1",
        port=0,
        interval_seconds=0.02,
    )
    server = KnxSourceEmulatorServer(plan)

    async with server:
        host, port = server.bound_address
        reader_one, writer_one = await asyncio.open_connection(host, port)
        reader_two, writer_two = await asyncio.open_connection(host, port)
        try:
            first = json.loads(await asyncio.wait_for(reader_one.readline(), timeout=2))
            second = json.loads(await asyncio.wait_for(reader_two.readline(), timeout=2))
        finally:
            writer_one.close()
            writer_two.close()
            await writer_one.wait_closed()
            await writer_two.wait_closed()

    assert first["message_type"] == "knx_source_emulator.event.v1"
    assert second["message_type"] == "knx_source_emulator.event.v1"
    assert first["signal_type"] != "command"
    assert server.stats.tcp_clients >= 2
    assert server.stats.events_sent >= 2
    assert server.stats.errors == 0


async def test_tcp_server_accepts_writes_for_command_points_only() -> None:
    model = generate_synthetic_config(
        GeneratorOptions(devices=1, tags_per_device=4, seed=17)
    )
    plan = build_emulator_plan(
        model,
        host="127.0.0.1",
        port=0,
        interval_seconds=0.05,
        enable_writes=True,
    )
    command = plan.command_points[0]
    sensor = plan.stream_points[0]
    server = KnxSourceEmulatorServer(plan)

    async with server:
        reader, writer = await asyncio.open_connection(*server.bound_address)
        await _discard_initial_event(reader)
        writer.write(
            json.dumps(
                {
                    "message_type": "knx_source_emulator.write.v1",
                    "source_id": plan.source_id,
                    "point_key": command.point_key,
                    "value": True,
                    "request_id": "req-command",
                }
            ).encode()
            + b"\n"
        )
        await writer.drain()
        ack = await _read_message_type(reader, "knx_source_emulator.write_ack.v1")
        writer.write(
            json.dumps(
                {
                    "message_type": "knx_source_emulator.write.v1",
                    "source_id": plan.source_id,
                    "point_ref": sensor.point_ref,
                    "value": True,
                    "request_id": "req-sensor",
                }
            ).encode()
            + b"\n"
        )
        await writer.drain()
        error = await _read_message_type(reader, "knx_source_emulator.error.v1")
        writer.close()
        with contextlib.suppress(ConnectionError):
            await writer.wait_closed()

    assert ack["message_type"] == "knx_source_emulator.write_ack.v1"
    assert ack["point_key"] == command.point_key
    assert error["message_type"] == "knx_source_emulator.error.v1"
    assert error["request_id"] == "req-sensor"
    assert "not writable" in error["reason"]
    assert server.stats.writes == 1


async def _discard_initial_event(reader: asyncio.StreamReader) -> None:
    await asyncio.wait_for(reader.readline(), timeout=2)


async def _read_message_type(
    reader: asyncio.StreamReader,
    message_type: str,
) -> dict[str, object]:
    while True:
        payload = json.loads(await asyncio.wait_for(reader.readline(), timeout=2))
        if payload["message_type"] == message_type:
            return payload
