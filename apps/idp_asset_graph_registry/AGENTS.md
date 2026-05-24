# Asset Graph Registry Agent Guide

Scope: `apps/idp_asset_graph_registry/`.

This package is the Industrial Data Platform Asset Graph Registry. It owns
asset graph nodes, logical attributes, semantic relations, telemetry bindings,
and catalog tree projections accepted by ADR-016.

## Do

- Keep the package, import path, CLI, Docker service, and image names scoped to
  Asset Graph Registry.
- Preserve the clean architecture direction: API routers call application use
  cases; application code depends on ports; infrastructure implements ports.
- Keep PostgreSQL migrations forward-only.
- Keep API/domain surfaces on public codes such as `tenant_code`,
  `asset_graph_node_code`, `attribute_key`, and `point_code`.
- Validate Config Registry references through a lookup boundary, not by
  importing Config Registry infrastructure.

## Do Not

- Do not embed this package inside `idp_config_registry`.
- Do not import `idp_config_registry.infrastructure.*`.
- Do not add SQLAdmin as the Asset Graph authoring surface.
- Do not change MQTT/Kafka/ClickHouse/edge contracts from this package.

## Validation

- `uv run --package idp-asset-graph-registry pytest apps/idp_asset_graph_registry/tests`
- `uv run --group lint ruff check apps/idp_asset_graph_registry`
