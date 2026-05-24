from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from idp_asset_graph_registry.application.errors import (
    DuplicateResourceError,
    InvalidOperationError,
    InvalidReferenceError,
    ResourceNotFoundError,
)
from idp_asset_graph_registry.application.ports.registry_lookup import (
    RegistryReferenceLookup,
)
from idp_asset_graph_registry.application.ports.unit_of_work import UnitOfWork
from idp_asset_graph_registry.domain.entities import (
    AssetGraphNode,
    AssetGraphNodeAttribute,
    AssetGraphRelationship,
    TelemetryBinding,
    utc_now,
)
from idp_asset_graph_registry.domain.value_objects import (
    ReferenceStatus,
    RelationType,
    ValueType,
)


@dataclass(frozen=True)
class CreateAssetGraphNodeCommand:
    tenant_code: str
    asset_graph_node_code: str
    display_name: str
    object_type: str
    vocabulary_term: str | None = None
    metadata_json: dict[str, Any] | None = None


@dataclass(frozen=True)
class UpdateAssetGraphNodeCommand:
    tenant_code: str
    asset_graph_node_code: str
    display_name: str
    object_type: str
    vocabulary_term: str | None = None
    metadata_json: dict[str, Any] | None = None


@dataclass(frozen=True)
class CreateAssetGraphNodeAttributeCommand:
    tenant_code: str
    asset_graph_node_code: str
    attribute_key: str
    value_type: ValueType
    unit: str | None = None
    vocabulary_term: str | None = None
    metadata_json: dict[str, Any] | None = None


@dataclass(frozen=True)
class UpdateAssetGraphNodeAttributeCommand:
    tenant_code: str
    asset_graph_node_code: str
    attribute_key: str
    value_type: ValueType
    unit: str | None = None
    vocabulary_term: str | None = None
    metadata_json: dict[str, Any] | None = None


@dataclass(frozen=True)
class CreateAssetGraphRelationshipCommand:
    tenant_code: str
    relationship_code: str
    source_asset_graph_node_code: str
    target_asset_graph_node_code: str
    relation_type: RelationType
    metadata_json: dict[str, Any] | None = None


@dataclass(frozen=True)
class UpdateAssetGraphRelationshipCommand:
    tenant_code: str
    relationship_code: str
    source_asset_graph_node_code: str
    target_asset_graph_node_code: str
    relation_type: RelationType
    metadata_json: dict[str, Any] | None = None


@dataclass(frozen=True)
class CreateTelemetryBindingCommand:
    tenant_code: str
    binding_code: str
    point_code: str
    asset_graph_node_code: str
    attribute_key: str
    metadata_json: dict[str, Any] | None = None


@dataclass(frozen=True)
class UpdateTelemetryBindingCommand:
    tenant_code: str
    binding_code: str
    point_code: str
    asset_graph_node_code: str
    attribute_key: str
    metadata_json: dict[str, Any] | None = None


class CreateAssetGraphNode:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        registry_lookup: RegistryReferenceLookup,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._registry_lookup = registry_lookup

    async def execute(self, command: CreateAssetGraphNodeCommand) -> AssetGraphNode:
        tenant_reference = await self._registry_lookup.tenant(command.tenant_code)
        if tenant_reference.status != ReferenceStatus.VALID:
            raise InvalidReferenceError("tenant", command.tenant_code)
        node = AssetGraphNode(
            tenant_code=command.tenant_code,
            asset_graph_node_code=command.asset_graph_node_code,
            display_name=command.display_name,
            object_type=command.object_type,
            vocabulary_term=command.vocabulary_term,
            metadata_json=command.metadata_json or {},
        )
        async with self._unit_of_work as unit_of_work:
            existing = await unit_of_work.asset_graph_nodes.get(
                node.tenant_code,
                node.asset_graph_node_code,
            )
            if existing is not None:
                raise DuplicateResourceError(
                    "asset graph node",
                    node.asset_graph_node_code,
                )
            await unit_of_work.asset_graph_nodes.add(node)
            await unit_of_work.commit()
        return node


class GetAssetGraphNode:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        tenant_code: str,
        asset_graph_node_code: str,
    ) -> AssetGraphNode:
        async with self._unit_of_work as unit_of_work:
            node = await unit_of_work.asset_graph_nodes.get(
                tenant_code,
                asset_graph_node_code,
            )
        if node is None:
            raise ResourceNotFoundError("asset graph node", asset_graph_node_code)
        return node


class ListAssetGraphNodes:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, tenant_code: str) -> list[AssetGraphNode]:
        async with self._unit_of_work as unit_of_work:
            return await unit_of_work.asset_graph_nodes.list_for_tenant(tenant_code)


