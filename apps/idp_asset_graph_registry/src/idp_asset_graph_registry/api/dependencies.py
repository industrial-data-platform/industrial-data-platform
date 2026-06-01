from __future__ import annotations

from collections.abc import Callable

from fastapi import Request

from idp_asset_graph_registry.application.ports.registry_lookup import (
    RegistryReferenceLookup,
)
from idp_asset_graph_registry.application.ports.unit_of_work import UnitOfWork

UnitOfWorkFactory = Callable[[], UnitOfWork]


def get_unit_of_work_factory(request: Request) -> UnitOfWorkFactory:
    return request.app.state.unit_of_work_factory


def get_registry_lookup(request: Request) -> RegistryReferenceLookup:
    return request.app.state.registry_lookup
