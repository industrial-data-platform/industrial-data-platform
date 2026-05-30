CREATE TABLE IF NOT EXISTS service_latest_agent_status_v1
(
    tenant_id String,
    asset_id String,
    agent_id String,
    status_state AggregateFunction(argMax, String, DateTime64(3, 'UTC')),
    last_status_ts_state AggregateFunction(max, DateTime64(3, 'UTC')),
    last_ingested_at_state AggregateFunction(max, DateTime64(3, 'UTC'))
)
ENGINE = AggregatingMergeTree()
ORDER BY (tenant_id, asset_id, agent_id);

CREATE MATERIALIZED VIEW IF NOT EXISTS service_latest_agent_status_mv_v1
TO service_latest_agent_status_v1
AS SELECT
    tenant_id,
    asset_id,
    agent_id,
    argMaxState(toString(status), ts) AS status_state,
    maxState(ts) AS last_status_ts_state,
    maxState(ingested_at) AS last_ingested_at_state
FROM agent_status_events_v1
GROUP BY
    tenant_id,
    asset_id,
    agent_id;

INSERT INTO service_latest_agent_status_v1
SELECT
    tenant_id,
    asset_id,
    agent_id,
    argMaxState(toString(status), ts) AS status_state,
    maxState(ts) AS last_status_ts_state,
    maxState(ingested_at) AS last_ingested_at_state
FROM agent_status_events_v1
GROUP BY
    tenant_id,
    asset_id,
    agent_id;

CREATE TABLE IF NOT EXISTS service_latest_source_connection_v1
(
    tenant_id String,
    asset_id String,
    agent_id String,
    source_id String,
    state_state AggregateFunction(argMax, String, DateTime64(3, 'UTC')),
    reason_state AggregateFunction(argMax, String, DateTime64(3, 'UTC')),
    last_state_ts_state AggregateFunction(max, DateTime64(3, 'UTC')),
    last_ingested_at_state AggregateFunction(max, DateTime64(3, 'UTC'))
)
ENGINE = AggregatingMergeTree()
ORDER BY (tenant_id, asset_id, agent_id, source_id);

CREATE MATERIALIZED VIEW IF NOT EXISTS service_latest_source_connection_mv_v1
TO service_latest_source_connection_v1
AS SELECT
    tenant_id,
    asset_id,
    agent_id,
    source_id,
    argMaxState(toString(state), ts) AS state_state,
    argMaxState(coalesce(reason, ''), ts) AS reason_state,
    maxState(ts) AS last_state_ts_state,
    maxState(ingested_at) AS last_ingested_at_state
FROM source_connection_events_v1
GROUP BY
    tenant_id,
    asset_id,
    agent_id,
    source_id;

INSERT INTO service_latest_source_connection_v1
SELECT
    tenant_id,
    asset_id,
    agent_id,
    source_id,
    argMaxState(toString(state), ts) AS state_state,
    argMaxState(coalesce(reason, ''), ts) AS reason_state,
    maxState(ts) AS last_state_ts_state,
    maxState(ingested_at) AS last_ingested_at_state
FROM source_connection_events_v1
GROUP BY
    tenant_id,
    asset_id,
    agent_id,
    source_id;

CREATE TABLE IF NOT EXISTS service_point_inventory_v1
(
    tenant_id String,
    asset_id String,
    source_type LowCardinality(String),
    agent_id String,
    source_id String,
    point_key String,
    point_id_state AggregateFunction(argMax, String, Tuple(DateTime64(3, 'UTC'), DateTime64(3, 'UTC'))),
    point_ref_state AggregateFunction(argMax, String, Tuple(DateTime64(3, 'UTC'), DateTime64(3, 'UTC'))),
    source_config_revision_state AggregateFunction(argMax, String, Tuple(DateTime64(3, 'UTC'), DateTime64(3, 'UTC'))),
    value_type_state AggregateFunction(argMax, String, Tuple(DateTime64(3, 'UTC'), DateTime64(3, 'UTC'))),
    quality_state AggregateFunction(argMax, String, Tuple(DateTime64(3, 'UTC'), DateTime64(3, 'UTC'))),
    first_seen_state AggregateFunction(min, DateTime64(3, 'UTC')),
    last_seen_state AggregateFunction(max, DateTime64(3, 'UTC')),
    last_ingested_at_state AggregateFunction(max, DateTime64(3, 'UTC'))
)
ENGINE = AggregatingMergeTree()
ORDER BY (tenant_id, asset_id, source_type, agent_id, source_id, point_key);

