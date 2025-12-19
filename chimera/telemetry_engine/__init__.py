"""
Telemetry Engine - Privacy-Preserving Event Collection

High-velocity telemetry collection with:
- ClickHouse for data storage
- Differential privacy anonymization
- Behavioral fingerprinting (non-tracking)
- Ethical data retention policies
"""

from .telemetry_collector import TelemetryCollector
from .privacy_filter import PrivacyFilter

__all__ = ["TelemetryCollector", "PrivacyFilter"]


