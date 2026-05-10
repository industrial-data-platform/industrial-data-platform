# Edge Telemetry Agent Guide

Scope: `apps/wm_edge_agent/`.

This package is the on-site Edge Telemetry Agent runtime. It reads retained
agent/source config, processes observations, stores local technical state, and
publishes MQTT telemetry/status messages.

## Do

- Keep `wm_edge_agent` and `wm-edge-agent` stable.
- Treat `docs/contracts/wm-edge-agent/` as the source of truth for MQTT payloads,
  retained config, topic tree, and SQLite local storage contracts.
- Keep local SQLite as technical state only, not historical telemetry storage.
- Keep command points suppressed from production telemetry publication.
- Update edge docs when config, MQTT, CLI, or processing behavior changes.

## Do Not

- Do not add a control/write path from Web Monitoring UI into production data
  flow.
- Do not derive tenant identity from MQTT topic paths; tenant comes from
  server-issued config and payload claims.
- Do not change MQTT topic templates without updating contracts and integration
  tests.

## Validation

- `uv run --package wm-edge-agent pytest apps/wm_edge_agent/tests`
- For MQTT path:
  `uv run --group integration pytest tests/integration/test_edge_agent_mqtt_publisher.py tests/integration/test_edge_agent_knx_to_mqtt.py`
