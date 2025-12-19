# CHIMERA Framework - Operational Metrics & Monitoring
# Version: 1.0.0
# Created: December 2025
# Purpose: Prometheus-compatible metrics collection and alerting

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set
from collections import defaultdict, deque

from prometheus_client import (
    Counter, Gauge, Histogram, Summary, CollectorRegistry,
    generate_latest, CONTENT_TYPE_LATEST
)

# ===========================================
# CONFIGURATION
# ===========================================

class MetricsConfig:
    """Configuration for metrics collection."""

    # Prometheus settings
    METRICS_PREFIX = "chimera"
    METRICS_PORT = 9090
    COLLECTION_INTERVAL = 15  # seconds

    # Alert thresholds
    CONSENT_VIOLATION_ALERT_THRESHOLD = 1  # Any consent violations trigger alert
    KILL_SWITCH_TRIGGER_ALERT_THRESHOLD = 1
    RATE_LIMIT_EXCEEDED_ALERT_THRESHOLD = 10  # per minute

    # Metric retention
    METRICS_RETENTION_HOURS = 24
    ALERT_RETENTION_HOURS = 168  # 7 days

    # Performance monitoring
    ENABLE_PERFORMANCE_METRICS = True
    SLOW_QUERY_THRESHOLD_MS = 1000
    MEMORY_USAGE_ALERT_MB = 1024

# ===========================================
# METRICS DEFINITIONS
# ===========================================

class MetricLabels:
    """Standard metric labels for consistent tagging."""

    # Common labels
    CAMPAIGN_ID = "campaign_id"
    PARTICIPANT_ID = "participant_id"
    ORGANIZATION_ID = "organization_id"
    OPERATION_TYPE = "operation_type"
    SEVERITY_LEVEL = "severity_level"
    STATUS_CODE = "status_code"
    ENDPOINT = "endpoint"
    METHOD = "method"

    # Security-specific labels
    CONSENT_STATUS = "consent_status"
    KILL_SWITCH_TRIGGER = "kill_switch_trigger"
    RATE_LIMIT_SCOPE = "rate_limit_scope"
    PRIVACY_VIOLATION_TYPE = "privacy_violation_type"

