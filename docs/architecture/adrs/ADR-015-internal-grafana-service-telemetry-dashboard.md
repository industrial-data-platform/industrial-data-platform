# ADR-015: Internal Grafana service telemetry dashboards

Дата: 2026-05-23
Статус: proposed

## Контекст

В репозитории уже есть первый `Grafana` surface внутри `Web Monitoring Module`:
локальный provisioned dashboard читает `ClickHouse Telemetry Store` read models
`telemetry_latest_v1`, `telemetry_1m_v1`, `telemetry_1h_v1` и диагностические
таблицы ingestion path.

Следующий операционный шаг — служебный dashboard для platform/service команды,
который показывает состояние телеметрии по всем tenants:

- сколько tenants уже наблюдается платформой;
- сколько agents/sources/points настроено или фактически передает данные;
- какие agents/sources online/offline или stale;
- сколько точек имеет актуальное значение, плохое качество или нет свежих
  наблюдений;
- как выглядят time-series графики выбранных points в разрезе tenant/asset/source;
- где есть ingestion/backfill/dedup проблемы.

Такой dashboard видит cross-tenant данные. Поэтому он не является tenant-facing
UI и не заменяет будущий пользовательский `Web Monitoring Frontend` или
tenant-facing telemetry API.

Есть риск спроектировать dashboard как "одна панель со всеми point series". Для
industrial telemetry это быстро приводит к высокой кардинальности, тяжелым
ClickHouse scans, нечитаемым графикам и перегрузке Grafana. Dashboard должен
давать обзор всей платформы и направленный drilldown, а не пытаться вывести все
точки на один график по умолчанию.

## Бизнес-требования

| ID | Требование |
| --- | --- |
| BR-001 | Нужен общий служебный dashboard состояния системы, который с первого экрана показывает агрегированную статистику по всем tenants. |
| BR-002 | Общая статистика должна показывать количество tenants, assets, agents, sources, configured points, observed points, active/stale points и базовую динамику событий. |
| BR-003 | Служебная команда должна видеть runtime health: online/offline/stale agents, connected/disconnected sources, bad/uncertain quality и задержку поступления данных. |
| BR-004 | Нужны отдельные графики телеметрии, где можно выбрать tenant, asset, agent, source и одну или несколько points через фильтры. |
| BR-005 | Пользователь должен быстро перейти от общей системной статистики к графику конкретной точки без ручного написания SQL. |
| BR-006 | При выборе `All tenants` dashboard должен оставаться обзорным: aggregate, top-N и счетчики, а не вывод всех point series всех tenants. |
| BR-007 | Dashboard set должен быть read-only и предназначен для internal platform/service ролей, а не для tenant/client users. |
| BR-008 | Фильтры должны различать `source_type` как тип протокола/адаптера и `source_id` как конкретный экземпляр source внутри agent. |

## Решение

Создать internal-only набор `Grafana` dashboards внутри
`Web Monitoring Module`.

Первый набор состоит из двух обязательных dashboard types:

- `Service Telemetry Overview` — общий dashboard системы со статистикой по всем
  tenants, agents, sources, points, telemetry flow и health indicators.
- `Telemetry Point Drilldown` — dashboard графиков, где service user выбирает
  `tenant_id`, `asset_id`, `source_type`, `agent_id`, `source_id` и
  `point_key`, а затем смотрит time-series, latest values и quality/event
  distribution.

Dashboard set остается read-only visualization layer поверх `Industrial Data
Platform`:

```text
Service engineer / platform operator
  -> Grafana Service Telemetry Overview / Telemetry Point Drilldown
  -> ClickHouse Telemetry Store read models
  -> telemetry, status, source config snapshots, derived service read models
```

Dashboard set не вводит новый runtime module и не переносит alarm workflow в
`Web Monitoring Module`. Он показывает operational observability по telemetry
path. Правила alarm, acknowledgement, escalation и notifications остаются в
будущем `Alarm Management Module`.

## Dashboard model

Dashboard set строится как общий service overview плюс графический drilldown с
переменными и links, а не как отдельный dashboard на каждого tenant.

