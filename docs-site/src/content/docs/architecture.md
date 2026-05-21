---
title: Architecture
description: Current architecture reading path for the Industrial Data Platform.
---

The current system boundary is:

- `Industrial Data Platform`: ingestion, delivery, Kafka Event Log, contracts,
  Config Registry, ClickHouse Telemetry Store, PostgreSQL Platform Store, and
  local infrastructure.
- `Edge Telemetry Agent`: on-site runtime for southbound reads, normalization,
  local buffering, and telemetry/status publishing.
- `Web Monitoring Module`: dashboards, history, latest values, and read-only
  visualization over data-platform read models.
- `Alarm Management Module`: planned rules, lifecycle, workflow, and
  notifications above the data platform.

## Core files

- `docs/architecture/current-state.md`: operational snapshot for humans and
  agents.
- `docs/architecture/solution-architecture.md`: target architecture, dataflow,
  deployment modes, and runtime scenarios.
- `docs/architecture/glossary.md`: canonical terms and boundaries.
- `docs/architecture/open-questions.md`: live unresolved product and operations
  decisions.
- `docs/architecture/hierarchical-catalog-v1.md`: working plan for the first
  tree projection inside the Digital Twin / Asset Graph Registry boundary.
- `docs/architecture/adrs/ADR-016-digital-twin-asset-graph-boundary.md`:
  accepted boundary decision for the separate Digital Twin / Asset Graph
  Registry service/package.
- `docs/architecture/adrs/ADR-015-hierarchical-catalog-runtime-boundary.md`:
  superseded comparison material for the Catalog V1 versus Digital Twin / Asset
  Graph boundary discussion.
- `arch/README.md`: LikeC4 model entrypoint and commands.

## Rules

- Do not reintroduce `Monitoring & Alarm Platform` as the current central
  system name.
- Keep `Industrial Data Platform` as the core data collection, delivery,
  contracts, configuration, and storage boundary.
- Keep `Web Monitoring Module` and `Alarm Management Module` as modules above
  the data platform.
- Do not add Alarm Management runtime code until alarm use cases are selected.
