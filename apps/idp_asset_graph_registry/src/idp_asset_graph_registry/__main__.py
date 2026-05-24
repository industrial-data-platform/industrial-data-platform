from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from idp_asset_graph_registry.settings import AssetGraphRegistrySettings


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    command = args.command or "serve"
    if command == "serve":
        _serve(reload=getattr(args, "reload", False))
        return
    parser.error(f"Unknown command {command!r}")


def _serve(*, reload: bool = False) -> None:
    settings = AssetGraphRegistrySettings.from_env()
    package_source_dir = Path(__file__).resolve().parents[1]
    uvicorn.run(
        "idp_asset_graph_registry.main:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        reload=reload,
        reload_dirs=[str(package_source_dir)] if reload else None,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="idp-asset-graph-registry")
    subparsers = parser.add_subparsers(dest="command")
    serve_parser = subparsers.add_parser(
        "serve",
        help="Run the Asset Graph Registry HTTP API",
    )
    serve_parser.add_argument(
        "--reload",
        action="store_true",
        help="Reload the HTTP API when Asset Graph Registry source files change",
    )
    return parser


if __name__ == "__main__":
    main()