`Service Telemetry Overview`:

| Блок | Назначение |
| --- | --- |
| `Service inventory` | tenants, assets, agents, sources, configured points, observed points |
| `Runtime health` | online/offline/stale agents, connected/disconnected sources, bad/uncertain quality |
| `Telemetry flow` | event rate, deduplicated events, raw -> contract -> dedup counts, ingestion latency |
| `Point drilldown` | selected point график, latest value table, quality/event type distribution |
| `Top offenders` | top tenants/sources/points by event rate, stale age, bad quality, missing telemetry |

`Telemetry Point Drilldown`:

| Блок | Назначение |
| --- | --- |
| `Point selector` | chained filters для tenant/asset/source type/agent/source instance/point |
| `Point trends` | time-series выбранных points за dashboard time range |
| `Latest values` | последние значения, quality, value_type, source_config_revision |
| `Quality and events` | distribution по quality/event_type и event rate |
| `Context` | agent/source status и links обратно в общий overview |

Переменные в drilldown dashboard должны быть chained и идти от широкого scope к
узкому. `source_type` означает тип протокола/адаптера, а `source_id` — конкретный
source instance внутри agent:

```text
tenant_id -> asset_id -> source_type -> agent_id -> source_id -> point_key
```

Для нового contract increment `source_type` должен стать controlled enum:

```text
knx | modbus | opc-ua | can
```

Добавление нового protocol/source adapter требует явного расширения этого enum
в canonical schemas/contracts и проверки producers/consumers. В текущем ADR это
фиксируется как архитектурное требование; фактическое изменение JSON Schema,
Config Registry validation и ClickHouse ingestion guards выполняется отдельным
contract change.

`All` допустим для overview/stat panels и bounded top-N таблиц. Для time-series
панелей `All points` не должен означать unbounded rendering всех series. Если
пользователь не выбрал конкретные points, панель должна показывать:

- агрегированный trend;
- top-N points по event rate или bad quality;
- либо пустое/ограниченное состояние с понятным panel description.

## Data access

Первый development increment может использовать текущие ClickHouse views:

- `telemetry_latest_v1` для latest values и observed point count;
- `telemetry_1m_v1` для коротких трендов и event rate;
- `telemetry_1h_v1` для длинных интервалов;
- `telemetry_events_dedup_v1` только для коротких bounded drilldown запросов;
- `agent_status_events_v1` и `source_connection_events_v1` для status history;
- `source_config_snapshots_v1` для сверки source config revisions.

Production dashboard не должен регулярно парсить `points_json` из
`source_config_snapshots_v1` и не должен делать тяжелые joins при каждом refresh.
Перед production hardening нужно добавить contract-backed service read models
или materialized projections для текущего inventory/status:

- latest agent status по `tenant_id + asset_id + agent_id`;
- latest source connection state по `tenant_id + asset_id + agent_id + source_id`;
- current point inventory по
  `tenant_id + asset_id + source_type + agent_id + source_id + point_key`;
- telemetry activity rollups по tenant/source type/source instance/point для
  dashboard counts и top-N.

Имена новых tables/views должны быть зафиксированы в
`docs/contracts/clickhouse/telemetry-store.v1.md` или новой версии контракта до
реализации миграций. Текущие table/view names не переименовываются.

## Best practices

Grafana dashboard design:

- начинать overview dashboard с business/system summary: tenants, agents,
  sources, points, telemetry freshness и quality health;
- держать overview и point investigation раздельными dashboards, связывая их
  dashboard links и shared variable values;
- использовать stat/gauge/table panels для service inventory и health, а
  time-series panels оставлять для trends и point drilldown;
- не показывать все series по умолчанию; для режима `All` использовать
  aggregate, top-N и bounded таблицы;
- задавать panel descriptions для служебных метрик, где важно объяснить
  "observed" vs "configured" semantics;
- держать default time range и refresh interval консервативными, а incident
  mode оформлять отдельной копией или явным override.

Variables and navigation:

