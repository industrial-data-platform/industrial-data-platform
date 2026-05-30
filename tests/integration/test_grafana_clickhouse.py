from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.integration_grafana,
    pytest.mark.integration_web_monitoring,
]
REPO_ROOT = Path(__file__).resolve().parents[2]
GRAFANA_DASHBOARDS_DIR = REPO_ROOT / "infra" / "local" / "grafana" / "dashboards"
DATASOURCE_UID = "idp-telemetry-store-telemetry-store"
SERVICE_FOLDER_TITLE = "Service Operations"
SERVICE_FOLDER_UID = "idp-service-operations"
SERVICE_OVERVIEW_UID = "idp-service-telemetry-overview"
POINT_DRILLDOWN_UID = "idp-telemetry-point-drilldown"
DRILLDOWN_VARIABLES = [
    "tenant_id",
    "asset_id",
    "source_type",
    "agent_id",
    "source_id",
    "point_key",
]
DASHBOARDS = {
    SERVICE_OVERVIEW_UID: {
        "file": GRAFANA_DASHBOARDS_DIR / "service-telemetry-overview.json",
        "title": "Service Telemetry Overview",
        "query": "Service%20Telemetry%20Overview",
    },
    POINT_DRILLDOWN_UID: {
        "file": GRAFANA_DASHBOARDS_DIR / "telemetry-point-drilldown.json",
        "title": "Telemetry Point Drilldown",
        "query": "Telemetry%20Point%20Drilldown",
    },
}
RUN_ID = "grafana-it"
RUN_TENANT_ID = f"poc-tenant-{RUN_ID}"
RUN_ASSET_ID = f"poc-asset-{RUN_ID}"
RUN_AGENT_ID = "poc-agent"
RUN_SOURCE_ID = "poc-source"
RUN_SOURCE_TYPE = "poc"
RUN_POINT_KEY = "point-00000"


def test_service_dashboard_json_static_guardrails() -> None:
    loaded_dashboards = {
        dashboard_uid: json.loads(Path(expected["file"]).read_text(encoding="utf-8"))
        for dashboard_uid, expected in DASHBOARDS.items()
    }
    _assert_service_dashboard_contract(
        loaded_dashboards[SERVICE_OVERVIEW_UID],
        loaded_dashboards[POINT_DRILLDOWN_UID],
    )


