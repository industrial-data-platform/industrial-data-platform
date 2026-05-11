# Ручной запуск synthetic KNX emulator и local platform

Эта инструкция описывает production-like локальный поток:

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

Команды выполняются из корня репозитория.

## 1. Подготовить окружение

Нужен запущенный Docker и локальный `.env` рядом с `.env.example`.

```bash
test -f .env || cp .env.example .env
```

Проверьте, что в `.env` нет старых `wm`-значений:

```bash
rg '(^|[=:/.-])wm([_./:-]|$)|wm-' .env
```

Команда не должна ничего вывести. Нормальный MQTT/Kafka prefix сейчас:

- MQTT: `idp/v1`
- Kafka: `idp.*`

Если в MQTT снова видны retained `wm/v1/...`, это старый broker volume. Для
полного локального reset:

```bash
docker compose --env-file .env -f infra/local/compose.yaml down -v --remove-orphans
```

Для старых compose-проектов, поднятых до переименования, дополнительно:

```bash
docker compose -p web-monitoring-local -f infra/local/compose.yaml down -v --remove-orphans
```

## 2. Поднять platform services

Поднимите полный local stack:

```bash
./infra/local/up-platform.sh
```

Wrapper:

- пересобирает `idp-config-registry`, `grafana`, `kafka-connect`;
- применяет Alembic migrations для PostgreSQL Config Registry;
- поднимает MQTT, Kafka, Redpanda Connect pipelines, PostgreSQL, ClickHouse,
  Config Registry, Kafka Connect, Kafka UI, MQTTX Web и Grafana.

Для полного пути до ClickHouse примените storage migrations и включите
ClickHouse sink connector:

```bash
uv run --env-file .env idp-telemetry-store migrate up
uv run --env-file .env python infra/local/kafka-connect/bootstrap_connector.py
```

Быстрая проверка контейнеров:

```bash
docker compose --env-file .env -f infra/local/compose.yaml ps
```

Ожидаемо все long-running сервисы должны быть `Up`; `kafka-init` может быть
`Exited`, это одноразовый bootstrap.

## 3. Проверить platform до запуска эмулятора

HTTP endpoints:

```bash
curl -fsS http://localhost:8000/docs >/dev/null
curl -fsS http://localhost:8083/connectors
curl -fsS http://localhost:4195/ready
curl -fsS http://localhost:4196/ready
curl -fsS http://localhost:4197/ready
```

Kafka topics:

```bash
docker exec industrial-data-platform-local-kafka-1 \
  /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:19092 --list | sort
```

В списке должны быть:

- `idp.edge.configs.v1`
- `idp.source.configs.v1`
- `idp.telemetry.events.v1`
- `idp.source.connections.v1`
- `idp.agent.status.v1`
- `idp.ingestion.errors.v1`
- `idp.telemetry-store.dlq.v1`

ClickHouse:

```bash
docker exec industrial-data-platform-local-clickhouse-1 sh -lc \
  'clickhouse-client --user "$CLICKHOUSE_USER" --password "$CLICKHOUSE_PASSWORD" --database "$CLICKHOUSE_DB" --query "SELECT 1"'
```

MQTT должен быть пустым до seed/run или содержать только свежие `idp/v1/...`:

```bash
docker exec industrial-data-platform-local-mqtt-broker-1 sh -lc \
  'mosquitto_sub -h 127.0.0.1 -p 1883 -u "$MQTT_USERNAME" -P "$MQTT_PASSWORD" -t "wm/#" -C 1 -W 3'
```

Если эта команда что-то выводит, локальный broker содержит старое retained
состояние.

## 4. Запустить synthetic KNX emulator

В терминале 1:

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

Что делает `start`:

- генерирует synthetic tenant/asset/agent/source/points;
- пишет TCP endpoint эмулятора в Config Registry source connection;
- вызывает `render-config`;
- Config Registry outbox worker публикует records в `idp.edge.configs.v1`;
- Redpanda Connect projection материализует retained MQTT config;
- TCP emulator остается работать до `Ctrl+C`.

Дефолтные identifiers для этого сценария:

- `tenant_id`: `synthetic-tenant`
- `asset_id`: `mall-synthetic-01`
- `agent_id`: `edge-synthetic-01`
- `source_id`: `knx_synthetic`

`--allow-destructive-reset` удаляет и пересоздает локальный generated graph для
этих synthetic IDs. Для общего dev-стенда используйте его только когда это
ожидаемый reset.

Проверьте, что retained config появился в MQTT:

```bash
docker exec industrial-data-platform-local-mqtt-broker-1 sh -lc \
  'mosquitto_sub -h 127.0.0.1 -p 1883 -u "$MQTT_USERNAME" -P "$MQTT_PASSWORD" -t "idp/v1/agents/edge-synthetic-01/#" -C 2 -W 10 -F "%r %t %p"'
```

Ожидаемые retained topics:

- `idp/v1/agents/edge-synthetic-01/config/agent-runtime`
- `idp/v1/agents/edge-synthetic-01/sources/knx_synthetic/config`

## 5. Запустить Edge Telemetry Agent

Bootstrap example для этого synthetic сценария:

```text
apps/edge_telemetry_agent/config/examples/bootstrap.synthetic-emulator.yaml
```

Проверка retained runtime/source config:

```bash
uv run --env-file .env --package edge-telemetry-agent \
  edge-telemetry-agent check-config \
  --bootstrap-config apps/edge_telemetry_agent/config/examples/bootstrap.synthetic-emulator.yaml
```

Для короткой smoke-проверки в терминале 2:

```bash
uv run --env-file .env --package edge-telemetry-agent \
  edge-telemetry-agent run-source-adapter \
  --bootstrap-config apps/edge_telemetry_agent/config/examples/bootstrap.synthetic-emulator.yaml \
  --source-id knx_synthetic \
  --max-events 5
```