- строить chained variables от широкого scope к узкому:
  `tenant_id -> asset_id -> source_type -> agent_id -> source_id -> point_key`;
- разделять `source_type` и `source_id` в UI labels: protocol/adapter type
  против concrete source instance;
- ограничивать option queries через `LIMIT` и предыдущие variable filters;
- не использовать free-text SQL input для internal users, если тот же сценарий
  закрывается variables и dashboard links.

ClickHouse query design:

- для drilldown фильтровать по prefix columns основного sort key:
  `tenant_id`, `asset_id`, `source_id`, `point_key`, затем time range;
- overview counts читать из latest/rollup/service read models, а не из raw
  landing tables;
- для high-frequency global counters и top-N после load PoC использовать
  materialized/incremental read models;
- при joins сначала фильтровать или агрегировать обе стороны, а для current
  metadata использовать `ANY JOIN`, если нужна одна matching row;
- все table panels должны иметь `LIMIT`, а heavy panels должны иметь bounded
  top-N semantics;
- `telemetry_events_dedup_v1` использовать только для коротких drilldown
  запросов до появления production performance read models.

Security and operations:

- dashboards должны быть provisioned from git, `editable=false`, чтобы PR
  review был source of truth для изменений;
- datasource должен работать от read-only ClickHouse пользователя с
  production query limits;
- all-tenant dashboards должны жить в internal folder и не использоваться как
  tenant-facing authorization boundary;
- изменения dashboard JSON должны проходить integration smoke через Grafana API:
  datasource exists, dashboards provisioned, variables present, core queries
  execute against seeded ClickHouse.

## Query rules

Все time-series panels должны использовать dashboard time range:

```sql
WHERE $__timeFilter_ms(bucket_start)
```

или для raw/dedup short drilldown:

```sql
WHERE $__timeFilter_ms(ts)
```

Основной ClickHouse sort key для telemetry сейчас:

```text
(tenant_id, asset_id, source_id, point_key, ts, idempotency_key)
```

Поэтому drilldown queries должны по возможности фильтровать prefix columns в
том же порядке:

```sql
WHERE tenant_id = '$tenant_id'
  AND asset_id = '$asset_id'
  AND source_id = '$source_id'
  AND point_key IN (${point_key:sqlstring})
  AND $__timeFilter_ms(bucket_start)
```

Global overview panels не должны сканировать raw telemetry history на каждый
refresh. Для cross-tenant counts и top-N нужно читать latest/rollup/service
read models. Если dashboard query все же соединяет inventory metadata и
telemetry facts, он должен сначала фильтровать/агрегировать обе стороны и
использовать `ANY JOIN`, когда нужна только одна matching metadata row.

Обязательные ограничения:

- default time range: не шире `now-6h` для live/drilldown dashboard;
- default refresh: не чаще `1m` для production service dashboard, быстрее только
  для incident/debug copy;
- все table panels имеют `LIMIT`;
- all-tenant panels показывают aggregate или top-N, а не все raw rows;
- `FINAL` на больших таблицах допускается только через уже принятые
  correctness-first views или отдельное performance решение после load PoC.

## Security boundary

`Service Telemetry Overview` и `Telemetry Point Drilldown` являются
internal-only dashboards.

Минимальные правила:

- dashboard лежит в служебной папке Grafana, например `Service Operations`;
- anonymous access выключен;
- доступ только у platform/service ролей, не у tenant/client users;
- datasource использует read-only ClickHouse пользователя;
- ClickHouse grants ограничены нужными read models, без write privileges;
- для production profile задаются query limits: timeout, max rows/result rows,
  memory limits и readonly mode;
- provisioned dashboard JSON хранится в git и не редактируется вручную в
  production Grafana.

Важно: Grafana folder permissions ограничивают видимость dashboards, но не
являются row-level security по `tenant_id`. В Grafana OSS viewer внутри
organization может выполнять произвольные datasource queries. Поэтому
tenant-facing dashboards нельзя строить на all-tenant datasource. Для
tenant-facing доступа нужен отдельный design: Web Monitoring API с tenant
authorization, tenant-scoped datasource/organization, database-level policy или
Grafana Enterprise/Cloud data source permissions вместе с backend-side
изоляцией.

