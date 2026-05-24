# ADR-016: граница Asset Graph Registry

Дата: 2026-05-22
Статус: принято

## Контекст

`ADR-015` сравнил два scope, которые в обсуждении назывались `Catalog`:

- `Hierarchical Catalog V1`: navigation/authoring tree поверх registry entities;
- целевой `Asset Graph Registry` для реальных объектов, asset graph nodes,
  attributes, semantic relations и telemetry bindings.

Вывод review: ADR не должен оставаться нейтральной развилкой. `Catalog V1`
полезен как первая projection, но это не целевая domain model. Целевая
capability — `Asset Graph Registry`.

`Config Registry` отвечает на вопрос: как edge agent должен читать и доставлять
данные? `Asset Graph Registry` отвечает на вопрос: что существует в реальном
мире, как это связано и какие logical attributes наблюдаются или вычисляются?

## Референсная модель

Для building domain registry должен опираться на существующие ontologies и
industrial asset modeling patterns, а не изобретать vocabulary вслепую.

- `Brick` задает building relationships вроде `hasPart`, `hasPoint`,
  `hasLocation` и `feeds`.
- `Project Haystack` показывает прагматичную tag/ref модель с opaque
  identities, display metadata и reference tags.
- `RealEstateCore` разделяет buildings, spaces, assets, points, sensors,
  commands и readings.
- `Azure ADT`, `AWS IoT SiteWise`, `Cognite Data Fusion`,
  `Eclipse BaSyx/AAS` и `Eclipse Ditto` отделяют model/graph of things от
  telemetry storage и application-facing views/API.
- `AWS IoT SiteWise` asset model hierarchies можно использовать как reference
  для Asset Graph Registry Admin UI: parent/child asset hierarchy, named
  hierarchy relations, выбор child model/reference и console-style workflow для
  связывания объектов. Это UI/UX reference, а не требование копировать SiteWise
  data model или API.

V1 может использовать curated vocabulary profile. Для V1 не нужен полноценный
ontology runtime, RDF/SPARQL engine или automatic ontology import.

## Решение

Целевая domain/runtime boundary — `Asset Graph Registry`.

Это отдельная Industrial Data Platform runtime/service/package boundary, а не
embedded slice внутри `Config Registry`.

Первый implementation slice может дать Catalog-like tree projection для manual
authoring и navigation, но `Catalog` не является standalone final model. Это
projection поверх целевого asset graph.

Первый источник asset graph/catalog projection nodes — manual internal admin UI.
Automatic sources вроде ETS/KNX import, OPC UA import, synthetic generation и
discovery остаются future producers.

## Логическая Модель

Основной термин data model — `Asset Graph`. В V1 используется `asset graph node`
для строки реального объекта, чтобы модель естественно представляла buildings,
factories, quarries, sites, areas, lines, machines, assemblies, components и
spaces.

Принятая V1 logical data model:

- `asset graph node`: tenant-scoped real-world object с
  `asset_graph_node_code`, `display_name`, `object_type` и optional vocabulary
  term;
- `asset graph node attribute`: logical attribute node-а, keyed by
  `attribute_key`, с `value_type`, optional `unit` и optional vocabulary term;
- `asset graph node relationship`: typed directed relation между nodes, с
  relation types вроде `partOf`, `locatedIn`, `hasPoint`, `feeds`, `measures`
  и `controls`;
- `catalog tree` / `catalog node`: navigation и authoring projection поверх
  asset graph nodes и Config Registry references;
- `telemetry binding`: mapping от technical `point_code` или telemetry series
  identity к `asset_graph_node_code + attribute_key`;
- `vocabulary profile`: curated Brick/Haystack/RealEstateCore subset для object
  types, relation types и attribute semantics;
- `registry reference`: public-code reference на Config Registry tenants,
  assets, agents, sources и points, с optional display snapshot и
  stale/valid status.

Этот раздел фиксирует logical model и invariants для implementation issues.
Физические table names, indexes и query plans остаются деталями реализации
внутри принятого baseline ниже.

## Владение

`Asset Graph Registry` владеет:

- identity asset graph nodes;
- tree projections для navigation и authoring;
- logical attributes;
- semantic relations;
- telemetry binding metadata от technical series к logical attributes;
- curated building-domain vocabulary profile для authoring и validation;
- собственной API/storage/consistency boundary.

`Config Registry` владеет:

- tenants/assets/agents/sources/points, которые используются для render edge
  runtime/source configuration;
- config revisions и config delivery outbox;
- source/point technical metadata, которая нужна edge agent.

`Config Registry` не должен превращаться в Asset Graph Registry API.

## Объем V1

V1 намеренно узкий:

- minimal asset graph nodes;
- one default tree projection per tenant для navigation и internal admin
  authoring;
- references на Config Registry entities через public codes;
- prepared telemetry binding model:
  `point_code` или technical series identity ->
  `asset_graph_node_code + attribute_key`;
- minimal logical attributes с value type и unit metadata;
- minimal relation vocabulary для building/navigation needs.

Кандидатный relation vocabulary для V1:

- `partOf`
- `locatedIn`
- `hasPoint`
- `feeds`
- `measures`
- `controls`

За пределами V1:

- tenant-facing public UI;
- Keycloak/RBAC policy model;
- automatic import/discovery;
- full RDF/SPARQL reasoning;
- broad ontology tooling;
- search/indexing infrastructure;
- computed attributes;
- alarm rule execution;
- writes/control commands into field systems;
- changes to MQTT/Kafka/ClickHouse contracts.

## Ссылки и консистентность

Registry хранит references на Config Registry entities через public codes, а не
через прямую dependency на internal UUIDs Config Registry.

