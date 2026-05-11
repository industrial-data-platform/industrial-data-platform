from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import UTC, datetime

from knx_source_emulator.plan import EmulatorPlan, EmulatorPoint
from knx_source_emulator.protocol import (
    EmulatorEvent,
    encode_json_line,
    parse_json_line,
    parse_write_command,
    write_ack_payload,
    write_error_payload,
)
from knx_source_emulator.values import ValueGenerator


@dataclass
class EmulatorStats:
    devices: int
    points: int
    tcp_clients: int = 0
    events_sent: int = 0
    reads: int = 0
    writes: int = 0
    errors: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "devices": self.devices,
            "points": self.points,
            "tcp_clients": self.tcp_clients,
            "events_sent": self.events_sent,
            "reads": self.reads,
            "writes": self.writes,
            "errors": self.errors,
        }


class KnxSourceEmulatorServer:
    def __init__(self, plan: EmulatorPlan, *, seed: int = 0) -> None:
        self._plan = plan
        self._seed = seed
        self._server: asyncio.Server | None = None
        self._client_tasks: set[asyncio.Task[None]] = set()
        self.stats = EmulatorStats(devices=plan.devices, points=plan.point_count)

    @property
    def bound_address(self) -> tuple[str, int]:
        if self._server is None or not self._server.sockets:
            raise RuntimeError("server is not started")
        socket_name = self._server.sockets[0].getsockname()
        return str(socket_name[0]), int(socket_name[1])

    async def __aenter__(self) -> "KnxSourceEmulatorServer":
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        del exc_type, exc, traceback
        await self.stop()

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_client,
            host=self._plan.host,
            port=self._plan.port,
        )

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        for task in tuple(self._client_tasks):
            task.cancel()
        if self._client_tasks:
            await asyncio.gather(*self._client_tasks, return_exceptions=True)
        self._client_tasks.clear()

    async def serve_for(self, duration_seconds: float) -> EmulatorStats:
        async with self:
            await asyncio.sleep(duration_seconds)
        return self.stats

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        self.stats.tcp_clients += 1
        generator = ValueGenerator(seed=self._seed)
        sender = asyncio.create_task(self._send_events(writer, generator))
        receiver = asyncio.create_task(self._receive_commands(reader, writer))
        self._client_tasks.update({sender, receiver})
        try:
            done, pending = await asyncio.wait(
                {sender, receiver},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in done:
                task.result()
            for task in pending:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        finally:
            self._client_tasks.discard(sender)
            self._client_tasks.discard(receiver)
            writer.close()
            with contextlib.suppress(ConnectionError):
                await writer.wait_closed()

    async def _send_events(
        self,
        writer: asyncio.StreamWriter,
        generator: ValueGenerator,
    ) -> None:
        read_on_start_points = [
            point for point in self._plan.stream_points if point.read_on_start
        ]
        for point in read_on_start_points or list(self._plan.stream_points[:1]):
            await self._write_event(
                writer,
                point,
                generator=generator,
                observation_mode="read_on_start",
            )

        while True:
            await asyncio.sleep(self._next_sleep_seconds())
            for point in self._plan.stream_points:
                await self._write_event(
                    writer,
                    point,
                    generator=generator,
                    observation_mode="periodic_read",
                )

    async def _write_event(
        self,
        writer: asyncio.StreamWriter,
        point: EmulatorPoint,
        *,
        generator: ValueGenerator,
        observation_mode: str,
    ) -> None:
        now = datetime.now(tz=UTC).replace(microsecond=0)
        generated = generator.next_value(point, now=now)
        event = EmulatorEvent(
            source_id=point.source_id,
            point_ref=point.point_ref,
            point_key=point.point_key,
            observation_mode=observation_mode,
            value=generated.value,
            value_raw=generated.value_raw,
            quality="good",
            ts=now.isoformat().replace("+00:00", "Z"),
            name=point.name,
            description=point.description,
            signal_type=point.signal_type,
            value_model=point.value_model,
            unit=point.unit,
            tags=dict(point.tags),
        )
        writer.write(encode_json_line(event.to_payload()))
        await writer.drain()
        self.stats.events_sent += 1
        self.stats.reads += 1

    async def _receive_commands(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        while True:
            line = await reader.readline()
            if not line:
                return
            try:
                payload = parse_json_line(line)
                command = parse_write_command(payload)
                point = self._plan.point_by_ref_or_key(
                    point_ref=command.point_ref,
                    point_key=command.point_key,
                )
                if (
                    point is None
                    or not self._plan.enable_writes
                    or not point.writable
                    or command.source_id != self._plan.source_id
                ):
                    writer.write(
                        encode_json_line(
                            write_error_payload(
                                source_id=command.source_id,
                                request_id=command.request_id,
                                reason="point is not writable",
                            )
                        )
                    )
                    await writer.drain()
                    self.stats.errors += 1
                    continue
                writer.write(encode_json_line(write_ack_payload(command)))
                await writer.drain()
                self.stats.writes += 1
            except Exception as exc:
                writer.write(
                    encode_json_line(
                        write_error_payload(
                            source_id=self._plan.source_id,
                            request_id=None,
                            reason=str(exc),
                        )
                    )
                )
                await writer.drain()
                self.stats.errors += 1

    def _next_sleep_seconds(self) -> float:
        if self._plan.emission_interval_seconds is not None:
            return self._plan.emission_interval_seconds
        if not self._plan.stream_points:
            return 1.0
        return max(0.001, min(point.periodic_interval_seconds for point in self._plan.stream_points))
