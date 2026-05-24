from __future__ import annotations

from dataclasses import dataclass, field
from types import TracebackType
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from idp_asset_graph_registry.domain.entities import (
    AssetGraphNode,
    AssetGraphNodeAttribute,
    AssetGraphRelationship,
    CatalogNode,
    TelemetryBinding,
)
from idp_asset_graph_registry.domain.value_objects import (
    CatalogNodeType,
    ReferenceStatus,
    RelationType,
    ValueType,
)
from idp_asset_graph_registry.infrastructure.postgres.database import (
    PostgresSessionManager,
)
from idp_asset_graph_registry.infrastructure.postgres.models import (
    AssetGraphNodeAttributeModel,
    AssetGraphNodeModel,
    AssetGraphRelationshipModel,
    CatalogNodeModel,
    CatalogTreeModel,
    TelemetryBindingModel,
)


def _asset_graph_node_to_model(node: AssetGraphNode) -> AssetGraphNodeModel:
    return AssetGraphNodeModel(
        id=uuid4(),
        tenant_code=node.tenant_code,
        code=node.asset_graph_node_code,
        display_name=node.display_name,
        object_type=node.object_type,
        vocabulary_term=node.vocabulary_term,
        metadata_json=dict(node.metadata_json),
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


def _asset_graph_node_from_model(model: AssetGraphNodeModel) -> AssetGraphNode:
    return AssetGraphNode(
        tenant_code=model.tenant_code,
        asset_graph_node_code=model.code,
        display_name=model.display_name,
        object_type=model.object_type,
        vocabulary_term=model.vocabulary_term,
        metadata_json=dict(model.metadata_json),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _attribute_to_model(
    attribute: AssetGraphNodeAttribute,
) -> AssetGraphNodeAttributeModel:
    return AssetGraphNodeAttributeModel(
        id=uuid4(),
        tenant_code=attribute.tenant_code,
        asset_graph_node_code=attribute.asset_graph_node_code,
        attribute_key=attribute.attribute_key,
        value_type=attribute.value_type.value,
        unit=attribute.unit,
        vocabulary_term=attribute.vocabulary_term,
        metadata_json=dict(attribute.metadata_json),
        created_at=attribute.created_at,
        updated_at=attribute.updated_at,
    )


def _attribute_from_model(
    model: AssetGraphNodeAttributeModel,
) -> AssetGraphNodeAttribute:
    return AssetGraphNodeAttribute(
        tenant_code=model.tenant_code,
        asset_graph_node_code=model.asset_graph_node_code,
        attribute_key=model.attribute_key,
        value_type=ValueType(model.value_type),
        unit=model.unit,
        vocabulary_term=model.vocabulary_term,
        metadata_json=dict(model.metadata_json),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _relationship_to_model(
    relationship: AssetGraphRelationship,
) -> AssetGraphRelationshipModel:
    return AssetGraphRelationshipModel(
        id=uuid4(),
        tenant_code=relationship.tenant_code,
        code=relationship.relationship_code,
        source_asset_graph_node_code=relationship.source_asset_graph_node_code,
        target_asset_graph_node_code=relationship.target_asset_graph_node_code,
        relation_type=relationship.relation_type.value,
        metadata_json=dict(relationship.metadata_json),
        created_at=relationship.created_at,
        updated_at=relationship.updated_at,
    )


def _relationship_from_model(
    model: AssetGraphRelationshipModel,
) -> AssetGraphRelationship:
    return AssetGraphRelationship(
        tenant_code=model.tenant_code,
        relationship_code=model.code,
        source_asset_graph_node_code=model.source_asset_graph_node_code,
        target_asset_graph_node_code=model.target_asset_graph_node_code,
        relation_type=RelationType(model.relation_type),
        metadata_json=dict(model.metadata_json),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _binding_to_model(binding: TelemetryBinding) -> TelemetryBindingModel:
    return TelemetryBindingModel(
        id=uuid4(),
        tenant_code=binding.tenant_code,
        code=binding.binding_code,
        point_code=binding.point_code,
        asset_graph_node_code=binding.asset_graph_node_code,
        attribute_key=binding.attribute_key,
        reference_status=binding.reference_status.value,
        display_snapshot_json=dict(binding.display_snapshot_json),
        metadata_json=dict(binding.metadata_json),
        created_at=binding.created_at,
        updated_at=binding.updated_at,
    )


def _binding_from_model(model: TelemetryBindingModel) -> TelemetryBinding:
    return TelemetryBinding(
        tenant_code=model.tenant_code,
        binding_code=model.code,
        point_code=model.point_code,
        asset_graph_node_code=model.asset_graph_node_code,
        attribute_key=model.attribute_key,
        reference_status=ReferenceStatus(model.reference_status),
        display_snapshot_json=dict(model.display_snapshot_json),
        metadata_json=dict(model.metadata_json),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _catalog_node_to_model(node: CatalogNode) -> CatalogNodeModel:
    return CatalogNodeModel(
        id=uuid4(),
        tenant_code=node.tenant_code,
        tree_code=node.tree_code,
        code=node.node_code,
        parent_node_code=node.parent_node_code,
        node_type=node.node_type.value,
        display_name=node.display_name,
        sort_order=node.sort_order,
        target_json=dict(node.target) if node.target is not None else None,
        metadata_json=dict(node.metadata_json),
        reference_status=node.reference_status.value,
        display_snapshot_json=dict(node.display_snapshot_json),
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


def _catalog_node_from_model(model: CatalogNodeModel) -> CatalogNode:
    return CatalogNode(
        tenant_code=model.tenant_code,
        tree_code=model.tree_code,
        node_code=model.code,
        parent_node_code=model.parent_node_code,
        node_type=CatalogNodeType(model.node_type),
        display_name=model.display_name,
        sort_order=model.sort_order,
        target=dict(model.target_json) if model.target_json is not None else None,
        metadata_json=dict(model.metadata_json),
        reference_status=ReferenceStatus(model.reference_status),
        display_snapshot_json=dict(model.display_snapshot_json),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class PostgresAssetGraphNodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, node: AssetGraphNode) -> None:
        self.session.add(_asset_graph_node_to_model(node))
        await self.session.flush()

    async def update(self, node: AssetGraphNode) -> None:
        result = await self.session.scalars(
            select(AssetGraphNodeModel).where(
                AssetGraphNodeModel.tenant_code == node.tenant_code,
                AssetGraphNodeModel.code == node.asset_graph_node_code,
            )
        )
        model = result.first()
        if model is None:
            return
        model.display_name = node.display_name
        model.object_type = node.object_type
        model.vocabulary_term = node.vocabulary_term
        model.metadata_json = dict(node.metadata_json)
        model.updated_at = node.updated_at
        await self.session.flush()

    async def delete(self, tenant_code: str, asset_graph_node_code: str) -> None:
        result = await self.session.scalars(
            select(AssetGraphNodeModel).where(
                AssetGraphNodeModel.tenant_code == tenant_code,
                AssetGraphNodeModel.code == asset_graph_node_code,
            )
        )
        model = result.first()
        if model is not None:
            await self.session.delete(model)
            await self.session.flush()

    async def get(
        self,
        tenant_code: str,
        asset_graph_node_code: str,
    ) -> AssetGraphNode | None:
        result = await self.session.scalars(
            select(AssetGraphNodeModel).where(
                AssetGraphNodeModel.tenant_code == tenant_code,
                AssetGraphNodeModel.code == asset_graph_node_code,
            )
        )
        model = result.first()
        return _asset_graph_node_from_model(model) if model is not None else None

    async def list_for_tenant(self, tenant_code: str) -> list[AssetGraphNode]:
        result = await self.session.scalars(
            select(AssetGraphNodeModel)
            .where(AssetGraphNodeModel.tenant_code == tenant_code)
            .order_by(AssetGraphNodeModel.code)
        )
        return [_asset_graph_node_from_model(model) for model in result]


class PostgresAttributeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, attribute: AssetGraphNodeAttribute) -> None:
        self.session.add(_attribute_to_model(attribute))
        await self.session.flush()

    async def update(self, attribute: AssetGraphNodeAttribute) -> None:
        result = await self.session.scalars(
            select(AssetGraphNodeAttributeModel).where(
                AssetGraphNodeAttributeModel.tenant_code == attribute.tenant_code,
                AssetGraphNodeAttributeModel.asset_graph_node_code
                == attribute.asset_graph_node_code,
                AssetGraphNodeAttributeModel.attribute_key == attribute.attribute_key,
            )
        )
        model = result.first()
        if model is None:
            return
        model.value_type = attribute.value_type.value
        model.unit = attribute.unit
        model.vocabulary_term = attribute.vocabulary_term
        model.metadata_json = dict(attribute.metadata_json)
        model.updated_at = attribute.updated_at
        await self.session.flush()

    async def delete(
        self,
        tenant_code: str,
        asset_graph_node_code: str,
        attribute_key: str,
    ) -> None:
        result = await self.session.scalars(
            select(AssetGraphNodeAttributeModel).where(
                AssetGraphNodeAttributeModel.tenant_code == tenant_code,
                AssetGraphNodeAttributeModel.asset_graph_node_code
                == asset_graph_node_code,
                AssetGraphNodeAttributeModel.attribute_key == attribute_key,
            )
        )
        model = result.first()
        if model is not None:
            await self.session.delete(model)
            await self.session.flush()

    async def get(
        self,
        tenant_code: str,
        asset_graph_node_code: str,
        attribute_key: str,
    ) -> AssetGraphNodeAttribute | None:
        result = await self.session.scalars(
            select(AssetGraphNodeAttributeModel).where(
                AssetGraphNodeAttributeModel.tenant_code == tenant_code,
                AssetGraphNodeAttributeModel.asset_graph_node_code
                == asset_graph_node_code,
                AssetGraphNodeAttributeModel.attribute_key == attribute_key,
            )
        )
        model = result.first()
        return _attribute_from_model(model) if model is not None else None

    async def list_for_node(
        self,
        tenant_code: str,
        asset_graph_node_code: str,
    ) -> list[AssetGraphNodeAttribute]:
        result = await self.session.scalars(
            select(AssetGraphNodeAttributeModel)
            .where(
                AssetGraphNodeAttributeModel.tenant_code == tenant_code,
                AssetGraphNodeAttributeModel.asset_graph_node_code
                == asset_graph_node_code,
            )
            .order_by(AssetGraphNodeAttributeModel.attribute_key)
        )
        return [_attribute_from_model(model) for model in result]


class PostgresRelationshipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, relationship: AssetGraphRelationship) -> None:
        self.session.add(_relationship_to_model(relationship))
        await self.session.flush()

    async def update(self, relationship: AssetGraphRelationship) -> None:
        result = await self.session.scalars(
            select(AssetGraphRelationshipModel).where(
                AssetGraphRelationshipModel.tenant_code == relationship.tenant_code,
                AssetGraphRelationshipModel.code == relationship.relationship_code,
            )
        )
        model = result.first()
        if model is None:
            return
        model.source_asset_graph_node_code = relationship.source_asset_graph_node_code
        model.target_asset_graph_node_code = relationship.target_asset_graph_node_code
        model.relation_type = relationship.relation_type.value
        model.metadata_json = dict(relationship.metadata_json)
        model.updated_at = relationship.updated_at
        await self.session.flush()

    async def delete(self, tenant_code: str, relationship_code: str) -> None:
        result = await self.session.scalars(
            select(AssetGraphRelationshipModel).where(
                AssetGraphRelationshipModel.tenant_code == tenant_code,
                AssetGraphRelationshipModel.code == relationship_code,
            )
        )
        model = result.first()
        if model is not None:
            await self.session.delete(model)
            await self.session.flush()

    async def get(
        self,
        tenant_code: str,
        relationship_code: str,
    ) -> AssetGraphRelationship | None:
        result = await self.session.scalars(
            select(AssetGraphRelationshipModel).where(
                AssetGraphRelationshipModel.tenant_code == tenant_code,
                AssetGraphRelationshipModel.code == relationship_code,
            )
        )
        model = result.first()
        return _relationship_from_model(model) if model is not None else None

    async def list_for_tenant(self, tenant_code: str) -> list[AssetGraphRelationship]:
        result = await self.session.scalars(
            select(AssetGraphRelationshipModel)
            .where(AssetGraphRelationshipModel.tenant_code == tenant_code)
            .order_by(AssetGraphRelationshipModel.code)
        )
        return [_relationship_from_model(model) for model in result]


class PostgresTelemetryBindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, binding: TelemetryBinding) -> None:
        self.session.add(_binding_to_model(binding))
        await self.session.flush()

    async def update(self, binding: TelemetryBinding) -> None:
        result = await self.session.scalars(
            select(TelemetryBindingModel).where(
                TelemetryBindingModel.tenant_code == binding.tenant_code,
                TelemetryBindingModel.code == binding.binding_code,
            )
        )
        model = result.first()
        if model is None:
            return
        model.point_code = binding.point_code
        model.asset_graph_node_code = binding.asset_graph_node_code
        model.attribute_key = binding.attribute_key
        model.reference_status = binding.reference_status.value
        model.display_snapshot_json = dict(binding.display_snapshot_json)
        model.metadata_json = dict(binding.metadata_json)
        model.updated_at = binding.updated_at
        await self.session.flush()

    async def delete(self, tenant_code: str, binding_code: str) -> None:
        result = await self.session.scalars(
            select(TelemetryBindingModel).where(
                TelemetryBindingModel.tenant_code == tenant_code,
                TelemetryBindingModel.code == binding_code,
            )
        )
        model = result.first()
        if model is not None:
            await self.session.delete(model)
            await self.session.flush()

    async def get(self, tenant_code: str, binding_code: str) -> TelemetryBinding | None:
        result = await self.session.scalars(
            select(TelemetryBindingModel).where(
                TelemetryBindingModel.tenant_code == tenant_code,
                TelemetryBindingModel.code == binding_code,
            )
        )
        model = result.first()
        return _binding_from_model(model) if model is not None else None

    async def list_for_tenant(self, tenant_code: str) -> list[TelemetryBinding]:
        result = await self.session.scalars(
            select(TelemetryBindingModel)
            .where(TelemetryBindingModel.tenant_code == tenant_code)
            .order_by(TelemetryBindingModel.code)
        )
        return [_binding_from_model(model) for model in result]


class PostgresCatalogNodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, node: CatalogNode) -> None:
        await self._ensure_default_tree(node.tenant_code, node.tree_code)
        self.session.add(_catalog_node_to_model(node))
        await self.session.flush()

    async def get(
        self,
        tenant_code: str,
        tree_code: str,
        node_code: str,
    ) -> CatalogNode | None:
        result = await self.session.scalars(
            select(CatalogNodeModel).where(
                CatalogNodeModel.tenant_code == tenant_code,
                CatalogNodeModel.tree_code == tree_code,
                CatalogNodeModel.code == node_code,
            )
        )
        model = result.first()
        return _catalog_node_from_model(model) if model is not None else None

    async def update(self, node: CatalogNode) -> None:
        result = await self.session.scalars(
            select(CatalogNodeModel).where(
                CatalogNodeModel.tenant_code == node.tenant_code,
                CatalogNodeModel.tree_code == node.tree_code,
                CatalogNodeModel.code == node.node_code,
            )
        )
        model = result.first()
        if model is None:
            return
        model.parent_node_code = node.parent_node_code
        model.display_name = node.display_name
        model.sort_order = node.sort_order
        model.target_json = dict(node.target) if node.target is not None else None
        model.metadata_json = dict(node.metadata_json)
        model.reference_status = node.reference_status.value
        model.display_snapshot_json = dict(node.display_snapshot_json)
        model.updated_at = node.updated_at
        await self.session.flush()

    async def delete(self, tenant_code: str, tree_code: str, node_code: str) -> None:
        result = await self.session.scalars(
            select(CatalogNodeModel).where(
                CatalogNodeModel.tenant_code == tenant_code,
                CatalogNodeModel.tree_code == tree_code,
                CatalogNodeModel.code == node_code,
            )
        )
        model = result.first()
        if model is not None:
            await self.session.delete(model)
            await self.session.flush()

    async def list_for_tree(self, tenant_code: str, tree_code: str) -> list[CatalogNode]:
        result = await self.session.scalars(
            select(CatalogNodeModel)
            .where(
                CatalogNodeModel.tenant_code == tenant_code,
                CatalogNodeModel.tree_code == tree_code,
            )
            .order_by(
                CatalogNodeModel.parent_node_code.nullsfirst(),
                CatalogNodeModel.sort_order,
                CatalogNodeModel.code,
            )
        )
        return [_catalog_node_from_model(model) for model in result]

    async def _ensure_default_tree(self, tenant_code: str, tree_code: str) -> None:
        result = await self.session.scalars(
            select(CatalogTreeModel).where(
                CatalogTreeModel.tenant_code == tenant_code,
                CatalogTreeModel.code == tree_code,
            )
        )
        if result.first() is not None:
            return
        from idp_asset_graph_registry.domain.entities import utc_now

        now = utc_now()
        self.session.add(
            CatalogTreeModel(
                id=uuid4(),
                tenant_code=tenant_code,
                code=tree_code,
                display_name="Default",
                created_at=now,
            )
        )
        await self.session.flush()


@dataclass
class PostgresUnitOfWork:
    session_factory: async_sessionmaker[AsyncSession]
    asset_graph_nodes: PostgresAssetGraphNodeRepository = field(init=False)
    attributes: PostgresAttributeRepository = field(init=False)
    relationships: PostgresRelationshipRepository = field(init=False)
    telemetry_bindings: PostgresTelemetryBindingRepository = field(init=False)
    catalog_nodes: PostgresCatalogNodeRepository = field(init=False)
    _session: AsyncSession = field(init=False)
    _committed: bool = field(default=False, init=False)

    async def __aenter__(self) -> PostgresUnitOfWork:
        self._session = self.session_factory()
        self.asset_graph_nodes = PostgresAssetGraphNodeRepository(self._session)
        self.attributes = PostgresAttributeRepository(self._session)
        self.relationships = PostgresRelationshipRepository(self._session)
        self.telemetry_bindings = PostgresTelemetryBindingRepository(self._session)
        self.catalog_nodes = PostgresCatalogNodeRepository(self._session)
        self._committed = False
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None or not self._committed:
            await self._session.rollback()
        await self._session.close()

    async def commit(self) -> None:
        await self._session.commit()
        self._committed = True


@dataclass(frozen=True)
class PostgresUnitOfWorkFactory:
    session_manager: PostgresSessionManager

    @classmethod
    def from_url(cls, database_url: str) -> PostgresUnitOfWorkFactory:
        return cls(session_manager=PostgresSessionManager.from_url(database_url))

    def __call__(self) -> PostgresUnitOfWork:
        return PostgresUnitOfWork(self.session_manager.session_factory)

    async def dispose(self) -> None:
        await self.session_manager.dispose()
