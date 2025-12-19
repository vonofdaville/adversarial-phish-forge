# CHIMERA Framework - Credential Sanitization & Privacy Filter
# Version: 1.0.0
# Created: December 2025
# Purpose: Ensure ZERO credential storage and prevent data leakage

import hashlib
import hmac
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any
from urllib.parse import parse_qs, urlparse

import bcrypt
from pydantic import BaseModel, validator

# ===========================================
# CONFIGURATION
# ===========================================

class PrivacyFilterConfig:
    """Configuration for privacy filtering and credential sanitization."""

    # Credential detection patterns
    CREDENTIAL_FIELD_NAMES = {
        'password', 'passwd', 'pwd', 'pass', 'secret', 'token', 'key', 'api_key',
        'auth_token', 'access_token', 'refresh_token', 'session_token',
        'username', 'user', 'email', 'login', 'account',
        'credit_card', 'card_number', 'cc_number', 'cvv', 'cvc',
        'ssn', 'social_security', 'tax_id', 'pin', 'otp'
    }

    # High-risk patterns (immediate alert)
    HIGH_RISK_PATTERNS = [
        r'\b\d{4}[\s\-]\d{4}[\s\-]\d{4}[\s\-]\d{4}\b',  # Credit card numbers
        r'\b\d{3}[\s\-]\d{2}[\s\-]\d{4}\b',            # SSN
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email addresses
        r'\b\d{6,}\b'                                   # Long numeric sequences
    ]

    # Hashing configuration
    HASH_SALT_ROUNDS = 12
    HMAC_SECRET_KEY = "change_this_in_production"  # Must be set via environment

    # Storage limits
    MAX_FIELD_LENGTH = 1000  # Characters
    MAX_TOTAL_PAYLOAD_SIZE = 10000  # Bytes

    # Monitoring
    ALERT_ON_SUSPICIOUS_DATA = True
    LOG_SANITIZATION_EVENTS = True

# ===========================================
# DATA MODELS
# ===========================================

class SanitizationResult(BaseModel):
    """Result of data sanitization process."""
    original_field_count: int
    sanitized_field_count: int
    credential_fields_removed: int
    high_risk_patterns_detected: int
    payload_size_bytes: int
    processing_time_ms: float
    alerts_triggered: List[str] = []

class CredentialAlert(BaseModel):
    """Alert for detected credential data."""
    alert_type: str
    severity: str
    field_name: Optional[str]
    detected_pattern: Optional[str]
    sample_data: Optional[str]  # First 50 chars only
    timestamp: datetime
    campaign_id: Optional[str]
    participant_id: Optional[str]

    @validator('timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        return v or datetime.utcnow()

@dataclass
class SanitizedData:
    """Sanitized telemetry data ready for storage."""
    campaign_id: str
    participant_id: Optional[str]
    sanitized_payload: Dict[str, Any]
    credential_hashes: Dict[str, str]  # Field name -> bcrypt hash
    metadata: Dict[str, Any]
    sanitization_result: SanitizationResult
    created_at: datetime = field(default_factory=datetime.utcnow)

# ===========================================
# SANITIZATION ENGINES
# ===========================================

class CredentialDetector:
    """Detects credential-like fields and patterns."""

    def __init__(self, config: PrivacyFilterConfig):
        self.config = config
        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in config.HIGH_RISK_PATTERNS
        ]

    def is_credential_field(self, field_name: str, field_value: Any) -> bool:
        """Determine if a field contains credential data."""
        field_name_lower = field_name.lower()

        # Check field name against known credential fields
        if any(cred_name in field_name_lower for cred_name in self.config.CREDENTIAL_FIELD_NAMES):
            return True

        # Check field value for high-risk patterns
        if isinstance(field_value, str):
            for pattern in self._compiled_patterns:
                if pattern.search(field_value):
                    return True

        return False

    def detect_high_risk_patterns(self, data: Dict[str, Any]) -> List[Tuple[str, str]]:
        """Detect high-risk patterns in data. Returns list of (field_name, pattern_type)."""
        high_risk_fields = []

        for field_name, field_value in data.items():
            if isinstance(field_value, str):
                for i, pattern in enumerate(self._compiled_patterns):
                    if pattern.search(field_value):
                        pattern_type = f"pattern_{i}"
                        high_risk_fields.append((field_name, pattern_type))

        return high_risk_fields

