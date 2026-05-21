# ADR-016: Digital Twin / Asset Graph Registry boundary

Дата: 2026-05-22
Статус: accepted

## Context

`ADR-015` compared two scopes that were both called `Catalog`:

- a `Hierarchical Catalog V1` navigation/authoring tree over registry entities;
- a target `Digital Twin / Asset Graph Registry` for real-world objects,
  attributes, semantic relations and telemetry bindings.

The review conclusion is that the ADR should not stay as a neutral fork.
`Catalog V1` is useful as a first projection, but it is not the target domain
model. The target capability is a `Digital Twin / Asset Graph Registry`.

`Config Registry` answers: how should the edge agent read and deliver data?
`Digital Twin / Asset Graph Registry` answers: what exists in the real world,
how is it related, and which logical attributes are observed or derived?

## Reference Model

For the building domain, the registry should lean on existing ontologies and
industrial twin patterns instead of inventing a vocabulary blindly.

- `Brick` provides building relationships such as `hasPart`, `hasPoint`,
  `hasLocation` and `feeds`.
- `Project Haystack` shows a pragmatic tag/ref model with opaque identities,
  display metadata and reference tags.
- `RealEstateCore` separates buildings, spaces, assets, points, sensors,
  commands and readings.
- `Azure Digital Twins`, `AWS IoT SiteWise`, `Cognite Data Fusion`,
  `Eclipse BaSyx/AAS` and `Eclipse Ditto` all separate the model/graph of
  things from telemetry storage and application-facing views/API.

V1 may use a curated vocabulary profile. It does not require a full ontology
runtime, RDF/SPARQL engine or automatic ontology import.

## Decision

The target domain/runtime boundary is `Digital Twin / Asset Graph Registry`.

It is a separate Industrial Data Platform runtime/service/package boundary, not
an embedded slice inside `Config Registry`.

The first implementation slice may expose a Catalog-like tree projection for
manual authoring and navigation, but `Catalog` is not a standalone final model.
It is a projection over the target twin/asset graph.

The first creator of twin/catalog nodes is manual internal `/backoffice`.
Automatic sources such as ETS/KNX import, OPC UA import, synthetic generation
and discovery stay future producers.

## Ownership

`Digital Twin / Asset Graph Registry` owns:

- real-world object/twin identity;
- tree projections for navigation and authoring;
- logical attributes;
- semantic relations;
- telemetry binding metadata from technical series to logical attributes;
- the curated building-domain vocabulary profile used for authoring and
  validation;
- its own API/storage/consistency boundary.

`Config Registry` owns:

- tenants/assets/agents/sources/points used to render edge runtime/source
  configuration;
- config revisions and config delivery outbox;
- source/point technical metadata needed by the edge agent.

`Config Registry` must not grow into the Digital Twin / Asset Graph API.

## V1 Scope

V1 should be deliberately narrow:

- minimal twins/assets;
- one default tree projection per tenant for navigation and `/backoffice`;
- references to Config Registry entities via public codes;
- prepared telemetry binding model:
  `point_code` or technical series identity -> `twin_code + attribute_key`;
- minimal logical attributes with value type and unit metadata;
- minimal relation vocabulary for building/navigation needs.

Candidate relation vocabulary for V1:

- `partOf`
- `locatedIn`
- `hasPoint`
- `feeds`
- `measures`
- `controls`

Out of scope for V1:

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

## Reference And Consistency

The registry stores references to Config Registry entities by public codes, not
by direct dependency on Config Registry internal UUIDs.

Reference validation flow:

1. Internal authoring command receives public codes.
2. Digital Twin / Asset Graph use case validates tenant/entity existence via an
   internal registry lookup boundary.
3. The twin registry stores the public-code reference and optional resolved
   display snapshot.
4. If a referenced registry entity is deleted or renamed later, the twin
   registry marks the reference or binding as stale until a repair workflow
   updates it.

This keeps the future service independently packageable and avoids coupling the
twin graph to Config Registry database internals.

## Web Monitoring And Alarm Dependency

Web Monitoring and Alarm Management should not be forced to treat technical
`point_code` or registry rows as the long-term domain interface.

Target flow:

1. Edge telemetry arrives with technical wire/storage identities.
2. Digital Twin / Asset Graph binds technical series to logical
   `twin.attribute`.
3. Future Web Monitoring and Alarm APIs can read latest/history and evaluate
   rules by `twin`, `attribute`, unit, relation path and binding metadata.

The first read-only telemetry API may still read raw ClickHouse read models.
The boundary decision keeps a path toward semantic enrichment.

## Technology Decision

Technology stack selection is intentionally deferred to a separate ADR after the
domain/runtime boundary is accepted.

This ADR defines only baseline constraints:

- use existing Industrial Data Platform runtime conventions unless proven
  insufficient;
- keep API/storage/consistency ownership explicit;
- keep the boundary independently packageable;
- do not introduce graph database, search index, RDF/SPARQL or ontology runtime
  infrastructure before V1 query and consistency requirements are confirmed.

The follow-up technology ADR should compare persistence model, indexing/search,
API framework/package shape, migration strategy and operational cost.

## Consequences

- `ADR-015` is superseded as comparison rationale.
- LikeC4 must show a separate `Digital Twin / Asset Graph Registry` container,
  not an embedded candidate component inside `idp_config_registry`.
- `Hierarchical Catalog V1` becomes a first tree projection inside this
  boundary, not the accepted final domain model.
- The first implementation PR should create only the narrow boundary/skeleton
  needed for manual `/backoffice` authoring and prepared telemetry bindings.
- Concrete storage engine, API framework, package naming and UI stack require a
  follow-up technology ADR.

## References

- Brick relationships: https://docs.brickschema.org/brick/relationships.html
- Project Haystack relationships: https://project-haystack.org/doc/docHaystack/Relationships
- RealEstateCore documentation: https://doc.realestatecore.io/
- Azure Digital Twins models: https://learn.microsoft.com/en-us/azure/digital-twins/concepts-models
- AWS IoT SiteWise asset properties: https://docs.aws.amazon.com/en_us/iot-sitewise/latest/userguide/asset-properties.html
- Cognite Data Fusion views: https://docs.cognite.com/api-reference/concepts/views
- Eclipse BaSyx architecture: https://eclipse.dev/basyx/architecture/
- Eclipse Ditto project: https://projects.eclipse.org/projects/iot.ditto
