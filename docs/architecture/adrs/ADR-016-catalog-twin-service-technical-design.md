# ADR-016: Catalog/Twin service technical design

Дата: 2026-05-20
Статус: accepted

## Контекст

`ADR-015` сравнил два разных scope под словом `Catalog`:

- простой navigation/authoring tree поверх registry entities;
- полноценный `Catalog/Twin` слой для объектной модели здания/объекта,
  semantic relations, attributes и telemetry bindings.

Команда выбрала отдельный `Catalog/Twin` service/package. Первый источник,
который создает catalog/twin nodes, — ручной internal `/backoffice` workflow.
Автоматические importers из ETS/KNX, OPC UA, synthetic generator или discovery
остаются будущими источниками данных.

## Референсная модель

Для building-domain semantics используем готовые онтологии и reference models
как vocabulary source, а не изобретаем собственный словарь с нуля.

- `Brick` дает building relations вроде `hasPart`, `hasPoint`, `hasLocation`,
  `feeds` и inverse-relations между equipment, locations и points.
- `Project Haystack` показывает практичный tag/ref подход: opaque entity id,
  display metadata, containment refs (`siteRef`, `spaceRef`, `equipRef`) и flow
  refs для air/electricity/water/steam.
- `RealEstateCore` отделяет building/space/assets/points/sensors/commands и
  показывает, как описывать sensor readings в digital twin модели отдельно от
  ingestion.
- `Azure Digital Twins`, `AWS IoT SiteWise`, `Cognite Data Fusion`,
  `Eclipse BaSyx/AAS` и `Eclipse Ditto` подтверждают общий pattern:
  model/graph of things отдельно от telemetry storage, bindings и
  application-facing views/API.

V1 не внедряет RDF/SPARQL reasoner и не импортирует полные ontology graphs.
Мы берем curated ontology profile: stable term codes, external ontology refs и
минимальные relation/attribute semantics, необходимые для ручного authoring и
будущего semantic read path.

## Решение

Создаем отдельную runtime/domain boundary:

- future app: `apps/idp_catalog_twin`;
- future Python package/import: `idp_catalog_twin`;
- future CLI/service entrypoint: `idp-catalog-twin`;
- future Docker Compose service: `idp-catalog-twin`;
- persistence owner: own schema/tables in `Platform Store` (`PostgreSQL`);
- first authoring surface: internal `/backoffice` of this service.

`Config Registry` остается owner-ом tenants/assets/agents/sources/points и
agent runtime/source config revisions. Он не расширяется до Catalog/Twin API.

`Catalog/Twin` становится owner-ом:

- catalog trees and catalog nodes;
- domain twins / asset graph nodes;
- non-tree semantic relations;
- logical attributes;
- telemetry bindings from technical series to logical attributes;
- ontology vocabulary profile used by authoring and validation.

## V1 scope

Первый implementation slice остается маленьким, но строится внутри правильной
service boundary.

Входит в V1:

- один `default` catalog tree на tenant;
- ручное создание/edit/delete/move nodes через internal `/backoffice`;
- node types: `folder`, `asset_ref`, `agent_ref`, `source_ref`, `point_ref`,
  `twin_ref`;
- stable public codes: `tenant_code`, `tree_code`, `node_code`, `twin_code`,
  `attribute_key`, `relation_code`;
- curated building ontology profile with external refs to Brick/Haystack/REC;
- relation types baseline: `partOf`, `locatedIn`, `hasPoint`, `feeds`,
  `measures`, `controls`;
- logical attributes with `value_type`, `unit`, `ontology_term_code`;
- telemetry bindings from `point_code` or technical series identity to
  `twin_code + attribute_key`;
- recursive tree/subtree reads for backoffice and future presentation.

Не входит в V1:

- tenant-facing public UI;
- Keycloak/RBAC policy model;
- automatic discovery/import from ETS/OPC UA;
- RDF/SPARQL engine;
- computed attributes and rule engine execution;
- writes/control commands into field systems;
- changes to MQTT/Kafka/ClickHouse contracts.

## Persistence model

Logical PostgreSQL tables for the future implementation:

- `ontology_terms`: local term code, source ontology (`brick`, `haystack`,
  `realestatecore`, `idp`), external IRI/tag/ref, kind, display name.
- `twins`: tenant, `twin_code`, `twin_type`, display name, ontology term,
  metadata JSON, lifecycle timestamps.
