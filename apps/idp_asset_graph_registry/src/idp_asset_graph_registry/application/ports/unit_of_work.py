from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from idp_asset_graph_registry.domain.entities import (
    AssetGraphNode,
    AssetGraphNodeAttribute,
    AssetGraphRelationship,
    CatalogNode,
    TelemetryBinding,
)


class AssetGraphNodeRepository(Protocol):
    async def add(self, node: AssetGraphNode) -> None: ...

    async def update(self, node: AssetGraphNode) -> None: ...

    async def delete(self, tenant_code: str, asset_graph_node_code: str) -> None: ...

    async def get(
        self,
        tenant_code: str,
        asset_graph_node_code: str,
    ) -> AssetGraphNode | None: ...

    async def list_for_tenant(self, tenant_code: str) -> list[AssetGraphNode]: ...


class AssetGraphNodeAttributeRepository(Protocol):
    async def add(self, attribute: AssetGraphNodeAttribute) -> None: ...

    async def update(self, attribute: AssetGraphNodeAttribute) -> None: ...

    async def delete(
        self,
        tenant_code: str,
        asset_graph_node_code: str,
        attribute_key: str,
    ) -> None: ...

    async def get(
        self,
        tenant_code: str,
        asset_graph_node_code: str,
        attribute_key: str,
    ) -> AssetGraphNodeAttribute | None: ...

    async def list_for_node(
        self,
        tenant_code: str,
        asset_graph_node_code: str,
    ) -> list[AssetGraphNodeAttribute]: ...


class AssetGraphRelationshipRepository(Protocol):
    async def add(self, relationship: AssetGraphRelationship) -> None: ...

    async def update(self, relationship: AssetGraphRelationship) -> None: ...

    async def delete(self, tenant_code: str, relationship_code: str) -> None: ...

    async def get(
        self,
        tenant_code: str,
        relationship_code: str,
    ) -> AssetGraphRelationship | None: ...

    async def list_for_tenant(self, tenant_code: str) -> list[AssetGraphRelationship]: ...


class TelemetryBindingRepository(Protocol):
    async def add(self, binding: TelemetryBinding) -> None: ...

    async def update(self, binding: TelemetryBinding) -> None: ...

    async def delete(self, tenant_code: str, binding_code: str) -> None: ...

    async def get(
        self,
        tenant_code: str,
        binding_code: str,
    ) -> TelemetryBinding | None: ...

    async def list_for_tenant(self, tenant_code: str) -> list[TelemetryBinding]: ...


class CatalogNodeRepository(Protocol):
    async def add(self, node: CatalogNode) -> None: ...

    async def get(
        self,
        tenant_code: str,
        tree_code: str,
        node_code: str,
    ) -> CatalogNode | None: ...

    async def update(self, node: CatalogNode) -> None: ...

    async def delete(self, tenant_code: str, tree_code: str, node_code: str) -> None: ...

    async def list_for_tree(self, tenant_code: str, tree_code: str) -> list[CatalogNode]: ...


class UnitOfWork(Protocol):
    asset_graph_nodes: AssetGraphNodeRepository
    attributes: AssetGraphNodeAttributeRepository
    relationships: AssetGraphRelationshipRepository
    telemetry_bindings: TelemetryBindingRepository
    catalog_nodes: CatalogNodeRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...
