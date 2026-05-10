# ADR-014: Data Platform core and module boundaries

Дата: 2026-05-10
Статус: accepted

## Контекст

Текущий репозиторий уже фактически реализует ядро сбора и хранения данных:

- `wm_edge_agent` собирает telemetry рядом с объектом и надежно доставляет события;
- `Config Registry` хранит tenants/assets/agents/sources/points и выпускает edge config delivery records;
- `MQTT -> Redpanda Connect -> Kafka Event Log -> Kafka Connect -> ClickHouse`
  является рабочим local storage/read path;
- `Telemetry Store` и read models уже используются Grafana и integration-тестами.

При этом документация и C4-модель называли центральную систему
`Monitoring & Alarm Platform`, смешивая три разные ответственности:

- сбор, доставка, хранение, контракты и конфигурация данных;
- web monitoring: dashboards, history и operator read UI;
- alarm management: правила, lifecycle, workflow и notifications.

Такое смешение мешает развивать систему как data platform с независимыми
прикладными модулями поверх нее.

## Решение

Центральное ядро системы теперь называется `Industrial Data Platform`.

`Industrial Data Platform` отвечает за:

- northbound ingestion от edge agents;
- server-issued edge config delivery;
- canonical Kafka-compatible event log;
- source config snapshots и enrichment contracts;
- durable storage/read models на ClickHouse;
- transactional registry/config state на PostgreSQL;
- shared identity/platform services, пока они не выделены отдельным ADR.

`Web Monitoring Module` является отдельным прикладным модулем поверх data platform.
Он отвечает за dashboards, history views, latest values, operator read screens и
read-only visualization. Текущий Grafana surface относится к этому модулю.

`Alarm Management Module` является отдельным прикладным модулем поверх data
platform. Он отвечает за rule engine, alarm lifecycle, acknowledgements,
mutes/operator workflow и notification routing. `alarm_history_events_v1` в
ClickHouse остается storage sink в `Telemetry Store`, но writer/owner этого
потока — `Alarm Management Module`.

`Monitoring & Alarm Platform` больше не используется как имя новой центральной
системы. Это deprecated composite boundary для исторических документов, где
раньше вместе назывались data platform, monitoring UI и alarm workflow.

## Совместимость

Первый refactor является `Docs + C4 first` и не меняет runtime identifiers.

Сохраняются без переименования:

- Python packages и entrypoints: `wm_edge_agent`, `wm_config_registry`,
  `wm_clickhouse`;
- Docker Compose service names и image names;
- MQTT topic tree `wm/v1/...`;
- Kafka topics `wm.platform.*`;
- contract ids `wm.edge.*`, `wm.platform.*`, `wm.clickhouse.*`;
- ClickHouse table names и migration files.

Префикс `wm.platform.*` остается стабильным wire-prefix и означает platform
boundary в контрактах, а не старое продуктовое имя `Monitoring & Alarm Platform`.
Его изменение потребовало бы новых версий контрактов и не входит в этот ADR.

## Последствия

Положительные:

- C4-модель отражает реальные границы: data core отдельно, monitoring отдельно,
  alarms отдельно.
- Следующие backend/UI инкременты можно планировать по модулям, не расширяя
  `Config Registry` незаметно до всей платформы.
- Storage, ingestion и contract work можно делать независимо от UX/alarm scope.

Отрицательные:

- В старых ADR останется исторический термин `Monitoring & Alarm Platform`.
- Некоторые runtime имена с `wm-*` сохраняются ради совместимости, поэтому
  продуктовая терминология и wire-prefixes временно различаются.

## Проверки принятия

- LikeC4 содержит `Industrial Data Platform`, `Web Monitoring Module` и
  `Alarm Management Module` как отдельные developed systems.
- `Grafana` и future monitoring frontend находятся в `Web Monitoring Module`.
- `Alarm Rule Engine` и `Notification Service` находятся в
  `Alarm Management Module`.
- `Config Registry`, ingestion, Kafka Event Log, storage writer, ClickHouse и
  PostgreSQL остаются в `Industrial Data Platform`.
- Контрактная документация явно говорит, что `wm.platform.*` не переименовывается
  в рамках этого refactor.
