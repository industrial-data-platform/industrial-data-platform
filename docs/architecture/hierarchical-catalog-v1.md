# Hierarchical Catalog V1

Дата: 2026-05-18
Статус: accepted implementation planning

Этот документ фиксирует первый tree projection slice для accepted
`Digital Twin / Asset Graph Registry`: иерархию объектов, источников, точек и
twin refs поверх текущей registry model.

Runtime placement принят в
[`ADR-016: Digital Twin / Asset Graph Registry boundary`](adrs/ADR-016-digital-twin-asset-graph-boundary.md):
целевой boundary — отдельный `Digital Twin / Asset Graph Registry`
service/package, а не embedded slice внутри `Config Registry`. `Catalog V1`
является первым tree projection, а не конечной самостоятельной моделью.
`ADR-015` остается comparison rationale.

## Цель

`Catalog V1` нужен как первый ручной authoring/navigation слой для:

- навигации и authoring workflows рядом с `Config Registry`;
- internal `/backoffice` нового `Digital Twin / Asset Graph Registry`, где
  оператору нужна понятная структура объекта;
- будущего presentation layer `Web Monitoring Module`;
- будущего импорта ETS/OPC UA/других source maps в человеко-читаемое дерево.

Digital Twin / Asset Graph Registry реализуется как отдельный service/package
в monorepo. Ручной `/backoffice` workflow является первым source, который
создает twin/catalog projection nodes. Automatic importers остаются future
producers.

Storage technology is intentionally deferred to a follow-up technology ADR.

## Scope Split

`Catalog V1` не должен пытаться реализовать весь twin-layer, но он находится
внутри принятого `Digital Twin / Asset Graph Registry`.

Первый implementation slice означает:

- дерево для удобной навигации по объектам, источникам и точкам;
- folders и reference nodes на existing registry entities;
- public-code API/backoffice surface внутри Digital Twin / Asset Graph boundary;
- lightweight metadata для presentation/navigation needs;
- минимальный ontology vocabulary profile;
- базовые twin refs, relation types и telemetry bindings metadata, чтобы future
  Web Monitoring/Alarm flows могли перейти от raw point identity к
  `twin.attribute`.

Future расширение `Digital Twin Registry` / `Asset Graph Registry` добавит
более богатые arbitrary attributes, computed attributes, importers, graph
queries и tenant-facing APIs.

## Runtime Placement

Boundary placement принят:

- отдельный service/package boundary внутри `Industrial Data Platform`;
- не embedded slice внутри `Config Registry`;
- own API/storage/consistency ownership;
- concrete app/package name, persistence technology, API framework and UI stack
  are deferred to a follow-up technology ADR.

`Config Registry` остается owner-ом tenants/assets/agents/sources/points и
config revisions. `Digital Twin / Asset Graph Registry` owns tree projections,
twins/assets, relations, vocabulary profile and telemetry bindings metadata.

## C4 Placement

LikeC4 должен показывать Digital Twin / Asset Graph Registry как отдельный C2
container:

- `industrial-data-platform.digital-twin-asset-graph-registry`
- `c3-digital-twin-asset-graph-authoring`

## Identity Model

Config Registry использует две разные идентичности:

- Physical storage may have internal primary keys; exact storage technology and
  key strategy are deferred.
- Domain/API/backoffice workflows работают с public codes:
  `tenant_code`, `asset_code`, `agent_code`, `source_code`, `point_code`.
- Edge/MQTT payload contracts сохраняют `tenant_id`, `asset_id`, `agent_id`,
  `source_id`, `point_ref` и `point_key`; Catalog V1 не меняет эти контракты.
- Kafka/ClickHouse/platform ingestion boundary может использовать `point_id`
  как storage/platform identity.
- `point_ref` остается техническим адресом точки внутри source, например KNX
  group address, OPC UA node id или register reference.
- `point_key` остается safe representation для MQTT topic path.

Следствие: Digital Twin / Asset Graph API and backoffice forms should use public
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
- `registry_point_ref` — presentation reference на registry point.
- `twin_ref` — presentation reference на domain twin node.

Catalog node identity отдельна от registry entity identity. Один asset, source
или point может быть представлен в нескольких местах дерева разными catalog
nodes. Это нужно для разных пользовательских представлений: физическая
топология, этажи/зоны, инженерные системы, арендаторы или эксплуатационные
группы.

## Storage And Query Shape

V1 использует adjacency list plus recursive SQL/CTE для дерева и отдельные
tables для минимального twin/binding слоя:

- catalog trees and catalog nodes: tenant, tree code, parent node, node code,
  node type, display name, target public codes, sort order and metadata;
- minimal twins/assets and logical attributes;
- minimal relation vocabulary such as `partOf`, `locatedIn`, `hasPoint`,
  `feeds`, `measures`, `controls`;
- prepared telemetry binding metadata: `point_code` or technical series
  identity -> `twin_code + attribute_key`.

Exact persistence technology, table names, indexes and query strategy are
deferred to a follow-up technology ADR.

Default tree code: `default`.

Recursive CTE используется для:

- чтения всего дерева tenant-а;
- чтения subtree от выбранного node;
- проверки циклов при move/update;
- вычисления path/depth для backoffice и future UI.

Closure table/materialized path не нужны в V1. Их можно добавить после
измерений на реальном размере дерева.

## Internal API

Internal Digital Twin / Asset Graph API surface для будущей реализации:

- `GET /internal/tenants/{tenant_code}/catalog/default/tree`
- `POST /internal/tenants/{tenant_code}/catalog/default/nodes`
- `PATCH /internal/tenants/{tenant_code}/catalog/default/nodes/{node_code}`
- `POST /internal/tenants/{tenant_code}/catalog/default/nodes/{node_code}/move`
- `DELETE /internal/tenants/{tenant_code}/catalog/default/nodes/{node_code}`

These routes belong to the Digital Twin / Asset Graph boundary, not to
`idp_config_registry`. Exact route and package naming is deferred to the
technology/API ADR.

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
- для `registry_point_ref`: `point_code`;
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
Нужен отдельный internal `/backoffice` surface в Digital Twin / Asset Graph
boundary, который работает через its own API/internal use cases.

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
- persistence models and migrations after the technology ADR;
- in-memory adapter для fast tests;
- application use cases для create/update/delete/read tree;
- internal API router under tenant catalog path;
- backoffice views and selectors inside the new boundary;
- curated Brick/Haystack/RealEstateCore vocabulary seed;
- package tests, persistence-adapter tests and Playwright backoffice UI tests.

## Open Questions

- Нужны ли несколько именованных trees на tenant сразу после default tree?
- Какие exact ontology term codes из Brick/Haystack/RealEstateCore seed-им в
  первом PR?
- Когда добавлять automatic importers после ручного `/backoffice`: ETS/KNX,
  OPC UA или synthetic generator?
- Нужен ли tenant-facing Digital Twin / Asset Graph API до Keycloak/RBAC, или
  V1 остается internal `/backoffice` surface?
- Какие metadata fields нужны presentation layer beyond `metadata_json`?
