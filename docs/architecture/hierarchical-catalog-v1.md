# Hierarchical Catalog V1

Дата: 2026-05-18
Статус: accepted implementation planning

Этот документ фиксирует первый implementation slice для accepted
`Catalog/Twin Service`: иерархию объектов, источников, точек и twin refs поверх
текущей registry model.

Runtime placement принят в
[`ADR-016: Catalog/Twin service technical design`](adrs/ADR-016-catalog-twin-service-technical-design.md):
делаем отдельный `apps/idp_catalog_twin` / package `idp_catalog_twin`, а не
embedded slice внутри `Config Registry`. `ADR-015` остается comparison rationale.

## Цель

`Catalog V1` нужен как первый ручной authoring/navigation слой для:

- навигации и authoring workflows рядом с `Config Registry`;
- internal `/backoffice` нового `Catalog/Twin Service`, где оператору нужна
  понятная структура объекта;
- будущего presentation layer `Web Monitoring Module`;
- будущего импорта ETS/OPC UA/других source maps в человеко-читаемое дерево.

Catalog/Twin реализуется как отдельный service/package в monorepo. Ручной
`/backoffice` workflow является первым source, который создает catalog/twin
nodes. Automatic importers остаются будущими producers.

Storage baseline для вариантов, которые используют PostgreSQL: `Platform Store`.

## Scope Split

`Catalog V1` не должен пытаться реализовать весь twin-layer, но он находится
внутри принятого `Catalog/Twin Service`.

Первый implementation slice означает:

- дерево для удобной навигации по объектам, источникам и точкам;
- folders и reference nodes на existing registry entities;
- public-code API/backoffice surface внутри `idp_catalog_twin`;
- lightweight metadata для presentation/navigation needs;
- минимальный ontology vocabulary profile;
- базовые twin refs, relation types и telemetry bindings metadata, чтобы future
  Web Monitoring/Alarm flows могли перейти от raw point identity к
  `twin.attribute`.

Future расширение `Digital Twin Registry` / `Asset Graph Registry` добавит
более богатые arbitrary attributes, computed attributes, importers, graph
queries и tenant-facing APIs.

## Runtime Placement

Placement принят:

- отдельный future app `apps/idp_catalog_twin`;
- отдельный future Python package/import `idp_catalog_twin`;
- отдельный future service entrypoint `idp-catalog-twin`;
- own persistence schema/tables in `Platform Store`.

`Config Registry` остается owner-ом tenants/assets/agents/sources/points и
config revisions. `Catalog/Twin Service` хранит собственные catalog/twin nodes,
relations, ontology vocabulary profile и telemetry bindings metadata.

## C4 Placement

LikeC4 должен показывать Catalog/Twin как отдельный C2 container:

- `industrial-data-platform.idp-catalog-twin`
- `c3-idp-catalog-twin-authoring`

## Identity Model

Config Registry использует две разные идентичности:

- PostgreSQL tables имеют internal UUID primary key `id` и UUID foreign keys.
- Domain/API/backoffice workflows работают с public codes:
  `tenant_code`, `asset_code`, `agent_code`, `source_code`, `point_code`.
- Edge/Kafka/MQTT payload contracts остаются на wire names `tenant_id`,
  `asset_id`, `agent_id`, `source_id`, `point_id`; Catalog V1 не меняет эти
  контракты.
- `point_ref` остается техническим адресом точки внутри source, например KNX
  group address, OPC UA node id или register reference.
- `point_key` остается safe representation для MQTT topic path.

Следствие: Catalog/Twin API и backoffice forms должны использовать public
codes, а не internal UUID. UUID допустим только как storage key и SQLAdmin row
id.

## V1 Model

Рекомендуемая функциональная модель: один default catalog tree на tenant.

Catalog tree хранит произвольно вложенную hierarchy через adjacency list:

- каждый node принадлежит одному `tenant_code`;
- `parent_node_code` nullable: `null` означает root-level node;
- `node_code` уникален внутри tenant tree;
- `sort_order` задает порядок siblings;
- `display_name` хранит человеко-читаемое имя node;
- `node_type` определяет семантику node.

V1 node types:

- `folder` — чистый организационный раздел без ссылки на registry entity;
- `asset_ref` — presentation reference на asset;
- `agent_ref` — presentation reference на agent;
- `source_ref` — presentation reference на source;
- `point_ref` — presentation reference на point.
- `twin_ref` — presentation reference на domain twin node.

Catalog node identity отдельна от registry entity identity. Один asset, source
или point может быть представлен в нескольких местах дерева разными catalog
nodes. Это нужно для разных пользовательских представлений: физическая
топология, этажи/зоны, инженерные системы, арендаторы или эксплуатационные
группы.

## Storage And Query Shape

V1 использует adjacency list plus recursive SQL/CTE для дерева и отдельные
tables для минимального twin/binding слоя:

