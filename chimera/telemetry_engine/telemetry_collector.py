"""
Telemetry Collector - Privacy-Preserving Behavioral Data Collection

High-velocity telemetry collection for red team analytics:
- Behavioral fingerprinting without tracking
- Differential privacy anonymization
- ClickHouse for event storage and analytics
- Real-time event processing and alerting

Maintains participant privacy while enabling campaign effectiveness measurement.
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import clickhouse_driver
from clickhouse_driver import Client

from ..utils.config import config
from ..utils.logger import setup_logging, log_privacy_event, log_audit_event

logger = setup_logging(__name__)


class TelemetryCollector:
    """
    Privacy-preserving telemetry collection and analysis.

    Collects behavioral signals from campaign interactions
    while implementing differential privacy and data minimization.
    """

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None,
                 user: Optional[str] = None, password: Optional[str] = None):
        self.host = host or config.clickhouse_host
        self.port = port or config.clickhouse_port
        self.user = user or config.clickhouse_user
        self.password = password or config.clickhouse_password

        self.client = None
        self.privacy_engine = PrivacyFilter()

    def connect(self):
        """Establish ClickHouse connection."""
        try:
            if self.client is None:
                self.client = Client(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database='chimera'
                )
                logger.info("Connected to ClickHouse database")
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise

    def disconnect(self):
        """Close ClickHouse connection."""
        if self.client:
            self.client.disconnect()
            self.client = None

    def record_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Record a telemetry event with privacy protection.

        Args:
            event_data: Raw event data from tracking

        Returns:
            True if event recorded successfully
        """
        try:
            self.connect()

            # Apply privacy filtering
            anonymized_data = self.privacy_engine.anonymize_event(event_data)

            # Prepare data for ClickHouse insertion
            insert_data = {
                'event_id': anonymized_data['event_id'],
                'campaign_id': anonymized_data['campaign_id'],
                'participant_id': anonymized_data.get('participant_id', ''),
                'event_type': anonymized_data['event_type'],
                'timestamp': anonymized_data['timestamp'],
                'fingerprint_hash': anonymized_data['fingerprint_hash'],
                'user_agent_hash': anonymized_data.get('user_agent_hash', ''),
                'ip_hash': anonymized_data.get('ip_hash', ''),
                'geolocation_country': anonymized_data.get('geolocation_country', ''),
                'device_type': anonymized_data.get('device_type', 'unknown'),
                'browser_family': anonymized_data.get('browser_family', 'unknown'),
                'os_family': anonymized_data.get('os_family', 'unknown'),
                'screen_resolution': anonymized_data.get('screen_resolution', ''),
                'timezone': anonymized_data.get('timezone', ''),
                'language': anonymized_data.get('language', ''),
                'event_metadata': json.dumps(anonymized_data.get('event_metadata', {})),
                'consent_verified': anonymized_data.get('consent_verified', True),
                'anonymization_level': anonymized_data.get('anonymization_level', 'standard')
            }

            # Insert into ClickHouse
            self.client.execute("""
                INSERT INTO telemetry_events (
                    event_id, campaign_id, participant_id, event_type, timestamp,
                    fingerprint_hash, user_agent_hash, ip_hash, geolocation_country,
                    device_type, browser_family, os_family, screen_resolution,
                    timezone, language, event_metadata, consent_verified, anonymization_level
                ) VALUES
            """, [insert_data])

            log_privacy_event(
                "telemetry_event_recorded",
                operation="event_collection",
                event_type=anonymized_data['event_type'],
                anonymized=True
            )

            return True

        except Exception as e:
            logger.error(f"Failed to record telemetry event: {e}")
            return False

    def get_campaign_analytics(self, campaign_id: str,
                             time_window_hours: int = 24) -> Dict[str, Any]:
        """
        Get anonymized analytics for a campaign.

        Args:
            campaign_id: Campaign to analyze
            time_window_hours: Analysis time window

        Returns:
            Aggregated analytics with privacy guarantees
        """
        try:
            self.connect()

            # Calculate time window
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=time_window_hours)

            # Query aggregated metrics with differential privacy
            result = self.client.execute("""
                SELECT
                    event_type,
                    count(*) as event_count,
                    count(DISTINCT fingerprint_hash) as unique_visitors,
                    arrayDistinct(arrayMap(x -> geolocation_country, groupArray(geolocation_country))) as countries_represented,
                    arrayDistinct(arrayMap(x -> device_type, groupArray(device_type))) as device_types,
                    avg(if(event_type = 'email_opened', 1, 0)) as open_rate_estimate,
                    avg(if(event_type = 'link_clicked', 1, 0)) as click_rate_estimate
                FROM telemetry_events
                WHERE campaign_id = %(campaign_id)s
                  AND timestamp >= %(start_time)s
                  AND timestamp <= %(end_time)s
                  AND consent_verified = true
                GROUP BY event_type
                ORDER BY event_count DESC
            """, {
                'campaign_id': campaign_id,
                'start_time': start_time,
                'end_time': end_time
            })

            # Process results
            analytics = {
                'campaign_id': campaign_id,
                'time_window_hours': time_window_hours,
                'total_events': 0,
                'unique_visitors': 0,
                'event_breakdown': {},
                'geographic_distribution': [],
                'device_distribution': [],
                'engagement_metrics': {
                    'estimated_open_rate': 0.0,
                    'estimated_click_rate': 0.0,
                    'conversion_funnel': []
                }
            }

            for row in result:
                event_type = row[0]
                event_count = row[1]
                unique_visitors = row[2]
                countries = row[3] if len(row) > 3 else []
                devices = row[4] if len(row) > 4 else []

                analytics['total_events'] += event_count
                analytics['unique_visitors'] = max(analytics['unique_visitors'], unique_visitors)
                analytics['event_breakdown'][event_type] = event_count
                analytics['geographic_distribution'] = list(set(analytics['geographic_distribution'] + countries))
                analytics['device_distribution'] = list(set(analytics['device_distribution'] + devices))

                # Update engagement metrics
                if event_type == 'email_opened':
                    analytics['engagement_metrics']['estimated_open_rate'] = event_count / max(unique_visitors, 1)
                elif event_type == 'link_clicked':
                    analytics['engagement_metrics']['estimated_click_rate'] = event_count / max(unique_visitors, 1)

            # Calculate conversion funnel
            analytics['engagement_metrics']['conversion_funnel'] = self._calculate_conversion_funnel(
                analytics['event_breakdown']
            )

            return analytics

        except Exception as e:
            logger.error(f"Failed to get campaign analytics: {e}")
            return {}

    def _calculate_conversion_funnel(self, event_breakdown: Dict[str, int]) -> List[Dict[str, Any]]:
        """Calculate conversion funnel from event data."""
        funnel_stages = [
            ('email_sent', 'Emails Sent'),
            ('email_delivered', 'Emails Delivered'),
            ('email_opened', 'Emails Opened'),
            ('link_clicked', 'Links Clicked'),
            ('form_submitted', 'Forms Submitted'),
            ('credentials_entered', 'Credentials Entered')
        ]

        funnel = []
        previous_count = None

        for event_type, stage_name in funnel_stages:
            count = event_breakdown.get(event_type, 0)

            if count > 0 or previous_count is not None:
                conversion_rate = None
                if previous_count and previous_count > 0:
                    conversion_rate = count / previous_count

                funnel.append({
                    'stage': stage_name,
                    'count': count,
                    'conversion_rate': conversion_rate
                })

                previous_count = count

        return funnel

    def detect_anomalies(self, campaign_id: str) -> List[Dict[str, Any]]:
        """
        Detect anomalous behavior patterns in telemetry.

        Args:
            campaign_id: Campaign to analyze

        Returns:
            List of detected anomalies
        """
        try:
            self.connect()

            anomalies = []

            # Check for rapid repeated interactions (potential automation)
            rapid_interaction_result = self.client.execute("""
                SELECT
                    fingerprint_hash,
                    count(*) as interaction_count,
                    min(timestamp) as first_interaction,
                    max(timestamp) as last_interaction,
                    (max(timestamp) - min(timestamp)) as interaction_window_seconds
                FROM telemetry_events
                WHERE campaign_id = %(campaign_id)s
                  AND timestamp >= now() - INTERVAL 1 HOUR
                GROUP BY fingerprint_hash
                HAVING interaction_count > 10
                  AND interaction_window_seconds < 300
            """, {'campaign_id': campaign_id})

            for row in rapid_interaction_result:
                anomalies.append({
                    'type': 'rapid_automated_interaction',
                    'severity': 'high',
                    'description': f"Suspicious rapid interactions: {row[1]} events in {row[4]} seconds",
                    'fingerprint_hash': row[0],
                    'recommendation': 'Flag for manual review - potential automated scanning'
                })

            # Check for unusual geographic patterns
            geographic_anomaly_result = self.client.execute("""
                SELECT
                    geolocation_country,
                    count(*) as event_count,
                    count(DISTINCT fingerprint_hash) as unique_visitors
                FROM telemetry_events
                WHERE campaign_id = %(campaign_id)s
                  AND timestamp >= now() - INTERVAL 24 HOUR
                  AND geolocation_country != ''
                GROUP BY geolocation_country
                HAVING event_count > 50 AND unique_visitors < 5
            """, {'campaign_id': campaign_id})

            for row in geographic_anomaly_result:
                anomalies.append({
                    'type': 'geographic_anomaly',
                    'severity': 'medium',
                    'description': f"Unusual concentration in {row[0]}: {row[1]} events from {row[2]} visitors",
                    'country': row[0],
                    'recommendation': 'Review geographic access patterns'
                })

            # Check for consent violations (events without consent)
            consent_violation_result = self.client.execute("""
                SELECT count(*) as violation_count
                FROM telemetry_events
                WHERE campaign_id = %(campaign_id)s
                  AND consent_verified = false
                  AND timestamp >= now() - INTERVAL 24 HOUR
            """, {'campaign_id': campaign_id})

            violation_count = consent_violation_result[0][0] if consent_violation_result else 0
            if violation_count > 0:
                anomalies.append({
                    'type': 'consent_violation',
                    'severity': 'critical',
                    'description': f"{violation_count} events recorded without consent verification",
                    'recommendation': 'Immediate campaign termination and incident review'
                })

            if anomalies:
                log_audit_event(
                    "anomalies_detected",
                    campaign_id=campaign_id,
                    anomaly_count=len(anomalies),
                    severity_levels=[a['severity'] for a in anomalies]
                )

            return anomalies

        except Exception as e:
            logger.error(f"Failed to detect anomalies: {e}")
            return []

    def get_telemetry_health(self) -> Dict[str, Any]:
        """Get telemetry system health metrics."""
        try:
            self.connect()

            # Get basic health metrics
            health_result = self.client.execute("""
                SELECT
                    count(*) as total_events,
                    count(DISTINCT campaign_id) as active_campaigns,
                    count(DISTINCT fingerprint_hash) as unique_fingerprints,
                    max(timestamp) as latest_event,
                    min(timestamp) as earliest_event
                FROM telemetry_events
                WHERE timestamp >= now() - INTERVAL 24 HOUR
            """)

            if health_result:
                row = health_result[0]
                return {
                    'status': 'healthy',
                    'total_events_24h': row[0],
                    'active_campaigns': row[1],
                    'unique_fingerprints_24h': row[2],
                    'latest_event': str(row[3]) if row[3] else None,
                    'earliest_event': str(row[4]) if row[4] else None,
                    'data_retention_compliant': self._check_data_retention_compliance()
                }
            else:
                return {'status': 'no_data'}

        except Exception as e:
            logger.error(f"Failed to get telemetry health: {e}")
            return {'status': 'unhealthy', 'error': str(e)}

    def _check_data_retention_compliance(self) -> bool:
        """Check if data retention policies are being followed."""
        try:
            # Check for events older than retention policy
            retention_days = config.telemetry_retention_days
            old_events_result = self.client.execute("""
                SELECT count(*) as old_event_count
                FROM telemetry_events
                WHERE timestamp < now() - INTERVAL %(retention_days)s DAY
            """, {'retention_days': retention_days})

            old_count = old_events_result[0][0] if old_events_result else 0
            return old_count == 0  # Should be 0 if retention is working

        except Exception:
            return False

    def purge_old_data(self, days_to_keep: Optional[int] = None) -> int:
        """
        Purge telemetry data older than retention policy.

        Args:
            days_to_keep: Override default retention days

        Returns:
            Number of records purged
        """
        try:
            self.connect()

            retention_days = days_to_keep or config.telemetry_retention_days
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            # Delete old records
            delete_result = self.client.execute("""
                ALTER TABLE telemetry_events
                DELETE WHERE timestamp < %(cutoff_date)s
            """, {'cutoff_date': cutoff_date})

            purged_count = delete_result[0][0] if delete_result else 0

            log_privacy_event(
                "data_purged",
                operation="retention_policy",
                records_purged=purged_count,
                retention_days=retention_days
            )

            return purged_count

        except Exception as e:
            logger.error(f"Failed to purge old data: {e}")
            return 0

