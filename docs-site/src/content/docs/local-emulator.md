---
title: Local Emulator Runbook
description: How to start the local platform, KNX source emulator, edge agent, and verify MQTT, Kafka, ClickHouse, and Grafana.
---

This page is the human entrypoint for running the synthetic KNX emulator through
the local Industrial Data Platform stack.

The detailed command-by-command runbook lives in
`infra/local/emulator-runbook.md`. Use that file when you need exact diagnostic
commands or troubleshooting steps.

## Flow

```text
KNX Source Emulator
  -> Edge Telemetry Agent
  -> MQTT idp/v1/...
  -> Redpanda Connect
  -> Kafka idp.*
  -> Kafka Connect
  -> ClickHouse
  -> Grafana
```

## Start Platform

From the repository root:

```bash
test -f .env || cp .env.example .env
rg '(^|[=:/.-])wm([_./:-]|$)|wm-' .env
./infra/local/up-platform.sh
uv run --env-file .env idp-telemetry-store migrate up
uv run --env-file .env python infra/local/kafka-connect/bootstrap_connector.py
```

The `rg` command should print nothing. If it finds `wm`, fix `.env` before
starting the stack.

## Start Emulator

Terminal 1:

```bash
uv run --env-file .env --package knx-source-emulator \
  knx-source-emulator start \
  --host 127.0.0.1 \
  --port 3671 \
  --devices 1 \
  --tags-per-device 4 \
  --interval-seconds 1 \
  --allow-destructive-reset \
  --forever
```

This seeds synthetic config through Config Registry and keeps the TCP emulator
running until interrupted.

Default synthetic identifiers:

- `tenant_id`: `synthetic-tenant`
- `asset_id`: `mall-synthetic-01`
- `agent_id`: `edge-synthetic-01`
- `source_id`: `knx_synthetic`

## Start Edge Agent

Terminal 2:

```bash
uv run --env-file .env --package edge-telemetry-agent \
  edge-telemetry-agent check-config \
  --bootstrap-config apps/edge_telemetry_agent/config/examples/bootstrap.synthetic-emulator.yaml
```

Smoke run:

```bash
uv run --env-file .env --package edge-telemetry-agent \
  edge-telemetry-agent run-source-adapter \
  --bootstrap-config apps/edge_telemetry_agent/config/examples/bootstrap.synthetic-emulator.yaml \
  --source-id knx_synthetic \
  --max-events 5
```

Continuous run:

```bash
uv run --env-file .env --package edge-telemetry-agent \
  edge-telemetry-agent run-source-adapter \
  --bootstrap-config apps/edge_telemetry_agent/config/examples/bootstrap.synthetic-emulator.yaml \
  --source-id knx_synthetic
```

## Verify

MQTT:

```bash
docker exec industrial-data-platform-local-mqtt-broker-1 sh -lc \
  'mosquitto_sub -h 127.0.0.1 -p 1883 -u "$MQTT_USERNAME" -P "$MQTT_PASSWORD" -t "idp/v1/#" -C 5 -W 10 -v'
```

Kafka:

```bash
docker exec industrial-data-platform-local-kafka-1 \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka:19092 \
  --topic idp.telemetry.events.v1 \
  --from-beginning \
  --max-messages 5 \
  --property print.key=true
```

Kafka Connect:

```bash
curl -fsS http://localhost:8083/connectors
curl -fsS http://localhost:8083/connectors/idp-telemetry-store-telemetry-store-v1/status
```

ClickHouse:

```bash
docker exec industrial-data-platform-local-clickhouse-1 sh -lc \
  'clickhouse-client --user "$CLICKHOUSE_USER" --password "$CLICKHOUSE_PASSWORD" --database "$CLICKHOUSE_DB" --query "
    SELECT tenant_id, asset_id, agent_id, source_id, point_key, value_type, value_float, ts
    FROM telemetry_events_v1
    ORDER BY ingested_at DESC
    LIMIT 5
    FORMAT Vertical
  "'
```

Grafana:

- URL: `http://localhost:3000`
- Dashboard: `Web Monitoring / Telemetry Overview`
- Credentials: `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD` from `.env`

Operational UIs:

- Config Registry API: `http://localhost:8000/docs`
- Config Registry Backoffice: `http://localhost:8000/backoffice`
- Kafka UI: `http://localhost:8080`
- MQTTX Web: `http://localhost:8081`

## Troubleshooting

| Symptom | Check | Common cause |
| --- | --- | --- |
| MQTT shows `wm/v1/...` | `mosquitto_sub -t "wm/#"` | Old retained broker volume |
| `check-config` fails | MQTT retained config, `idp.edge.configs.v1`, config projection logs | Config seed has not reached MQTT projection |
| MQTT has events, Kafka does not | `industrial-data-platform-local-redpanda-connect-1` logs, `idp.ingestion.errors.v1` | Missing source config revision cache |
| Kafka has events, ClickHouse does not | Kafka Connect status, ClickHouse migrations | Connector not applied or tables missing |
| Grafana is empty | ClickHouse query, dashboard time range | No rows in ClickHouse yet |