@pytest.mark.integration_smoke
def test_grafana_provisions_service_dashboards(
    local_grafana_clickhouse_stack,
) -> None:
    start_ts = (datetime.now(tz=UTC) - timedelta(hours=1)).replace(microsecond=0)
    load_poc_result = subprocess.run(
        [
            "uv",
            "run",
            "--env-file",
            str(local_grafana_clickhouse_stack.env_file),
            "idp-telemetry-store",
            "load-poc",
            "telemetry-read-models",
            "--rows",
            "2000",
            "--points",
            "20",
            "--batch-size",
            "1000",
            "--duplicate-every",
            "10",
            "--run-id",
            RUN_ID,
            "--start-ts",
            start_ts.isoformat().replace("+00:00", "Z"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert load_poc_result.returncode == 0, load_poc_result.stderr

    datasource = local_grafana_clickhouse_stack.grafana_json(
        "GET",
        f"/api/datasources/uid/{DATASOURCE_UID}",
    )
    assert isinstance(datasource, dict)
    assert datasource["uid"] == DATASOURCE_UID
    assert datasource["type"] == "grafana-clickhouse-datasource"

    service_folder = _wait_for_grafana_json(
        local_grafana_clickhouse_stack,
        "GET",
        f"/api/folders/{SERVICE_FOLDER_UID}",
    )
    assert isinstance(service_folder, dict)
    assert service_folder["title"] == SERVICE_FOLDER_TITLE

    loaded_dashboards: dict[str, dict[str, Any]] = {}
    for dashboard_uid, expected in DASHBOARDS.items():
        search_results = _wait_for_dashboard_search_results(
            local_grafana_clickhouse_stack,
            query=str(expected["query"]),
            dashboard_uid=dashboard_uid,
        )
        assert any(item.get("uid") == dashboard_uid for item in search_results)

        dashboard_response = local_grafana_clickhouse_stack.grafana_json(
            "GET",
            f"/api/dashboards/uid/{dashboard_uid}",
        )
        assert isinstance(dashboard_response, dict)
        meta = dashboard_response["meta"]
        dashboard = dashboard_response["dashboard"]
        assert isinstance(meta, dict)
        assert isinstance(dashboard, dict)
        assert dashboard["uid"] == dashboard_uid
        assert dashboard["title"] == expected["title"]
        assert dashboard["editable"] is False
        assert dashboard["refresh"] == "1m"
        assert dashboard["time"] == {"from": "now-6h", "to": "now"}
        assert meta["folderTitle"] == SERVICE_FOLDER_TITLE
        loaded_dashboards[dashboard_uid] = dashboard

    overview = loaded_dashboards[SERVICE_OVERVIEW_UID]
    drilldown = loaded_dashboards[POINT_DRILLDOWN_UID]
    _assert_service_dashboard_contract(overview, drilldown)

    query_response = local_grafana_clickhouse_stack.grafana_json(
        "POST",
        "/api/ds/query",
        _grafana_table_query_payload(
            f"""
            SELECT uniqExact(tuple(tenant_id, asset_id, source_type, agent_id, source_id, point_key)) AS latest_points
            FROM service_point_inventory_v1
            WHERE tenant_id = 'poc-tenant-{RUN_ID}'
            """.strip()
        ),
        timeout=60,
    )
    assert isinstance(query_response, dict)
    _assert_grafana_query_succeeded(query_response)
    assert _contains_scalar_value(query_response, 20), json.dumps(
        query_response,
        indent=2,
        sort_keys=True,
    )

    for raw_sql in _representative_dashboard_sql(overview, drilldown):
        query_response = local_grafana_clickhouse_stack.grafana_json(
            "POST",
            "/api/ds/query",
            _grafana_table_query_payload(_replace_dashboard_variables(raw_sql)),
            timeout=60,
        )
        assert isinstance(query_response, dict)
        _assert_grafana_query_succeeded(query_response)


@pytest.mark.integration_smoke
def test_seeded_clickhouse_rows_are_visible_through_service_dashboard_api(
    local_grafana_clickhouse_stack,
) -> None:
    run_id = uuid.uuid4().hex[:10]
    seed = _DashboardApiSeed(
        tenant_id=f"grafana-api-tenant-{run_id}",
        asset_id=f"grafana-api-asset-{run_id}",
        agent_id=f"grafana-api-agent-{run_id}",
        source_id=f"grafana-api-source-{run_id}",
        source_type="knx",
        point_key=f"api-point-{run_id}",
        source_config_revision=f"rev-grafana-api-{run_id}",
        event_count=150,
    )
    _seed_clickhouse_dashboard_rows(local_grafana_clickhouse_stack, seed)

    overview = _wait_for_grafana_dashboard(
        local_grafana_clickhouse_stack,
        SERVICE_OVERVIEW_UID,
    )
    drilldown = _wait_for_grafana_dashboard(
        local_grafana_clickhouse_stack,
        POINT_DRILLDOWN_UID,
    )

    top_points_response = _query_dashboard_panel(
        local_grafana_clickhouse_stack,
        overview,
        "Top points by activity and quality",
    )[0]
    assert _contains_scalar_value(top_points_response, seed.tenant_id), json.dumps(
        top_points_response,
        indent=2,
        sort_keys=True,
    )
    assert _contains_scalar_value(top_points_response, seed.point_key), json.dumps(
        top_points_response,
        indent=2,
        sort_keys=True,
    )
    assert _contains_scalar_value(top_points_response, seed.event_count), json.dumps(
        top_points_response,
        indent=2,
        sort_keys=True,
    )

    agent_status_response = _query_dashboard_panel(
        local_grafana_clickhouse_stack,
        overview,
        "Agent status",
    )[0]
    assert _contains_scalar_value(agent_status_response, "online"), json.dumps(
        agent_status_response,
        indent=2,
        sort_keys=True,
    )

    source_status_response = _query_dashboard_panel(
        local_grafana_clickhouse_stack,
        overview,
        "Source status",
    )[0]
    assert _contains_scalar_value(source_status_response, "connected"), json.dumps(
        source_status_response,
        indent=2,
        sort_keys=True,
    )

    latest_values_response = _query_dashboard_panel(
        local_grafana_clickhouse_stack,
        drilldown,
        "Latest values",
        seed=seed,
    )[0]
    assert _contains_scalar_value(latest_values_response, seed.point_key), json.dumps(
        latest_values_response,
        indent=2,
        sort_keys=True,
    )
    assert _contains_scalar_value(
        latest_values_response,
        seed.source_config_revision,
    ), json.dumps(latest_values_response, indent=2, sort_keys=True)
    assert _contains_scalar_value(latest_values_response, "good"), json.dumps(
        latest_values_response,
        indent=2,
        sort_keys=True,
    )

    point_trend_responses = _query_dashboard_panel(
        local_grafana_clickhouse_stack,
        drilldown,
        "Point trend",
        seed=seed,
    )
    point_trend_values = [
        value
        for response in point_trend_responses
        for value in _grafana_field_values(response, "value")
    ]
    assert len(point_trend_values) == seed.event_count, json.dumps(
        point_trend_responses,
        indent=2,
        sort_keys=True,
    )
    assert _contains_scalar_value(point_trend_responses, 1000), json.dumps(
        point_trend_responses,
        indent=2,
        sort_keys=True,
    )
    assert _contains_scalar_value(
        point_trend_responses,
        1000 + seed.event_count - 1,
    ), json.dumps(point_trend_responses, indent=2, sort_keys=True)

    second_seed = _DashboardApiSeed(
        tenant_id=seed.tenant_id,
        asset_id=seed.asset_id,
        agent_id=seed.agent_id,
        source_id=seed.source_id,
        source_type=seed.source_type,
        point_key=f"{seed.point_key}-second",
        source_config_revision=f"{seed.source_config_revision}-second",
        event_count=25,
    )
    _seed_clickhouse_dashboard_rows(local_grafana_clickhouse_stack, second_seed)
    multi_point_trend_responses = _query_dashboard_panel(
        local_grafana_clickhouse_stack,
        drilldown,
        "Point trend",
        seed=seed,
        point_keys=[seed.point_key, second_seed.point_key],
    )
    multi_point_trend_values = [
        value
        for response in multi_point_trend_responses
        for value in _grafana_field_values(response, "value")
    ]
    assert len(multi_point_trend_values) == (
        seed.event_count + second_seed.event_count
    ), json.dumps(multi_point_trend_responses, indent=2, sort_keys=True)

    event_rate_response = _query_dashboard_panel(
        local_grafana_clickhouse_stack,
        drilldown,
        "Event rate",
        seed=seed,
    )[0]
    assert sum(_grafana_field_values(event_rate_response, "value")) == (
        seed.event_count
    ), json.dumps(event_rate_response, indent=2, sort_keys=True)

    quality_distribution_response = _query_dashboard_panel(
        local_grafana_clickhouse_stack,
        drilldown,
        "Quality distribution",
        seed=seed,
    )[0]
    assert sum(_grafana_field_values(quality_distribution_response, "events")) == (
        seed.event_count
    ), json.dumps(quality_distribution_response, indent=2, sort_keys=True)

    runtime_status_response = _query_dashboard_panel(
        local_grafana_clickhouse_stack,
        drilldown,
        "Runtime status context",
        seed=seed,
    )[0]
    assert _contains_scalar_value(
        runtime_status_response,
        "service_latest_agent_status_v1",
    ), json.dumps(runtime_status_response, indent=2, sort_keys=True)
    assert _contains_scalar_value(
        runtime_status_response,
        "service_latest_source_connection_v1",
    ), json.dumps(runtime_status_response, indent=2, sort_keys=True)


def _assert_service_dashboard_contract(
    overview: dict[str, Any],
    drilldown: dict[str, Any],
) -> None:
    overview_sql = _dashboard_raw_sql(overview)
    drilldown_sql = _dashboard_raw_sql(drilldown)
    all_sql = overview_sql + drilldown_sql
    dashboard_json = "\n".join(
        Path(expected["file"]).read_text(encoding="utf-8")
        for expected in DASHBOARDS.values()
    )

    assert DATASOURCE_UID in dashboard_json
    assert "service_point_inventory_v1" in dashboard_json
    assert "service_telemetry_activity_1m_v1" in dashboard_json
    assert "service_latest_agent_status_v1" in dashboard_json
    assert "service_latest_source_connection_v1" in dashboard_json
    assert "telemetry_latest_v1" in dashboard_json
    assert "telemetry_events_dedup_v1" in dashboard_json
    assert "agent_status_events_v1" not in dashboard_json
    assert "source_connection_events_v1" not in dashboard_json
    assert "source_config_snapshots_v1" not in dashboard_json
    assert "configured_points" not in dashboard_json
    assert "meta/catalog" not in dashboard_json
    assert "idp/v1/" not in dashboard_json
    assert "Asset Graph" not in dashboard_json
    assert "derived_events_v1" not in dashboard_json
    assert "alarm_history_events_v1" not in dashboard_json

    assert all("LIMIT" in sql.upper() for sql in _table_or_topn_sql(all_sql))
    assert all(
        "$__timeFilter_ms(" in sql
        for sql in _time_series_sql(overview, drilldown)
    )
    assert all(
        _time_series_points_are_visible(panel)
        for dashboard in (overview, drilldown)
        for panel in dashboard.get("panels", [])
        if isinstance(panel, dict) and panel.get("type") == "timeseries"
    )
    assert not any(
        "FROM telemetry_1m_v1" in sql
        and "point_key" in sql
        and "GROUP BY bucket_start, point_key" in sql
        and "LIMIT" not in sql.upper()
        for sql in all_sql
    )
    _assert_overview_point_drilldown_links(overview)
    _assert_drilldown_service_model_filters(drilldown)

    variable_by_name = {
        variable["name"]: variable
        for variable in drilldown["templating"]["list"]
        if isinstance(variable, dict)
    }
    assert list(variable_by_name) == DRILLDOWN_VARIABLES
    for variable_name in DRILLDOWN_VARIABLES:
        variable = variable_by_name[variable_name]
        assert variable["type"] == "query"
        assert variable["datasource"]["uid"] == DATASOURCE_UID
        assert "LIMIT" in variable["query"].upper()
        assert variable["multi"] is (variable_name == "point_key")
    assert "${tenant_id:singlequote}" in variable_by_name["asset_id"]["query"]
    assert "${asset_id:singlequote}" in variable_by_name["source_type"]["query"]
    assert "${source_type:singlequote}" in variable_by_name["agent_id"]["query"]
    assert "${agent_id:singlequote}" in variable_by_name["source_id"]["query"]
    assert "${source_id:singlequote}" in variable_by_name["point_key"]["query"]

    point_trend_sql = "\n".join(_dashboard_panel_sql(drilldown, "Point trend"))
    _assert_sql_contains_fragments(
        point_trend_sql,
        [
            "FROM telemetry_events_dedup_v1",
            "tenant_id IN (${tenant_id:singlequote})",
            "asset_id IN (${asset_id:singlequote})",
            "source_id IN (${source_id:singlequote})",
            "point_key IN (${point_key:singlequote})",
            "value_float AS value",
        ],
    )


def _time_series_points_are_visible(panel: dict[str, Any]) -> bool:
    custom = panel.get("fieldConfig", {}).get("defaults", {}).get("custom", {})
    return custom.get("showPoints") == "always" and custom.get("pointSize", 0) > 0


def _assert_overview_point_drilldown_links(overview: dict[str, Any]) -> None:
    point_identity_variables = [
        "tenant_id",
        "asset_id",
        "source_type",
        "agent_id",
        "source_id",
        "point_key",
    ]
    linked_panel_titles = {"Top points by activity and quality"}
    panels_by_title = {
        panel["title"]: panel
        for panel in overview.get("panels", [])
        if isinstance(panel, dict) and panel.get("title") in linked_panel_titles
    }
    assert set(panels_by_title) == linked_panel_titles

    for panel in panels_by_title.values():
        defaults = panel["fieldConfig"]["defaults"]
        links = defaults.get("links")
        assert isinstance(links, list) and len(links) == 1
        link = links[0]
        assert link["title"] == "Open point drilldown"
        assert link["targetBlank"] is False
        url = link["url"]
        assert POINT_DRILLDOWN_UID in url
        assert "${__url_time_range}" in url
        for variable_name in point_identity_variables:
            expected_mapping = (
                f"var-{variable_name}="
                f'${{__data.fields["{variable_name}"]}}'
            )
            assert expected_mapping in url


def _assert_drilldown_service_model_filters(drilldown: dict[str, Any]) -> None:
    event_rate_sql = "\n".join(_dashboard_panel_sql(drilldown, "Event rate"))
    _assert_sql_contains_fragments(
        event_rate_sql,
        [
            "FROM service_telemetry_activity_1m_v1",
            "tenant_id IN (${tenant_id:singlequote})",
            "asset_id IN (${asset_id:singlequote})",
            "source_type IN (${source_type:singlequote})",
            "source_id IN (${source_id:singlequote})",
            "point_key IN (${point_key:singlequote})",
            "agent_id IN (${agent_id:singlequote})",
            "$__timeFilter_ms(bucket_start)",
        ],
    )

    runtime_status_sql = "\n".join(
        _dashboard_panel_sql(drilldown, "Runtime status context")
    )
    _assert_sql_contains_fragments(
        runtime_status_sql,
        [
            "FROM service_point_inventory_v1",
            "tenant_id IN (${tenant_id:singlequote})",
            "asset_id IN (${asset_id:singlequote})",
            "source_type IN (${source_type:singlequote})",
            "agent_id IN (${agent_id:singlequote})",
            "source_id IN (${source_id:singlequote})",
        ],
    )


def _assert_sql_contains_fragments(sql: str, fragments: list[str]) -> None:
    missing = [fragment for fragment in fragments if fragment not in sql]
    assert missing == [], f"Missing SQL fragments: {missing!r} in {sql}"


def _grafana_table_query_payload(raw_sql: str) -> dict[str, object]:
    now_ms = int(time.time() * 1000)
    return {
        "from": str(now_ms - 6 * 60 * 60 * 1000),
        "to": str(now_ms),
        "queries": [
            {
                "datasource": {
                    "type": "grafana-clickhouse-datasource",
                    "uid": DATASOURCE_UID,
                },
                "editorType": "sql",
                "format": 1,
                "intervalMs": 60000,
                "maxDataPoints": 500,
                "meta": {
                    "builderOptions": {
                        "columns": [],
                        "database": "",
                        "limit": 1000,
                        "mode": "list",
                        "queryType": "table",
                        "table": "",
                    }
                },
                "pluginVersion": "4.15.0",
                "queryType": "table",
                "rawSql": raw_sql,
                "refId": "A",
            }
        ],
        "range": {
            "from": "now-6h",
            "to": "now",
            "raw": {
                "from": "now-6h",
                "to": "now",
            },
        },
    }


def _dashboard_raw_sql(dashboard: dict[str, Any]) -> list[str]:
    sql: list[str] = []
    for panel in dashboard.get("panels", []):
        if not isinstance(panel, dict):
            continue
        for target in panel.get("targets", []):
            if isinstance(target, dict) and isinstance(target.get("rawSql"), str):
                assert target["datasource"]["uid"] == DATASOURCE_UID
                sql.append(target["rawSql"])
    return sql


def _dashboard_panel_sql(dashboard: dict[str, Any], title: str) -> list[str]:
    matching_panels = [
        panel
        for panel in dashboard.get("panels", [])
        if isinstance(panel, dict) and panel.get("title") == title
    ]
    assert len(matching_panels) == 1
    return _dashboard_raw_sql({"panels": matching_panels})


def _query_dashboard_panel(
    local_grafana_clickhouse_stack,
    dashboard: dict[str, Any],
    title: str,
    *,
    seed: _DashboardApiSeed | None = None,
    point_keys: list[str] | None = None,
) -> list[dict[str, Any]]:
    responses: list[dict[str, Any]] = []
    for raw_sql in _dashboard_panel_sql(dashboard, title):
        query_response = local_grafana_clickhouse_stack.grafana_json(
            "POST",
            "/api/ds/query",
            _grafana_table_query_payload(
                _replace_dashboard_variables(
                    raw_sql,
                    seed=seed,
                    point_keys=point_keys,
                )
            ),
            timeout=60,
        )
        assert isinstance(query_response, dict)
        _assert_grafana_query_succeeded(query_response)
        responses.append(query_response)
    return responses


def _table_or_topn_sql(sql: list[str]) -> list[str]:
    return [
        statement
        for statement in sql
        if "ORDER BY" in statement.upper()
        or "GROUP BY" in statement.upper()
        or "FROM TELEMETRY_EVENTS_DEDUP_V1" in statement.upper()
    ]


def _time_series_sql(*dashboards: dict[str, Any]) -> list[str]:
    statements: list[str] = []
    for dashboard in dashboards:
        for panel in dashboard.get("panels", []):
            if not isinstance(panel, dict) or panel.get("type") != "timeseries":
                continue
            statements.extend(_dashboard_raw_sql({"panels": [panel]}))
    return statements


def _representative_dashboard_sql(
    overview: dict[str, Any],
    drilldown: dict[str, Any],
) -> list[str]:
    panels_by_dashboard_and_title: dict[tuple[str, str], dict[str, Any]] = {}
    for dashboard_uid, dashboard in (
        (SERVICE_OVERVIEW_UID, overview),
        (POINT_DRILLDOWN_UID, drilldown),
    ):
        for panel in dashboard.get("panels", []):
            if isinstance(panel, dict):
                panels_by_dashboard_and_title[(dashboard_uid, panel["title"])] = panel

    panels_to_execute = [
        (SERVICE_OVERVIEW_UID, "Observed points"),
        (SERVICE_OVERVIEW_UID, "Telemetry event rate"),
        (SERVICE_OVERVIEW_UID, "Quality distribution"),
        (SERVICE_OVERVIEW_UID, "Top points by activity and quality"),
        (POINT_DRILLDOWN_UID, "Point trend"),
        (POINT_DRILLDOWN_UID, "Latest values"),
        (POINT_DRILLDOWN_UID, "Quality distribution"),
        (POINT_DRILLDOWN_UID, "Event rate"),
        (POINT_DRILLDOWN_UID, "Runtime status context"),
    ]
    return [
        sql
        for dashboard_uid, title in panels_to_execute
        for sql in _dashboard_raw_sql(
            {"panels": [panels_by_dashboard_and_title[(dashboard_uid, title)]]}
        )
    ]


def _assert_grafana_query_succeeded(response: dict[str, Any]) -> None:
    results = response.get("results")
    assert isinstance(results, dict) and results, json.dumps(
        response,
        indent=2,
        sort_keys=True,
    )
    for result in results.values():
        assert isinstance(result, dict), json.dumps(
            response,
            indent=2,
            sort_keys=True,
        )
        assert "error" not in result, json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )


def _replace_dashboard_variables(
    raw_sql: str,
    *,
    seed: _DashboardApiSeed | None = None,
    point_keys: list[str] | None = None,
) -> str:
    tenant_id = RUN_TENANT_ID if seed is None else seed.tenant_id
    asset_id = RUN_ASSET_ID if seed is None else seed.asset_id
    source_type = RUN_SOURCE_TYPE if seed is None else seed.source_type
    agent_id = RUN_AGENT_ID if seed is None else seed.agent_id
    source_id = RUN_SOURCE_ID if seed is None else seed.source_id
    point_key = RUN_POINT_KEY if seed is None else seed.point_key
    point_key_values = point_keys if point_keys is not None else [point_key]
    replacements = {
        "${tenant_id:singlequote}": f"'{tenant_id}'",
        "${asset_id:singlequote}": f"'{asset_id}'",
        "${source_type:singlequote}": f"'{source_type}'",
        "${agent_id:singlequote}": f"'{agent_id}'",
        "${source_id:singlequote}": f"'{source_id}'",
        "${point_key:singlequote}": ",".join(f"'{key}'" for key in point_key_values),
    }
    sql = raw_sql
    for needle, replacement in replacements.items():
        sql = sql.replace(needle, replacement)
    return sql


def _contains_scalar_value(value: Any, expected: object) -> bool:
    if value == expected:
        return True
    if isinstance(value, dict):
        return any(_contains_scalar_value(item, expected) for item in value.values())
    if isinstance(value, list):
        return any(_contains_scalar_value(item, expected) for item in value)
    return False


def _grafana_field_values(response: dict[str, Any], field_name: str) -> list[int | float]:
    values: list[int | float] = []
    results = response.get("results", {})
    if not isinstance(results, dict):
        return values
    for result in results.values():
        if not isinstance(result, dict):
            continue
        for frame in result.get("frames", []):
            if not isinstance(frame, dict):
                continue
            fields = frame.get("schema", {}).get("fields", [])
            data_values = frame.get("data", {}).get("values", [])
            if not isinstance(fields, list) or not isinstance(data_values, list):
                continue
            for index, field in enumerate(fields):
                if (
                    isinstance(field, dict)
                    and field.get("name") == field_name
                    and index < len(data_values)
                    and isinstance(data_values[index], list)
                ):
                    values.extend(
                        value
                        for value in data_values[index]
                        if isinstance(value, int | float)
                    )
    return values


def _wait_for_dashboard_search_results(
    local_grafana_clickhouse_stack,
    *,
    query: str,
    dashboard_uid: str,
    timeout: float = 30.0,
) -> list[dict[str, object]]:
    deadline = time.monotonic() + timeout
    last_results: list[dict[str, object]] = []

    while time.monotonic() < deadline:
        search_results = local_grafana_clickhouse_stack.grafana_json(
            "GET",
            f"/api/search?query={query}",
        )
        assert isinstance(search_results, list)

        normalized_results = [
            item for item in search_results if isinstance(item, dict)
        ]
        if any(item.get("uid") == dashboard_uid for item in normalized_results):
            return normalized_results

        last_results = normalized_results
        time.sleep(1)

    raise AssertionError(
        f"Grafana dashboard {dashboard_uid!r} did not appear in search within "
        f"{timeout:.0f}s. Last search results: {json.dumps(last_results, sort_keys=True)}"
    )


def _wait_for_grafana_json(
    local_grafana_clickhouse_stack,
    method: str,
    path: str,
    *,
    timeout: float = 30.0,
) -> dict[str, object] | list[object]:
    deadline = time.monotonic() + timeout
    last_error = "Grafana resource has not appeared yet."

    while time.monotonic() < deadline:
        try:
            return local_grafana_clickhouse_stack.grafana_json(method, path)
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
            last_error = f"HTTP {exc.code}: {exc.reason}"
        time.sleep(1)

    raise AssertionError(
        f"Grafana resource {path!r} did not appear within {timeout:.0f}s. "
        f"Last error: {last_error}"
    )


def _wait_for_grafana_dashboard(
    local_grafana_clickhouse_stack,
    dashboard_uid: str,
) -> dict[str, Any]:
    response = _wait_for_grafana_json(
        local_grafana_clickhouse_stack,
        "GET",
        f"/api/dashboards/uid/{dashboard_uid}",
    )
    assert isinstance(response, dict)
    dashboard = response["dashboard"]
    assert isinstance(dashboard, dict)
    return dashboard


class _DashboardApiSeed:
    def __init__(
        self,
        *,
        tenant_id: str,
        asset_id: str,
        agent_id: str,
        source_id: str,
        source_type: str,
        point_key: str,
        source_config_revision: str,
        event_count: int,
    ) -> None:
        self.tenant_id = tenant_id
        self.asset_id = asset_id
        self.agent_id = agent_id
        self.source_id = source_id
        self.source_type = source_type
        self.point_key = point_key
        self.point_ref = f"1/2/{point_key}"
        self.source_config_revision = source_config_revision
        self.event_count = event_count


def _seed_clickhouse_dashboard_rows(
    local_grafana_clickhouse_stack,
    seed: _DashboardApiSeed,
) -> None:
    base_ts = (datetime.now(tz=UTC) - timedelta(minutes=5)).replace(
        second=0,
        microsecond=0,
    )
    telemetry_rows = []
    for index in range(seed.event_count):
        ts = base_ts + timedelta(seconds=index)
        quality = "bad" if index % 10 == 0 else "good"
        telemetry_rows.append(
            "\t".join(
                [
                    seed.tenant_id,
                    f"{seed.point_key}-event-{index:04d}",
                    (
                        f"{seed.tenant_id}|{seed.asset_id}|{seed.agent_id}|"
                        f"{seed.point_key}-event-{index:04d}"
                    ),
                    seed.asset_id,
                    seed.agent_id,
                    seed.source_id,
                    seed.source_type,
                    f"{seed.tenant_id}|{seed.asset_id}|{seed.source_id}|{seed.point_key}",
                    seed.point_key,
                    seed.point_ref,
                    seed.source_config_revision,
                    _format_clickhouse_datetime64(ts),
                    _format_clickhouse_datetime64(ts + timedelta(milliseconds=1)),
                    "telemetry.sample",
                    "periodic_read",
                    "number",
                    str(1000 + index),
                    r"\N",
                    r"\N",
                    str(1000 + index),
                    quality,
                    str(index + 1),
                ]
            )
        )

    _insert_tsv(
        local_grafana_clickhouse_stack,
        "telemetry_events_v1",
        [
            "tenant_id",
            "event_id",
            "idempotency_key",
            "asset_id",
            "agent_id",
            "source_id",
            "source_type",
            "point_id",
            "point_key",
            "point_ref",
            "source_config_revision",
            "ts",
            "ingested_at",
            "event_type",
            "observation_mode",
            "value_type",
            "value_float",
            "value_bool",
            "value_string",
            "value_raw",
            "quality",
            "sequence",
        ],
        telemetry_rows,
    )

    _insert_tsv(
        local_grafana_clickhouse_stack,
        "agent_status_events_v1",
        ["tenant_id", "asset_id", "agent_id", "status", "ts", "ingested_at"],
        [
            "\t".join(
                [
                    seed.tenant_id,
                    seed.asset_id,
                    seed.agent_id,
                    "online",
                    _format_clickhouse_datetime64(base_ts),
                    _format_clickhouse_datetime64(base_ts + timedelta(milliseconds=2)),
                ]
            )
        ],
    )
    _insert_tsv(
        local_grafana_clickhouse_stack,
        "source_connection_events_v1",
        [
            "tenant_id",
            "asset_id",
            "agent_id",
            "source_id",
            "state",
            "reason",
            "ts",
            "ingested_at",
        ],
        [
            "\t".join(
                [
                    seed.tenant_id,
                    seed.asset_id,
                    seed.agent_id,
                    seed.source_id,
                    "connected",
                    r"\N",
                    _format_clickhouse_datetime64(base_ts),
                    _format_clickhouse_datetime64(base_ts + timedelta(milliseconds=3)),
                ]
            )
        ],
    )

    # These contract tables are intentionally not dashboard sources per ADR-017,
    # but seeding them catches accidental coupling through the static guardrails.
    _insert_tsv(
        local_grafana_clickhouse_stack,
        "source_config_snapshots_v1",
        [
            "tenant_id",
            "asset_id",
            "agent_id",
            "source_id",
            "source_type",
            "source_config_revision",
            "points_json",
            "ts",
            "ingested_at",
        ],
        [
            "\t".join(
                [
                    seed.tenant_id,
                    seed.asset_id,
                    seed.agent_id,
                    seed.source_id,
                    seed.source_type,
                    seed.source_config_revision,
                    json.dumps(
                        [
                            {
                                "point_key": seed.point_key,
                                "point_ref": seed.point_ref,
                                "value_type": "number",
                            }
                        ],
                        separators=(",", ":"),
                    ),
                    _format_clickhouse_datetime64(base_ts),
                    _format_clickhouse_datetime64(base_ts + timedelta(milliseconds=4)),
                ]
            )
        ],
    )
    _insert_tsv(
        local_grafana_clickhouse_stack,
        "derived_events_v1",
        [
            "tenant_id",
            "derived_event_id",
            "idempotency_key",
            "asset_id",
            "rule_or_metric_id",
            "event_type",
            "ts",
            "produced_at",
            "value_type",
            "value_float",
            "value_bool",
            "value_string",
            "source_event_ids_json",
            "attributes_json",
        ],
        [
            "\t".join(
                [
                    seed.tenant_id,
                    f"derived-{seed.point_key}",
                    f"{seed.tenant_id}|{seed.asset_id}|derived-{seed.point_key}",
                    seed.asset_id,
                    "dashboard-api-derived-check",
                    "derived.metric",
                    _format_clickhouse_datetime64(base_ts),
                    _format_clickhouse_datetime64(base_ts + timedelta(milliseconds=5)),
                    "number",
                    "42.5",
                    r"\N",
                    r"\N",
                    json.dumps([f"{seed.point_key}-event-0000"], separators=(",", ":")),
                    json.dumps({"seed": "grafana-api"}, separators=(",", ":")),
                ]
            )
        ],
    )
    _insert_tsv(
        local_grafana_clickhouse_stack,
        "alarm_history_events_v1",
        [
            "tenant_id",
            "alarm_event_id",
            "alarm_id",
            "asset_id",
            "event_type",
            "severity",
            "state",
            "operator_id",
            "reason",
            "ts",
            "ingested_at",
            "payload_json",
        ],
        [
            "\t".join(
                [
                    seed.tenant_id,
                    f"alarm-event-{seed.point_key}",
                    f"alarm-{seed.point_key}",
                    seed.asset_id,
                    "alarm.raised",
                    "warning",
                    "active",
                    r"\N",
                    "dashboard api seed",
                    _format_clickhouse_datetime64(base_ts),
                    _format_clickhouse_datetime64(base_ts + timedelta(milliseconds=6)),
                    json.dumps({"seed": "grafana-api"}, separators=(",", ":")),
                ]
            )
        ],
    )


def _insert_tsv(
    local_grafana_clickhouse_stack,
    table: str,
    columns: list[str],
    rows: list[str],
) -> None:
    local_grafana_clickhouse_stack.clickhouse_query(
        "\n".join(
            [
                f"INSERT INTO {table} ({', '.join(columns)})",
                "FORMAT TabSeparated",
                *rows,
            ]
        )
    )


def _format_clickhouse_datetime64(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")[:23]