Ожидаемый итог:

```text
Source adapter run: observations_read=5 events_enqueued=... events_delivered=...
```

Для непрерывной ручной работы уберите `--max-events`:

```bash
uv run --env-file .env --package edge-telemetry-agent \
  edge-telemetry-agent run-source-adapter \
  --bootstrap-config apps/edge_telemetry_agent/config/examples/bootstrap.synthetic-emulator.yaml \
  --source-id knx_synthetic
```

Этот процесс тоже останавливается через `Ctrl+C`.

## 6. Куда смотреть, что все работает

### MQTT

Telemetry events от edge-agent:

```bash
docker exec industrial-data-platform-local-mqtt-broker-1 sh -lc \
  'mosquitto_sub -h 127.0.0.1 -p 1883 -u "$MQTT_USERNAME" -P "$MQTT_PASSWORD" -t "idp/v1/assets/mall-synthetic-01/agents/edge-synthetic-01/sources/knx_synthetic/points/+/event" -v'
```

В payload должен быть:

- `message_type`: `idp.edge.telemetry.event.v1`
- `tenant_id`: `synthetic-tenant`
- `source_config_revision`
- `event_type`: `telemetry.sample`

UI вариант: открыть `http://localhost:8081` и подписаться на `idp/v1/#`.

### Kafka

Telemetry topic:

```bash
docker exec industrial-data-platform-local-kafka-1 \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka:19092 \
  --topic idp.telemetry.events.v1 \
  --from-beginning \
  --max-messages 5 \
  --property print.key=true \
  --property key.separator=" | "
```

В value должен быть:

- `message_type`: `idp.telemetry.event.v1`
- `tenant_id`: `synthetic-tenant`
- `asset_id`: `mall-synthetic-01`
- `agent_id`: `edge-synthetic-01`
- `source_id`: `knx_synthetic`

Если events не попали в normal topic, проверьте error topic:

```bash
docker exec industrial-data-platform-local-kafka-1 \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka:19092 \
  --topic idp.ingestion.errors.v1 \
  --from-beginning \
  --max-messages 5 \
  --property print.key=true \
  --property key.separator=" | "
```

UI вариант: `http://localhost:8080`, cluster `local`, topics `idp.*`.

### Kafka Connect

Connector должен быть создан и работать:

```bash
curl -fsS http://localhost:8083/connectors
curl -fsS http://localhost:8083/connectors/idp-telemetry-store-telemetry-store-v1/status
```

Если connector отсутствует, повторите:

```bash
uv run --env-file .env python infra/local/kafka-connect/bootstrap_connector.py
```

### ClickHouse

Последние telemetry rows:

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

Если таблицы нет, не применены ClickHouse migrations:

```bash
uv run --env-file .env idp-telemetry-store migrate up
```

### Config Registry

API:

```bash
curl -fsS http://localhost:8000/tenants
```

UI:

- API docs: `http://localhost:8000/docs`
- Backoffice: `http://localhost:8000/backoffice`

В backoffice должны быть synthetic tenant, asset, agent, source и points.

### Redpanda Connect pipelines

Readiness:

```bash
curl -fsS http://localhost:4195/ready
curl -fsS http://localhost:4196/ready
curl -fsS http://localhost:4197/ready
```

Назначение:

- `4195`: MQTT `idp/v1/#` -> Kafka `idp.*`
- `4196`: Kafka `idp.edge.configs.v1` -> retained MQTT config
- `4197`: Kafka `idp.edge.configs.v1` -> Kafka `idp.source.configs.v1`

### Grafana

Откройте `http://localhost:3000`, войдите с `GRAFANA_ADMIN_USER` /
`GRAFANA_ADMIN_PASSWORD` из `.env` и откройте dashboard:

```text
Web Monitoring / Telemetry Overview
```

Dashboard начнет показывать данные после того, как telemetry дошла до
ClickHouse.

### Логи

Основные логи:

```bash
docker logs -f industrial-data-platform-local-idp-config-registry-outbox-worker-1
docker logs -f industrial-data-platform-local-redpanda-connect-config-projection-1
docker logs -f industrial-data-platform-local-redpanda-connect-source-config-snapshot-1
docker logs -f industrial-data-platform-local-redpanda-connect-1
docker logs -f industrial-data-platform-local-kafka-connect-1
```

## 7. Остановка

Остановить ручные процессы:

- `Ctrl+C` в терминале с `knx-source-emulator`
- `Ctrl+C` в терминале с `edge-telemetry-agent`

Остановить platform services без удаления данных:

```bash
docker compose --env-file .env -f infra/local/compose.yaml stop
```

Остановить и удалить local state:

```bash
docker compose --env-file .env -f infra/local/compose.yaml down -v --remove-orphans
```

## Быстрая диагностика

| Симптом | Где смотреть | Частая причина |
| --- | --- | --- |
| В MQTT есть `wm/v1/...` | `mosquitto_sub -t "wm/#"` | Старый retained broker volume |
| `check-config` не проходит | MQTT retained config, `idp.edge.configs.v1`, logs projection | Config Registry seed еще не дошел до MQTT projection |
| Edge agent читает events, но MQTT пустой | Edge agent stdout, MQTT credentials, broker URL | Неверный `.env` или bootstrap config |
| MQTT есть, Kafka пустой | `redpanda-connect-1` logs, `idp.ingestion.errors.v1` | Ingestion не нашел source config revision |
| Kafka есть, ClickHouse пустой | Kafka Connect status, ClickHouse migrations | Connector не применен или таблицы не созданы |
| Grafana пустая | ClickHouse query, dashboard time range | В ClickHouse еще нет rows или выбран не тот диапазон времени |
