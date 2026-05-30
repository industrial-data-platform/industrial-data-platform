from __future__ import annotations

from pathlib import Path

import pytest

from idp_telemetry_store.migrations import (
    METADATA_TABLE_SQL,
    MigrationError,
    apply_pending_migrations,
    load_migrations,
    migration_statuses,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
REPO_MIGRATIONS_DIR = REPO_ROOT / "tools" / "idp_telemetry_store" / "migrations"


class FakeClickHouseClient:
    def __init__(self, applied: dict[str, str] | None = None) -> None:
        self.applied = applied or {}
        self.sql: list[str] = []

    def execute(self, sql: str) -> str:
        self.sql.append(sql)
        if "SELECT version, checksum FROM schema_migrations" in sql:
            return "\n".join(
                f"{version}\t{checksum}"
                for version, checksum in sorted(self.applied.items())
            )
        if sql.startswith("INSERT INTO schema_migrations"):
            version = sql.split("VALUES ('", maxsplit=1)[1].split("'", maxsplit=1)[0]
            checksum = sql.split("', '", maxsplit=1)[1].split("'", maxsplit=1)[0]
            self.applied[version] = checksum
        return ""


def test_load_migrations_in_filename_order(tmp_path: Path) -> None:
    _write(tmp_path, "0002_second.sql", "SELECT 2")
    _write(tmp_path, "0001_first.sql", "SELECT 1")

    migrations = load_migrations(tmp_path)

    assert [migration.version for migration in migrations] == [
        "0001_first",
        "0002_second",
    ]
    assert all(len(migration.checksum) == 64 for migration in migrations)


def test_status_marks_pending_and_applied(tmp_path: Path) -> None:
    first = _write(tmp_path, "0001_first.sql", "SELECT 1")
    second = _write(tmp_path, "0002_second.sql", "SELECT 2")
    first_checksum = load_migrations(tmp_path)[0].checksum
    client = FakeClickHouseClient(applied={"0001_first": first_checksum})

    statuses = migration_statuses(client, tmp_path)

    assert [status.state for status in statuses] == ["applied", "pending"]
    assert [status.path for status in statuses] == [first, second]
    assert client.sql[0] == METADATA_TABLE_SQL


def test_apply_pending_migrations_records_checksums(tmp_path: Path) -> None:
    _write(tmp_path, "0001_first.sql", "CREATE TABLE first")
    _write(tmp_path, "0002_second.sql", "CREATE TABLE second")
    client = FakeClickHouseClient()

    applied = apply_pending_migrations(client, tmp_path)

    assert [migration.version for migration in applied] == [
        "0001_first",
        "0002_second",
    ]
    assert "CREATE TABLE first" in client.sql
    assert "CREATE TABLE second" in client.sql
    assert set(client.applied) == {"0001_first", "0002_second"}


def test_apply_pending_migrations_is_idempotent(tmp_path: Path) -> None:
    _write(tmp_path, "0001_first.sql", "CREATE TABLE first")
    first_checksum = load_migrations(tmp_path)[0].checksum
    client = FakeClickHouseClient(applied={"0001_first": first_checksum})

    applied = apply_pending_migrations(client, tmp_path)

    assert applied == []
    assert "CREATE TABLE first" not in client.sql


def test_checksum_mismatch_is_fatal(tmp_path: Path) -> None:
    _write(tmp_path, "0001_first.sql", "CREATE TABLE first")
    client = FakeClickHouseClient(applied={"0001_first": "not-the-current-checksum"})

    with pytest.raises(MigrationError, match="checksum mismatch"):
        apply_pending_migrations(client, tmp_path)


def test_missing_migrations_directory_is_fatal(tmp_path: Path) -> None:
    with pytest.raises(MigrationError, match="does not exist"):
        load_migrations(tmp_path / "missing")


def test_repo_migrations_include_service_dashboard_read_models() -> None:
    migrations = load_migrations(REPO_MIGRATIONS_DIR)
    migration_by_version = {migration.version: migration for migration in migrations}

    assert list(migration_by_version) == [
        "0001_idp_telemetry_store_v1",
        "0002_service_dashboard_read_models",
    ]

    service_migration = migration_by_version["0002_service_dashboard_read_models"].sql
    expected_objects = [
        "service_latest_agent_status_v1",
        "service_latest_agent_status_mv_v1",
        "service_latest_source_connection_v1",
        "service_latest_source_connection_mv_v1",
        "service_point_inventory_v1",
        "service_point_inventory_mv_v1",
        "service_telemetry_activity_1m_v1",
        "service_telemetry_activity_1m_mv_v1",
    ]

    for object_name in expected_objects:
        assert object_name in service_migration
    assert (
        "AggregateFunction(argMax, String, "
        "Tuple(DateTime64(3, 'UTC'), DateTime64(3, 'UTC')))"
    ) in service_migration
    assert (
        "argMaxState(toString(source_config_revision), tuple(ts, ingested_at))"
        in service_migration
    )
    assert "ALTER TABLE telemetry_events_v1" not in service_migration
    assert "DROP TABLE" not in service_migration


def _write(directory: Path, name: str, sql: str) -> Path:
    path = directory / name
    path.write_text(sql, encoding="utf-8")
    return path