class ChimerametricsCollector:
    """Prometheus metrics collector for CHIMERA operations."""

    def __init__(self, config: MetricsConfig = None):
        self.config = config or MetricsConfig()
        self.registry = CollectorRegistry()

        # Initialize all metrics
        self._setup_core_metrics()
        self._setup_security_metrics()
        self._setup_performance_metrics()
        self._setup_business_metrics()

    def _setup_core_metrics(self):
        """Setup core operational metrics."""
        prefix = self.config.METRICS_PREFIX

        # Request metrics
        self.http_requests_total = Counter(
            f"{prefix}_http_requests_total",
            "Total HTTP requests",
            [MetricLabels.ENDPOINT, MetricLabels.METHOD, MetricLabels.STATUS_CODE],
            registry=self.registry
        )

        self.http_request_duration_seconds = Histogram(
            f"{prefix}_http_request_duration_seconds",
            "HTTP request duration in seconds",
            [MetricLabels.ENDPOINT, MetricLabels.METHOD],
            registry=self.registry
        )

        # System health
        self.uptime_seconds = Gauge(
            f"{prefix}_uptime_seconds",
            "Service uptime in seconds",
            registry=self.registry
        )

        self.health_status = Gauge(
            f"{prefix}_health_status",
            "Service health status (1=healthy, 0=unhealthy)",
            registry=self.registry
        )

    def _setup_security_metrics(self):
        """Setup security-specific metrics."""
        prefix = self.config.METRICS_PREFIX

        # Consent metrics
        self.consent_checks_total = Counter(
            f"{prefix}_consent_checks_total",
            "Total consent verification checks",
            [MetricLabels.CONSENT_STATUS, MetricLabels.OPERATION_TYPE],
            registry=self.registry
        )

        self.consent_violations_total = Counter(
            f"{prefix}_consent_violations_total",
            "Total consent violations detected",
            [MetricLabels.CAMPAIGN_ID, MetricLabels.SEVERITY_LEVEL],
            registry=self.registry
        )

        # Kill switch metrics
        self.kill_switch_triggers_total = Counter(
            f"{prefix}_kill_switch_triggers_total",
            "Total kill switch activations",
            [MetricLabels.KILL_SWITCH_TRIGGER, MetricLabels.SEVERITY_LEVEL],
            registry=self.registry
        )

        # Rate limiting metrics
        self.rate_limit_exceeded_total = Counter(
            f"{prefix}_rate_limit_exceeded_total",
            "Total rate limit violations",
            [MetricLabels.RATE_LIMIT_SCOPE, MetricLabels.ENDPOINT],
            registry=self.registry
        )

        # Privacy metrics
        self.privacy_violations_total = Counter(
            f"{prefix}_privacy_violations_total",
            "Total privacy violations detected",
            [MetricLabels.PRIVACY_VIOLATION_TYPE, MetricLabels.SEVERITY_LEVEL],
            registry=self.registry
        )

    def _setup_performance_metrics(self):
        """Setup performance monitoring metrics."""
        prefix = self.config.METRICS_PREFIX

        # Database performance
        self.db_query_duration_seconds = Histogram(
            f"{prefix}_db_query_duration_seconds",
            "Database query duration",
            ["query_type", "table_name"],
            registry=self.registry
        )

        self.db_connection_pool_size = Gauge(
            f"{prefix}_db_connection_pool_size",
            "Database connection pool size",
            ["pool_type"],
            registry=self.registry
        )

        # Cache performance
        self.cache_hit_total = Counter(
            f"{prefix}_cache_hit_total",
            "Cache hits",
            ["cache_type"],
            registry=self.registry
        )

        self.cache_miss_total = Counter(
            f"{prefix}_cache_miss_total",
            "Cache misses",
            ["cache_type"],
            registry=self.registry
        )

        # Memory usage
        self.memory_usage_bytes = Gauge(
            f"{prefix}_memory_usage_bytes",
            "Memory usage in bytes",
            ["component"],
            registry=self.registry
        )

    def _setup_business_metrics(self):
        """Setup business intelligence metrics."""
        prefix = self.config.METRICS_PREFIX

        # Campaign metrics
        self.campaigns_active = Gauge(
            f"{prefix}_campaigns_active",
            "Number of currently active campaigns",
            registry=self.registry
        )

        self.campaigns_created_total = Counter(
            f"{prefix}_campaigns_created_total",
            "Total campaigns created",
            [MetricLabels.ORGANIZATION_ID],
            registry=self.registry
        )

        # Email metrics
        self.emails_sent_total = Counter(
            f"{prefix}_emails_sent_total",
            "Total emails sent",
            [MetricLabels.CAMPAIGN_ID, MetricLabels.ORGANIZATION_ID],
            registry=self.registry
        )

        self.emails_delivered_total = Counter(
            f"{prefix}_emails_delivered_total",
            "Total emails delivered successfully",
            [MetricLabels.CAMPAIGN_ID],
            registry=self.registry
        )

        # Engagement metrics
        self.email_opens_total = Counter(
            f"{prefix}_email_opens_total",
            "Total email opens tracked",
            [MetricLabels.CAMPAIGN_ID, MetricLabels.PARTICIPANT_ID],
            registry=self.registry
        )

        self.link_clicks_total = Counter(
            f"{prefix}_link_clicks_total",
            "Total link clicks tracked",
            [MetricLabels.CAMPAIGN_ID, MetricLabels.PARTICIPANT_ID],
            registry=self.registry
        )

        # Success rate metrics
        self.click_rate_percent = Gauge(
            f"{prefix}_click_rate_percent",
            "Click rate percentage per campaign",
            [MetricLabels.CAMPAIGN_ID],
            registry=self.registry
        )

        self.open_rate_percent = Gauge(
            f"{prefix}_open_rate_percent",
            "Open rate percentage per campaign",
            [MetricLabels.CAMPAIGN_ID],
            registry=self.registry
        )

        # Detection metrics
        self.detection_time_seconds = Histogram(
            f"{prefix}_detection_time_seconds",
            "Time to detect security incidents",
            [MetricLabels.SEVERITY_LEVEL],
            registry=self.registry
        )

    def record_consent_check(self, status: str, operation_type: str = "email_send"):
        """Record a consent verification check."""
        self.consent_checks_total.labels(
            consent_status=status,
            operation_type=operation_type
        ).inc()

    def record_consent_violation(self, campaign_id: str = "", severity: str = "high"):
        """Record a consent violation."""
        self.consent_violations_total.labels(
            campaign_id=campaign_id,
            severity_level=severity
        ).inc()

    def record_kill_switch_trigger(self, trigger_type: str, severity: str = "high"):
        """Record a kill switch activation."""
        self.kill_switch_triggers_total.labels(
            kill_switch_trigger=trigger_type,
            severity_level=severity
        ).inc()

    def record_rate_limit_exceeded(self, scope: str, endpoint: str = ""):
        """Record a rate limit violation."""
        self.rate_limit_exceeded_total.labels(
            rate_limit_scope=scope,
            endpoint=endpoint
        ).inc()

    def record_privacy_violation(self, violation_type: str, severity: str = "medium"):
        """Record a privacy violation."""
        self.privacy_violations_total.labels(
            privacy_violation_type=violation_type,
            severity_level=severity
        ).inc()

    def record_http_request(self, endpoint: str, method: str, status_code: int, duration: float):
        """Record an HTTP request."""
        self.http_requests_total.labels(
            endpoint=endpoint,
            method=method,
            status_code=status_code
        ).inc()

        self.http_request_duration_seconds.labels(
            endpoint=endpoint,
            method=method
        ).observe(duration)

    def record_email_sent(self, campaign_id: str, organization_id: str = ""):
        """Record an email being sent."""
        self.emails_sent_total.labels(
            campaign_id=campaign_id,
            organization_id=organization_id
        ).inc()

    def record_email_open(self, campaign_id: str, participant_id: str = ""):
        """Record an email open event."""
        self.email_opens_total.labels(
            campaign_id=campaign_id,
            participant_id=participant_id
        ).inc()

    def record_link_click(self, campaign_id: str, participant_id: str = ""):
        """Record a link click event."""
        self.link_clicks_total.labels(
            campaign_id=campaign_id,
            participant_id=participant_id
        ).inc()

    def update_campaign_count(self, active_count: int):
        """Update the active campaign count."""
        self.campaigns_active.set(active_count)

    def get_metrics_output(self) -> str:
        """Get Prometheus-formatted metrics output."""
        return generate_latest(self.registry).decode('utf-8')

    def get_metrics_json(self) -> Dict:
        """Get metrics in JSON format for dashboard consumption."""
        # This would convert Prometheus metrics to JSON format
        # Implementation would iterate through collectors and extract values
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": self._get_gauge_value(self.uptime_seconds),
            "health_status": self._get_gauge_value(self.health_status),
            "active_campaigns": self._get_gauge_value(self.campaigns_active),
            "consent_violations": self._get_counter_values(self.consent_violations_total),
            "kill_switch_triggers": self._get_counter_values(self.kill_switch_triggers_total),
            "rate_limit_violations": self._get_counter_values(self.rate_limit_exceeded_total)
        }

    def _get_gauge_value(self, gauge) -> float:
        """Extract value from a Prometheus gauge."""
        # Implementation would extract the actual value
        return 0.0

    def _get_counter_values(self, counter) -> Dict:
        """Extract values from a Prometheus counter."""
        # Implementation would extract values by labels
        return {}

