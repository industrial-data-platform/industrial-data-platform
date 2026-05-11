from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from idp_synthetic_config.models import JsonObject, SyntheticModel
from idp_synthetic_config.reset import ResetPolicy, ResetSummary, ResetTargetSummary


class ConfigRegistryApi(Protocol):
    def get_json(self, path: str) -> object: ...

    def post_json(self, path: str, payload: JsonObject) -> JsonObject: ...

    def delete_json(self, path: str) -> JsonObject: ...


class ConfigRegistryError(RuntimeError):
    """Base class for Config Registry seeding failures."""


class ConfigRegistryConflict(ConfigRegistryError):
    def __init__(self, *, path: str, body: str) -> None:
        super().__init__(f"Config Registry conflict: path={path} body={body}")
        self.path = path
        self.body = body


class ConfigRegistryNotFound(ConfigRegistryError):
    def __init__(self, *, path: str, body: str) -> None:
        super().__init__(f"Config Registry record not found: path={path} body={body}")
        self.path = path
        self.body = body


class ConfigRegistryHttpClient:
    def __init__(self, base_url: str, *, timeout_seconds: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def get_json(self, path: str) -> object:
        return self._request_json("GET", path)

    def post_json(self, path: str, payload: JsonObject) -> JsonObject:
        parsed = self._request_json("POST", path, payload)
        if not isinstance(parsed, dict):
            raise ConfigRegistryError(
                f"Config Registry response for {path} must be an object"
            )
        return parsed

    def delete_json(self, path: str) -> JsonObject:
        parsed = self._request_json("DELETE", path)
        if not isinstance(parsed, dict):
            raise ConfigRegistryError(
                f"Config Registry response for {path} must be an object"
            )
        return parsed

    def _request_json(
        self,
        method: str,
        path: str,
        payload: JsonObject | None = None,
    ) -> object:
        data = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=True).encode()
        request = urllib.request.Request(
            f"{self._base_url}{path}",
            data=data,
            method=method,
        )
        request.add_header("Accept", "application/json")
        request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                response_text = response.read().decode()
        except urllib.error.HTTPError as exc:
            response_text = exc.read().decode(errors="replace")
            if exc.code == 409:
                raise ConfigRegistryConflict(path=path, body=response_text) from exc
            if exc.code == 404:
                raise ConfigRegistryNotFound(path=path, body=response_text) from exc
            raise ConfigRegistryError(
                "Config Registry request failed: "
                f"method={method} path={path} status={exc.code} body={response_text}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ConfigRegistryError(
                f"Config Registry request failed: method={method} path={path} "
                f"reason={exc.reason}"
            ) from exc
        return json.loads(response_text) if response_text else {}