class UpdateAssetGraphNode:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, command: UpdateAssetGraphNodeCommand) -> AssetGraphNode:
        async with self._unit_of_work as unit_of_work:
            existing = await unit_of_work.asset_graph_nodes.get(
                command.tenant_code,
                command.asset_graph_node_code,
            )
            if existing is None:
                raise ResourceNotFoundError(
                    "asset graph node",
                    command.asset_graph_node_code,
                )
            updated = replace(
                existing,
                display_name=command.display_name,
                object_type=command.object_type,
                vocabulary_term=command.vocabulary_term,
                metadata_json=command.metadata_json or {},
                updated_at=utc_now(),
            )
            await unit_of_work.asset_graph_nodes.update(updated)
            await unit_of_work.commit()
        return updated


class DeleteAssetGraphNode:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, tenant_code: str, asset_graph_node_code: str) -> None:
        async with self._unit_of_work as unit_of_work:
            existing = await unit_of_work.asset_graph_nodes.get(
                tenant_code,
                asset_graph_node_code,
            )
            if existing is None:
                raise ResourceNotFoundError("asset graph node", asset_graph_node_code)
            attributes = await unit_of_work.attributes.list_for_node(
                tenant_code,
                asset_graph_node_code,
            )
            if attributes:
                raise InvalidOperationError(
                    "asset graph node cannot be deleted while it has attributes"
                )
            relationships = await unit_of_work.relationships.list_for_tenant(tenant_code)
            if any(
                relationship.source_asset_graph_node_code == asset_graph_node_code
                or relationship.target_asset_graph_node_code == asset_graph_node_code
                for relationship in relationships
            ):
                raise InvalidOperationError(
                    "asset graph node cannot be deleted while it has relationships"
                )
            bindings = await unit_of_work.telemetry_bindings.list_for_tenant(
                tenant_code
            )
            if any(
                binding.asset_graph_node_code == asset_graph_node_code
                for binding in bindings
            ):
                raise InvalidOperationError(
                    "asset graph node cannot be deleted while it has telemetry bindings"
                )
            catalog_nodes = await unit_of_work.catalog_nodes.list_for_tree(
                tenant_code,
                "default",
            )
            if any(
                (node.target or {}).get("asset_graph_node_code")
                == asset_graph_node_code
                for node in catalog_nodes
            ):
                raise InvalidOperationError(
                    "asset graph node cannot be deleted while catalog nodes reference it"
                )
            await unit_of_work.asset_graph_nodes.delete(
                tenant_code,
                asset_graph_node_code,
            )
            await unit_of_work.commit()


class CreateAssetGraphNodeAttribute:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: CreateAssetGraphNodeAttributeCommand,
    ) -> AssetGraphNodeAttribute:
        attribute = AssetGraphNodeAttribute(
            tenant_code=command.tenant_code,
            asset_graph_node_code=command.asset_graph_node_code,
            attribute_key=command.attribute_key,
            value_type=command.value_type,
            unit=command.unit,
            vocabulary_term=command.vocabulary_term,
            metadata_json=command.metadata_json or {},
        )
        async with self._unit_of_work as unit_of_work:
            if (
                await unit_of_work.asset_graph_nodes.get(
                    command.tenant_code,
                    command.asset_graph_node_code,
                )
                is None
            ):
                raise ResourceNotFoundError(
                    "asset graph node",
                    command.asset_graph_node_code,
                )
            existing = await unit_of_work.attributes.get(
                attribute.tenant_code,
                attribute.asset_graph_node_code,
                attribute.attribute_key,
            )
            if existing is not None:
                raise DuplicateResourceError("attribute", attribute.attribute_key)
            await unit_of_work.attributes.add(attribute)
            await unit_of_work.commit()
        return attribute


class GetAssetGraphNodeAttribute:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        tenant_code: str,
        asset_graph_node_code: str,
        attribute_key: str,
    ) -> AssetGraphNodeAttribute:
        async with self._unit_of_work as unit_of_work:
            attribute = await unit_of_work.attributes.get(
                tenant_code,
                asset_graph_node_code,
                attribute_key,
            )
        if attribute is None:
            raise ResourceNotFoundError("attribute", attribute_key)
        return attribute


class ListAssetGraphNodeAttributes:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        tenant_code: str,
        asset_graph_node_code: str,
    ) -> list[AssetGraphNodeAttribute]:
        async with self._unit_of_work as unit_of_work:
            return await unit_of_work.attributes.list_for_node(
                tenant_code,
                asset_graph_node_code,
            )


class UpdateAssetGraphNodeAttribute:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: UpdateAssetGraphNodeAttributeCommand,
    ) -> AssetGraphNodeAttribute:
        async with self._unit_of_work as unit_of_work:
            existing = await unit_of_work.attributes.get(
                command.tenant_code,
                command.asset_graph_node_code,
                command.attribute_key,
            )
            if existing is None:
                raise ResourceNotFoundError("attribute", command.attribute_key)
            updated = replace(
                existing,
                value_type=command.value_type,
                unit=command.unit,
                vocabulary_term=command.vocabulary_term,
                metadata_json=command.metadata_json or {},
                updated_at=utc_now(),
            )
            await unit_of_work.attributes.update(updated)
            await unit_of_work.commit()
        return updated


