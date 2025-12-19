# CHIMERA Framework - Kill Switch System
# Version: 1.0.0
# Created: December 2025
# Purpose: Multi-level emergency termination system for campaign safety

import asyncio
import logging
import signal
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Callable
from concurrent.futures import ThreadPoolExecutor

import redis.asyncio as redis
from pydantic import BaseModel, validator
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ===========================================
# CONFIGURATION
# ===========================================

class KillSwitchConfig:
    """Configuration for kill switch system."""

    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 2  # Separate DB for kill switch state

    # Response time requirements
    MAX_RESPONSE_TIME_MS: int = 5000  # 5 seconds
    HEALTH_CHECK_INTERVAL: int = 30   # seconds

    # Emergency contacts
    EMERGENCY_EMAILS: List[str] = ["security@chimera-project.org"]
    EMERGENCY_SMS_NUMBERS: List[str] = []
    SLACK_WEBHOOK_URL: Optional[str] = None

    # Geographic restrictions
    ALLOWED_COUNTRIES: Set[str] = {"US", "CA", "GB", "DE", "FR", "AU"}
    GEOIP_API_KEY: Optional[str] = None

    # Campaign limits
    MAX_CAMPAIGN_DURATION_HOURS: int = 168  # 7 days
    MAX_RECIPIENTS_PER_CAMPAIGN: int = 10000

    # Email settings for notifications
    SMTP_SERVER: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: str = "kill-switch@chimera-project.org"

# ===========================================
# DATA MODELS
# ===========================================

class KillSwitchTrigger(Enum):
    """Types of events that can trigger the kill switch."""
    GEOGRAPHIC_ANOMALY = "geographic_anomaly"
    TIME_BOUNDARY_EXCEEDED = "time_boundary_exceeded"
    CONSENT_REVOCATION = "consent_revocation"
    ESCALATION_DETECTION = "escalation_detection"
    MANUAL_OVERRIDE = "manual_override"
    SYSTEM_HEALTH_FAILURE = "system_health_failure"
    SECURITY_INCIDENT = "security_incident"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

class KillSwitchSeverity(Enum):
    """Severity levels for kill switch activation."""
    LOW = "low"         # Log and alert, continue operation
    MEDIUM = "medium"   # Pause campaign, require manual review
    HIGH = "high"       # Terminate campaign, notify stakeholders
    CRITICAL = "critical"  # Full system shutdown, emergency response

@dataclass
class KillSwitchEvent:
    """Represents a kill switch trigger event."""
    trigger_type: KillSwitchTrigger
    severity: KillSwitchSeverity
    campaign_id: Optional[str] = None
    participant_id: Optional[str] = None
    details: Dict = field(default_factory=dict)
    triggered_at: datetime = field(default_factory=datetime.utcnow)
    triggered_by: str = "system"
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

@dataclass
class KillSwitchState:
    """Current state of the kill switch system."""
    is_active: bool = False
    activated_at: Optional[datetime] = None
    activated_by: Optional[str] = None
    reason: Optional[str] = None
    affected_campaigns: Set[str] = field(default_factory=set)
    severity: KillSwitchSeverity = KillSwitchSeverity.LOW

class KillSwitchAction(BaseModel):
    """Action to take when kill switch is triggered."""
    campaign_id: Optional[str] = None  # None means global
    action: str  # terminate, pause, alert, quarantine
    reason: str
    triggered_by: str
    priority: str = "normal"  # normal, urgent, critical

    @validator('action')
    def validate_action(cls, v):
        valid_actions = {'terminate', 'pause', 'alert', 'quarantine', 'resume'}
        if v not in valid_actions:
            raise ValueError(f'Invalid action: {v}. Must be one of {valid_actions}')
        return v

    @validator('priority')
    def validate_priority(cls, v):
        valid_priorities = {'normal', 'urgent', 'critical'}
        if v not in valid_priorities:
            raise ValueError(f'Invalid priority: {v}. Must be one of {valid_priorities}')
        return v