@dataclass(frozen=True)
class SeedEntry:
    action: str
    record_type: str
    record_id: str
    path: str
    detail: str

    def to_dict(self) -> JsonObject:
        return {
            "action": self.action,
            "record_type": self.record_type,
            "record_id": self.record_id,
            "path": self.path,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class SeedSummary:
    config_revision: str
    issued_at: str
    source_config_revisions: dict[str, str]
    reset: ResetSummary
    entries: tuple[SeedEntry, ...]
    render_response: JsonObject | None = None

    @property
    def counts(self) -> dict[str, int]:
        return dict(Counter(entry.action for entry in self.entries))

    @property
    def ok(self) -> bool:
        return not any(entry.action in {"drift", "error"} for entry in self.entries)

    def to_dict(self) -> JsonObject:
        return {
            "ok": self.ok,
            "config_revision": self.config_revision,
            "issued_at": self.issued_at,
            "source_config_revisions": dict(self.source_config_revisions),
            "counts": self.counts,
            "reset": self.reset.to_dict(),
            "entries": [entry.to_dict() for entry in self.entries],
            "render_response": self.render_response,
        }


class ConfigRegistrySeeder:
    def __init__(
        self,
        client: ConfigRegistryApi,
        *,
        reset_policy: ResetPolicy | None = None,
    ) -> None:
        self._client = client
        self._reset_policy = reset_policy or ResetPolicy()

    def seed(
        self,
        model: SyntheticModel,
        *,
        config_registry_url: str,
        config_revision: str | None = None,
        issued_at: datetime | str | None = None,
        source_config_revisions: dict[str, str] | None = None,
    ) -> SeedSummary:
        revision = config_revision or _default_config_revision()
        issued_at_text = _format_issued_at(issued_at)
        revisions = source_config_revisions or model.source_config_revisions(revision)
        reset_summary = self._reset_policy.evaluate(
            model,
            config_registry_url=config_registry_url,
        )
        reset_summary, reset_entries = self._apply_config_registry_reset(
            model,
            reset_summary,
        )

        entries = list(reset_entries)
        entries.extend(self._detect_stale_generated_points(model))
        if _has_drift_or_error(entries):
            return SeedSummary(
                config_revision=revision,
                issued_at=issued_at_text,
                source_config_revisions=revisions,
                reset=reset_summary,
                entries=tuple(entries),
            )

        entries.append(
            self._create_or_match(
                record_type="tenant",
                record_id=model.tenant.tenant_id,
                create_path="/tenants",
                list_path="/tenants",
                id_field="tenant_id",
                payload=model.tenant.to_create_payload(),
            )
        )
        entries.append(
            self._create_or_match(
                record_type="asset",
                record_id=model.asset.asset_id,
                create_path=_path("tenants", model.tenant.tenant_id, "assets"),
                list_path=_path("tenants", model.tenant.tenant_id, "assets"),
                id_field="asset_id",
                payload=model.asset.to_create_payload(),
            )
        )
        entries.append(
            self._create_or_match(
                record_type="agent",
                record_id=model.agent.agent_id,
                create_path=_path(
                    "tenants",
                    model.tenant.tenant_id,
                    "assets",
                    model.asset.asset_id,
                    "agents",
                ),
                list_path=_path(
                    "tenants",
                    model.tenant.tenant_id,
                    "assets",
                    model.asset.asset_id,
                    "agents",
                ),
                id_field="agent_id",
                payload=model.agent.to_create_payload(),
            )
        )
        for source in model.sources:
            source_path = _path(
                "tenants",
                model.tenant.tenant_id,
                "assets",
                model.asset.asset_id,
                "agents",
                model.agent.agent_id,
                "sources",
            )
            entries.append(
                self._create_or_match(
                    record_type="source",
                    record_id=source.source_id,
                    create_path=source_path,
                    list_path=source_path,
                    id_field="source_id",
                    payload=source.to_create_payload(),
                )
            )
            point_path = _path(
                "tenants",
                model.tenant.tenant_id,
                "assets",
                model.asset.asset_id,
                "agents",
                model.agent.agent_id,
                "sources",
                source.source_id,
                "points",
            )
            for point in source.points:
                entries.append(
                    self._create_or_match(
                        record_type="point",
                        record_id=point.point_id,
                        create_path=point_path,
                        list_path=point_path,
                        id_field="point_id",
                        payload=point.to_create_payload(),
                    )
                )

        if _has_drift_or_error(entries):
            return SeedSummary(
                config_revision=revision,
                issued_at=issued_at_text,
                source_config_revisions=revisions,
                reset=reset_summary,
                entries=tuple(entries),
            )

        render_path = _path(
            "tenants",
            model.tenant.tenant_id,
            "assets",
            model.asset.asset_id,
            "agents",
            model.agent.agent_id,
            "render-config",
        )
        render_payload = {
            "config_revision": revision,
            "issued_at": issued_at_text,
            "source_config_revisions": revisions,
        }
        try:
            render_response = self._client.post_json(render_path, render_payload)
        except ConfigRegistryConflict:
            entries.append(
                SeedEntry(
                    action="drift",
                    record_type="rendered_config",
                    record_id=revision,
                    path=render_path,
                    detail=(
                        "render conflict cannot verify existing revision through "
                        "public Config Registry API"
                    ),
                )
            )
            render_response = None
        except ConfigRegistryError as exc:
            entries.append(
                SeedEntry(
                    action="error",
                    record_type="rendered_config",
                    record_id=revision,
                    path=render_path,
                    detail=str(exc),
                )
            )
            render_response = None
        else:
            entries.append(
                SeedEntry(
                    action="created",
                    record_type="rendered_config",
                    record_id=revision,
                    path=render_path,
                    detail="render-config created agent runtime/source revisions",
                )
            )

        return SeedSummary(
            config_revision=revision,
            issued_at=issued_at_text,
            source_config_revisions=revisions,
            reset=reset_summary,
            entries=tuple(entries),
            render_response=render_response,
        )

    def _create_or_match(
        self,
        *,
        record_type: str,
        record_id: str,
        create_path: str,
        list_path: str,
        id_field: str,
        payload: JsonObject,
    ) -> SeedEntry:
        try:
            self._client.post_json(create_path, payload)
        except ConfigRegistryConflict:
            existing = self._find_existing(list_path, id_field, record_id)
            if existing is None:
                return SeedEntry(
                    action="error",
                    record_type=record_type,
                    record_id=record_id,
                    path=create_path,
                    detail="conflict response but existing record was not listed",
                )
            if _payload_matches(existing, payload):
                return SeedEntry(
                    action="exists",
                    record_type=record_type,
                    record_id=record_id,
                    path=create_path,
                    detail="existing payload matches generated payload",
                )
            return SeedEntry(
                action="drift",
                record_type=record_type,
                record_id=record_id,
                path=create_path,
                detail="existing payload differs from generated payload",
            )
        except ConfigRegistryError as exc:
            return SeedEntry(
                action="error",
                record_type=record_type,
                record_id=record_id,
                path=create_path,
                detail=str(exc),
            )
        return SeedEntry(
            action="created",
            record_type=record_type,
            record_id=record_id,
            path=create_path,
            detail="created",
        )

    def _find_existing(
        self,
        list_path: str,
        id_field: str,
        record_id: str,
    ) -> JsonObject | None:
        try:
            response = self._client.get_json(list_path)
        except ConfigRegistryError:
            return None
        if not isinstance(response, list):
            return None
        for item in response:
            if isinstance(item, dict) and item.get(id_field) == record_id:
                return item
        return None

    def _apply_config_registry_reset(
        self,
        model: SyntheticModel,
        reset_summary: ResetSummary,
    ) -> tuple[ResetSummary, tuple[SeedEntry, ...]]:
        if not reset_summary.enabled:
            return reset_summary, ()

        deleted = 0
        entries: list[SeedEntry] = []
        for source in model.sources:
            point_path = _path(
                "tenants",
                model.tenant.tenant_id,
                "assets",
                model.asset.asset_id,
                "agents",
                model.agent.agent_id,
                "sources",
                source.source_id,
                "points",
            )
            try:
                response = self._client.get_json(point_path)
            except ConfigRegistryNotFound:
                continue
            except ConfigRegistryError as exc:
                entries.append(
                    SeedEntry(
                        action="error",
                        record_type="reset",
                        record_id=source.source_id,
                        path=point_path,
                        detail=str(exc),
                    )
                )
                continue
            if not isinstance(response, list):
                continue
            for item in response:
                point_id = _generated_point_id(item)
                if point_id is None:
                    continue
                delete_path = f"{point_path}/{urllib.parse.quote(point_id, safe='')}"
                try:
                    self._client.delete_json(delete_path)
                except ConfigRegistryNotFound:
                    continue
                except ConfigRegistryError as exc:
                    entries.append(
                        SeedEntry(
                            action="error",
                            record_type="reset",
                            record_id=point_id,
                            path=delete_path,
                            detail=str(exc),
                        )
                    )
                    continue
                deleted += 1

        status = "error" if entries else "cleared"
        detail = (
            f"Deleted {deleted} existing generated Config Registry point records."
            if not entries
            else "Config Registry reset failed for at least one generated point."
        )
        return (
            reset_summary.with_target(
                ResetTargetSummary(
                    name="config_registry",
                    status=status,
                    records_affected=deleted,
                    detail=detail,
                )
            ),
            tuple(entries),
        )

    def _detect_stale_generated_points(
        self,
        model: SyntheticModel,
    ) -> tuple[SeedEntry, ...]:
        entries: list[SeedEntry] = []
        desired_point_ids = {
            point.point_id
            for source in model.sources
            for point in source.points
        }
        for source in model.sources:
            point_path = _path(
                "tenants",
                model.tenant.tenant_id,
                "assets",
                model.asset.asset_id,
                "agents",
                model.agent.agent_id,
                "sources",
                source.source_id,
                "points",
            )
            try:
                response = self._client.get_json(point_path)
            except ConfigRegistryError:
                continue
            if not isinstance(response, list):
                continue
            for item in response:
                stale_point = _stale_generated_point(item, desired_point_ids)
                if stale_point is None:
                    continue
                entries.append(
                    SeedEntry(
                        action="drift",
                        record_type="point",
                        record_id=stale_point.point_id,
                        path=point_path,
                        detail=(
                            "stale generated point exists outside desired model; "
                            "Config Registry cleanup API is required before render"
                        ),
                    )
                )
        return tuple(entries)


@dataclass(frozen=True)
class _StalePoint:
    point_id: str


def _stale_generated_point(
    item: object,
    desired_point_ids: set[str],
) -> _StalePoint | None:
    if not isinstance(item, dict):
        return None
    point_id = item.get("point_id")
    tags = item.get("tags_json")
    if not isinstance(point_id, str) or point_id in desired_point_ids:
        return None
    if isinstance(tags, dict) and tags.get("generated_by") == "idp_synthetic_config":
        return _StalePoint(point_id=point_id)
    return None


def _generated_point_id(item: object) -> str | None:
    if not isinstance(item, dict):
        return None
    point_id = item.get("point_id")
    tags = item.get("tags_json")
    if isinstance(point_id, str) and isinstance(tags, dict):
        if tags.get("generated_by") == "idp_synthetic_config":
            return point_id
    return None


def _payload_matches(existing: JsonObject, expected: JsonObject) -> bool:
    for key, expected_value in expected.items():
        if existing.get(key) != expected_value:
            return False
    return True


def _has_drift_or_error(entries: list[SeedEntry]) -> bool:
    return any(entry.action in {"drift", "error"} for entry in entries)


def _default_config_revision() -> str:
    return "synthetic-" + datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")


def _format_issued_at(value: datetime | str | None) -> str:
    if value is None:
        value = datetime.now(tz=UTC)
    if isinstance(value, str):
        return value
    resolved = value
    if resolved.tzinfo is None:
        resolved = resolved.replace(tzinfo=UTC)
    return (
        resolved.astimezone(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _path(*segments: str) -> str:
    escaped = [urllib.parse.quote(segment, safe="") for segment in segments]
    return "/" + "/".join(escaped)