- `catalog_trees`: tenant, tree code, display name, status/timestamps;
- `catalog_nodes`: tree, parent node, node code, node type, display name,
  target public codes, sort order, metadata JSON, timestamps.
- `ontology_terms`: curated Brick/Haystack/RealEstateCore/IDP terms;
- `twins`: tenant, twin code/type, display name, ontology term, metadata JSON;
- `twin_attributes`: logical attributes, value type, unit and ontology term;
- `twin_relationships`: `partOf`, `locatedIn`, `hasPoint`, `feeds`,
  `measures`, `controls` relations;
- `telemetry_bindings`: `point_code` or technical series identity ->
  `twin_code + attribute_key`.

Default tree code: `default`.

Recursive CTE используется для:

- чтения всего дерева tenant-а;
- чтения subtree от выбранного node;
- проверки циклов при move/update;
- вычисления path/depth для backoffice и future UI.

Closure table/materialized path не нужны в V1. Их можно добавить после
измерений на реальном размере дерева.

## Internal API

Internal Catalog/Twin API surface для будущей реализации:

- `GET /internal/tenants/{tenant_code}/catalog/default/tree`
- `POST /internal/tenants/{tenant_code}/catalog/default/nodes`
- `PATCH /internal/tenants/{tenant_code}/catalog/default/nodes/{node_code}`
- `POST /internal/tenants/{tenant_code}/catalog/default/nodes/{node_code}/move`
- `DELETE /internal/tenants/{tenant_code}/catalog/default/nodes/{node_code}`

These routes belong to `idp_catalog_twin`, not to `idp_config_registry`.

Requests/responses используют public codes. Internal UUID не выходит в API.

Minimal node payload:

- `node_code`
- `parent_node_code`
- `node_type`
- `display_name`
- `sort_order`
- `target`
- `metadata_json`

`target` зависит от `node_type`:

- для `folder`: `null`;
- для `asset_ref`: `asset_code`;
- для `agent_ref`: `asset_code`, `agent_code`;
- для `source_ref`: `asset_code`, `agent_code`, `source_code`;
- для `point_ref`: `point_code`;
- для `twin_ref`: `twin_code`.

## Backoffice Surface

`Catalog V1` должен проектироваться с internal authoring/admin surface, но
текущий SQLAdmin не нужно считать целевым tree editor.

Issue #21 закрепил `/backoffice` как browser-tested workflow и показал важную
деталь: SQLAdmin работает с persisted UUID row ids, а application use cases
работают с public codes. Это полезно для narrow internal CRUD/admin flows, но
плохо покрывает нормальное редактирование дерева.

Для реализации Catalog нужно:

- проводить create/update/delete/move через application use cases или Catalog
  API;
- добавить UUID-to-public-code bridge для SQLAdmin row actions;
- показывать selectors по public codes и readable labels;
- предусмотреть dedicated internal tree UI для navigation, move subtree,
  sibling ordering и validation;
- добавить Playwright coverage для folder/ref node creation, edit/delete,
  subtree/tree read и basic selector flows.

Current Config Registry SQLAdmin не является UI управления новой иерархией.
Нужен отдельный internal `/backoffice` surface в `Catalog/Twin Service`, который
работает через Catalog/Twin API/internal use cases.

## Boundaries

V1 не меняет:

- edge runtime config payloads;
- MQTT topic tree;
- Kafka topics;
- ClickHouse tables/views;
- telemetry read API;
- alarm workflow;
- Keycloak/RBAC model.

V1 оставляет за future PR:

- computed/derived attributes;
- full RDF/SPARQL reasoning;
- automatic ontology import/discovery;
- tenant-facing semantic APIs;
- semantic enrichment joins inside Web Monitoring/Alarms.

V1 не решает автоматическое discovery всех tags/models. Importers могут
создавать catalog nodes позже, но discovery policy остается отдельным решением.

## Implementation Notes For Future Issue

Первую implementation issue стоит резать вокруг отдельного service/package:

- domain entities/value objects для tree/node;
- repository/unit-of-work protocols;
- PostgreSQL models and Alembic migration;
- in-memory adapter для fast tests;
- application use cases для create/update/delete/read tree;
- internal API router under tenant catalog path;
- backoffice views and selectors in `idp_catalog_twin`;
- curated Brick/Haystack/RealEstateCore vocabulary seed;
- package tests, PostgreSQL tests и Playwright backoffice UI tests.

## Open Questions

- Нужны ли несколько именованных trees на tenant сразу после default tree?
- Какие exact ontology term codes из Brick/Haystack/RealEstateCore seed-им в
  первом PR?
- Когда добавлять automatic importers после ручного `/backoffice`: ETS/KNX,
  OPC UA или synthetic generator?
- Нужен ли tenant-facing Catalog/Twin API до Keycloak/RBAC, или V1 остается
  internal `/backoffice` surface?
- Какие metadata fields нужны presentation layer beyond `metadata_json`?