# ===========================================
# ALERTING SYSTEM
# ===========================================

class AlertManager:
    """Alert management system for critical events."""

    def __init__(self, config: MetricsConfig):
        self.config = config
        self.alerts: List[Dict] = []
        self._alert_queue: deque = deque(maxlen=1000)

    def create_alert(self, alert_type: str, severity: str, description: str,
                    labels: Dict = None, value: float = None):
        """Create a new alert."""
        alert = {
            "alert_type": alert_type,
            "severity": severity,
            "description": description,
            "labels": labels or {},
            "value": value,
            "timestamp": datetime.utcnow(),
            "status": "firing"
        }

        self.alerts.append(alert)
        self._alert_queue.append(alert)

        # Log critical alerts
        if severity in ["critical", "high"]:
            logging.warning(f"ALERT {severity.upper()}: {alert_type} - {description}")

    def resolve_alert(self, alert_type: str, labels: Dict = None):
        """Resolve an existing alert."""
        for alert in self.alerts:
            if (alert["alert_type"] == alert_type and
                alert["status"] == "firing" and
                (labels is None or alert["labels"].items() <= labels.items())):
                alert["status"] = "resolved"
                alert["resolved_at"] = datetime.utcnow()
                break

    def get_active_alerts(self, severity_filter: List[str] = None) -> List[Dict]:
        """Get currently active alerts."""
        active = [a for a in self.alerts if a["status"] == "firing"]
        if severity_filter:
            active = [a for a in active if a["severity"] in severity_filter]
        return active

    def check_alert_thresholds(self, metrics: ChimerametricsCollector):
        """Check metrics against alert thresholds."""
        # Consent violations
        if self._get_metric_value(metrics.consent_violations_total) >= self.config.CONSENT_VIOLATION_ALERT_THRESHOLD:
            self.create_alert(
                "consent_violations_high",
                "critical",
                f"Consent violations exceeded threshold: {self.config.CONSENT_VIOLATION_ALERT_THRESHOLD}",
                {"threshold": self.config.CONSENT_VIOLATION_ALERT_THRESHOLD}
            )

        # Kill switch triggers
        if self._get_metric_value(metrics.kill_switch_triggers_total) >= self.config.KILL_SWITCH_TRIGGER_ALERT_THRESHOLD:
            self.create_alert(
                "kill_switch_triggers_high",
                "high",
                f"Kill switch triggers exceeded threshold: {self.config.KILL_SWITCH_TRIGGER_ALERT_THRESHOLD}",
                {"threshold": self.config.KILL_SWITCH_TRIGGER_ALERT_THRESHOLD}
            )

        # Rate limit violations
        rate_limit_violations = self._get_metric_value(metrics.rate_limit_exceeded_total)
        if rate_limit_violations >= self.config.RATE_LIMIT_EXCEEDED_ALERT_THRESHOLD:
            self.create_alert(
                "rate_limit_violations_high",
                "medium",
                f"Rate limit violations exceeded threshold: {rate_limit_violations}",
                {"threshold": self.config.RATE_LIMIT_EXCEEDED_ALERT_THRESHOLD}
            )

    def _get_metric_value(self, metric) -> float:
        """Extract current value from a Prometheus metric."""
        # Implementation would get the actual current value
        return 0.0

