from __future__ import annotations

import re
from enum import StrEnum


class DomainValidationError(ValueError):
    """Raised when an Asset Graph domain value violates V1 constraints."""


class CatalogNodeType(StrEnum):
    FOLDER = "folder"
    ASSET_REF = "asset_ref"
    AGENT_REF = "agent_ref"
    SOURCE_REF = "source_ref"
    REGISTRY_POINT_REF = "registry_point_ref"
    ASSET_GRAPH_NODE_REF = "asset_graph_node_ref"


class ReferenceStatus(StrEnum):
    VALID = "valid"
    STALE = "stale"
    UNKNOWN = "unknown"


class RelationType(StrEnum):
    PART_OF = "partOf"
    LOCATED_IN = "locatedIn"
    HAS_POINT = "hasPoint"
    FEEDS = "feeds"
    MEASURES = "measures"
    CONTROLS = "controls"


class ValueType(StrEnum):
    BOOLEAN = "boolean"
    NUMBER = "number"
    STRING = "string"


_PATH_CODE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,127}$")


def require_non_empty(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise DomainValidationError(f"{field_name} must be non-empty")
    return normalized


def require_path_code(value: str, *, field_name: str) -> str:
    normalized = require_non_empty(value, field_name=field_name)
    if _PATH_CODE_PATTERN.fullmatch(normalized) is None:
        raise DomainValidationError(
            f"{field_name} must match public path-code pattern"
        )
    return normalized


def require_optional_path_code(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    return require_path_code(value, field_name=field_name)