CREATE MATERIALIZED VIEW IF NOT EXISTS service_point_inventory_mv_v1
TO service_point_inventory_v1
AS SELECT
    tenant_id,
    asset_id,
    source_type,
    agent_id,
    source_id,
    point_key,
    argMaxState(toString(point_id), tuple(ts, ingested_at)) AS point_id_state,
    argMaxState(toString(point_ref), tuple(ts, ingested_at)) AS point_ref_state,
    argMaxState(toString(source_config_revision), tuple(ts, ingested_at)) AS source_config_revision_state,
    argMaxState(toString(value_type), tuple(ts, ingested_at)) AS value_type_state,
    argMaxState(toString(quality), tuple(ts, ingested_at)) AS quality_state,
    minState(ts) AS first_seen_state,
    maxState(ts) AS last_seen_state,
    maxState(ingested_at) AS last_ingested_at_state
FROM telemetry_events_v1
GROUP BY
    tenant_id,
    asset_id,
    source_type,
    agent_id,
    source_id,
    point_key;

INSERT INTO service_point_inventory_v1
SELECT
    tenant_id,
    asset_id,
    source_type,
    agent_id,
    source_id,
    point_key,
    argMaxState(toString(point_id), tuple(ts, ingested_at)) AS point_id_state,
    argMaxState(toString(point_ref), tuple(ts, ingested_at)) AS point_ref_state,
    argMaxState(toString(source_config_revision), tuple(ts, ingested_at)) AS source_config_revision_state,
    argMaxState(toString(value_type), tuple(ts, ingested_at)) AS value_type_state,
    argMaxState(toString(quality), tuple(ts, ingested_at)) AS quality_state,
    minState(ts) AS first_seen_state,
    maxState(ts) AS last_seen_state,
    maxState(ingested_at) AS last_ingested_at_state
FROM telemetry_events_v1 FINAL
GROUP BY
    tenant_id,
    asset_id,
    source_type,
    agent_id,
    source_id,
    point_key;

CREATE TABLE IF NOT EXISTS service_telemetry_activity_1m_v1
(
    tenant_id String,
    asset_id String,
    source_type LowCardinality(String),
    agent_id String,
    source_id String,
    point_key String,
    bucket_start DateTime64(3, 'UTC'),
    event_count_state AggregateFunction(uniq, String),
    good_count_state AggregateFunction(uniqIf, String, UInt8),
    uncertain_count_state AggregateFunction(uniqIf, String, UInt8),
    bad_count_state AggregateFunction(uniqIf, String, UInt8),
    first_ts_state AggregateFunction(min, DateTime64(3, 'UTC')),
    last_ts_state AggregateFunction(max, DateTime64(3, 'UTC'))
)
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(bucket_start)
ORDER BY (tenant_id, asset_id, source_type, source_id, point_key, bucket_start, agent_id)
TTL toDateTime(bucket_start) + INTERVAL 180 DAY DELETE;

CREATE MATERIALIZED VIEW IF NOT EXISTS service_telemetry_activity_1m_mv_v1
TO service_telemetry_activity_1m_v1
AS SELECT
    tenant_id,
    asset_id,
    source_type,
    agent_id,
    source_id,
    point_key,
    toStartOfMinute(ts) AS bucket_start,
    uniqState(idempotency_key) AS event_count_state,
    uniqIfState(idempotency_key, quality = 'good') AS good_count_state,
    uniqIfState(idempotency_key, quality = 'uncertain') AS uncertain_count_state,
    uniqIfState(idempotency_key, quality = 'bad') AS bad_count_state,
    minState(ts) AS first_ts_state,
    maxState(ts) AS last_ts_state
FROM telemetry_events_v1
GROUP BY
    tenant_id,
    asset_id,
    source_type,
    agent_id,
    source_id,
    point_key,
    bucket_start;

INSERT INTO service_telemetry_activity_1m_v1
SELECT
    tenant_id,
    asset_id,
    source_type,
    agent_id,
    source_id,
    point_key,
    toStartOfMinute(ts) AS bucket_start,
    uniqState(idempotency_key) AS event_count_state,
    uniqIfState(idempotency_key, quality = 'good') AS good_count_state,
    uniqIfState(idempotency_key, quality = 'uncertain') AS uncertain_count_state,
    uniqIfState(idempotency_key, quality = 'bad') AS bad_count_state,
    minState(ts) AS first_ts_state,
    maxState(ts) AS last_ts_state
FROM telemetry_events_v1 FINAL
GROUP BY
    tenant_id,
    asset_id,
    source_type,
    agent_id,
    source_id,
    point_key,
    bucket_start;
