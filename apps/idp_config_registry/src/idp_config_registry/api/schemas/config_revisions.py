from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from idp_config_registry.application.use_cases.render_config import (
    RenderedAgentRuntimeConfig,
)


class RenderAgentRuntimeConfigRequest(BaseModel):
    config_revision: str = Field(min_length=1)
    issued_at: datetime
    source_config_revisions: dict[str, str] | None = None


class RenderedSourceConfigResponse(BaseModel):
    source_code: str
    source_config_revision: str
    payload: dict[str, Any]


class RenderAgentRuntimeConfigResponse(BaseModel):
    tenant_code: str
    asset_code: str
    agent_code: str
    config_revision: str
    agent_runtime_payload: dict[str, Any]
    source_payloads: list[RenderedSourceConfigResponse]
    outbox_record_count: int

    @classmethod
    def from_rendered(cls, rendered: RenderedAgentRuntimeConfig) -> RenderAgentRuntimeConfigResponse:
        agent_runtime_payload = rendered.agent_runtime_payload
        return cls(
            tenant_code=rendered.tenant_code,
            asset_code=rendered.asset_code,
            agent_code=rendered.agent_code,
            config_revision=str(agent_runtime_payload["config_revision"]),
            agent_runtime_payload=dict(agent_runtime_payload),
            source_payloads=[
                RenderedSourceConfigResponse(
                    source_code=source.source_code,
                    source_config_revision=source.source_config_revision,
                    payload=dict(source.payload),
                )
                for source in rendered.source_payloads
            ],
            outbox_record_count=1 + len(rendered.source_payloads),
        )