## Рассмотренные варианты

Decision drivers:

- быстро дать service-команде all-tenant обзор без разработки нового frontend;
- сохранить `Web Monitoring Module` как read-only visualization boundary;
- не смешивать telemetry observability и alarm workflow;
- не создавать dashboard sprawl на каждого tenant/source;
- не перегрузить ClickHouse/Grafana высококардинальными unbounded series;
- оставить путь к future tenant-facing UI/API без привязки к internal
  all-tenant datasource.

| Вариант | Решение | Почему | Trade-off |
| --- | --- | --- | --- |
| `Service Telemetry Overview` + `Telemetry Point Drilldown` | Принят | Разделяет business/system overview и графики точек; поддерживает all-tenant статистику, фильтры и guided drilldown без копий dashboard на tenant. | Нужно поддерживать links/variables между двумя dashboards и отдельно тестировать оба JSON. |
| Один большой service dashboard со статистикой и графиками | Отклонено | Прост в создании, но смешивает обзор и investigation workflow; при росте числа panels становится тяжелым и плохо читаемым. | Меньше файлов, но хуже UX и выше риск тяжелых запросов по умолчанию. |
| Отдельный dashboard на каждого tenant | Отклонено | Может быть удобен tenant-by-tenant, но не решает all-tenant service overview и быстро создает dashboard sprawl. | Можно использовать позже для curated tenant views, но не как default internal service design. |
| Один график со всеми points всех tenants | Отклонено | Высокая кардинальность, тяжелые scans и нечитаемая визуализация. Нарушает требование, что `All tenants` остается overview mode. | Самый быстрый прототип, но непригоден как устойчивый dashboard pattern. |
| Grafana напрямую читает Config Registry/PostgreSQL для inventory | Отклонено для production default | Config Registry остается transactional source of truth; dashboard должен читать prepared ClickHouse/read models, чтобы не нагружать operational store и не смешивать ownership. | Может быть допустимо как temporary dev/debug query, но не как production dashboard dependency. |
| Сразу строить custom Web Monitoring Frontend | Отклонено для этого инкремента | Полноценный frontend нужен позже для tenant-facing UX и authorization, но текущий запрос — internal service observability, где Grafana уже является принятым surface. | Frontend даст лучший product UX, но дороже и задержит operational visibility. |
| Делать dashboard частью `Alarm Management Module` | Отклонено | Dashboard наблюдает telemetry/status path и не владеет alarm lifecycle, acknowledgement, escalation или notification routing. | Alarm dashboards могут появиться позже, но это отдельное решение поверх Alarm Management use cases. |
| Оставить `source_type` свободной строкой без controlled vocabulary | Отклонено как целевое состояние | Для фильтров и cross-protocol статистики нужен стабильный набор protocol/source adapter types. | Внедрение enum в schemas/validation является отдельным contract change, чтобы не смешивать ADR dashboard scope с wire-compatibility изменением. |

## Последствия

Положительные:

- platform команда получает единый operational обзор по всем tenants;
- Grafana surface развивается в уже принятой границе `Web Monitoring Module`;
- dashboard можно версионировать, тестировать и поставлять через provisioning;
- ClickHouse read models остаются основным способом визуализации telemetry;
- будущий frontend сможет ссылаться на dashboard или встраивать его без смены
  data platform contracts.

Отрицательные:

- нужен отдельный security discipline: all-tenant dashboard нельзя показывать
  tenant users;
- текущие correctness-first query views могут быть тяжелыми на production scale;
- для точных counts configured points/agents потребуется service inventory read
  model, а не ad-hoc JSON parsing;
- без load PoC нельзя считать refresh interval и query shape production-ready.

## План реализации

1. Согласовать ADR и перевести статус в `accepted`.
2. Добавить provisioned dashboard JSON для общего overview:
   `infra/local/grafana/dashboards/service-telemetry-overview.json`.
