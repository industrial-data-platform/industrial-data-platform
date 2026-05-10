# Platform Ingestion Contracts

Дата: 2026-05-10
Статус: working draft

Раздел фиксирует контракты преобразования:

```text
MQTT topic + MQTT payload + retained source config
  -> canonical Kafka record
  -> downstream consumers
```

Эти контракты принадлежат `Industrial Data Platform`. Существующие
`wm.platform.*` message types и topics сохраняются как compatibility surface.

## Контракты

| Contract-id | Файл | Назначение |
| --- | --- | --- |
| `wm.platform-ingestion.mqtt-to-kafka.v1` | `mqtt-to-kafka.v1.md` | Mapping MQTT edge boundary в canonical Kafka records |