# ===========================================
# DASHBOARD INTEGRATION
# ===========================================

class MetricsDashboard:
    """Dashboard integration for metrics visualization."""

    def __init__(self, collector: ChimerametricsCollector, alert_manager: AlertManager):
        self.collector = collector
        self.alert_manager = alert_manager

    def get_dashboard_data(self) -> Dict:
        """Get comprehensive dashboard data."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "health_status": "healthy",  # Would check actual health
                "active_campaigns": 5,  # Would get from metrics
                "total_emails_sent": 1250,
                "active_alerts": len(self.alert_manager.get_active_alerts())
            },
            "security_metrics": {
                "consent_violations": 0,
                "kill_switch_triggers": 1,
                "rate_limit_violations": 5,
                "privacy_violations": 2
            },
            "performance_metrics": {
                "avg_response_time": 245.5,  # ms
                "error_rate": 0.02,  # 2%
                "uptime_percentage": 99.9
            },
            "campaign_metrics": {
                "active_campaigns": [
                    {
                        "id": "bec_training_q4",
                        "name": "BEC Training Q4",
                        "emails_sent": 150,
                        "open_rate": 68.5,
                        "click_rate": 12.3,
                        "status": "active"
                    }
                ]
            },
            "alerts": self.alert_manager.get_active_alerts(["critical", "high"]),
            "recent_activity": [
                {
                    "timestamp": "2025-12-19T10:30:00Z",
                    "event": "Campaign started",
                    "details": "BEC simulation campaign initiated"
                },
                {
                    "timestamp": "2025-12-19T10:25:00Z",
                    "event": "Consent verified",
                    "details": "10 participants verified for campaign"
                }
            ]
        }

    def export_grafana_dashboard(self) -> Dict:
        """Export dashboard configuration for Grafana."""
        return {
            "dashboard": {
                "title": "CHIMERA Security Operations Dashboard",
                "tags": ["chimera", "security", "monitoring"],
                "timezone": "UTC",
                "panels": [
                    {
                        "title": "Security Violations",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "rate(chimera_consent_violations_total[5m])",
                                "legendFormat": "Consent Violations"
                            },
                            {
                                "expr": "rate(chimera_kill_switch_triggers_total[5m])",
                                "legendFormat": "Kill Switch Triggers"
                            }
                        ]
                    },
                    {
                        "title": "System Health",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "chimera_health_status",
                                "legendFormat": "Health Status"
                            }
                        ]
                    }
                ]
            }
        }

# ===========================================
# FASTAPI INTEGRATION
# ===========================================

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse

def create_metrics_router(collector: ChimerametricsCollector,
                         dashboard: MetricsDashboard) -> APIRouter:
    """Create FastAPI router for metrics endpoints."""

    router = APIRouter(prefix="/metrics", tags=["metrics"])

    @router.get("/prometheus")
    async def get_prometheus_metrics():
        """Get Prometheus-formatted metrics."""
        try:
            return PlainTextResponse(
                collector.get_metrics_output(),
                media_type=CONTENT_TYPE_LATEST
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/dashboard")
    async def get_dashboard_data():
        """Get dashboard data for frontend consumption."""
        try:
            return dashboard.get_dashboard_data()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/health")
    async def get_health_status():
        """Get system health status."""
        try:
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "uptime": 123456  # Would calculate actual uptime
            }
        except Exception as e:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

    @router.get("/alerts")
    async def get_active_alerts(severity: str = None):
        """Get active alerts."""
        try:
            severities = [severity] if severity else ["critical", "high", "medium"]
            alerts = dashboard.alert_manager.get_active_alerts(severities)
            return {"alerts": alerts, "count": len(alerts)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router

# ===========================================
# UTILITY FUNCTIONS
# ===========================================

def create_metrics_collector(config: MetricsConfig = None) -> ChimerametricsCollector:
    """Factory function to create metrics collector."""
    return ChimerametricsCollector(config)

def create_alert_manager(config: MetricsConfig = None) -> AlertManager:
    """Factory function to create alert manager."""
    return AlertManager(config or MetricsConfig())

def create_metrics_dashboard(collector: ChimerametricsCollector,
                           alert_manager: AlertManager) -> MetricsDashboard:
    """Factory function to create metrics dashboard."""
    return MetricsDashboard(collector, alert_manager)

# ===========================================
# LOGGING CONFIGURATION
# ===========================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ===========================================
# END OF MODULE
# ===========================================
