from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from idp_config_registry.application.use_cases.reference_lookup import (
    RegistryReferenceLookupResult,
)


class RegistryReferenceLookupResponse(BaseModel):
    reference_type: str
    status: str
    display_name: str | None = None
    snapshot_json: dict[str, Any]

    @classmethod
    def from_result(
        cls,
        result: RegistryReferenceLookupResult,
    ) -> RegistryReferenceLookupResponse:
        return cls(
            reference_type=result.reference_type,
            status=result.status,
            display_name=result.display_name,
            snapshot_json=result.snapshot_json,
        )