3. Добавить provisioned dashboard JSON для графиков:
   `infra/local/grafana/dashboards/telemetry-point-drilldown.json`.
4. Добавить chained variables `tenant_id`, `asset_id`, `agent_id`,
   `source_id`, `point_key`.
5. Добавить panels первого инкремента поверх существующих ClickHouse views с
   bounded queries и `LIMIT`.
6. Расширить `tests/integration/test_grafana_clickhouse.py`, чтобы проверять
   provisioning новых dashboards, datasource UID, variables и отсутствие
   MQTT topic coupling.
7. Перед production hardening добавить contract-backed latest/status/inventory
   read models и миграции Telemetry Store.
8. После добавления новых ClickHouse tables/views обновить
   `docs/contracts/clickhouse/telemetry-store.v1.md`, LikeC4 при изменении
   зависимостей и relevant integration tests.

## Проверки принятия

- Dashboard set принадлежит `Web Monitoring Module`, а не `Industrial Data Platform`
  core и не `Alarm Management Module`.
- Dashboards помечены как internal/service и не являются tenant-facing surface.
- Overview dashboard показывает общую статистику системы по tenants, agents,
  sources, points и telemetry health.
- Drilldown dashboard позволяет выбрать `tenant_id`, `asset_id`, `source_type`,
  `agent_id`, `source_id`, `point_key` и посмотреть графики выбранных points.
- `source_type` зафиксирован как controlled enum candidate
  `knx | modbus | opc-ua | can`; его внедрение в schemas/validation выполняется
  отдельным contract change.
- Dashboards поставляются из git через provisioning, `editable=false`.
- Anonymous access выключен в target deployment.
- Datasource user read-only и ограничен ClickHouse query limits.
- Time-series panels используют Grafana time range macros.
- Drilldown panels фильтруют
  `tenant_id -> asset_id -> source_type -> agent_id -> source_id -> point_key`
  или читают prepared rollup/service read models.
- Ни одна default-панель не рисует все points всех tenants как unbounded series.
- Heavy global counters читают latest/rollup/service read models, а не raw
  telemetry history.
- Новые tables/views добавлены в contract docs до реализации.
- Validation для первого dashboard increment:
  `docker compose -f infra/local/compose.yaml config --quiet` и
  `uv run --group integration pytest tests/integration/test_grafana_clickhouse.py`.

## Источники

- Grafana dashboard best practices:
  https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/best-practices/
- Grafana variables:
  https://grafana.com/docs/grafana/latest/visualizations/dashboards/variables/
- Grafana chained variables:
  https://grafana.com/docs/grafana/latest/visualizations/dashboards/variables/add-template-variables/
- Grafana provisioning:
  https://grafana.com/docs/grafana/latest/administration/provisioning/
- Grafana security:
  https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/
- Grafana folder access control:
  https://grafana.com/docs/grafana/latest/administration/roles-and-permissions/folder-access-control/
- Grafana data source management:
  https://grafana.com/docs/grafana/latest/administration/data-source-management/
- Grafana ClickHouse query editor:
  https://grafana.com/docs/plugins/grafana-clickhouse-datasource/latest/query-editor/
- ClickHouse Grafana integration:
  https://clickhouse.com/integrations/grafana
- ClickHouse query optimization:
  https://clickhouse.com/resources/engineering/clickhouse-query-optimisation-definitive-guide
- ClickHouse materialized views:
  https://clickhouse.com/blog/using-materialized-views-in-clickhouse

## ClickHouse rules checked

- `schema-pk-filter-on-orderby`: dashboard drilldown queries должны фильтровать
  sort key prefix columns.
- `schema-pk-prioritize-filters`: future service read models должны проектироваться
  под реальные dashboard filters.
- `query-mv-incremental`: high-frequency dashboard counts и top-N должны перейти
  на incremental/materialized rollups после load PoC.
- `query-join-filter-before`: joins с inventory/status metadata должны
  фильтровать/агрегировать данные до join.
- `query-join-use-any`: `ANY JOIN` подходит для присоединения одной current
  metadata row к telemetry facts.