# ===========================================
# EXCEPTIONS
# ===========================================

class KillSwitchException(Exception):
    """Base exception for kill switch operations."""
    pass

class KillSwitchTimeoutException(KillSwitchException):
    """Exception raised when kill switch operation times out."""
    pass

class KillSwitchAlreadyActiveException(KillSwitchException):
    """Exception raised when trying to activate an already active kill switch."""
    pass

# ===========================================
# STATE MANAGEMENT
# ===========================================

class KillSwitchStateManager:
    """Manages kill switch state in Redis."""

    def __init__(self, config: KillSwitchConfig):
        self.config = config
        self._redis: Optional[redis.Redis] = None
        self._state_cache: Optional[KillSwitchState] = None
        self._lock = asyncio.Lock()

    async def connect(self):
        """Establish Redis connection."""
        if self._redis is None:
            self._redis = redis.Redis(
                host=self.config.REDIS_HOST,
                port=self.config.REDIS_PORT,
                db=self.config.REDIS_DB,
                decode_responses=True
            )

    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def get_state(self) -> KillSwitchState:
        """Get current kill switch state."""
        async with self._lock:
            if self._state_cache:
                return self._state_cache

            try:
                data = await self._redis.get("kill_switch:state")
                if data:
                    import json
                    state_data = json.loads(data)
                    self._state_cache = KillSwitchState(**state_data)
                    return self._state_cache
            except Exception as e:
                logging.error(f"Failed to load kill switch state: {e}")

            # Return default state
            self._state_cache = KillSwitchState()
            return self._state_cache

    async def set_state(self, state: KillSwitchState):
        """Update kill switch state."""
        async with self._lock:
            try:
                import json
                data = json.dumps({
                    'is_active': state.is_active,
                    'activated_at': state.activated_at.isoformat() if state.activated_at else None,
                    'activated_by': state.activated_by,
                    'reason': state.reason,
                    'affected_campaigns': list(state.affected_campaigns),
                    'severity': state.severity.value
                })
                await self._redis.set("kill_switch:state", data)
                self._state_cache = state
            except Exception as e:
                logging.error(f"Failed to save kill switch state: {e}")

    async def add_campaign_to_kill_list(self, campaign_id: str):
        """Add a campaign to the kill list."""
        state = await self.get_state()
        state.affected_campaigns.add(campaign_id)
        await self.set_state(state)

    async def remove_campaign_from_kill_list(self, campaign_id: str):
        """Remove a campaign from the kill list."""
        state = await self.get_state()
        state.affected_campaigns.discard(campaign_id)
        await self.set_state(state)

    async def is_campaign_killed(self, campaign_id: str) -> bool:
        """Check if a campaign is on the kill list."""
        state = await self.get_state()
        return campaign_id in state.affected_campaigns

# ===========================================
# TRIGGER DETECTORS
# ===========================================

class TriggerDetector:
    """Base class for trigger detection."""

    def __init__(self, config: KillSwitchConfig):
        self.config = config

    async def detect(self, event_data: Dict) -> Optional[KillSwitchEvent]:
        """Detect if trigger conditions are met. Override in subclasses."""
        raise NotImplementedError

class GeographicAnomalyDetector(TriggerDetector):
    """Detects when emails are opened from non-whitelisted countries."""

    async def detect(self, event_data: Dict) -> Optional[KillSwitchEvent]:
        country = event_data.get('country_code')
        if country and country not in self.config.ALLOWED_COUNTRIES:
            return KillSwitchEvent(
                trigger_type=KillSwitchTrigger.GEOGRAPHIC_ANOMALY,
                severity=KillSwitchSeverity.HIGH,
                campaign_id=event_data.get('campaign_id'),
                participant_id=event_data.get('participant_id'),
                details={
                    'country': country,
                    'ip_address': event_data.get('ip_address'),
                    'user_agent': event_data.get('user_agent')
                }
            )
        return None

