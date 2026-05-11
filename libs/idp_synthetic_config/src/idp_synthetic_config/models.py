from __future__ import annotations

from dataclasses import dataclass
from typing import Any

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class SyntheticTenant:
    tenant_id: str
    name: str

    def to_create_payload(self) -> JsonObject:
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
        }

    def to_dict(self) -> JsonObject:
        return self.to_create_payload()


@dataclass(frozen=True)
class SyntheticAsset:
    asset_id: str
    name: str
    description: str

    def to_create_payload(self) -> JsonObject:
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "description": self.description,
        }

    def to_dict(self) -> JsonObject:
        return self.to_create_payload()


@dataclass(frozen=True)
class SyntheticAgent:
    agent_id: str
    name: str
    bootstrap_hint_json: JsonObject

    def to_create_payload(self) -> JsonObject:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "bootstrap_hint_json": dict(self.bootstrap_hint_json),
        }

    def to_dict(self) -> JsonObject:
        return self.to_create_payload()


@dataclass(frozen=True)
class SyntheticDevice:
    device_id: str
    name: str
    floor: str
    zone: str
    subsystem: str
    tenant_space: str

    def to_dict(self) -> JsonObject:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "floor": self.floor,
            "zone": self.zone,
            "subsystem": self.subsystem,
            "tenant_space": self.tenant_space,
        }


@dataclass(frozen=True)
class SyntheticPoint:
    point_id: str
    point_key: str
    point_ref: str
    name: str
    description: str
    value_type: str
    value_model: str
    signal_type: str
    unit: str | None
    acquisition: JsonObject
    publish: JsonObject
    tags: dict[str, str]

    def to_create_payload(self) -> JsonObject:
        return {
            "point_id": self.point_id,
            "point_key": self.point_key,
            "point_ref": self.point_ref,
            "name": self.name,
            "description": self.description,
            "value_type": self.value_type,
            "value_model": self.value_model,
            "signal_type": self.signal_type,
            "unit": self.unit,
            "acquisition_json": dict(self.acquisition),
            "publish_json": dict(self.publish),
            "tags_json": dict(self.tags),
        }

    def source_config_entry(self) -> JsonObject:
        return {
            "point_key": self.point_key,
            "point_ref": self.point_ref,
            "name": self.name,
            "description": self.description,
            "value_type": self.value_type,
            "value_model": self.value_model,
            "signal_type": self.signal_type,
            "unit": self.unit,
            "acquisition": dict(self.acquisition),
            "publish": dict(self.publish),
            "tags": dict(self.tags),
        }

    def to_dict(self) -> JsonObject:
        return {
            "point_id": self.point_id,
            **self.source_config_entry(),
        }


@dataclass(frozen=True)
class SyntheticSource:
    source_id: str
    source_type: str
    enabled: bool
    name: str
    description: str
    connection_json: JsonObject
    acquisition_defaults_json: JsonObject
    publish_defaults_json: JsonObject
    points: tuple[SyntheticPoint, ...]

    def to_create_payload(self) -> JsonObject:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "enabled": self.enabled,
            "name": self.name,
            "description": self.description,
            "connection_json": dict(self.connection_json),
            "acquisition_defaults_json": dict(self.acquisition_defaults_json),
            "publish_defaults_json": dict(self.publish_defaults_json),
        }

    def source_config_payload(
        self,
        *,
        tenant_id: str,
        asset_id: str,
        agent_id: str,
        config_revision: str,
        source_config_revision: str,
    ) -> JsonObject:
        return {
            "message_type": "idp.edge.source-config.v1",
            "tenant_id": tenant_id,
            "asset_id": asset_id,
            "agent_id": agent_id,
            "config_revision": config_revision,
            "source_id": self.source_id,
            "source_config_revision": source_config_revision,
            "source_type": self.source_type,
            "enabled": self.enabled,
            "connection": dict(self.connection_json),
            "acquisition_defaults": dict(self.acquisition_defaults_json),
            "publish_defaults": dict(self.publish_defaults_json),
            "points": [point.source_config_entry() for point in self.points],
        }

    def to_dict(self) -> JsonObject:
        return {
            **self.to_create_payload(),
            "points": [point.to_dict() for point in self.points],
        }


@dataclass(frozen=True)
class ValueProfile:
    profile_id: str
    point_id: str
    value_type: str
    signal_type: str
    parameters: JsonObject

    def to_dict(self) -> JsonObject:
        return {
            "profile_id": self.profile_id,
            "point_id": self.point_id,
            "value_type": self.value_type,
            "signal_type": self.signal_type,
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True)
class SyntheticModel:
    tenant: SyntheticTenant
    asset: SyntheticAsset
    agent: SyntheticAgent
    sources: tuple[SyntheticSource, ...]
    devices: tuple[SyntheticDevice, ...]
    value_profiles: tuple[ValueProfile, ...]
    seed: int

    def source_config_revisions(self, config_revision: str) -> dict[str, str]:
        return {
            source.source_id: f"{config_revision}-{source.source_id}"
            for source in self.sources
        }

    def agent_runtime_payload(
        self,
        *,
        config_revision: str,
        issued_at: str,
        source_config_revisions: dict[str, str],
    ) -> JsonObject:
        return {
            "message_type": "idp.edge.agent-runtime-config.v1",
            "tenant_id": self.tenant.tenant_id,
            "asset_id": self.asset.asset_id,
            "agent_id": self.agent.agent_id,
            "config_revision": config_revision,
            "issued_at": issued_at,
            "sources": [
                {
                    "source_id": source.source_id,
                    "source_config_revision": source_config_revisions[source.source_id],
                    "enabled": source.enabled,
                }
                for source in self.sources
            ],
        }

    def source_config_payloads(
        self,
        *,
        config_revision: str,
        source_config_revisions: dict[str, str],
    ) -> tuple[JsonObject, ...]:
        return tuple(
            source.source_config_payload(
                tenant_id=self.tenant.tenant_id,
                asset_id=self.asset.asset_id,
                agent_id=self.agent.agent_id,
                config_revision=config_revision,
                source_config_revision=source_config_revisions[source.source_id],
            )
            for source in self.sources
        )

    def to_plan_dict(self) -> JsonObject:
        return {
            "seed": self.seed,
            "tenant": self.tenant.to_dict(),
            "asset": self.asset.to_dict(),
            "agent": self.agent.to_dict(),
            "devices": [device.to_dict() for device in self.devices],
            "sources": [source.to_dict() for source in self.sources],
            "value_profiles": [profile.to_dict() for profile in self.value_profiles],
        }

