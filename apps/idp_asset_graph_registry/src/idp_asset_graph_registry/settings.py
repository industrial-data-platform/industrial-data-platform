from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AssetGraphRegistrySettings:
    host: str = "127.0.0.1"
    port: int = 8010
    database_url: str | None = None
    config_registry_url: str | None = None

    @classmethod
    def from_env(cls) -> AssetGraphRegistrySettings:
        return cls(
            host=os.getenv("ASSET_GRAPH_REGISTRY_HOST", "127.0.0.1"),
            port=int(os.getenv("ASSET_GRAPH_REGISTRY_PORT", "8010")),
            database_url=os.getenv("ASSET_GRAPH_REGISTRY_DATABASE_URL"),
            config_registry_url=os.getenv("ASSET_GRAPH_CONFIG_REGISTRY_URL"),
        )

