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
    RegistryReference,
    RegistryReferenceLookup,
)
from idp_asset_graph_registry.application.ports.unit_of_work import UnitOfWork
from idp_asset_graph_registry.domain.entities import CatalogNode, utc_now
from idp_asset_graph_registry.domain.value_objects import (
    CatalogNodeType,
    ReferenceStatus,
)


@dataclass(frozen=True)
class CreateCatalogNodeCommand:
    tenant_code: str
    node_code: str
    node_type: CatalogNodeType
    display_name: str
    parent_node_code: str | None = None
    sort_order: int = 0
    target: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None


@dataclass(frozen=True)
class UpdateCatalogNodeCommand:
    tenant_code: str
    node_code: str
    display_name: str
    sort_order: int
    target: dict[str, Any] | None
    metadata_json: dict[str, Any] | None = None


@dataclass(frozen=True)
class MoveCatalogNodeCommand:
    tenant_code: str
    node_code: str
    parent_node_code: str | None
    sort_order: int


@dataclass(frozen=True)
class CatalogTree:
    tenant_code: str
    tree_code: str
    nodes: list[CatalogNode]


class GetCatalogTree:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, tenant_code: str) -> CatalogTree:
        async with self._unit_of_work as unit_of_work:
            nodes = await unit_of_work.catalog_nodes.list_for_tree(
                tenant_code,
                "default",
            )
        return CatalogTree(tenant_code=tenant_code, tree_code="default", nodes=nodes)


class CreateCatalogNode:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        registry_lookup: RegistryReferenceLookup,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._registry_lookup = registry_lookup

    async def execute(self, command: CreateCatalogNodeCommand) -> CatalogNode:
        tenant_reference = await self._registry_lookup.tenant(command.tenant_code)
        if tenant_reference.status != ReferenceStatus.VALID:
            raise InvalidReferenceError("tenant", command.tenant_code)
        async with self._unit_of_work as unit_of_work:
            if await unit_of_work.catalog_nodes.get(
                command.tenant_code,
                "default",
                command.node_code,
            ):
                raise DuplicateResourceError("catalog node", command.node_code)
            if command.parent_node_code is not None and await unit_of_work.catalog_nodes.get(
                command.tenant_code,
                "default",
                command.parent_node_code,
            ) is None:
                raise ResourceNotFoundError("catalog node", command.parent_node_code)
            reference = await _validate_target(
                unit_of_work,
                self._registry_lookup,
                command.tenant_code,
                command.node_type,
                command.target,
            )
            node = CatalogNode(
                tenant_code=command.tenant_code,
                node_code=command.node_code,
                node_type=command.node_type,
                display_name=command.display_name,
                parent_node_code=command.parent_node_code,
                sort_order=command.sort_order,
                target=command.target,
                metadata_json=command.metadata_json or {},
                reference_status=reference.status,
                display_snapshot_json=reference.snapshot_json,
            )
            await unit_of_work.catalog_nodes.add(node)
            await unit_of_work.commit()
        return node


class UpdateCatalogNode:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        registry_lookup: RegistryReferenceLookup,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._registry_lookup = registry_lookup

    async def execute(self, command: UpdateCatalogNodeCommand) -> CatalogNode:
        async with self._unit_of_work as unit_of_work:
            existing = await unit_of_work.catalog_nodes.get(
                command.tenant_code,
                "default",
                command.node_code,
            )
            if existing is None:
                raise ResourceNotFoundError("catalog node", command.node_code)
            reference = await _validate_target(
                unit_of_work,
                self._registry_lookup,
                command.tenant_code,
                existing.node_type,
                command.target,
            )
            updated = replace(
                existing,
                display_name=command.display_name,
                sort_order=command.sort_order,
                target=command.target,
                metadata_json=command.metadata_json or {},
                reference_status=reference.status,
                display_snapshot_json=reference.snapshot_json,
                updated_at=utc_now(),
            )
            await unit_of_work.catalog_nodes.update(updated)
            await unit_of_work.commit()
        return updated