class DataSanitizer:
    """Sanitizes telemetry data by removing or hashing credentials."""

    def __init__(self, config: PrivacyFilterConfig):
        self.config = config
        self.detector = CredentialDetector(config)
        self._hmac_key = config.HMAC_SECRET_KEY.encode() if config.HMAC_SECRET_KEY else b"default_key_change_me"

    def sanitize_payload(self, raw_payload: Dict[str, Any],
                        campaign_id: str,
                        participant_id: Optional[str] = None) -> SanitizedData:
        """Sanitize a telemetry payload."""
        import time
        start_time = time.time()

        alerts = []
        credential_hashes = {}
        sanitized_payload = {}
        credential_fields_removed = 0
        high_risk_patterns = 0

        # Process each field
        for field_name, field_value in raw_payload.items():
            # Size limits
            if len(str(field_value)) > self.config.MAX_FIELD_LENGTH:
                field_value = str(field_value)[:self.config.MAX_FIELD_LENGTH] + "..."

            # Check if this is credential data
            if self.detector.is_credential_field(field_name, field_value):
                if self._is_password_field(field_name):
                    # Hash passwords immediately (never store plaintext)
                    credential_hashes[field_name] = self._hash_credential(str(field_value))
                    sanitized_payload[field_name] = "[PASSWORD_HASHED]"
                elif self._is_username_field(field_name):
                    # Hash usernames for correlation without storage
                    credential_hashes[field_name] = self._hash_credential(str(field_value))
                    sanitized_payload[field_name] = "[USERNAME_HASHED]"
                else:
                    # Remove other credentials entirely
                    credential_fields_removed += 1
                    alerts.append(f"Removed credential field: {field_name}")
                    continue  # Don't include in sanitized payload
            else:
                # Check for high-risk patterns in non-credential fields
                high_risk_detected = self.detector.detect_high_risk_patterns({field_name: field_value})
                if high_risk_detected:
                    high_risk_patterns += len(high_risk_detected)
                    for hr_field, pattern in high_risk_detected:
                        alerts.append(f"High-risk pattern in {hr_field}: {pattern}")
                        # Remove or mask the field
                        if "email" in field_name.lower():
                            sanitized_payload[field_name] = "[EMAIL_MASKED]"
                        elif "card" in field_name.lower():
                            sanitized_payload[field_name] = "[CARD_MASKED]"
                        else:
                            sanitized_payload[field_name] = "[HIGH_RISK_DATA_REMOVED]"
                        credential_fields_removed += 1
                else:
                    # Safe field - include as-is
                    sanitized_payload[field_name] = field_value

        # Calculate payload size
        payload_size = len(str(sanitized_payload).encode('utf-8'))

        # Check total payload size limit
        if payload_size > self.config.MAX_TOTAL_PAYLOAD_SIZE:
            # Truncate large payloads
            sanitized_payload = {"error": "Payload too large", "size": payload_size}
            alerts.append(f"Payload truncated due to size: {payload_size} bytes")

        processing_time = (time.time() - start_time) * 1000  # milliseconds

        sanitization_result = SanitizationResult(
            original_field_count=len(raw_payload),
            sanitized_field_count=len(sanitized_payload),
            credential_fields_removed=credential_fields_removed,
            high_risk_patterns_detected=high_risk_patterns,
            payload_size_bytes=payload_size,
            processing_time_ms=processing_time,
            alerts_triggered=alerts
        )

        metadata = {
            "user_agent": raw_payload.get("user_agent", "unknown"),
            "ip_address": self._extract_ip_from_payload(raw_payload),
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": processing_time
        }

        return SanitizedData(
            campaign_id=campaign_id,
            participant_id=participant_id,
            sanitized_payload=sanitized_payload,
            credential_hashes=credential_hashes,
            metadata=metadata,
            sanitization_result=sanitization_result
        )

    def _is_password_field(self, field_name: str) -> bool:
        """Check if field contains password data."""
        return any(pwd in field_name.lower() for pwd in ['password', 'passwd', 'pwd', 'pass'])

    def _is_username_field(self, field_name: str) -> bool:
        """Check if field contains username/login data."""
        return any(user in field_name.lower() for user in ['username', 'user', 'email', 'login', 'account'])

    def _hash_credential(self, value: str) -> str:
        """Hash a credential value using bcrypt."""
        try:
            # Generate salt and hash
            salt = bcrypt.gensalt(rounds=self.config.HASH_SALT_ROUNDS)
            hashed = bcrypt.hashpw(value.encode('utf-8'), salt)
            return hashed.decode('utf-8')
        except Exception as e:
            logging.error(f"Failed to hash credential: {e}")
            # Return a placeholder hash if hashing fails
            return "$2b$12$placeholder.hash.for.failed.hashing"

    def _extract_ip_from_payload(self, payload: Dict[str, Any]) -> Optional[str]:
        """Extract IP address from payload."""
        # Check common IP field names
        ip_fields = ['ip', 'ip_address', 'remote_addr', 'client_ip']
        for field in ip_fields:
            if field in payload and isinstance(payload[field], str):
                return payload[field]
        return None

