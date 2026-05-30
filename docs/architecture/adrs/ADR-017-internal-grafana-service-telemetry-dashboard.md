# ADR-017: Internal Grafana service telemetry dashboards

Дата: 2026-05-23
Статус: принято

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
| BR-002 | Общая статистика должна показывать количество tenants, assets, agents, sources, observed/current points, active/stale points и базовую динамику событий; configured points показываются только после появления config/inventory-backed read model. |
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
  -> telemetry/status facts and contract-backed service read models
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
| `Service inventory` | tenants, assets, agents, sources, observed/current points; configured points только после config/inventory-backed read model |
| `Runtime health` | online/offline/stale agents, connected/disconnected sources, bad/uncertain quality |
| `Telemetry flow` | event rate, deduplicated events, raw -> contract -> dedup counts, ingestion latency |
| `Point drilldown` | selected points график, latest value table, quality/event type distribution |
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

## Relation to Asset Graph Registry

Этот ADR фиксирует первый internal/service increment для технической
observability по raw telemetry identity. Он не является целевой semantic
monitoring model и не заменяет принятое решение
[`ADR-016: Asset Graph Registry boundary`](ADR-016-asset-graph-registry-boundary.md).

`Asset Graph Registry` владеет объектной моделью: `asset graph node`,
logical attributes, semantic relations и telemetry bindings. Telemetry binding
связывает technical point/series identity (`point_code`,
`source_id + point_key`, ClickHouse/Kafka series) с logical attribute:
`asset_graph_node_code + attribute_key`.

Будущий tenant-facing `Web Monitoring Frontend` и semantic monitoring/API
должны уметь идти от смыслового объекта, а не только от source/point:

```text
building / area / machine / component
  -> attribute
  -> telemetry binding
  -> ClickHouse latest/history
```

Эквивалентный machine-readable path:

```text
asset_graph_node_code -> attribute_key -> telemetry binding -> ClickHouse latest/history
```

Grafana service dashboards в этом решении остаются technical/internal. Они
могут читать prepared semantic read models в будущем, но не должны дергать
`Asset Graph Registry` API на каждый panel refresh. Если появится semantic
Grafana/dashboard surface, binding должен быть заранее материализован в
contract-backed ClickHouse read model/projection, которой владеет `Telemetry
Store` / `Industrial Data Platform`.

Для будущего contract increment `source_type` должен получить controlled
vocabulary. Начальные кандидаты для этого vocabulary:

```text
knx | modbus | opc-ua | can
```

Добавление нового protocol/source adapter должно проходить через явное
расширение canonical schemas/contracts и проверку producers/consumers. В текущем
ADR это фиксируется как архитектурное направление и candidate vocabulary, а не
как contract change. Фактическое изменение JSON Schema, Config Registry
validation, ClickHouse storage type/ingestion guards и compatibility policy
выполняется отдельным contract change.

`All` допустим для overview/stat panels и bounded top-N таблиц. Для time-series
панелей `All points` не должен означать unbounded rendering всех series. Если
пользователь не выбрал конкретные points, панель должна показывать:

- агрегированный trend;
- top-N points по event rate или bad quality;
- либо пустое/ограниченное состояние с понятным panel description.

## Data access

Текущий implementation increment использует contract-backed service read models
для production-heavy dashboard refresh paths:

- `service_latest_agent_status_v1` для latest agent status по
  `tenant_id + asset_id + agent_id`;
- `service_latest_source_connection_v1` для latest source connection state по
  `tenant_id + asset_id + agent_id + source_id`;
- `service_point_inventory_v1` для current observed point inventory по
  `tenant_id + asset_id + source_type + agent_id + source_id + point_key`;
- `service_telemetry_activity_1m_v1` для telemetry activity rollups по
  tenant/source type/source instance/point для dashboard counts, top-N и
  selected-point event rate.

Bounded drilldown остается на существующих correctness-first views, когда нужна
value-level или event-level история:

- `telemetry_latest_v1` для latest values;
- `telemetry_events_dedup_v1` для коротких bounded drilldown запросов,
  включая raw numeric/boolean samples выбранных points.

Production dashboard не должен регулярно парсить `points_json` из
`source_config_snapshots_v1` и не должен делать тяжелые joins при каждом refresh.
`source_config_snapshots_v1` может использоваться для debug/audit сценариев, но
не является refresh path для service overview.

Ownership этих read models остается за `Telemetry Store` /
`Industrial Data Platform`. `Web Monitoring Module` владеет dashboard JSON,
variables, links и read-only visualization workflow, но не storage contract,
ClickHouse migrations или ingestion semantics. Grafana только читает
contract-backed read models.

Имена новых tables/views должны быть зафиксированы в
`docs/contracts/clickhouse/telemetry-store.v1.md` или новой версии контракта до
реализации миграций. Текущие table/view names не переименовываются.

Current implementation должен явно различать метрики:

- `observed_points` / current point inventory считается из
  `service_point_inventory_v1`;
- `configured_points` нельзя считать production-ready метрикой из
  `points_json` на каждый refresh; она появляется только после
  config/inventory-backed service read model, который отражает configured
  inventory, а не только наблюдаемую telemetry.

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
- `source_type` и `agent_id` использовать для variable option queries и
  narrowing через inventory/service read models; telemetry panels должны
  получать уже суженные `source_id` и `point_key`, чтобы не обходить sort-key
  prefix;
- overview counts читать из latest/rollup/service read models, а не из raw
  landing tables;
- для high-frequency global counters и top-N после load PoC использовать
  materialized/incremental read models;
- при joins сначала фильтровать или агрегировать обе стороны, а для current
  metadata использовать `ANY JOIN`, если нужна одна matching row;
- все table panels должны иметь `LIMIT`, а heavy panels должны иметь bounded
  top-N semantics;
- `telemetry_events_dedup_v1` использовать только для коротких bounded drilldown
  запросов, где нужна event-level история.

Security and operations:

- dashboards должны быть provisioned from git, `editable=false`, чтобы PR
  review был source of truth для изменений;
- production datasource должен работать от read-only ClickHouse пользователя с
  production query limits; local validation не блокируется на этом пункте, если
  dedicated read-only profile еще не смоделирован в repo;
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

`source_type` и `agent_id` участвуют в chained variable discovery и inventory
queries. Они не должны заменять фильтр по `source_id`/`point_key` в telemetry
time-series queries, потому что основной sort key telemetry read models не
начинается с `source_type` или `agent_id`.

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
- production datasource использует read-only ClickHouse пользователя;
- production ClickHouse grants ограничены нужными read models, без write
  privileges;
- для production profile задаются query limits: timeout, max rows/result rows,
  memory limits и readonly mode;
- local stack может временно использовать общий development ClickHouse user,
  пока read-only profile не смоделирован; это не является tenant authorization
  boundary и остается production hardening item;
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
- для точных counts configured points/agents потребуется config/inventory-backed
  service read model, а не ad-hoc JSON parsing;
- без load PoC нельзя считать refresh interval и query shape production-ready.

## План реализации

1. ADR принят; активное решение отражено в `docs/architecture/decisions.md`.
2. Зафиксировать новые service read models в
   `docs/contracts/clickhouse/telemetry-store.v1.md` до реализации миграций.
3. Добавить forward-only Telemetry Store migration для
   `service_latest_agent_status_v1`,
   `service_latest_source_connection_v1`, `service_point_inventory_v1` и
   `service_telemetry_activity_1m_v1`.
4. Добавить provisioned dashboard JSON для общего overview:
   `infra/local/grafana/dashboards/service-telemetry-overview.json`.
5. Добавить provisioned dashboard JSON для графиков:
   `infra/local/grafana/dashboards/telemetry-point-drilldown.json`.
6. Добавить chained variables `tenant_id`, `asset_id`, `source_type`,
   `agent_id`, `source_id`, `point_key`.
