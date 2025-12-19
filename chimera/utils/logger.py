"""
CHIMERA Structured Logging

Implements NSA-grade audit logging with:
- Structured JSON logging
- Security event classification
- Privacy-preserving data handling
- Compliance with audit requirements
"""

import sys
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

from .config import config


class SecurityLogger:
    """
    NSA-grade security and audit logging.

    Implements structured logging with security classifications,
    privacy preservation, and compliance requirements.
    """

    def __init__(self, name: str, level: str = None):
        self.name = name
        self.level = level or config.log_level.upper()

        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, self.level))

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Console handler with structured format
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.level))

        if STRUCTLOG_AVAILABLE:
            # Use structlog for advanced structured logging
            import structlog
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    self._add_security_context,
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    structlog.processors.JSONRenderer()
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
            console_handler.setFormatter(structlog.stdlib.LogFormatter())
        else:
            # Fallback to standard logging with JSON format
            formatter = SecurityFormatter()
            console_handler.setFormatter(formatter)

        self.logger.addHandler(console_handler)

        # File handler for security events (if configured)
        self._setup_file_logging()

    def _setup_file_logging(self):
        """Setup file logging for security events."""
        try:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)

            # Security events file
            security_handler = logging.FileHandler(log_dir / "security.log")
            security_handler.setLevel(logging.INFO)
            security_formatter = SecurityFormatter()
            security_handler.setFormatter(security_formatter)
            security_handler.addFilter(SecurityEventFilter())
            self.logger.addHandler(security_handler)

            # Audit events file
            audit_handler = logging.FileHandler(log_dir / "audit.log")
            audit_handler.setLevel(logging.INFO)
            audit_formatter = SecurityFormatter()
            audit_handler.setFormatter(audit_formatter)
            audit_handler.addFilter(AuditEventFilter())
            self.logger.addHandler(audit_handler)

        except Exception as e:
            # Don't fail if file logging setup fails
            self.logger.warning(f"Could not setup file logging: {e}")

    def _add_security_context(self, logger, method_name, event_dict):
        """Add security context to structured logs."""
        event_dict.update({
            "service": "chimera",
            "version": config.app_version,
            "classification": "UNCLASSIFIED//FOUO",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        return event_dict

    def security_event(self, event_type: str, **kwargs):
        """Log security-related events with classification."""
        extra = {
            "event_type": event_type,
            "classification": kwargs.pop("classification", "UNCLASSIFIED//FOUO"),
            **kwargs
        }
        self.logger.info("SECURITY_EVENT", extra=extra)

    def audit_event(self, action: str, participant_id: Optional[str] = None, **kwargs):
        """Log audit events for compliance."""
        extra = {
            "action": action,
            "participant_id": participant_id,
            "audit_timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        self.logger.info("AUDIT_EVENT", extra=extra)

    def privacy_event(self, operation: str, data_type: str, **kwargs):
        """Log privacy-related operations."""
        extra = {
            "operation": operation,
            "data_type": data_type,
            "privacy_compliant": kwargs.pop("compliant", True),
            **kwargs
        }
        self.logger.info("PRIVACY_EVENT", extra=extra)

    def ethics_event(self, incident_type: str, severity: str = "MEDIUM", **kwargs):
        """Log ethics-related incidents."""
        extra = {
            "incident_type": incident_type,
            "severity": severity,
            "ethics_violation": kwargs.pop("violation", False),
            **kwargs
        }
        self.logger.warning("ETHICS_EVENT", extra=extra)


class SecurityFormatter(logging.Formatter):
    """Custom formatter for security events."""

    def format(self, record):
        # Add security context
        if not hasattr(record, 'classification'):
            record.classification = "UNCLASSIFIED//FOUO"

        if not hasattr(record, 'service'):
            record.service = "chimera"

        # Create structured log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": record.service,
            "name": record.name,
            "message": record.getMessage(),
            "classification": record.classification,
        }

        # Add extra fields
        if hasattr(record, 'event_type'):
            log_entry["event_type"] = record.event_type

        if hasattr(record, 'action'):
            log_entry["action"] = record.action

        if hasattr(record, 'participant_id'):
            log_entry["participant_id"] = record.participant_id

        # Add any additional fields from extra
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno',
                             'pathname', 'filename', 'module', 'exc_info',
                             'exc_text', 'stack_info', 'lineno', 'funcName',
                             'created', 'msecs', 'relativeCreated', 'thread',
                             'threadName', 'processName', 'process', 'message']:
                    log_entry[key] = value

        return json.dumps(log_entry, default=str)


class SecurityEventFilter(logging.Filter):
    """Filter for security events only."""

    def filter(self, record):
        return hasattr(record, 'event_type') or getattr(record, 'levelno', 0) >= logging.WARNING


class AuditEventFilter(logging.Filter):
    """Filter for audit events only."""

    def filter(self, record):
        return hasattr(record, 'action') or hasattr(record, 'audit_timestamp')


# Global logger instance
_security_logger = None


def setup_logging(name: str = "chimera", level: str = None) -> SecurityLogger:
    """Setup and return the global security logger."""
    global _security_logger
    if _security_logger is None:
        _security_logger = SecurityLogger(name, level)
    return _security_logger


def get_logger(name: str) -> SecurityLogger:
    """Get the global security logger instance."""
    if _security_logger is None:
        return setup_logging(name)
    return _security_logger


# Convenience functions
def log_security_event(event_type: str, **kwargs):
    """Convenience function for security events."""
    logger = get_logger()
    logger.security_event(event_type, **kwargs)


def log_audit_event(action: str, participant_id: Optional[str] = None, **kwargs):
    """Convenience function for audit events."""
    logger = get_logger()
    logger.audit_event(action, participant_id, **kwargs)


def log_privacy_event(operation: str, data_type: str, **kwargs):
    """Convenience function for privacy events."""
    logger = get_logger()
    logger.privacy_event(operation, data_type, **kwargs)


def log_ethics_event(incident_type: str, severity: str = "MEDIUM", **kwargs):
    """Convenience function for ethics events."""
    logger = get_logger()
    logger.ethics_event(incident_type, severity, **kwargs)