# ===========================================
# MONITORING & ALERTING
# ===========================================

class PrivacyMonitor:
    """Monitors privacy violations and triggers alerts."""

    def __init__(self, config: PrivacyFilterConfig):
        self.config = config
        self.alerts: List[CredentialAlert] = []

    def process_sanitization_result(self, result: SanitizationResult,
                                  campaign_id: str,
                                  participant_id: Optional[str] = None) -> List[CredentialAlert]:
        """Process sanitization results and generate alerts."""
        alerts = []

        # Alert on credential fields removed
        if result.credential_fields_removed > 0:
            alerts.append(CredentialAlert(
                alert_type="credential_fields_removed",
                severity="high" if result.credential_fields_removed > 5 else "medium",
                detected_pattern=f"{result.credential_fields_removed} credential fields",
                campaign_id=campaign_id,
                participant_id=participant_id
            ))

        # Alert on high-risk patterns
        if result.high_risk_patterns_detected > 0:
            alerts.append(CredentialAlert(
                alert_type="high_risk_patterns_detected",
                severity="critical",
                detected_pattern=f"{result.high_risk_patterns_detected} high-risk patterns",
                campaign_id=campaign_id,
                participant_id=participant_id
            ))

        # Alert on large payloads (potential data exfiltration)
        if result.payload_size_bytes > self.config.MAX_TOTAL_PAYLOAD_SIZE * 0.8:
            alerts.append(CredentialAlert(
                alert_type="large_payload_detected",
                severity="medium",
                detected_pattern=f"Payload size: {result.payload_size_bytes} bytes",
                campaign_id=campaign_id,
                participant_id=participant_id
            ))

        # Log alerts if configured
        if self.config.LOG_SANITIZATION_EVENTS:
            for alert in alerts:
                logging.warning(f"Privacy alert: {alert.alert_type} - {alert.severity} for campaign {campaign_id}")

        self.alerts.extend(alerts)
        return alerts

# ===========================================
# TELEMETRY PROCESSOR
# ===========================================

class TelemetryPrivacyFilter:
    """Main privacy filter for telemetry data processing."""

    def __init__(self, config: PrivacyFilterConfig = None):
        self.config = config or PrivacyFilterConfig()
        self.sanitizer = DataSanitizer(self.config)
        self.monitor = PrivacyMonitor(self.config)

    def process_telemetry(self, raw_data: Dict[str, Any],
                         campaign_id: str,
                         participant_id: Optional[str] = None) -> Tuple[SanitizedData, List[CredentialAlert]]:
        """Process raw telemetry data through privacy filters."""
        # Sanitize the data
        sanitized_data = self.sanitizer.sanitize_payload(raw_data, campaign_id, participant_id)

        # Generate alerts
        alerts = self.monitor.process_sanitization_result(
            sanitized_data.sanitization_result,
            campaign_id,
            participant_id
        )

        return sanitized_data, alerts

    def validate_no_credentials(self, data: Dict[str, Any]) -> bool:
        """Validate that data contains no credential information."""
        for field_name, field_value in data.items():
            if self.sanitizer.detector.is_credential_field(field_name, field_value):
                return False
        return True

    def get_privacy_stats(self) -> Dict[str, Any]:
        """Get privacy monitoring statistics."""
        return {
            "total_alerts": len(self.monitor.alerts),
            "alerts_by_type": self._count_alerts_by_type(),
            "alerts_by_severity": self._count_alerts_by_severity(),
            "recent_alerts": len([a for a in self.monitor.alerts
                                if (datetime.utcnow() - a.timestamp).seconds < 3600])  # Last hour
        }

    def _count_alerts_by_type(self) -> Dict[str, int]:
        """Count alerts by type."""
        counts = {}
        for alert in self.monitor.alerts:
            counts[alert.alert_type] = counts.get(alert.alert_type, 0) + 1
        return counts

    def _count_alerts_by_severity(self) -> Dict[str, int]:
        """Count alerts by severity."""
        counts = {}
        for alert in self.monitor.alerts:
            counts[alert.severity] = counts.get(alert.severity, 0) + 1
        return counts

