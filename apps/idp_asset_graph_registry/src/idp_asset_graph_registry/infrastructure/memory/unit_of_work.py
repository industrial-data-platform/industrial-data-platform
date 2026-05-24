from __future__ import annotations

from dataclasses import dataclass, field
from types import TracebackType

from idp_asset_graph_registry.domain.entities import (
    AssetGraphNode,
    AssetGraphNodeAttribute,
    AssetGraphRelationship,
    CatalogNode,
    TelemetryBinding,
)


@dataclass
class InMemoryAssetGraphNodeRepository:
    _items: dict[tuple[str, str], AssetGraphNode] = field(default_factory=dict)

    async def add(self, node: AssetGraphNode) -> None:
        self._items[(node.tenant_code, node.asset_graph_node_code)] = node

    async def update(self, node: AssetGraphNode) -> None:
        self._items[(node.tenant_code, node.asset_graph_node_code)] = node

    async def delete(self, tenant_code: str, asset_graph_node_code: str) -> None:
        self._items.pop((tenant_code, asset_graph_node_code), None)

    async def get(
        self,
        tenant_code: str,
        asset_graph_node_code: str,
    ) -> AssetGraphNode | None:
        return self._items.get((tenant_code, asset_graph_node_code))

    async def list_for_tenant(self, tenant_code: str) -> list[AssetGraphNode]:
        return sorted(
            (
                node
                for (node_tenant_code, _), node in self._items.items()
                if node_tenant_code == tenant_code
            ),
            key=lambda node: node.asset_graph_node_code,
        )


@dataclass
class InMemoryAttributeRepository:
    _items: dict[tuple[str, str, str], AssetGraphNodeAttribute] = field(
        default_factory=dict
    )

    async def add(self, attribute: AssetGraphNodeAttribute) -> None:
        self._items[
            (
                attribute.tenant_code,
                attribute.asset_graph_node_code,
                attribute.attribute_key,
            )
        ] = attribute

    async def update(self, attribute: AssetGraphNodeAttribute) -> None:
        await self.add(attribute)

    async def delete(
        self,
        tenant_code: str,
        asset_graph_node_code: str,
        attribute_key: str,
    ) -> None:
        self._items.pop((tenant_code, asset_graph_node_code, attribute_key), None)

    async def get(
        self,
        tenant_code: str,
        asset_graph_node_code: str,
        attribute_key: str,
    ) -> AssetGraphNodeAttribute | None:
        return self._items.get((tenant_code, asset_graph_node_code, attribute_key))

    async def list_for_node(
        self,
        tenant_code: str,
        asset_graph_node_code: str,
    ) -> list[AssetGraphNodeAttribute]:
        return sorted(
            (
                attribute
                for (
                    attribute_tenant_code,
                    attribute_node_code,
                    _,
                ), attribute in self._items.items()
                if attribute_tenant_code == tenant_code
                and attribute_node_code == asset_graph_node_code
            ),
            key=lambda attribute: attribute.attribute_key,
        )


@dataclass
class InMemoryRelationshipRepository:
    _items: dict[tuple[str, str], AssetGraphRelationship] = field(
        default_factory=dict
    )

    async def add(self, relationship: AssetGraphRelationship) -> None:
        self._items[(relationship.tenant_code, relationship.relationship_code)] = (
            relationship
        )

    async def update(self, relationship: AssetGraphRelationship) -> None:
        await self.add(relationship)

    async def delete(self, tenant_code: str, relationship_code: str) -> None:
        self._items.pop((tenant_code, relationship_code), None)

    async def get(
        self,
        tenant_code: str,
        relationship_code: str,
    ) -> AssetGraphRelationship | None:
        return self._items.get((tenant_code, relationship_code))

    async def list_for_tenant(self, tenant_code: str) -> list[AssetGraphRelationship]:
        return sorted(
            (
                relationship
                for (relationship_tenant_code, _), relationship in self._items.items()
                if relationship_tenant_code == tenant_code
            ),
            key=lambda relationship: relationship.relationship_code,
        )


@dataclass
class InMemoryTelemetryBindingRepository:
    _items: dict[tuple[str, str], TelemetryBinding] = field(default_factory=dict)

    async def add(self, binding: TelemetryBinding) -> None:
        self._items[(binding.tenant_code, binding.binding_code)] = binding

    async def update(self, binding: TelemetryBinding) -> None:
        self._items[(binding.tenant_code, binding.binding_code)] = binding

    async def delete(self, tenant_code: str, binding_code: str) -> None:
        self._items.pop((tenant_code, binding_code), None)

    async def get(
        self,
        tenant_code: str,
        binding_code: str,
    ) -> TelemetryBinding | None:
        return self._items.get((tenant_code, binding_code))

    async def list_for_tenant(self, tenant_code: str) -> list[TelemetryBinding]:
        return sorted(
            (
                binding
                for (binding_tenant_code, _), binding in self._items.items()
                if binding_tenant_code == tenant_code
            ),
            key=lambda binding: binding.binding_code,
        )


@dataclass
class InMemoryCatalogNodeRepository:
    _items: dict[tuple[str, str, str], CatalogNode] = field(default_factory=dict)

    async def add(self, node: CatalogNode) -> None:
        self._items[(node.tenant_code, node.tree_code, node.node_code)] = node

    async def get(
        self,
        tenant_code: str,
        tree_code: str,
        node_code: str,
    ) -> CatalogNode | None:
        return self._items.get((tenant_code, tree_code, node_code))

    async def update(self, node: CatalogNode) -> None:
        self._items[(node.tenant_code, node.tree_code, node.node_code)] = node

    async def delete(self, tenant_code: str, tree_code: str, node_code: str) -> None:
        self._items.pop((tenant_code, tree_code, node_code), None)

    async def list_for_tree(self, tenant_code: str, tree_code: str) -> list[CatalogNode]:
        return sorted(
            (
                node
                for (node_tenant_code, node_tree_code, _), node in self._items.items()
                if node_tenant_code == tenant_code and node_tree_code == tree_code
            ),
            key=lambda node: (node.parent_node_code or "", node.sort_order, node.node_code),
        )


@dataclass
class InMemoryUnitOfWork:
    asset_graph_nodes: InMemoryAssetGraphNodeRepository
    attributes: InMemoryAttributeRepository
    relationships: InMemoryRelationshipRepository
    telemetry_bindings: InMemoryTelemetryBindingRepository
    catalog_nodes: InMemoryCatalogNodeRepository

    async def __aenter__(self) -> InMemoryUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        return None


@dataclass
class InMemoryUnitOfWorkFactory:
    asset_graph_nodes: InMemoryAssetGraphNodeRepository = field(
        default_factory=InMemoryAssetGraphNodeRepository
    )
    attributes: InMemoryAttributeRepository = field(
        default_factory=InMemoryAttributeRepository
    )
    relationships: InMemoryRelationshipRepository = field(
        default_factory=InMemoryRelationshipRepository
    )
    telemetry_bindings: InMemoryTelemetryBindingRepository = field(
        default_factory=InMemoryTelemetryBindingRepository
    )
    catalog_nodes: InMemoryCatalogNodeRepository = field(
        default_factory=InMemoryCatalogNodeRepository
    )

    def __call__(self) -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(
            asset_graph_nodes=self.asset_graph_nodes,
            attributes=self.attributes,
            relationships=self.relationships,
            telemetry_bindings=self.telemetry_bindings,
            catalog_nodes=self.catalog_nodes,
        )
