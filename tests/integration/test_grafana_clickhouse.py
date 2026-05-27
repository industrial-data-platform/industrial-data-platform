from __future__ import annotations

import json
import subprocess
import time
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

    service_folder = local_grafana_clickhouse_stack.grafana_json(
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
            SELECT count() AS latest_points
            FROM telemetry_latest_v1
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
    assert "telemetry_latest_v1" in dashboard_json
    assert "telemetry_1m_v1" in dashboard_json
    assert "telemetry_1h_v1" in dashboard_json
    assert "telemetry_events_dedup_v1" in dashboard_json
    assert "agent_status_events_v1" in dashboard_json
    assert "source_connection_events_v1" in dashboard_json
    assert "source_config_snapshots_v1" not in dashboard_json
    assert "configured_points" not in dashboard_json
    assert "meta/catalog" not in dashboard_json
    assert "idp/v1/" not in dashboard_json
    assert "Asset Graph" not in dashboard_json

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
    assert "${tenant_id:singlequote}" in variable_by_name["asset_id"]["query"]
    assert "${asset_id:singlequote}" in variable_by_name["source_type"]["query"]
    assert "${source_type:singlequote}" in variable_by_name["agent_id"]["query"]
    assert "${agent_id:singlequote}" in variable_by_name["source_id"]["query"]
    assert "${source_id:singlequote}" in variable_by_name["point_key"]["query"]


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


def _replace_dashboard_variables(raw_sql: str) -> str:
    replacements = {
        "${tenant_id:singlequote}": f"'{RUN_TENANT_ID}'",
        "${asset_id:singlequote}": f"'{RUN_ASSET_ID}'",
        "${source_type:singlequote}": f"'{RUN_SOURCE_TYPE}'",
        "${agent_id:singlequote}": f"'{RUN_AGENT_ID}'",
        "${source_id:singlequote}": f"'{RUN_SOURCE_ID}'",
        "${point_key:singlequote}": f"'{RUN_POINT_KEY}'",
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
