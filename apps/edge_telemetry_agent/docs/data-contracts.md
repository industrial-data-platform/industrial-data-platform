# Контракты данных edge-telemetry-agent

Дата: 2026-05-02
Статус: guide

Этот документ является guide-ом по контрактам `edge_telemetry_agent`.
Канонический source of truth для схем находится в
[`docs/contracts/edge-telemetry-agent/`](../../../docs/contracts/edge-telemetry-agent/).

## Где искать полные контракты

| Область | Source of truth |
| --- | --- |
| Bootstrap-конфигурация агента | `docs/contracts/edge-telemetry-agent/schemas/edge.bootstrap-config.v1.schema.json` |
| Retained agent runtime/source configs | `docs/contracts/edge-telemetry-agent/schemas/idp.edge.agent-runtime-config.v1.schema.json`, `docs/contracts/edge-telemetry-agent/schemas/idp.edge.source-config.v1.schema.json` |
| Каноническое telemetry event внутри edge-telemetry-agent | `docs/contracts/edge-telemetry-agent/schemas/edge.telemetry-event.v1.schema.json` |
| SQLite Point State Cache | `docs/contracts/edge-telemetry-agent/schemas/edge.sqlite-point-state-cache.v1.schema.json` |
| SQLite Delivery Outbox | `docs/contracts/edge-telemetry-agent/schemas/edge.sqlite-outbox-record.v1.schema.json` |
| MQTT messages и topic tree | `docs/contracts/edge-telemetry-agent/README.md` и `docs/contracts/edge-telemetry-agent/mqtt-topic-tree.v1.md` |
| Revision-модель agent runtime/source config | `docs/contracts/edge-telemetry-agent/config-revision-model.md` |

## Runtime dataflow

```text
Observation
  -> Bootstrap Config
  -> Retained Agent Runtime Config
  -> Retained Source Configs by source_id
  -> Protocol Decoder / Normalizer
  -> In-memory Last Value Cache
  -> SQLite Point State Cache
  -> Change Filter
  -> SQLite Delivery Outbox
  -> Delivery Worker
  -> MQTT topic tree
```

## Основные правила

- `event_id` является непрозрачной непустой строкой для дедупликации, а не UUID-only типом.
- `tenant_id` приходит из retained agent runtime config и публикуется в MQTT telemetry payload как claim.
- `source_config_revision` связывает telemetry event с retained source config.
- `point_key` строится как обратимое percent-encoding от `point_ref`.
- `command` points по умолчанию не публикуются как telemetry, если `publish.enabled` не задан явно.
- `storage.sqlite_path` указывает на локальное техническое SQLite-хранилище агента, а не только на outbox.
- SQLite на edge не является историческим архивом телеметрии и не заменяет `Telemetry Store`.
- `SQLite Point State Cache` используется для warm restart, change filtering и восстановления sequence.
- Agent runtime/source configs публикуются через `idp_config_registry`,
  Kafka delivery log и Redpanda Connect projection как retained MQTT messages.
- В текущей реализации edge-telemetry-agent публикует telemetry; config status и operational status остаются следующей фазой.

## Связанные документы

- [`mqtt-topics.md`](./mqtt-topics.md) — guide по MQTT publish contract.
- [`ADR-005`](../../../docs/architecture/adrs/ADR-005-mqtt-event-transport.md) — решение по MQTT transport.
- [`ADR-008`](../../../docs/architecture/adrs/ADR-008-server-issued-edge-runtime-configuration.md) — целевое решение по server-issued config.
