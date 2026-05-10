# Текущее состояние системы

Дата: 2026-05-10
Статус: working snapshot

Этот документ является коротким operational snapshot для людей и AI-agent.
Он описывает текущее состояние системы без истории решений. История и trade-off
остаются в `docs/architecture/adrs/`.

## Статус MVP

Проект уже достиг `MVP baseline`.

Под `MVP` в текущем репозитории понимается не “полная платформа во всех
компонентах”, а уже реализованный рабочий baseline:

- `Edge Telemetry Agent`
- server-issued agent runtime config через retained `MQTT`
- reliable telemetry delivery через `MQTT`
- локальный ingestion slice `MQTT -> Redpanda Connect -> Apache Kafka`
- versioned config bundle и integration-тесты для этого контура

Поверх этого baseline в текущей ветке уже реализованы первые data-platform
foundation инкременты: `Config Registry` на `PostgreSQL`, Kafka-first config
delivery, локальный `ClickHouse Telemetry Store` path и `Grafana` read-model
surface как первый `Web Monitoring Module` surface.

## Назначение

Система строится прежде всего как `Industrial Data Platform`: промышленное ядро
сбора, доставки, конфигурации и хранения данных. `Web Monitoring` и
`Alarm Management` являются отдельными модулями поверх этого ядра.

Целевая линия:

- `Edge Telemetry Agent` работает рядом с объектом автоматизации.
- Agent читает данные из southbound-источников, нормализует наблюдения,
  фильтрует изменения, хранит техническое состояние в SQLite и доставляет
  события наружу.
- `Industrial Data Platform` принимает поток, валидирует и обогащает его,
  пишет события в Kafka-compatible event log и хранилища, а прикладные модули
  читают подготовленные данные и используют shared platform services.
- `Industrial Data Platform` должна поддерживать два deployment modes:
  `self-hosted` и `cloud`, без расхождения по основным contracts и data path.
- Первый post-MVP пилот запускается cloud-first в российском облаке (`VK Cloud`
  или `Yandex Cloud`), потому что on-prem/self-hosted инфраструктура первых
  заказчиков пока не готова.

## Что реализовано сейчас

- Monorepo с Python workspace, LikeC4-моделью, архитектурными документами и
  contract registry.
- `Edge Telemetry Agent` с bootstrap config, загрузкой retained agent runtime/source
  config из MQTT, fail-fast validation и CLI:
  `check-config`, `show-config`, `enqueue-demo-event`, `deliver-once`.
- Runtime-модель `tenant_id`, `asset_id`, `agent_id`, `source_id`,
  `point_ref`, `point_key`, `config_revision` и `source_config_revision`.
- Processing pipeline для observation -> normalized telemetry event:
  подавление непубликуемых `command`-точек, threshold/change filtering,
  sequence/value metadata и quality.
- `SQLite` technical state: point state cache и delivery outbox для retry.
- MQTT delivery slice для telemetry events, source connection status и agent LWT.
- Demo/config bundle для `demo-stand` и первый `KNX`-срез.
- `Config Registry` foundation: FastAPI backend на clean architecture,
  PostgreSQL persistence, Alembic migrations, transactional outbox и Kafka
  config delivery publisher.
- Local development stack: MQTT broker, Apache Kafka, Redpanda Connect
  ingestion/config projection pipelines, PostgreSQL, ClickHouse, Kafka Connect
  и provisioned Grafana.
- `Kafka Event Log` зафиксирован как логический Kafka-compatible event stream:
  локальный broker runtime сейчас `Apache Kafka`, а `Redpanda broker` остается
  candidate после отдельного compatibility PoC.
- `docs/contracts/` как канонический каталог схем, topic names, Kafka topics,
  ClickHouse contract tables и boundary rules.

## Что остается post-MVP развитием

- Расширение `Industrial Data Platform` от текущего `MVP baseline` до
  production-инсталляции: production `MQTT Ingestion Gateway`, production
  Kafka-compatible broker runtime, storage writer/Kafka Connect,
  `Streaming Analytics`, `Telemetry Store`, `Platform Store`, `Config Registry`
  и shared IAM. Локально уже есть foundation-срезы `Config Registry`,
  `ClickHouse`, `Kafka Connect` и `Grafana`, но core runtime еще не доведен до
  production-grade.
- Развитие `Web Monitoring Module`: Grafana/read dashboards уже представлены
  локально, полноценный monitoring frontend и tenant-facing read API остаются
  следующим модульным слоем поверх data platform.
- Развитие `Alarm Management Module`: `Alarm Rule Engine`, alarm lifecycle,
  current alarm workflow state и `Notification Service` являются отдельным
  модулем поверх data platform, а не частью ingestion/storage core.
- Production hardening существующих foundation stores: `ClickHouse` как
  `Telemetry Store` и `PostgreSQL` как `Platform Store` уже представлены в
  локальном dev/integration контуре, но не доведены до production sizing,
  backup/restore, HA и операционных процедур.
- Расширение `Config Registry` от текущего foundation-среза до tenant-facing
  data-platform backend: authn/authz, richer revision workflow, rollout controls,
  approval/publish process и API boundaries beyond current internal/backoffice
  scope.
