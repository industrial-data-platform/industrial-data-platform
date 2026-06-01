# Hierarchical Catalog V1

Дата: 2026-05-18
Статус: accepted implementation planning

Этот документ фиксирует первый tree projection slice для accepted
`Asset Graph Registry`: иерархию объектов, источников, точек и
asset graph node refs поверх текущей registry model.

Runtime placement принят в
[`ADR-016: Asset Graph Registry boundary`](adrs/ADR-016-asset-graph-registry-boundary.md):
целевой boundary — отдельный `Asset Graph Registry`
service/package, а не embedded slice внутри `Config Registry`. `Catalog V1`
является первым tree projection, а не конечной самостоятельной моделью.
`ADR-015` остается comparison rationale.

## Цель

`Catalog V1` нужен как первый ручной authoring/navigation слой для:

- навигации и authoring workflows рядом с `Config Registry`;
- internal admin UI нового `Asset Graph Registry`, где
  оператору нужна понятная структура объекта;
- будущего presentation layer `Web Monitoring Module`;
- будущего импорта ETS/OPC UA/других source maps в человеко-читаемое дерево.

Asset Graph Registry реализуется как отдельный service/package
в monorepo. Ручной internal admin workflow является первым source, который
создает asset graph/catalog projection nodes. Automatic importers остаются
future producers.

ADR-016 accepts the V1 implementation baseline: existing Python/FastAPI
service conventions, SQLAlchemy/Alembic migrations, PostgreSQL/Platform Store
and a dedicated internal admin frontend on `Next.js` / `React` /
`Ant Design Admin`. A follow-up technology ADR is required only before deviating
from that baseline or adding graph/search/RDF/ontology runtime infrastructure.

## Scope Split

`Catalog V1` не должен пытаться реализовать весь asset graph layer, но он находится
внутри принятого `Asset Graph Registry`.

Первый implementation slice означает:

- дерево для удобной навигации по объектам, источникам и точкам;
- folders и reference nodes на existing registry entities;
- public-code API/admin surface внутри Asset Graph Registry boundary;
- lightweight metadata для presentation/navigation needs;
- минимальный ontology vocabulary profile;
- базовые asset graph node refs, relation types и telemetry bindings metadata,
  чтобы future Web Monitoring/Alarm flows могли перейти от raw point identity
  к `asset_graph_node.attribute`.

Future расширение `Asset Graph Registry` добавит более богатые attributes,
computed attributes, importers, graph queries и tenant-facing APIs.

## Runtime Placement

Boundary placement принят:

- отдельный service/package boundary внутри `Industrial Data Platform`;
- не embedded slice внутри `Config Registry`;
- own API/storage/consistency ownership;
- concrete app/package name, physical tables, indexes, query plans and
  admin screen depth are implementation-design details inside the
  ADR-016 baseline.

`Config Registry` остается owner-ом tenants/assets/agents/sources/points и
config revisions. `Asset Graph Registry` owns tree projections,
asset graph nodes, relations, vocabulary profile and telemetry bindings
metadata.

## C4 Placement

LikeC4 должен показывать Asset Graph Registry как отдельный C2
container:

- `industrial-data-platform.asset-graph-registry`
- `c3-asset-graph-registry-authoring`

## Identity Model

Config Registry использует две разные идентичности:

- Physical storage may have internal primary keys; exact storage key strategy is
  an implementation-design detail inside the ADR-016 baseline.
- Domain/API/admin workflows работают с public codes:
  `tenant_code`, `asset_code`, `agent_code`, `source_code`, `point_code`.
- Edge/MQTT payload contracts сохраняют `tenant_id`, `asset_id`, `agent_id`,
  `source_id`, `point_ref` и `point_key`; Catalog V1 не меняет эти контракты.
- Kafka/ClickHouse/platform ingestion boundary может использовать `point_id`
  как storage/platform identity.
- `point_ref` остается техническим адресом точки внутри source, например KNX
  group address, OPC UA node id или register reference.
- `point_key` остается safe representation для MQTT topic path.

Следствие: Asset Graph Registry API and admin forms should use public
codes, а не internal UUID. UUID допустим только как storage key/backend
implementation detail.

## V1 Tree Projection

Рекомендуемая функциональная модель: один default catalog tree на tenant.

Catalog tree хранит произвольно вложенную parent/child hierarchy:

- каждый node принадлежит одному `tenant_code`;
- `tenant_code` проверяется через Config Registry lookup перед созданием
  любого catalog node, включая `folder`;
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
- `asset_graph_node_ref` — presentation reference на asset graph node.

Catalog node identity отдельна от registry entity identity. Один asset, source
или point может быть представлен в нескольких местах дерева разными catalog
nodes. Это нужно для разных пользовательских представлений: физическая
топология, этажи/зоны, инженерные системы, арендаторы или эксплуатационные
группы.

## Accepted Logical Data Model

V1 фиксирует логическую модель до implementation PR. Она не задает физические
имена таблиц, индексы или query plans.

Core entities and invariants:

- `asset graph node`: tenant-scoped real-world object with
  `asset_graph_node_code`, `display_name`, `object_type` and optional
  vocabulary term. Example `object_type` values: `site`, `factory`, `building`,
  `quarry`, `area`, `line`, `machine`, `assembly`, `component`, `space`.
- `asset graph node attribute`: logical attribute of a node with
  `attribute_key`, `value_type`, optional `unit` and optional vocabulary term.
- `asset graph node relationship`: typed directed relation between nodes.
  Candidate V1 relation types: `partOf`, `locatedIn`, `hasPoint`, `feeds`,
  `measures`, `controls`.
- `catalog tree` / `catalog node`: navigation projection over asset graph nodes
  and Config Registry references. Catalog node identity is separate from target
  entity identity.
- `telemetry binding`: mapping from technical `point_code` or telemetry series
  identity to `asset_graph_node_code + attribute_key`.
- `vocabulary profile`: curated Brick/Haystack/RealEstateCore subset for
  object types, relation types and attribute semantics.
- `registry reference`: public-code reference to Config Registry entities with
  optional display snapshot and stale/valid status after delete/rename.

Default tree code: `default`.

Within the accepted ADR-016 baseline, the first implementation may represent
tree parent/child relations in PostgreSQL and read them with recursive queries:

- чтения всего дерева tenant-а;
- чтения subtree от выбранного node;
- проверки циклов при move/update;
- вычисления path/depth для internal admin UI и future UI.

Closure table/materialized path, graph database, search index and ontology
runtime are not needed in V1. They require measurements and a follow-up
technology ADR before introduction.

## Internal API

Internal Asset Graph Registry API surface для будущей реализации:

- `GET /internal/tenants/{tenant_code}/catalog/default/tree`
- `POST /internal/tenants/{tenant_code}/catalog/default/nodes`
- `PATCH /internal/tenants/{tenant_code}/catalog/default/nodes/{node_code}`
- `POST /internal/tenants/{tenant_code}/catalog/default/nodes/{node_code}/move`
- `DELETE /internal/tenants/{tenant_code}/catalog/default/nodes/{node_code}`

These routes belong to the Asset Graph Registry boundary, not to
`idp_config_registry`. Exact route and package naming is an
implementation-design detail inside the ADR-016 baseline.

Requests/responses используют public codes. Internal UUID не выходит в API.

Config Registry lookup имеет два разных результата:

- `stale` или missing reference означает invalid/stale business reference и
  не должен сохранять новый node/binding как valid;
- недоступность Config Registry lookup API, non-2xx HTTP response или
  malformed response считается dependency failure Asset Graph Registry API,
  а не `unknown` registry reference.

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
- для `asset_graph_node_ref`: `asset_graph_node_code`.

## Backoffice Surface

`Catalog V1` должен проектироваться с собственным internal admin frontend в
Asset Graph Registry boundary:

- `Next.js` app для internal admin surface;
- `React` UI;
- `Ant Design Admin` / Ant Design components для layout, forms, tables, tree
  controls и selectors;
- API client поверх Asset Graph Registry internal API/application use cases;
- Playwright browser coverage для authoring workflows.

Это не SQLAdmin и не extension текущего Config Registry Backoffice Admin UI.
Config Registry SQLAdmin остается adjacent internal surface для narrow registry
CRUD/admin workflows, но не становится шаблоном реализации asset graph tree
editor.

Синхронизация с текущим Backoffice Admin UI означает shared platform rules, а
не общий UI framework:

- internal-only access/routing/deployment posture;
- public-code selectors и readable labels;
- все create/update/delete/move operations идут через Asset Graph Registry
  application use cases или Catalog API;
- frontend не пишет напрямую в PostgreSQL;
- browser-tested workflows через Playwright;
- если нужны общие helpers, их следует вынести в neutral shared internal
  package, а не импортировать `idp_config_registry.infrastructure.backoffice*`
  напрямую.

Для реализации Catalog нужно:

- проводить create/update/delete/move через application use cases или Catalog
  API;
- показывать selectors по public codes и readable labels;
- предусмотреть dedicated tree editor screens для navigation, move subtree,
  sibling ordering и validation;
- добавить Playwright coverage для folder/ref node creation, edit/delete,
  subtree/tree read и basic selector flows.

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
- persistence models and migrations using the ADR-016 baseline;
- in-memory adapter для fast tests;
- application use cases для create/update/delete/read tree;
- internal API router under tenant catalog path;
- internal `Next.js` / `React` / `Ant Design Admin` app inside the new boundary,
  with API client, tree editor screens, public-code selectors and Playwright
  tests;
- curated Brick/Haystack/RealEstateCore vocabulary seed;
- package tests, persistence-adapter tests and Playwright admin UI tests.

## Open Questions

- Нужны ли несколько именованных trees на tenant сразу после default tree?
- Какие exact ontology term codes из Brick/Haystack/RealEstateCore seed-им в
  первом PR?
- Когда добавлять automatic importers после ручного internal admin workflow: ETS/KNX,
  OPC UA или synthetic generator?
- Нужен ли tenant-facing Asset Graph Registry API до Keycloak/RBAC, или
  V1 остается internal admin surface?
- Какие metadata fields нужны presentation layer beyond `metadata_json`?