class TimeBoundaryDetector(TriggerDetector):
    """Detects when campaigns exceed maximum duration."""

    async def detect(self, event_data: Dict) -> Optional[KillSwitchEvent]:
        campaign_start = event_data.get('campaign_start')
        if campaign_start:
            start_time = datetime.fromisoformat(campaign_start)
            duration = datetime.utcnow() - start_time
            max_duration = timedelta(hours=self.config.MAX_CAMPAIGN_DURATION_HOURS)

            if duration > max_duration:
                return KillSwitchEvent(
                    trigger_type=KillSwitchTrigger.TIME_BOUNDARY_EXCEEDED,
                    severity=KillSwitchSeverity.MEDIUM,
                    campaign_id=event_data.get('campaign_id'),
                    details={
                        'campaign_start': campaign_start,
                        'duration_hours': duration.total_seconds() / 3600,
                        'max_duration_hours': self.config.MAX_CAMPAIGN_DURATION_HOURS
                    }
                )
        return None

class ConsentRevocationDetector(TriggerDetector):
    """Detects when participants revoke consent."""

    async def detect(self, event_data: Dict) -> Optional[KillSwitchEvent]:
        if event_data.get('consent_revoked') == True:
            return KillSwitchEvent(
                trigger_type=KillSwitchTrigger.CONSENT_REVOCATION,
                severity=KillSwitchSeverity.CRITICAL,
                campaign_id=event_data.get('campaign_id'),
                participant_id=event_data.get('participant_id'),
                details={
                    'revocation_reason': event_data.get('reason', 'User request'),
                    'revocation_timestamp': event_data.get('timestamp')
                }
            )
        return None

class EscalationDetector(TriggerDetector):
    """Detects when emails are forwarded to HR/legal domains."""

    ESCALATION_DOMAINS = {
        'hr@', 'legal@', 'compliance@', 'security@',
        'abuse@', 'admin@', 'it@', 'helpdesk@'
    }

    async def detect(self, event_data: Dict) -> Optional[KillSwitchEvent]:
        forwarded_to = event_data.get('forwarded_to', '').lower()
        if any(domain in forwarded_to for domain in self.ESCALATION_DOMAINS):
            return KillSwitchEvent(
                trigger_type=KillSwitchTrigger.ESCALATION_DETECTION,
                severity=KillSwitchSeverity.HIGH,
                campaign_id=event_data.get('campaign_id'),
                participant_id=event_data.get('participant_id'),
                details={
                    'forwarded_to': forwarded_to,
                    'original_recipient': event_data.get('original_recipient')
                }
            )
        return None

# ===========================================
# NOTIFICATION SYSTEM
# ===========================================