- Tenant-facing UI для редактирования agent runtime/source config. На текущем этапе
  source of truth уже переехал в `Config Registry`/`PostgreSQL`, а versioned
  YAML bundle остается import/bootstrap path; полноценный внешний UI и workflow
  публикации остаются следующими шагами.
- Расширение southbound-адаптеров. Текущий практический срез остается
  `KNX-first`, а следующий выбранный protocol track — `OPC UA read-only
  ingestion`: `wm_edge_agent` работает как `OPC UA client` и только считывает
  данные из `OPC UA server`. `Modbus TCP`, `DB` и другие источники остаются
  future adapters.
- Production security hardening: TLS/certificates/ACL/secrets lifecycle,
  конкретные broker policies, production observability и support workflows.

## Production Boundaries

В production data path система является read-only контуром сбора и хранения
данных:

- wm-edge-agent читает и наблюдает сигналы;
- управляющие команды из Web Monitoring UI/API не входят в первый продуктовый
  scope;
- технические platform writes для telemetry/status storage, config revisions,
  outbox, audit и alarm workflow state остаются частью платформы;
- полноценная `SCADA/HMI` не входит в текущий объем;
- автоматическое полное discovery всех тегов и информационных моделей не
  входит в текущий объем;
- edge SQLite не является историческим архивом телеметрии;
- локальный `MQTT/Kafka` stack является dev/integration slice, а не полной
  production platform.

Для `Industrial Data Platform` действуют дополнительные границы deployment-модели:

- `self-hosted` и `cloud` считаются двумя вариантами поставки одной и той же
  `Industrial Data Platform` с модулями поверх нее, а не двумя разными
  архитектурами;
- первый pilot target для `Industrial Data Platform` — cloud-first в российском
  облаке; self-hosted/on-prem остается целевым mode после cloud validation и
  готовности инфраструктуры заказчика;
- baseline contracts, основной ingestion/data path и acceptance criteria должны
  совпадать между deployment modes;
- cloud-managed optimization допустима только если она не создает отдельный
  cloud-only contract path и не ломает parity с `self-hosted`.
- локальная `Docker Compose` infra является обязательным dev/test baseline для
  integration-тестов, smoke-тестов, onboarding и воспроизведения инцидентов, но
  не считается production target первого пилота.

Отдельный пилот `KNX -> OPC` может иметь write-path из внешнего OPC-клиента,
но это отдельный сервисный контур, не основной data-platform data path.

## Source Of Truth

| Область | Source of truth |
| --- | --- |
| Текущий снимок системы | `docs/architecture/current-state.md` |
| История решений и trade-off | `docs/architecture/adrs/` |
| Карта систем и контейнеров | `arch/likec4/` |
| Термины | `docs/architecture/glossary.md` |
| Открытые вопросы | `docs/architecture/open-questions.md` |
| Контракты данных и topic/table names | `docs/contracts/` |
| Edge guide-документация | `apps/wm_edge_agent/docs/` |
| Demo/agent runtime config bundle | `environments/demo-stand/wm_edge_agent/` |
| Execution backlog, приоритеты и статусы | internal `YouTrack` |

## ADR Reading Guide

Для большинства задач агенту не нужно читать все ADR. Используйте такой порядок:

1. Для ориентации: этот документ и `docs/architecture/glossary.md`.
2. Для edge agent runtime config: `ADR-008`, затем `docs/contracts/wm-edge-agent/`.
3. Для MQTT delivery и topic tree: `ADR-005`, затем
   `docs/contracts/wm-edge-agent/mqtt-topic-tree.v1.md`.
4. Для identity model: `ADR-004`.
5. Для границ data platform, web monitoring и alarms: `ADR-014`.
6. Для storage/platform design: `ADR-007`, затем `docs/contracts/clickhouse/`
   и `docs/contracts/kafka/`.
7. Для deployment parity `self-hosted`/`cloud`: `ADR-009`, затем `ADR-013` для
   cloud-first pilot и local Docker infra policy.
8. Для backend хранения настроек платформы: `ADR-010`.
9. Для post-MVP product/pilot governance, `OPC UA` read-only track и internal
   `YouTrack`: `ADR-013`.
10. Для KNX-first MVP behavior: `ADR-001`, `ADR-002`, `ADR-003`.

Если ADR и `docs/contracts/` расходятся по полям сообщения, topic/table names
или schema details, приоритет у `docs/contracts/`. ADR объясняет решение, но не
заменяет contract registry.

## Next Decisions

Ближайшие развилки ведутся в `docs/architecture/open-questions.md`. Критичные
темы сейчас:

- production MQTT broker, TLS, ACL и secrets handling;
- limits и lifecycle для retained agent runtime/source config;
- эволюция YAML config bundle из import/bootstrap path в полностью data-platform-led
  authoring workflow;
- concrete `VK Cloud` vs `Yandex Cloud` choice, managed-service packaging and
  secrets backend for the cloud-first pilot;
- production host/deployment model для edge runtime.
