# Hierarchical Catalog V1

Дата: 2026-05-18
Статус: working plan

Этот документ фиксирует рабочий план для `Hierarchical Catalog V1`: иерархии
объектов, источников и точек поверх текущей модели `Config Registry`.

Это еще не accepted architecture decision и не ADR. Если команда принимает этот
срез к реализации, результат нужно перенести в `decisions.md`, living docs и,
при изменении runtime boundaries, в LikeC4.

## Цель

`Catalog V1` нужен как общий иерархический слой для:

- навигации и authoring workflows в `Config Registry`;
- internal `/backoffice`, где оператору нужна понятная структура объекта;
- будущего presentation layer `Web Monitoring Module`;
- импорта ETS/OPC UA/других source maps в человеко-читаемое дерево.

Первый implementation home: `apps/idp_config_registry`. Отдельный service и
shared library не создаются в V1.

Storage home: PostgreSQL `Platform Store`.

## C4 Placement

В LikeC4 Catalog показан как C3 component внутри container
`industrial-data-platform.idp-config-registry`.

Это намеренно не отдельный C2 container: V1 не создает новый runtime service,
image, deployment unit или package. Он расширяет текущий `Config Registry` /
`Platform Store` slice и должен попадать в тот же validation/deployment контур,
что и `apps/idp_config_registry`.

C3 view:

- `c3-idp-config-registry-catalog`

## Текущая Identity Model

После rebaseline Config Registry использует две разные идентичности:

- PostgreSQL tables имеют internal UUID primary key `id` и UUID foreign keys.
- Domain/API/backoffice workflows работают с public codes:
  `tenant_code`, `asset_code`, `agent_code`, `source_code`, `point_code`.
- Edge/Kafka/MQTT payload contracts остаются на wire names `tenant_id`,
  `asset_id`, `agent_id`, `source_id`, `point_id`; Catalog V1 не меняет эти
  контракты.
- `point_ref` остается техническим адресом точки внутри source, например KNX
  group address, OPC UA node id или register reference.
- `point_key` остается safe representation для MQTT topic path.

Следствие: Catalog API и backoffice forms должны использовать public codes, а
не internal UUID. UUID допустим только как storage key и SQLAdmin row id.

## V1 Model

Рекомендуемая модель: один default catalog tree на tenant.

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

Catalog node identity отдельна от registry entity identity. Один asset, source
или point может быть представлен в нескольких местах дерева разными catalog
nodes. Это нужно для разных пользовательских представлений: физическая
топология, этажи/зоны, инженерные системы, арендаторы или эксплуатационные
группы.

## Storage And Query Shape

V1 достаточно adjacency list plus recursive SQL/CTE:

- `catalog_trees`: tenant, tree code, display name, status/timestamps;
- `catalog_nodes`: tree, parent node, node code, node type, display name,
  target public codes, sort order, metadata JSON, timestamps.

Default tree code: `default`.

Recursive CTE используется для:

- чтения всего дерева tenant-а;
- чтения subtree от выбранного node;
- проверки циклов при move/update;
- вычисления path/depth для backoffice и future UI.

Closure table/materialized path не нужны в V1. Их можно добавить после
измерений на реальном размере дерева.

## Candidate API

Future Config Registry API surface для реализации:

- `GET /tenants/{tenant_code}/catalog/default/tree`
- `POST /tenants/{tenant_code}/catalog/default/nodes`
- `PATCH /tenants/{tenant_code}/catalog/default/nodes/{node_code}`
- `DELETE /tenants/{tenant_code}/catalog/default/nodes/{node_code}`

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
- для `point_ref`: `point_code`.

## Backoffice Surface

`Catalog V1` должен проектироваться сразу с internal `/backoffice` surface.
Issue #21 закрепил `/backoffice` как browser-tested workflow и показал важную
деталь: SQLAdmin работает с persisted UUID row ids, а application use cases
работают с public codes.

Для реализации Catalog нужно:

- добавить `Catalog Tree` и `Catalog Node` views в `/backoffice`;
- проводить create/update/delete через application use cases, как текущие
  registry views;
- добавить UUID-to-public-code bridge для SQLAdmin row actions;
- показывать selectors по public codes и readable labels;
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

V1 не является заменой `Config Registry`. Это слой представления и навигации
поверх уже существующих registry entities.

V1 не решает автоматическое discovery всех tags/models. Importers могут
создавать catalog nodes позже, но discovery policy остается отдельным решением.

## Implementation Notes For Future Issue

Первую implementation issue стоит резать как backend + backoffice slice:

- domain entities/value objects для tree/node;
- repository/unit-of-work protocols;
- PostgreSQL models and Alembic migration;
- in-memory adapter для fast tests;
- application use cases для create/update/delete/read tree;
- FastAPI router under tenant catalog path;
- backoffice views and selectors;
- package tests, PostgreSQL tests и Playwright backoffice UI tests.

После implementation нужно обновить `apps/idp_config_registry/README.md` и,
если Catalog становится accepted boundary, `decisions.md` и LikeC4.

## Open Questions

- Нужны ли несколько именованных trees на tenant сразу после default tree?
- Какие import sources первыми создают catalog nodes: synthetic generator,
  ETS/KNX project parser, OPC UA importer или ручной backoffice workflow?
- Нужен ли tenant-facing Catalog API до Keycloak/RBAC, или V1 остается internal
  Config Registry/backoffice surface?
- Какие metadata fields нужны presentation layer beyond `metadata_json`?