class NotificationManager:
    """Handles emergency notifications when kill switch is triggered."""

    def __init__(self, config: KillSwitchConfig):
        self.config = config
        self._executor = ThreadPoolExecutor(max_workers=5)

    async def notify_kill_switch_activation(self, event: KillSwitchEvent, state: KillSwitchState):
        """Send notifications about kill switch activation."""
        message = self._format_notification_message(event, state)

        # Send notifications in parallel
        tasks = []

        # Email notifications
        if self.config.EMERGENCY_EMAILS:
            tasks.append(self._send_email_notification(
                subject=f"🚨 KILL SWITCH ACTIVATED - {event.severity.value.upper()}",
                message=message
            ))

        # Slack notifications
        if self.config.SLACK_WEBHOOK_URL:
            tasks.append(self._send_slack_notification(message))

        # SMS notifications (if configured)
        if self.config.EMERGENCY_SMS_NUMBERS:
            tasks.append(self._send_sms_notification(message))

        # Execute all notifications
        await asyncio.gather(*tasks, return_exceptions=True)

    def _format_notification_message(self, event: KillSwitchEvent, state: KillSwitchState) -> str:
        """Format notification message."""
        return f"""
KILL SWITCH ACTIVATION ALERT

Severity: {event.severity.value.upper()}
Trigger: {event.trigger_type.value.replace('_', ' ').title()}
Time: {event.triggered_at.isoformat()}

Campaign ID: {event.campaign_id or 'GLOBAL'}
Participant ID: {event.participant_id or 'N/A'}

Reason: {event.details.get('reason', 'N/A')}
Triggered By: {event.triggered_by}

Affected Campaigns: {', '.join(state.affected_campaigns) if state.affected_campaigns else 'None'}

System State: ACTIVE
Activated At: {state.activated_at.isoformat() if state.activated_at else 'N/A'}

Please review immediately and take appropriate action.
        """.strip()

    async def _send_email_notification(self, subject: str, message: str):
        """Send email notification."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor,
                self._send_email_sync,
                subject,
                message
            )
        except Exception as e:
            logging.error(f"Failed to send email notification: {e}")

    def _send_email_sync(self, subject: str, message: str):
        """Synchronous email sending."""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config.FROM_EMAIL
            msg['To'] = ', '.join(self.config.EMERGENCY_EMAILS)
            msg['Subject'] = subject

            msg.attach(MIMEText(message, 'plain'))

            server = smtplib.SMTP(self.config.SMTP_SERVER, self.config.SMTP_PORT)
            if self.config.SMTP_USERNAME and self.config.SMTP_PASSWORD:
                server.starttls()
                server.login(self.config.SMTP_USERNAME, self.config.SMTP_PASSWORD)

            text = msg.as_string()
            server.sendmail(self.config.FROM_EMAIL, self.config.EMERGENCY_EMAILS, text)
            server.quit()

        except Exception as e:
            logging.error(f"Email sending failed: {e}")

    async def _send_slack_notification(self, message: str):
        """Send Slack notification."""
        try:
            payload = {"text": message}
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.SLACK_WEBHOOK_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        logging.error(f"Slack notification failed: {response.status}")
        except Exception as e:
            logging.error(f"Slack notification error: {e}")

    async def _send_sms_notification(self, message: str):
        """Send SMS notification (placeholder - implement with Twilio/etc)."""
        # Placeholder for SMS implementation
        logging.info(f"SMS notification would be sent: {message[:100]}...")

# ===========================================
# MAIN KILL SWITCH SYSTEM
# ===========================================

class KillSwitchSystem:
    """Main kill switch system orchestrator."""

    def __init__(self, config: KillSwitchConfig = None):
        self.config = config or KillSwitchConfig()
        self.state_manager = KillSwitchStateManager(self.config)
        self.notification_manager = NotificationManager(self.config)

        # Initialize detectors
        self.detectors = [
            GeographicAnomalyDetector(self.config),
            TimeBoundaryDetector(self.config),
            ConsentRevocationDetector(self.config),
            EscalationDetector(self.config)
        ]

        self._initialized = False
        self._shutdown_event = asyncio.Event()

    async def initialize(self):
        """Initialize the kill switch system."""
        if not self._initialized:
            await self.state_manager.connect()
            self._initialized = True
            logging.info("Kill switch system initialized")

    async def shutdown(self):
        """Shutdown the kill switch system."""
        self._shutdown_event.set()
        await self.state_manager.disconnect()
        self._initialized = False
        logging.info("Kill switch system shutdown")

    async def evaluate_event(self, event_data: Dict) -> Optional[KillSwitchEvent]:
        """Evaluate an event against all trigger detectors."""
        await self.initialize()

        # Run all detectors in parallel
        tasks = [detector.detect(event_data) for detector in self.detectors]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Find first trigger (highest priority first)
        severity_order = {
            KillSwitchSeverity.CRITICAL: 4,
            KillSwitchSeverity.HIGH: 3,
            KillSwitchSeverity.MEDIUM: 2,
            KillSwitchSeverity.LOW: 1
        }

        triggered_events = [r for r in results if isinstance(r, KillSwitchEvent)]
        if triggered_events:
            # Return highest severity event
            return max(triggered_events, key=lambda e: severity_order[e.severity])

        return None

    async def activate_kill_switch(self, event: KillSwitchEvent) -> KillSwitchState:
        """Activate the kill switch based on a trigger event."""
        await self.initialize()

        # Get current state
        state = await self.state_manager.get_state()

        if state.is_active:
            # If already active, check if this is a higher severity event
            severity_order = {
                KillSwitchSeverity.CRITICAL: 4,
                KillSwitchSeverity.HIGH: 3,
                KillSwitchSeverity.MEDIUM: 2,
                KillSwitchSeverity.LOW: 1
            }

            if severity_order[event.severity] <= severity_order[state.severity]:
                logging.info(f"Kill switch already active with higher severity: {state.severity}")
                return state

        # Activate kill switch
        state.is_active = True
        state.activated_at = datetime.utcnow()
        state.activated_by = event.triggered_by
        state.reason = f"{event.trigger_type.value}: {event.details.get('reason', 'N/A')}"
        state.severity = event.severity

        # Add affected campaign
        if event.campaign_id:
            state.affected_campaigns.add(event.campaign_id)

        # Save state
        await self.state_manager.set_state(state)

        # Send notifications
        await self.notification_manager.notify_kill_switch_activation(event, state)

        # Log activation
        logging.critical(f"KILL SWITCH ACTIVATED: {event.trigger_type.value} - {event.severity.value}")

        return state

    async def deactivate_kill_switch(self, reason: str = "Manual deactivation") -> KillSwitchState:
        """Deactivate the kill switch."""
        await self.initialize()

        state = await self.state_manager.get_state()
        if not state.is_active:
            return state

        # Deactivate
        state.is_active = False
        state.reason = reason

        # Clear affected campaigns
        state.affected_campaigns.clear()

        await self.state_manager.set_state(state)

        logging.info(f"KILL SWITCH DEACTIVATED: {reason}")
        return state

    async def manual_kill_switch(self, action: KillSwitchAction) -> KillSwitchState:
        """Manually trigger kill switch actions."""
        await self.initialize()

        # Create manual event
        event = KillSwitchEvent(
            trigger_type=KillSwitchTrigger.MANUAL_OVERRIDE,
            severity={
                'terminate': KillSwitchSeverity.CRITICAL,
                'pause': KillSwitchSeverity.HIGH,
                'alert': KillSwitchSeverity.MEDIUM,
                'quarantine': KillSwitchSeverity.MEDIUM
            }.get(action.action, KillSwitchSeverity.MEDIUM),
            campaign_id=action.campaign_id,
            details={'reason': action.reason, 'action': action.action},
            triggered_by=action.triggered_by
        )

        # Handle different actions
        if action.action == 'terminate':
            return await self.activate_kill_switch(event)
        elif action.action == 'pause':
            # Add to kill list but don't fully activate
            await self.state_manager.add_campaign_to_kill_list(action.campaign_id)
            logging.warning(f"Campaign {action.campaign_id} paused: {action.reason}")
        elif action.action == 'resume':
            await self.state_manager.remove_campaign_from_kill_list(action.campaign_id)
            logging.info(f"Campaign {action.campaign_id} resumed")

        return await self.state_manager.get_state()

    async def check_campaign_status(self, campaign_id: str) -> Dict:
        """Check if a campaign is affected by kill switch."""
        await self.initialize()

        state = await self.state_manager.get_state()
        is_killed = campaign_id in state.affected_campaigns

        return {
            'campaign_id': campaign_id,
            'is_killed': is_killed,
            'global_kill_active': state.is_active,
            'kill_reason': state.reason if state.is_active else None,
            'severity': state.severity.value if state.is_active else None
        }

    async def emergency_terminate_campaign(self, campaign_id: str, reason: str) -> bool:
        """Emergency terminate a specific campaign."""
        action = KillSwitchAction(
            campaign_id=campaign_id,
            action='terminate',
            reason=reason,
            triggered_by='emergency_system',
            priority='critical'
        )

        state = await self.manual_kill_switch(action)
        return campaign_id in state.affected_campaigns

    async def emergency_terminate_all(self, reason: str) -> KillSwitchState:
        """Emergency terminate all campaigns (global kill switch)."""
        event = KillSwitchEvent(
            trigger_type=KillSwitchTrigger.MANUAL_OVERRIDE,
            severity=KillSwitchSeverity.CRITICAL,
            details={'reason': reason, 'action': 'global_terminate'},
            triggered_by='emergency_system'
        )

        return await self.activate_kill_switch(event)

# ===========================================
# FASTAPI INTEGRATION
# ===========================================

from fastapi import APIRouter, HTTPException, BackgroundTasks

def create_kill_switch_router(kill_switch: KillSwitchSystem) -> APIRouter:
    """Create FastAPI router for kill switch endpoints."""

    router = APIRouter(prefix="/api/v1/emergency", tags=["emergency"])

    @router.post("/kill-switch/{campaign_id}")
    async def activate_campaign_kill_switch(
        campaign_id: str,
        action: KillSwitchAction,
        background_tasks: BackgroundTasks
    ):
        """Activate kill switch for a specific campaign."""
        try:
            action.campaign_id = campaign_id
            state = await kill_switch.manual_kill_switch(action)

            # Add background notification task
            background_tasks.add_task(
                kill_switch.notification_manager.notify_kill_switch_activation,
                KillSwitchEvent(
                    trigger_type=KillSwitchTrigger.MANUAL_OVERRIDE,
                    severity=KillSwitchSeverity.HIGH,
                    campaign_id=campaign_id,
                    details={'action': action.action, 'reason': action.reason}
                ),
                state
            )

            return {
                "status": "success",
                "campaign_id": campaign_id,
                "action": action.action,
                "global_state": {
                    "is_active": state.is_active,
                    "severity": state.severity.value,
                    "affected_campaigns": list(state.affected_campaigns)
                }
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/global-stop")
    async def activate_global_kill_switch(action: KillSwitchAction):
        """Activate global kill switch."""
        try:
            state = await kill_switch.manual_kill_switch(action)
            return {
                "status": "success",
                "action": "global_stop",
                "state": {
                    "is_active": state.is_active,
                    "severity": state.severity.value,
                    "reason": state.reason
                }
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/status")
    async def get_kill_switch_status():
        """Get current kill switch status."""
        try:
            state = await kill_switch.state_manager.get_state()
            return {
                "is_active": state.is_active,
                "activated_at": state.activated_at.isoformat() if state.activated_at else None,
                "activated_by": state.activated_by,
                "reason": state.reason,
                "severity": state.severity.value,
                "affected_campaigns": list(state.affected_campaigns)
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/campaign/{campaign_id}/status")
    async def get_campaign_kill_status(campaign_id: str):
        """Check if a campaign is killed."""
        try:
            status = await kill_switch.check_campaign_status(campaign_id)
            return status
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router

# ===========================================
# UTILITY FUNCTIONS
# ===========================================

async def create_kill_switch_system(config: KillSwitchConfig = None) -> KillSwitchSystem:
    """Factory function to create and initialize kill switch system."""
    kill_switch = KillSwitchSystem(config)
    await kill_switch.initialize()
    return kill_switch

def setup_signal_handlers(kill_switch: KillSwitchSystem):
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logging.info(f"Received signal {signum}, initiating kill switch shutdown")
        asyncio.create_task(kill_switch.shutdown())

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

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