- `twin_attributes`: tenant, twin, `attribute_key`, value type, unit, ontology
  term, metadata JSON.
- `twin_relationships`: tenant, source twin, target twin, relation type,
  relation code, ontology term, metadata JSON.
- `catalog_trees`: tenant, tree code, display name, status/timestamps.
- `catalog_nodes`: tenant, tree, parent node, node code, node type, target,
  display name, sort order, metadata JSON.
- `telemetry_bindings`: tenant, twin, attribute, technical target
  (`point_code` and/or `asset_code/agent_code/source_code/point_key`),
  binding status, unit override, metadata JSON.

Implementation PR may split or rename exact table names, but it must preserve
these ownership boundaries and concepts.

## Reference and consistency rules

`Catalog/Twin` stores references to Config Registry entities by public codes,
not by foreign keys to Config Registry internal UUIDs.

Reference validation flow:

1. Backoffice command receives public codes.
2. `Catalog/Twin` application use case validates tenant/entity existence via an
   internal Config Registry API/client port.
3. `Catalog/Twin` stores the public-code reference and optional resolved
   display snapshot.
4. If a registry entity is deleted or renamed later, `Catalog/Twin` marks the
   binding/reference as stale until a repair workflow updates it.

This keeps `Catalog/Twin` independently packageable and open-source friendly:
the service can run with another registry adapter later, without depending on
Config Registry database internals.

## API and backoffice shape

Initial service API is internal-only:

- `GET /health`
- `GET /ready`
- `GET /internal/tenants/{tenant_code}/catalog/default/tree`
- `POST /internal/tenants/{tenant_code}/catalog/default/nodes`
- `PATCH /internal/tenants/{tenant_code}/catalog/default/nodes/{node_code}`
- `POST /internal/tenants/{tenant_code}/catalog/default/nodes/{node_code}/move`
- `DELETE /internal/tenants/{tenant_code}/catalog/default/nodes/{node_code}`
- `POST /internal/tenants/{tenant_code}/twins`
- `PATCH /internal/tenants/{tenant_code}/twins/{twin_code}`
- `POST /internal/tenants/{tenant_code}/twins/{twin_code}/attributes`
- `POST /internal/tenants/{tenant_code}/twins/{twin_code}/relationships`
- `POST /internal/tenants/{tenant_code}/telemetry-bindings`

The first `/backoffice` UI belongs to `idp_catalog_twin`. It may reuse the same
technical style as existing internal backoffice, but tree move/order/reference
validation must go through application use cases, not direct table edits.

## Open-source readiness

Design the package as a reusable Catalog/Twin service:

- no customer-specific naming in package, tables, routes or ontology terms;
- ontology profile data stored as versioned seed/migration assets;
- clean adapter ports for registry lookup, persistence and future eventing;
- no hard dependency on KNX, OPC UA, MQTT, Kafka or ClickHouse for core CRUD;
- explicit public-code API surface and stable domain concepts;
- docs explaining how to run the service against a generic PostgreSQL backend.

Future open-source extraction should be mostly repository packaging work, not a
domain model rewrite.

## Consequences

- `ADR-015` is superseded as decision material; its comparison remains useful
  rationale.
- LikeC4 must show `idp_catalog_twin` as a separate Industrial Data Platform
  container, not as candidate component inside `idp_config_registry`.
- `Config Registry` keeps its current scope and does not own Catalog/Twin
  tables, tree editing, ontology vocabulary or telemetry bindings.
- Web Monitoring and Alarm Management can later depend on semantic
  `twin.attribute` metadata without coupling to Config Registry internals.
- First implementation PR should create service skeleton/domain/persistence
  for manual backoffice authoring before adding automatic importers.

## References

- Brick relationships: https://docs.brickschema.org/brick/relationships.html
- Project Haystack relationships: https://project-haystack.org/doc/docHaystack/Relationships
- RealEstateCore documentation: https://doc.realestatecore.io/
- Azure Digital Twins models: https://learn.microsoft.com/en-us/azure/digital-twins/concepts-models
- AWS IoT SiteWise asset properties: https://docs.aws.amazon.com/en_us/iot-sitewise/latest/userguide/asset-properties.html
- Cognite Data Fusion views: https://docs.cognite.com/api-reference/concepts/views
- Eclipse BaSyx architecture: https://eclipse.dev/basyx/architecture/
- Eclipse Ditto project: https://projects.eclipse.org/projects/iot.ditto