Поток проверки ссылок:

1. Internal authoring command получает public codes.
2. Asset Graph Registry use case проверяет существование tenant/entity через
   internal registry lookup boundary.
3. Asset graph registry сохраняет public-code reference и optional resolved
   display snapshot.
4. Если referenced registry entity позже удалена или переименована, asset graph
   registry помечает reference или binding как stale до repair workflow.

Это сохраняет будущий service independently packageable и не связывает asset
graph с database internals Config Registry.

## Зависимость Web Monitoring И Alarm

Web Monitoring и Alarm Management не должны быть вынуждены считать technical
`point_code` или registry rows долгосрочным domain interface.

Целевой поток:

1. Edge telemetry приходит с technical wire/storage identities.
2. Asset Graph Registry связывает technical series с logical
   `asset_graph_node.attribute`.
3. Future Web Monitoring и Alarm APIs могут читать latest/history и оценивать
   rules по asset graph node, `attribute_key`, unit, relation path и binding
   metadata.

Первый read-only telemetry API все еще может читать raw ClickHouse read models.
Это boundary decision оставляет путь к semantic enrichment.

## Технологическое решение

Первая backend implementation может идти на существующем Industrial Data
Platform runtime baseline:

- Python service/package conventions, которые используются текущими platform
  backends;
- FastAPI-style internal API/application use cases;
- SQLAlchemy/Alembic migrations;
- PostgreSQL/Platform Store для mutable V1 state.

Internal admin/authoring surface для Asset Graph Registry — dedicated frontend
app, которым владеет эта boundary:

- `Next.js` application для internal admin surface;
- `React` UI implementation;
- `Ant Design Admin` / Ant Design components для admin layout, forms, tables,
  tree controls и selectors;
- API client, который вызывает Asset Graph Registry internal API/application
  use cases;
- Playwright coverage для critical authoring workflows в браузере.

Это намеренно не SQLAdmin и не extension существующего Config Registry
Backoffice Admin UI. Tree navigation, subtree moves, sibling ordering,
reference validation, logical attributes и telemetry bindings — это
operator workflows, похожие на product UI, а не narrow row CRUD.

При проектировании screens для tree/hierarchy authoring можно использовать AWS
IoT SiteWise asset hierarchy console flow как reference: выбор parent context,
именование hierarchy relation, выбор child asset/model reference, readable
labels и явное associate/disassociate действие. Для нашей модели это остается
ориентиром UX, а source of truth и use cases находятся в Asset Graph Registry.

Новый admin surface должен оставаться синхронизированным с Config Registry
backoffice по общим правилам платформы:

- internal-only access, routing и deployment posture;
- public-code selectors и readable labels в UI/API boundaries;
- writes идут через Asset Graph Registry API/application use cases;
- frontend не пишет напрямую в PostgreSQL;
- Playwright coverage для browser workflows;
- shared helpers можно вынести в neutral internal package, но Asset Graph
  Registry не должен импортировать `idp_config_registry` infrastructure modules
  напрямую.

Asset Graph Registry должен сохранять собственное API/use-case/persistence
ownership. Если первой реализации нужны shared admin helpers, их следует
вынести в neutral shared internal package; нельзя импортировать
`idp_config_registry` infrastructure modules напрямую из Asset Graph Registry
package.

Этот ADR также фиксирует constraints:

- держать API/storage/consistency ownership явным;
- держать boundary independently packageable;
- не вводить graph database, search index, RDF/SPARQL или ontology runtime
  infrastructure до подтверждения V1 query и consistency requirements;
- не добавлять SQLAdmin в Asset Graph Registry admin UI;
- держать admin frontend на принятом `Next.js` / `React` /
  `Ant Design Admin` stack, пока follow-up ADR не изменит platform-wide admin
  baseline.

Follow-up technology ADR требуется перед отклонением от этого baseline или перед
добавлением graph database, search/indexing infrastructure, RDF/SPARQL,
ontology runtime tooling или другого API/UI stack. Точные package names,
physical table names, indexes, query plans и admin screen depth остаются
деталями implementation design, пока они остаются внутри этого baseline.

## Последствия

- `ADR-015` становится superseded материалом для comparison rationale.
- LikeC4 должен показывать отдельный `Asset Graph Registry` container, а не
  embedded candidate component внутри `idp_config_registry`.
- `Hierarchical Catalog V1` становится первой tree projection внутри этой
  boundary, а не принятой конечной domain model.
- Первый implementation PR должен создать только узкий boundary/skeleton,
  нужный для manual internal admin authoring и prepared telemetry bindings.
- Первый implementation PR может использовать принятый Python/FastAPI,
  SQLAlchemy/Alembic, PostgreSQL и `Next.js` / `React` /
  `Ant Design Admin` baseline без нового ADR; отклонения требуют follow-up
  technology ADR.

## Ссылки

- Brick relationships: https://docs.brickschema.org/brick/relationships.html
- Project Haystack relationships: https://project-haystack.org/doc/docHaystack/Relationships
- RealEstateCore documentation: https://doc.realestatecore.io/
- Azure ADT models
- AWS IoT SiteWise asset properties: https://docs.aws.amazon.com/en_us/iot-sitewise/latest/userguide/asset-properties.html
- AWS IoT SiteWise asset model hierarchies: https://docs.aws.amazon.com/iot-sitewise/latest/userguide/define-asset-hierarchies.html
- Cognite Data Fusion views: https://docs.cognite.com/api-reference/concepts/views
- Eclipse BaSyx architecture: https://eclipse.dev/basyx/architecture/
- Eclipse Ditto project: https://projects.eclipse.org/projects/iot.ditto
