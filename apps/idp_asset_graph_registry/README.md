# idp-asset-graph-registry

First backend slice for the ADR-016 `Asset Graph Registry` boundary.

The package owns asset graph nodes, logical attributes, semantic relations,
telemetry bindings, and the default `Catalog V1` tree projection. It is a
separate Industrial Data Platform runtime/package boundary, not an embedded
slice of `idp_config_registry`.

Stable identifiers for this package:

- import path: `idp_asset_graph_registry`
- package/distribution: `idp-asset-graph-registry`
- CLI entrypoint: `idp-asset-graph-registry`

Implemented V1 surface:

- `GET /health`
- `GET /ready`
- `GET /internal/vocabulary/relation-types`
- `GET /internal/tenants/{tenant_code}/catalog/default/tree`
- `POST /internal/tenants/{tenant_code}/catalog/default/nodes`
- `PATCH /internal/tenants/{tenant_code}/catalog/default/nodes/{node_code}`
- `POST /internal/tenants/{tenant_code}/catalog/default/nodes/{node_code}/move`
- `DELETE /internal/tenants/{tenant_code}/catalog/default/nodes/{node_code}`
- `POST /internal/tenants/{tenant_code}/asset-graph/nodes`
- `GET /internal/tenants/{tenant_code}/asset-graph/nodes`
- `GET /internal/tenants/{tenant_code}/asset-graph/nodes/{asset_graph_node_code}`
- `PATCH /internal/tenants/{tenant_code}/asset-graph/nodes/{asset_graph_node_code}`
- `DELETE /internal/tenants/{tenant_code}/asset-graph/nodes/{asset_graph_node_code}`
- `POST /internal/tenants/{tenant_code}/asset-graph/nodes/{asset_graph_node_code}/attributes`
- `GET /internal/tenants/{tenant_code}/asset-graph/nodes/{asset_graph_node_code}/attributes`
- `GET /internal/tenants/{tenant_code}/asset-graph/nodes/{asset_graph_node_code}/attributes/{attribute_key}`
- `PATCH /internal/tenants/{tenant_code}/asset-graph/nodes/{asset_graph_node_code}/attributes/{attribute_key}`
- `DELETE /internal/tenants/{tenant_code}/asset-graph/nodes/{asset_graph_node_code}/attributes/{attribute_key}`
- `POST /internal/tenants/{tenant_code}/asset-graph/relationships`
- `GET /internal/tenants/{tenant_code}/asset-graph/relationships`
- `GET /internal/tenants/{tenant_code}/asset-graph/relationships/{relationship_code}`
- `PATCH /internal/tenants/{tenant_code}/asset-graph/relationships/{relationship_code}`
- `DELETE /internal/tenants/{tenant_code}/asset-graph/relationships/{relationship_code}`
- `POST /internal/tenants/{tenant_code}/asset-graph/telemetry-bindings`
- `GET /internal/tenants/{tenant_code}/asset-graph/telemetry-bindings`
- `GET /internal/tenants/{tenant_code}/asset-graph/telemetry-bindings/{binding_code}`
- `PATCH /internal/tenants/{tenant_code}/asset-graph/telemetry-bindings/{binding_code}`
- `DELETE /internal/tenants/{tenant_code}/asset-graph/telemetry-bindings/{binding_code}`

The API uses public codes. Internal UUIDs, when present in PostgreSQL, remain
storage-only details.

Run tests:

```bash
uv run --package idp-asset-graph-registry pytest apps/idp_asset_graph_registry/tests
```

Run locally without PostgreSQL:

```bash
uv run --package idp-asset-graph-registry idp-asset-graph-registry
```

Run with PostgreSQL:

```bash
ASSET_GRAPH_REGISTRY_DATABASE_URL=postgresql+asyncpg://idp:change-me-local-postgres@localhost:5432/idp_config_registry \
  uv run --package idp-asset-graph-registry idp-asset-graph-registry
```

Migrations:

```bash
ASSET_GRAPH_REGISTRY_DATABASE_URL=postgresql+asyncpg://idp:change-me-local-postgres@localhost:5432/idp_config_registry \
  uv run --package idp-asset-graph-registry alembic \
  -c apps/idp_asset_graph_registry/alembic.ini upgrade head
```

When `ASSET_GRAPH_CONFIG_REGISTRY_URL` is set, Config Registry references are
validated through its internal read-only lookup API. Without that setting, the
service uses an in-process permissive lookup for standalone package tests and
local smoke checks.
