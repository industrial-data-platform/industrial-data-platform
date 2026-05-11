from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from idp_synthetic_config.models import SyntheticModel, ValueProfile

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class EmulatorPoint:
    source_id: str
    point_ref: str
    point_key: str
    name: str
    description: str
    value_type: str
    value_model: str
    signal_type: str
    unit: str | None
    tags: dict[str, str]
    periodic_interval_seconds: float
    change_threshold: float | None
    read_on_start: bool
    profile: ValueProfile

    @property
    def writable(self) -> bool:
        return self.signal_type == "command"

    def to_dict(self) -> JsonObject:
        return {
            "source_id": self.source_id,
            "point_ref": self.point_ref,
            "point_key": self.point_key,
            "name": self.name,
            "description": self.description,
            "value_type": self.value_type,
            "value_model": self.value_model,
            "signal_type": self.signal_type,
            "unit": self.unit,
            "tags": dict(self.tags),
            "periodic_interval_seconds": self.periodic_interval_seconds,
            "change_threshold": self.change_threshold,
            "read_on_start": self.read_on_start,
            "writable": self.writable,
            "value_profile": self.profile.to_dict(),
        }


@dataclass(frozen=True)
class EmulatorPlan:
    host: str
    port: int
    source_id: str
    devices: int
    points: tuple[EmulatorPoint, ...]
    emission_interval_seconds: float | None = None
    enable_writes: bool = True

    @property
    def point_count(self) -> int:
        return len(self.points)

    @property
    def stream_points(self) -> tuple[EmulatorPoint, ...]:
        return tuple(point for point in self.points if point.signal_type != "command")

    @property
    def command_points(self) -> tuple[EmulatorPoint, ...]:
        return tuple(point for point in self.points if point.signal_type == "command")

    def point_by_ref_or_key(
        self,
        *,
        point_ref: str | None,
        point_key: str | None,
    ) -> EmulatorPoint | None:
        for point in self.points:
            if point_ref is not None and point.point_ref == point_ref:
                return point
            if point_key is not None and point.point_key == point_key:
                return point
        return None

    def to_dict(self) -> JsonObject:
        return {
            "host": self.host,
            "port": self.port,
            "source_id": self.source_id,
            "enable_writes": self.enable_writes,
            "stats": {
                "devices": self.devices,
                "points": self.point_count,
                "stream_points": len(self.stream_points),
                "command_points": len(self.command_points),
            },
            "points": [point.to_dict() for point in self.points],
        }


def build_emulator_plan(
    model: SyntheticModel,
    *,
    host: str,
    port: int,
    source_id: str | None = None,
    interval_seconds: float | None = None,
    enable_writes: bool = True,
) -> EmulatorPlan:
    if not model.sources:
        raise ValueError("synthetic model must contain at least one source")

    selected_source_id = source_id or model.sources[0].source_id
    source = next(
        (item for item in model.sources if item.source_id == selected_source_id),
        None,
    )
    if source is None:
        raise ValueError(f"source_id {selected_source_id!r} not found in synthetic model")

    profiles_by_point_id = {profile.point_id: profile for profile in model.value_profiles}
    points: list[EmulatorPoint] = []
    for point in source.points:
        profile = profiles_by_point_id.get(point.point_id)
        if profile is None:
            raise ValueError(f"value profile missing for point_id {point.point_id!r}")
        periodic = point.acquisition.get(
            "periodic_interval_seconds",
            source.acquisition_defaults_json.get("periodic_interval_seconds"),
        )
        points.append(
            EmulatorPoint(
                source_id=source.source_id,
                point_ref=point.point_ref,
                point_key=point.point_key,
                name=point.name,
                description=point.description,
                value_type=point.value_type,
                value_model=point.value_model,
                signal_type=point.signal_type,
                unit=point.unit,
                tags=dict(point.tags),
                periodic_interval_seconds=float(periodic or 60),
                change_threshold=point.publish.get("change_threshold"),
                read_on_start=bool(point.acquisition.get("read_on_start", False)),
                profile=profile,
            )
        )

    return EmulatorPlan(
        host=host,
        port=port,
        source_id=source.source_id,
        devices=len(model.devices),
        points=tuple(points),
        emission_interval_seconds=interval_seconds,
        enable_writes=enable_writes,
    )