class MoveCatalogNode:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, command: MoveCatalogNodeCommand) -> CatalogNode:
        async with self._unit_of_work as unit_of_work:
            existing = await unit_of_work.catalog_nodes.get(
                command.tenant_code,
                "default",
                command.node_code,
            )
            if existing is None:
                raise ResourceNotFoundError("catalog node", command.node_code)
            nodes = await unit_of_work.catalog_nodes.list_for_tree(
                command.tenant_code,
                "default",
            )
            if command.parent_node_code is not None:
                if command.parent_node_code == command.node_code:
                    raise InvalidOperationError("catalog node cannot be moved under itself")
                if not any(node.node_code == command.parent_node_code for node in nodes):
                    raise ResourceNotFoundError("catalog node", command.parent_node_code)
                descendants = _descendant_codes(nodes, command.node_code)
                if command.parent_node_code in descendants:
                    raise InvalidOperationError(
                        "catalog node cannot be moved under its descendant"
                    )
            updated = replace(
                existing,
                parent_node_code=command.parent_node_code,
                sort_order=command.sort_order,
                updated_at=utc_now(),
            )
            await unit_of_work.catalog_nodes.update(updated)
            await unit_of_work.commit()
        return updated


class DeleteCatalogNode:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, tenant_code: str, node_code: str) -> None:
        async with self._unit_of_work as unit_of_work:
            existing = await unit_of_work.catalog_nodes.get(
                tenant_code,
                "default",
                node_code,
            )
            if existing is None:
                raise ResourceNotFoundError("catalog node", node_code)
            nodes = await unit_of_work.catalog_nodes.list_for_tree(tenant_code, "default")
            if any(node.parent_node_code == node_code for node in nodes):
                raise InvalidOperationError(
                    "catalog node cannot be deleted while it has children"
                )
            await unit_of_work.catalog_nodes.delete(tenant_code, "default", node_code)
            await unit_of_work.commit()


async def _validate_target(
    unit_of_work: UnitOfWork,
    registry_lookup: RegistryReferenceLookup,
    tenant_code: str,
    node_type: CatalogNodeType,
    target: dict[str, Any] | None,
) -> RegistryReference:
    if node_type == CatalogNodeType.FOLDER:
        if target:
            raise InvalidReferenceError("folder target", str(target))
        return RegistryReference("folder", ReferenceStatus.UNKNOWN)
    target = target or {}
    if node_type == CatalogNodeType.ASSET_REF:
        asset_code = _target_value(target, "asset_code")
        reference = await registry_lookup.asset(tenant_code, asset_code)
    elif node_type == CatalogNodeType.AGENT_REF:
        asset_code = _target_value(target, "asset_code")
        agent_code = _target_value(target, "agent_code")
        reference = await registry_lookup.agent(tenant_code, asset_code, agent_code)
    elif node_type == CatalogNodeType.SOURCE_REF:
        asset_code = _target_value(target, "asset_code")
        agent_code = _target_value(target, "agent_code")
        source_code = _target_value(target, "source_code")
        reference = await registry_lookup.source(
            tenant_code,
            asset_code,
            agent_code,
            source_code,
        )
    elif node_type == CatalogNodeType.REGISTRY_POINT_REF:
        point_code = _target_value(target, "point_code")
        reference = await registry_lookup.point(tenant_code, point_code)
    elif node_type == CatalogNodeType.ASSET_GRAPH_NODE_REF:
        asset_graph_node_code = _target_value(target, "asset_graph_node_code")
        if await unit_of_work.asset_graph_nodes.get(
            tenant_code,
            asset_graph_node_code,
        ) is None:
            raise InvalidReferenceError("asset graph node", asset_graph_node_code)
        reference = RegistryReference(
            "asset_graph_node",
            ReferenceStatus.VALID,
            snapshot_json={"asset_graph_node_code": asset_graph_node_code},
        )
    else:
        raise InvalidReferenceError("catalog node type", node_type.value)
    if reference.status != ReferenceStatus.VALID:
        raise InvalidReferenceError(node_type.value, str(target))
    return reference


def _target_value(target: dict[str, Any], key: str) -> str:
    value = target.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InvalidReferenceError(key, str(target))
    return value


def _descendant_codes(nodes: list[CatalogNode], node_code: str) -> set[str]:
    children_by_parent: dict[str, list[str]] = {}
    for node in nodes:
        if node.parent_node_code is not None:
            children_by_parent.setdefault(node.parent_node_code, []).append(node.node_code)
    descendants: set[str] = set()
    stack = list(children_by_parent.get(node_code, []))
    while stack:
        child = stack.pop()
        if child in descendants:
            continue
        descendants.add(child)
        stack.extend(children_by_parent.get(child, []))
    return descendants
