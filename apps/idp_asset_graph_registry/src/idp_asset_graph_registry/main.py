from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from idp_asset_graph_registry.api.routers import (
    asset_graph,
    catalog,
    health,
    vocabulary,
)
from idp_asset_graph_registry.application.ports.registry_lookup import (
    RegistryReferenceLookup,
)
from idp_asset_graph_registry.application.ports.unit_of_work import UnitOfWork
from idp_asset_graph_registry.infrastructure.memory.unit_of_work import (
    InMemoryUnitOfWorkFactory,
)
from idp_asset_graph_registry.infrastructure.postgres.unit_of_work import (
    PostgresUnitOfWorkFactory,
)
from idp_asset_graph_registry.infrastructure.registry_lookup import (
    ConfigRegistryHttpReferenceLookup,
    PermissiveRegistryReferenceLookup,
)
from idp_asset_graph_registry.settings import AssetGraphRegistrySettings


def create_app(
    settings: AssetGraphRegistrySettings | None = None,
    unit_of_work_factory: Callable[[], UnitOfWork] | None = None,
    registry_lookup: RegistryReferenceLookup | None = None,
) -> FastAPI:
    resolved_settings = settings or AssetGraphRegistrySettings.from_env()
    resolved_unit_of_work_factory = unit_of_work_factory
    if (
        resolved_unit_of_work_factory is None
        and resolved_settings.database_url is not None
    ):
        resolved_unit_of_work_factory = PostgresUnitOfWorkFactory.from_url(
            resolved_settings.database_url
        )
    if resolved_unit_of_work_factory is None:
        resolved_unit_of_work_factory = InMemoryUnitOfWorkFactory()
    resolved_registry_lookup = registry_lookup
    if (
        resolved_registry_lookup is None
        and resolved_settings.config_registry_url is not None
    ):
        resolved_registry_lookup = ConfigRegistryHttpReferenceLookup(
            resolved_settings.config_registry_url
        )
    if resolved_registry_lookup is None:
        resolved_registry_lookup = PermissiveRegistryReferenceLookup()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            dispose = getattr(app.state.unit_of_work_factory, "dispose", None)
            if dispose is not None:
                await dispose()

    app = FastAPI(
        title="Industrial Data Platform Asset Graph Registry",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.state.unit_of_work_factory = resolved_unit_of_work_factory
    app.state.registry_lookup = resolved_registry_lookup
    app.include_router(health.router)
    app.include_router(vocabulary.router)
    app.include_router(catalog.router)
    app.include_router(asset_graph.router)
    return app

