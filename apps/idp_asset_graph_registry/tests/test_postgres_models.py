from __future__ import annotations

from idp_asset_graph_registry.infrastructure.postgres.models import Base


def test_asset_graph_registry_tables_are_owned_by_package_metadata() -> None:
    assert {
        "asset_graph_nodes",
        "asset_graph_node_attributes",
        "asset_graph_relationships",
        "asset_graph_telemetry_bindings",
        "catalog_trees",
        "catalog_nodes",
    }.issubset(Base.metadata.tables.keys())


def test_asset_graph_registry_tables_do_not_fk_to_config_registry_internals() -> None:
    for table in Base.metadata.tables.values():
        for foreign_key in table.foreign_keys:
            assert not foreign_key.target_fullname.startswith(
                ("tenants.", "assets.", "agents.", "sources.", "points.")
            )