class DeleteAssetGraphNodeAttribute:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        tenant_code: str,
        asset_graph_node_code: str,
        attribute_key: str,
    ) -> None:
        async with self._unit_of_work as unit_of_work:
            existing = await unit_of_work.attributes.get(
                tenant_code,
                asset_graph_node_code,
                attribute_key,
            )
            if existing is None:
                raise ResourceNotFoundError("attribute", attribute_key)
            bindings = await unit_of_work.telemetry_bindings.list_for_tenant(
                tenant_code
            )
            if any(
                binding.asset_graph_node_code == asset_graph_node_code
                and binding.attribute_key == attribute_key
                for binding in bindings
            ):
                raise InvalidOperationError(
                    "attribute cannot be deleted while telemetry bindings reference it"
                )
            await unit_of_work.attributes.delete(
                tenant_code,
                asset_graph_node_code,
                attribute_key,
            )
            await unit_of_work.commit()


class CreateAssetGraphRelationship:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: CreateAssetGraphRelationshipCommand,
    ) -> AssetGraphRelationship:
        relationship = AssetGraphRelationship(
            tenant_code=command.tenant_code,
            relationship_code=command.relationship_code,
            source_asset_graph_node_code=command.source_asset_graph_node_code,
            target_asset_graph_node_code=command.target_asset_graph_node_code,
            relation_type=command.relation_type,
            metadata_json=command.metadata_json or {},
        )
        async with self._unit_of_work as unit_of_work:
            if await unit_of_work.relationships.get(
                command.tenant_code,
                command.relationship_code,
            ):
                raise DuplicateResourceError(
                    "relationship",
                    command.relationship_code,
                )
            for node_code in [
                command.source_asset_graph_node_code,
                command.target_asset_graph_node_code,
            ]:
                if await unit_of_work.asset_graph_nodes.get(
                    command.tenant_code,
                    node_code,
                ) is None:
                    raise ResourceNotFoundError("asset graph node", node_code)
            await unit_of_work.relationships.add(relationship)
            await unit_of_work.commit()
        return relationship


class GetAssetGraphRelationship:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        tenant_code: str,
        relationship_code: str,
    ) -> AssetGraphRelationship:
        async with self._unit_of_work as unit_of_work:
            relationship = await unit_of_work.relationships.get(
                tenant_code,
                relationship_code,
            )
        if relationship is None:
            raise ResourceNotFoundError("relationship", relationship_code)
        return relationship


class ListAssetGraphRelationships:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, tenant_code: str) -> list[AssetGraphRelationship]:
        async with self._unit_of_work as unit_of_work:
            return await unit_of_work.relationships.list_for_tenant(tenant_code)


class UpdateAssetGraphRelationship:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: UpdateAssetGraphRelationshipCommand,
    ) -> AssetGraphRelationship:
        async with self._unit_of_work as unit_of_work:
            existing = await unit_of_work.relationships.get(
                command.tenant_code,
                command.relationship_code,
            )
            if existing is None:
                raise ResourceNotFoundError(
                    "relationship",
                    command.relationship_code,
                )
            for node_code in [
                command.source_asset_graph_node_code,
                command.target_asset_graph_node_code,
            ]:
                if await unit_of_work.asset_graph_nodes.get(
                    command.tenant_code,
                    node_code,
                ) is None:
                    raise ResourceNotFoundError("asset graph node", node_code)
            updated = replace(
                existing,
                source_asset_graph_node_code=command.source_asset_graph_node_code,
                target_asset_graph_node_code=command.target_asset_graph_node_code,
                relation_type=command.relation_type,
                metadata_json=command.metadata_json or {},
                updated_at=utc_now(),
            )
            await unit_of_work.relationships.update(updated)
            await unit_of_work.commit()
        return updated


class DeleteAssetGraphRelationship:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, tenant_code: str, relationship_code: str) -> None:
        async with self._unit_of_work as unit_of_work:
            existing = await unit_of_work.relationships.get(
                tenant_code,
                relationship_code,
            )
            if existing is None:
                raise ResourceNotFoundError("relationship", relationship_code)
            await unit_of_work.relationships.delete(tenant_code, relationship_code)
            await unit_of_work.commit()