# ===========================================
# UTILITY FUNCTIONS
# ===========================================

def create_privacy_filter(config: PrivacyFilterConfig = None) -> TelemetryPrivacyFilter:
    """Factory function to create privacy filter."""
    return TelemetryPrivacyFilter(config)

def hash_credential(value: str, salt_rounds: int = 12) -> str:
    """Utility function to hash credentials."""
    try:
        salt = bcrypt.gensalt(rounds=salt_rounds)
        hashed = bcrypt.hashpw(value.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        logging.error(f"Credential hashing failed: {e}")
        return ""

def verify_credential_hash(value: str, hashed: str) -> bool:
    """Verify a credential against its hash."""
    try:
        return bcrypt.checkpw(value.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

# ===========================================
# FASTAPI INTEGRATION
# ===========================================

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

class PrivacyFilterMiddleware:
    """FastAPI middleware for automatic privacy filtering."""

    def __init__(self, privacy_filter: TelemetryPrivacyFilter):
        self.privacy_filter = privacy_filter

    async def __call__(self, request: Request, call_next):
        # Only process telemetry endpoints
        if not request.url.path.startswith(("/api/v1/telemetry", "/pixel", "/track")):
            return await call_next(request)

        try:
            # Extract campaign and participant IDs
            campaign_id = self._extract_campaign_id(request)
            participant_id = self._extract_participant_id(request)

            # Get request data
            request_data = await self._extract_request_data(request)

            # Process through privacy filter
            sanitized_data, alerts = self.privacy_filter.process_telemetry(
                request_data, campaign_id, participant_id
            )

            # Store sanitized data in request state for further processing
            request.state.sanitized_data = sanitized_data
            request.state.privacy_alerts = alerts

            # Log alerts
            for alert in alerts:
                logging.warning(f"Privacy violation detected: {alert.alert_type} in campaign {campaign_id}")

        except Exception as e:
            logging.error(f"Privacy filter error: {e}")
            # Continue processing but log the error

        return await call_next(request)

    def _extract_campaign_id(self, request: Request) -> str:
        """Extract campaign ID from request."""
        # Check path parameters
        campaign_id = request.path_params.get("campaign_id")
        if campaign_id:
            return campaign_id

        # Check query parameters
        campaign_id = request.query_params.get("cid") or request.query_params.get("campaign")
        if campaign_id:
            return campaign_id

        # Default fallback
        return "unknown_campaign"

    def _extract_participant_id(self, request: Request) -> Optional[str]:
        """Extract participant ID from request."""
        # Check path parameters
        participant_id = request.path_params.get("participant_id")
        if participant_id:
            return participant_id

        # Check query parameters
        participant_id = request.query_params.get("pid") or request.query_params.get("participant")
        if participant_id:
            return participant_id

        return None

    async def _extract_request_data(self, request: Request) -> Dict[str, Any]:
        """Extract data from request (query params, form data, JSON body)."""
        data = {}

        # Add query parameters
        data.update(request.query_params)

        # Add form data if present
        try:
            form_data = await request.form()
            data.update(form_data)
        except:
            pass

        # Add JSON body if present
        try:
            json_data = await request.json()
            data.update(json_data)
        except:
            pass

        # Convert to strings where possible
        for key, value in data.items():
            if not isinstance(value, str):
                data[key] = str(value)

        return data

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
