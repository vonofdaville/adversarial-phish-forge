-- CHIMERA Telemetry Database Schema
-- High-velocity event storage with privacy-preserving design

-- Create database
CREATE DATABASE IF NOT EXISTS chimera;

-- Use chimera database
USE chimera;

-- Telemetry Events Table (Main event storage)
CREATE TABLE IF NOT EXISTS telemetry_events (
    -- Event identification
    event_id String,
    campaign_id String,
    participant_id String,

    -- Event metadata
    event_type String,
    timestamp DateTime64(3),

    -- Anonymized fingerprinting data
    fingerprint_hash String,
    user_agent_hash String,
    ip_hash String,

    -- Geographic data (country-level only)
    geolocation_country String,

    -- Device/browser metadata
    device_type String,
    browser_family String,
    os_family String,
    screen_resolution String,
    timezone String,
    language String,

    -- Event-specific data
    event_metadata String,

    -- Privacy and compliance
    consent_verified Bool,
    anonymization_level String,

    -- Technical metadata
    created_at DateTime64(3) DEFAULT now(),
    processed_at DateTime64(3) DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (campaign_id, timestamp, event_type)
TTL toDate(created_at) + INTERVAL 365 DAY DELETE
SETTINGS index_granularity = 8192;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_campaign_timestamp ON telemetry_events (campaign_id, timestamp) TYPE minmax GRANULARITY 1;
CREATE INDEX IF NOT EXISTS idx_event_type ON telemetry_events (event_type) TYPE bloom_filter GRANULARITY 1;
CREATE INDEX IF NOT EXISTS idx_fingerprint ON telemetry_events (fingerprint_hash) TYPE bloom_filter GRANULARITY 1;
CREATE INDEX IF NOT EXISTS idx_participant ON telemetry_events (participant_id) TYPE bloom_filter GRANULARITY 1;

-- Aggregated Analytics Table (Pre-computed metrics)
CREATE TABLE IF NOT EXISTS campaign_analytics (
    campaign_id String,
    date Date,

    -- Event counts
    total_events UInt64,
    email_opened UInt64,
    link_clicked UInt64,
    form_submitted UInt64,
    credentials_entered UInt64,

    -- Unique visitor counts (anonymized)
    unique_visitors UInt64,
    unique_fingerprints UInt64,

    -- Geographic distribution
    countries Array(String),
    country_counts Array(UInt32),

    -- Device distribution
    device_types Array(String),
    device_counts Array(UInt32),

    -- Time-based metrics
    hourly_events Array(UInt32),
    peak_hour UInt8,

    -- Engagement rates (with differential privacy noise)
    open_rate Float64,
    click_rate Float64,
    conversion_rate Float64,

    -- Privacy metadata
    anonymization_epsilon Float64,
    k_anonymity_level UInt8,
    data_freshness_minutes UInt32,

    -- Technical metadata
    created_at DateTime64(3) DEFAULT now(),
    updated_at DateTime64(3) DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (campaign_id, date)
TTL toDate(created_at) + INTERVAL 90 DAY DELETE;

-- Anomaly Detection Table
CREATE TABLE IF NOT EXISTS telemetry_anomalies (
    anomaly_id String,
    campaign_id String,
    anomaly_type String,
    severity String,

    -- Anomaly details
    description String,
    fingerprint_hash String,
    affected_events UInt32,

    -- Detection metadata
    detection_timestamp DateTime64(3),
    detection_method String,

    -- Risk assessment
    risk_score Float64,
    risk_factors Array(String),

    -- Response actions
    recommended_actions Array(String),
    action_taken String,
    action_timestamp DateTime64(3),

    -- Technical metadata
    created_at DateTime64(3) DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(detection_timestamp)
ORDER BY (campaign_id, detection_timestamp, severity)
TTL toDate(created_at) + INTERVAL 180 DAY DELETE;

-- Privacy Audit Log
CREATE TABLE IF NOT EXISTS privacy_audit_log (
    audit_id String,
    operation_type String,
    data_type String,

    -- Privacy metrics
    records_processed UInt64,
    anonymization_technique String,
    privacy_risk_level String,
    differential_privacy_epsilon Float64,

    -- Data flow tracking
    source_system String,
    destination_system String,
    data_retention_days UInt16,

    -- Compliance metadata
    gdpr_compliant Bool,
    consent_verified Bool,
    data_minimization_applied Bool,

    -- Audit metadata
    performed_by String,
    performed_at DateTime64(3),
    audit_timestamp DateTime64(3) DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(audit_timestamp)
ORDER BY (audit_timestamp, operation_type)
TTL toDate(audit_timestamp) + INTERVAL 2555 DAY DELETE;  -- 7 years for compliance

-- Real-time Aggregations (Materialized Views)

-- Campaign hourly metrics
CREATE MATERIALIZED VIEW IF NOT EXISTS campaign_hourly_metrics
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (campaign_id, timestamp)
AS SELECT
    campaign_id,
    toStartOfHour(timestamp) as timestamp,
    count() as events_per_hour,
    countDistinct(fingerprint_hash) as unique_visitors_per_hour,
    arrayDistinct(groupArray(event_type)) as event_types_per_hour
FROM telemetry_events
WHERE consent_verified = true
GROUP BY campaign_id, toStartOfHour(timestamp);

-- Geographic distribution by campaign
CREATE MATERIALIZED VIEW IF NOT EXISTS campaign_geographic_distribution
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (campaign_id, geolocation_country)
AS SELECT
    campaign_id,
    geolocation_country,
    count() as events_per_country,
    countDistinct(fingerprint_hash) as unique_visitors_per_country,
    toStartOfDay(timestamp) as date
FROM telemetry_events
WHERE geolocation_country != '' AND consent_verified = true
GROUP BY campaign_id, geolocation_country, toStartOfDay(timestamp);

-- Device analytics
CREATE MATERIALIZED VIEW IF NOT EXISTS device_analytics
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (campaign_id, device_type, browser_family)
AS SELECT
    campaign_id,
    device_type,
    browser_family,
    os_family,
    count() as device_events,
    countDistinct(fingerprint_hash) as unique_devices,
    toStartOfDay(timestamp) as date
FROM telemetry_events
WHERE consent_verified = true
GROUP BY campaign_id, device_type, browser_family, os_family, toStartOfDay(timestamp);

-- Anomaly detection triggers (simplified example)
CREATE VIEW IF NOT EXISTS potential_automation_detection AS
SELECT
    campaign_id,
    fingerprint_hash,
    count(*) as rapid_events,
    min(timestamp) as first_event,
    max(timestamp) as last_event,
    (max(timestamp) - min(timestamp)) as time_window_seconds
FROM telemetry_events
WHERE timestamp >= now() - INTERVAL 1 HOUR
GROUP BY campaign_id, fingerprint_hash
HAVING rapid_events > 20 AND time_window_seconds < 300;

-- Data retention enforcement
CREATE TABLE IF NOT EXISTS data_retention_log (
    retention_id String,
    table_name String,
    records_deleted UInt64,
    retention_days UInt16,
    cutoff_date Date,
    executed_at DateTime64(3) DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(executed_at)
ORDER BY executed_at;

-- Sample data for testing (development only)
INSERT INTO telemetry_events (
    event_id, campaign_id, participant_id, event_type, timestamp,
    fingerprint_hash, user_agent_hash, ip_hash, geolocation_country,
    device_type, browser_family, os_family, screen_resolution,
    timezone, language, event_metadata, consent_verified, anonymization_level
) VALUES
(
    'sample-event-001', 'sample-campaign-001', 'sample-participant-001',
    'email_opened', now(),
    'sample_fingerprint_hash', 'sample_ua_hash', '192.168.0.0',
    'US', 'desktop', 'chrome', 'windows', 'mediumxmedium',
    'America/New_York', 'en', '{"referrer": "email"}', true, 'standard'
),
(
    'sample-event-002', 'sample-campaign-001', 'sample-participant-002',
    'link_clicked', now() - INTERVAL 5 MINUTE,
    'sample_fingerprint_hash_2', 'sample_ua_hash_2', '192.168.1.0',
    'CA', 'mobile', 'safari', 'ios', 'smallxsmall',
    'America/Toronto', 'en', '{"link_url": "/landing"}', true, 'standard'
);

-- Insert sample anomaly for testing
INSERT INTO telemetry_anomalies (
    anomaly_id, campaign_id, anomaly_type, severity, description,
    fingerprint_hash, affected_events, detection_timestamp, detection_method,
    risk_score, risk_factors, recommended_actions
) VALUES (
    'sample-anomaly-001', 'sample-campaign-001', 'rapid_automated_interaction',
    'high', 'Suspicious rapid interactions detected',
    'suspicious_fingerprint_hash', 25, now(), 'automated_detection',
    8.5, ['rapid_events', 'short_time_window'], ['flag_for_review', 'block_ip']
);

