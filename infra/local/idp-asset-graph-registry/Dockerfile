FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md ./
COPY apps/edge_telemetry_agent ./apps/edge_telemetry_agent
COPY apps/idp_asset_graph_registry ./apps/idp_asset_graph_registry
COPY apps/idp_config_registry ./apps/idp_config_registry
COPY apps/knx_demo ./apps/knx_demo
COPY apps/knx_source_emulator ./apps/knx_source_emulator
COPY libs/idp_demo_stack ./libs/idp_demo_stack
COPY libs/idp_synthetic_config ./libs/idp_synthetic_config
COPY libs/knx_project_parser ./libs/knx_project_parser
COPY tools/idp_telemetry_store ./tools/idp_telemetry_store
COPY docs ./docs

RUN uv sync --frozen --package idp-asset-graph-registry --no-dev

CMD ["idp-asset-graph-registry", "serve"]
