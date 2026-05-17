# idp-synthetic-config

Reusable synthetic configuration generator and Config Registry seeder for local
Industrial Data Platform scenarios.

The package has two layers:

- `generator`: deterministic, side-effect-free synthetic mall model generation.
- `config_registry_seeder`: stdlib HTTP client and seeding workflow for Config
  Registry API records plus `render-config`.

It does not import `idp_demo_stack`, `apps/*`, `edge_telemetry_agent`,
`idp_config_registry`, or a future KNX emulator package.

## CLI

```bash
uv run --package idp-synthetic-config idp-synthetic-config plan --format json
uv run --package idp-synthetic-config idp-synthetic-config plan --format yaml
uv run --package idp-synthetic-config idp-synthetic-config seed --config-registry-url http://localhost:8000
uv run --package idp-synthetic-config idp-synthetic-config delete --config-registry-url http://localhost:8000
```

Default generation is intentionally small for local smoke runs: `3` devices and
`10` tags per device. The upper local load/dev profile is `100 x 100`.

`seed` evaluates a local reset policy by default. Non-local targets refuse
destructive reset unless `--allow-destructive-reset` is provided. The current
Config Registry API exposes an agent-scoped registry graph cleanup endpoint, so
the seeder clears generated config outbox records, rendered config revisions,
points, sources, agent, and empty parent asset/tenant records in one request
before recreating the desired model. ClickHouse and MQTT retained cleanup are
reported in the machine-readable reset summary as `unsupported` when configured;
they are not executed by this package yet.

`delete` uses the same generated codes and calls the Config Registry
`DELETE /tenants/{tenant_code}/assets/{asset_code}/agents/{agent_code}/registry-graph`
API with `delete_empty_asset=true&delete_empty_tenant=true`. This is the
operator path for undoing a synthetic seed without direct database access.
