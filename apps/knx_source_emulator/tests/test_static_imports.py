from __future__ import annotations

from pathlib import Path


def test_knx_source_emulator_does_not_import_edge_telemetry_agent() -> None:
    src_dir = Path(__file__).resolve().parents[1] / "src" / "knx_source_emulator"
    for path in src_dir.rglob("*.py"):
        assert "edge_telemetry_agent" not in path.read_text(encoding="utf-8")