class CreateTelemetryBinding:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        registry_lookup: RegistryReferenceLookup,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._registry_lookup = registry_lookup

    async def execute(self, command: CreateTelemetryBindingCommand) -> TelemetryBinding:
        point_reference = await self._registry_lookup.point(
            command.tenant_code,
            command.point_code,
        )
        if point_reference.status != ReferenceStatus.VALID:
            raise InvalidReferenceError("point", command.point_code)
        binding = TelemetryBinding(
            tenant_code=command.tenant_code,
            binding_code=command.binding_code,
            point_code=command.point_code,
            asset_graph_node_code=command.asset_graph_node_code,
            attribute_key=command.attribute_key,
            reference_status=point_reference.status,
            display_snapshot_json=point_reference.snapshot_json,
            metadata_json=command.metadata_json or {},
        )
        async with self._unit_of_work as unit_of_work:
            if await unit_of_work.telemetry_bindings.get(
                command.tenant_code,
                command.binding_code,
            ):
                raise DuplicateResourceError("telemetry binding", command.binding_code)
            existing_bindings = await unit_of_work.telemetry_bindings.list_for_tenant(
                command.tenant_code
            )
            if any(binding.point_code == command.point_code for binding in existing_bindings):
                raise DuplicateResourceError("telemetry point binding", command.point_code)
            if any(
                binding.asset_graph_node_code == command.asset_graph_node_code
                and binding.attribute_key == command.attribute_key
                for binding in existing_bindings
            ):
                raise DuplicateResourceError(
                    "telemetry attribute binding",
                    f"{command.asset_graph_node_code}.{command.attribute_key}",
                )
            if await unit_of_work.attributes.get(
                command.tenant_code,
                command.asset_graph_node_code,
                command.attribute_key,
            ) is None:
                raise ResourceNotFoundError("attribute", command.attribute_key)
            await unit_of_work.telemetry_bindings.add(binding)
            await unit_of_work.commit()
        return binding


class GetTelemetryBinding:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, tenant_code: str, binding_code: str) -> TelemetryBinding:
        async with self._unit_of_work as unit_of_work:
            binding = await unit_of_work.telemetry_bindings.get(
                tenant_code,
                binding_code,
            )
        if binding is None:
            raise ResourceNotFoundError("telemetry binding", binding_code)
        return binding


class ListTelemetryBindings:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, tenant_code: str) -> list[TelemetryBinding]:
        async with self._unit_of_work as unit_of_work:
            return await unit_of_work.telemetry_bindings.list_for_tenant(tenant_code)


class UpdateTelemetryBinding:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        registry_lookup: RegistryReferenceLookup,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._registry_lookup = registry_lookup

    async def execute(self, command: UpdateTelemetryBindingCommand) -> TelemetryBinding:
        point_reference = await self._registry_lookup.point(
            command.tenant_code,
            command.point_code,
        )
        if point_reference.status != ReferenceStatus.VALID:
            raise InvalidReferenceError("point", command.point_code)
        async with self._unit_of_work as unit_of_work:
            existing = await unit_of_work.telemetry_bindings.get(
                command.tenant_code,
                command.binding_code,
            )
            if existing is None:
                raise ResourceNotFoundError("telemetry binding", command.binding_code)
            if await unit_of_work.attributes.get(
                command.tenant_code,
                command.asset_graph_node_code,
                command.attribute_key,
            ) is None:
                raise ResourceNotFoundError("attribute", command.attribute_key)
            existing_bindings = await unit_of_work.telemetry_bindings.list_for_tenant(
                command.tenant_code
            )
            if any(
                binding.binding_code != command.binding_code
                and binding.point_code == command.point_code
                for binding in existing_bindings
            ):
                raise DuplicateResourceError("telemetry point binding", command.point_code)
            if any(
                binding.binding_code != command.binding_code
                and binding.asset_graph_node_code == command.asset_graph_node_code
                and binding.attribute_key == command.attribute_key
                for binding in existing_bindings
            ):
                raise DuplicateResourceError(
                    "telemetry attribute binding",
                    f"{command.asset_graph_node_code}.{command.attribute_key}",
                )
            updated = replace(
                existing,
                point_code=command.point_code,
                asset_graph_node_code=command.asset_graph_node_code,
                attribute_key=command.attribute_key,
                reference_status=point_reference.status,
                display_snapshot_json=point_reference.snapshot_json,
                metadata_json=command.metadata_json or {},
                updated_at=utc_now(),
            )
            await unit_of_work.telemetry_bindings.update(updated)
            await unit_of_work.commit()
        return updated


class DeleteTelemetryBinding:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, tenant_code: str, binding_code: str) -> None:
        async with self._unit_of_work as unit_of_work:
            existing = await unit_of_work.telemetry_bindings.get(
                tenant_code,
                binding_code,
            )
            if existing is None:
                raise ResourceNotFoundError("telemetry binding", binding_code)
            await unit_of_work.telemetry_bindings.delete(tenant_code, binding_code)
            await unit_of_work.commit()