7. Перенести production-heavy overview/status/activity/top-N panels на service
   read models, а bounded point drilldown оставить на correctness-first views,
   где нужна value-level/event-level история.
8. Расширить `tests/integration/test_grafana_clickhouse.py`, чтобы проверять
   provisioning новых dashboards, datasource UID, variables, отсутствие MQTT/API
   coupling и representative queries against seeded ClickHouse data.
9. Проверить Kafka-to-ClickHouse path, чтобы service read models обновлялись из
   ingestion flow.
10. Для текущего increment показывать observed/current points; configured
   points включать только после появления config/inventory-backed read model.
11. LikeC4 обновлять только при изменении ownership, deployment или module
   dependencies.
12. Production hardening отдельным пунктом: dedicated read-only ClickHouse
   datasource user/profile, grants и query limits.

## Проверки принятия

- Dashboard set принадлежит `Web Monitoring Module`, а не `Industrial Data Platform`
  core и не `Alarm Management Module`.
- Dashboards помечены как internal/service и не являются tenant-facing surface.
- Overview dashboard показывает общую статистику системы по tenants, agents,
  sources, points и telemetry health.
- Current implementation не показывает `configured_points` как production-ready
  метрику без config/inventory-backed read model.
- Current implementation остается technical service observability over raw point
  identity и не блокирует future semantic/object drilldown через `Asset Graph
  Registry` telemetry bindings.
- Future semantic dashboards читают prepared ClickHouse read models/projections,
  а не вызывают `Asset Graph Registry` API на каждый panel refresh.
- ClickHouse inventory/status/rollup/projection read models принадлежат
  `Telemetry Store` / `Industrial Data Platform`; Grafana и `Web Monitoring
  Module` владеют только visualization/query surface поверх этих контрактов.
- Drilldown dashboard позволяет выбрать `tenant_id`, `asset_id`, `source_type`,
  `agent_id`, `source_id`, `point_key` и посмотреть графики выбранных points.
- `source_type` рассматривается как protocol/adapter type; controlled
  vocabulary candidates `knx | modbus | opc-ua | can` являются входом для
  отдельного contract change, а не частью первого dashboard increment.
- Dashboards поставляются из git через provisioning, `editable=false`.
- Anonymous access выключен в target deployment.
- Production datasource user read-only и ограничен ClickHouse query limits;
  local stack может временно использовать development ClickHouse user, если
  read-only profile еще не смоделирован.
- Time-series panels используют Grafana time range macros.
- Drilldown panels фильтруют
  `tenant_id -> asset_id -> source_type -> agent_id -> source_id -> point_key`
  или читают prepared rollup/service read models.
- Ни одна default-панель не рисует все points всех tenants как unbounded series.
- Heavy global counters читают latest/rollup/service read models, а не raw
  telemetry history.
- Новые tables/views добавлены в contract docs до реализации.
- Validation для текущего dashboard/read-model increment включает:
  - `uv run --package idp-telemetry-store pytest tools/idp_telemetry_store/tests`
  - `uv run --group integration pytest tests/integration/test_grafana_clickhouse.py tests/integration/test_kafka_to_clickhouse_storage.py`
  - `docker compose -f infra/local/compose.yaml config --quiet`
  - `git diff --check`
  - module-map parse
  - `npm --prefix docs-site run build`

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
- `schema-pk-prioritize-filters`: service read models должны проектироваться
  под реальные dashboard filters.
- `query-mv-incremental`: high-frequency dashboard counts и top-N должны читать
  incremental/materialized rollups вместо full aggregation на каждый refresh.
- `query-join-filter-before`: joins с inventory/status metadata должны
  фильтровать/агрегировать данные до join.
- `query-join-use-any`: `ANY JOIN` подходит для присоединения одной current
  metadata row к telemetry facts.
- `schema-types-enum`: future finite `source_type` vocabulary должен получить
  contract-level validation; конкретный ClickHouse storage type остается
  решением отдельного contract change.
