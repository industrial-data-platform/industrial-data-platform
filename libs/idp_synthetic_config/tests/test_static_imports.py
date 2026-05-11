from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_IMPORT_ROOTS = {
    "apps",
    "edge_telemetry_agent",
    "idp_config_registry",
    "idp_demo_stack",
    "knx_source_emulator",
}


def test_package_imports_do_not_depend_on_repo_local_runtime_or_demo_packages() -> None:
    package_root = (
        Path(__file__).resolve().parents[1] / "src" / "idp_synthetic_config"
    )
    imported_modules: set[str] = set()

    for path in package_root.rglob("*.py"):
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(module):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module.split(".", 1)[0])

    assert imported_modules.isdisjoint(FORBIDDEN_IMPORT_ROOTS)

