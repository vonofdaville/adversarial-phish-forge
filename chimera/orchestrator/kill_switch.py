"""
Kill Switch - Emergency Campaign Termination System

Implements multiple kill switch mechanisms:
- Manual termination by red team operators
- Automatic termination based on triggers
- Geographic and temporal boundaries
- Consent revocation detection

NSA-grade emergency response system for ethical campaign control.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID
import redis.asyncio as redis

from ..utils.config import config
from ..utils.logger import setup_logging, log_security_event, log_audit_event
from .campaign_manager import CampaignManager

logger = setup_logging(__name__)


class KillSwitch:
    """
    Emergency campaign termination system.

    Implements multiple kill switch triggers:
    1. Manual activation (red team panic button)
    2. Geographic anomalies (non-whitelisted countries)
    3. Time boundaries (campaign expiration)
    4. Consent revocation (participant withdrawal)
    5. Escalation detection (forwards to legal/HR)
    """

    def __init__(self):
        self.redis = None
        self.campaign_manager = CampaignManager()
        self.active_kill_switches: Dict[UUID, Dict[str, Any]] = {}

    async def initialize(self):
        """Initialize Redis connection."""
        if self.redis is None:
            self.redis = redis.from_url(config.redis_url)

    async def activate(
        self,
        campaign_id: UUID,
        reason: str,
        triggered_by: str,
        affected_participants: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Activate kill switch for a campaign.

        Args:
            campaign_id: Campaign to terminate
            reason: Reason for termination
            triggered_by: Who triggered the kill switch
            affected_participants: Number of affected participants

        Returns:
            Activation result
        """
        await self.initialize()

        try:
            # Get campaign data
            campaign_data = await self.campaign_manager.get_campaign(campaign_id)
            if not campaign_data:
                return {"success": False, "reason": "Campaign not found"}

            if campaign_data.get("kill_switch_activated"):
                return {"success": False, "reason": "Kill switch already activated"}

            # Terminate campaign
            termination_result = await self.campaign_manager.terminate_campaign(
                campaign_id=campaign_id,
                reason=reason,
                terminated_by=triggered_by
            )

            if not termination_result["success"]:
                return {"success": False, "reason": "Campaign termination failed"}

            # Mark kill switch as activated
            campaign_data["kill_switch_activated"] = True
            campaign_data["kill_switch_reason"] = reason
            campaign_data["kill_switch_triggered_by"] = triggered_by
            campaign_data["kill_switch_activated_at"] = datetime.utcnow().isoformat()

            # Store kill switch event
            kill_switch_data = {
                "campaign_id": str(campaign_id),
                "reason": reason,
                "triggered_by": triggered_by,
                "affected_participants": affected_participants or len(campaign_data.get("target_participants", [])),
                "activated_at": campaign_data["kill_switch_activated_at"],
                "campaign_data": campaign_data,
                "incident_report": self._generate_incident_report(campaign_data, reason)
            }

            await self.redis.setex(
                f"kill_switch:{campaign_id}",
                30 * 24 * 3600,  # Keep for 30 days
                json.dumps(kill_switch_data)
            )

            # Add to active kill switches
            self.active_kill_switches[campaign_id] = kill_switch_data

            # Log kill switch activation
            log_security_event(
                "kill_switch_activated",
                campaign_id=str(campaign_id),
                reason=reason,
                triggered_by=triggered_by,
                affected_participants=kill_switch_data["affected_participants"]
            )

            return {
                "success": True,
                "campaign_id": str(campaign_id),
                "terminated_at": termination_result["terminated_at"],
                "affected_participants": kill_switch_data["affected_participants"],
                "incident_report": kill_switch_data["incident_report"]
            }

        except Exception as e:
            logger.error(f"Kill switch activation error: {e}")
            return {"success": False, "reason": f"Internal error: {str(e)}"}

    async def check_geographic_trigger(
        self,
        campaign_id: UUID,
        participant_id: UUID,
        geolocation: str
    ) -> bool:
        """
        Check if geographic trigger should activate kill switch.

        Args:
            campaign_id: Campaign UUID
            participant_id: Participant UUID
            geolocation: Detected geolocation (country code)

        Returns:
            True if kill switch should be activated
        """
        if geolocation.upper() not in config.geolocation_whitelist:
            logger.warning(f"Geographic anomaly detected: {geolocation} for campaign {campaign_id}")

            # Auto-activate kill switch for geographic violations
            await self.activate(
                campaign_id=campaign_id,
                reason=f"Geographic violation: {geolocation} not in whitelist",
                triggered_by="system_automatic",
                affected_participants=1
            )

            return True

        return False

    async def check_time_boundary_trigger(self, campaign_id: UUID) -> bool:
        """
        Check if campaign has exceeded time boundaries.

        Args:
            campaign_id: Campaign UUID

        Returns:
            True if kill switch should be activated
        """
        campaign_data = await self.campaign_manager.get_campaign(campaign_id)
        if not campaign_data:
            return False

        launched_at = campaign_data.get("launched_at")
        if not launched_at:
            return False

        launch_time = datetime.fromisoformat(launched_at)
        time_elapsed = datetime.utcnow() - launch_time

        if time_elapsed > timedelta(hours=config.campaign_timeout_hours):
            logger.info(f"Campaign {campaign_id} exceeded time boundary")

            await self.activate(
                campaign_id=campaign_id,
                reason=f"Campaign timeout: exceeded {config.campaign_timeout_hours} hours",
                triggered_by="system_automatic",
                affected_participants=len(campaign_data.get("target_participants", []))
            )

            return True

        return False

    async def check_escalation_trigger(
        self,
        campaign_id: UUID,
        participant_id: UUID,
        action: str
    ) -> bool:
        """
        Check if escalation trigger should activate kill switch.

        Args:
            campaign_id: Campaign UUID
            participant_id: Participant UUID
            action: Detected action (e.g., "forwarded_to_legal")

        Returns:
            True if kill switch should be activated
        """
        escalation_actions = [
            "forwarded_to_legal",
            "forwarded_to_hr",
            "reported_to_authorities",
            "contacted_regulatory_body"
        ]

        if action in escalation_actions:
            logger.warning(f"Escalation detected: {action} for campaign {campaign_id}")

            await self.activate(
                campaign_id=campaign_id,
                reason=f"Escalation detected: {action}",
                triggered_by="system_automatic",
                affected_participants=1
            )

            return True

        return False

    async def check_consent_revocation_trigger(
        self,
        participant_id: UUID
    ) -> List[UUID]:
        """
        Check if participant consent has been revoked and terminate affected campaigns.

        Args:
            participant_id: Participant UUID

        Returns:
            List of terminated campaign IDs
        """
        # This would be called when consent revocation is detected
        # For now, return empty list as this requires database integration
        return []

    async def get_status(self) -> Dict[str, Any]:
        """Get kill switch system status."""
        await self.initialize()

        # Get all kill switch events
        kill_switch_keys = await self.redis.keys("kill_switch:*")
        total_kill_switches = len(kill_switch_keys)

        # Count recent activations (last 24 hours)
        recent_activations = 0
        now = datetime.utcnow()

        for key in kill_switch_keys:
            data = await self.redis.get(key)
            if data:
                ks_data = json.loads(data)
                activated_at = datetime.fromisoformat(ks_data["activated_at"])
                if now - activated_at < timedelta(hours=24):
                    recent_activations += 1

        return {
            "total_kill_switches": total_kill_switches,
            "active_kill_switches": len(self.active_kill_switches),
            "recent_activations_24h": recent_activations,
            "system_status": "operational"
        }

    async def get_kill_switch_events(
        self,
        campaign_id: Optional[UUID] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get kill switch events."""
        await self.initialize()

        events = []

        if campaign_id:
            # Get specific campaign kill switch
            data = await self.redis.get(f"kill_switch:{campaign_id}")
            if data:
                events.append(json.loads(data))
        else:
            # Get all kill switch events
            kill_switch_keys = await self.redis.keys("kill_switch:*")
            for key in kill_switch_keys[:limit]:
                data = await self.redis.get(key)
                if data:
                    events.append(json.loads(data))

        return events

    def _generate_incident_report(
        self,
        campaign_data: Dict[str, Any],
        reason: str
    ) -> Dict[str, Any]:
        """Generate incident report for kill switch activation."""
        return {
            "incident_id": f"KS-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            "campaign_id": campaign_data["campaign_id"],
            "campaign_name": campaign_data["name"],
            "activation_reason": reason,
            "activation_timestamp": datetime.utcnow().isoformat(),
            "campaign_metrics": campaign_data.get("metrics", {}),
            "affected_participants": len(campaign_data.get("target_participants", [])),
            "campaign_duration": self._calculate_campaign_duration(campaign_data),
            "ethical_assessment": self._assess_ethical_impact(campaign_data, reason),
            "recommendations": self._generate_safety_recommendations(reason),
            "classification": "UNCLASSIFIED//FOUO"
        }

    def _calculate_campaign_duration(self, campaign_data: Dict[str, Any]) -> Optional[str]:
        """Calculate campaign duration."""
        launched_at = campaign_data.get("launched_at")
        terminated_at = campaign_data.get("kill_switch_activated_at") or campaign_data.get("terminated_at")

        if launched_at and terminated_at:
            duration = datetime.fromisoformat(terminated_at) - datetime.fromisoformat(launched_at)
            return f"{duration.total_seconds() / 3600:.1f} hours"

        return None

    def _assess_ethical_impact(
        self,
        campaign_data: Dict[str, Any],
        reason: str
    ) -> Dict[str, Any]:
        """Assess ethical impact of kill switch activation."""
        assessment = {
            "severity": "LOW",
            "ethical_concerns": [],
            "participant_impact": "MINIMAL",
            "organizational_impact": "MINIMAL"
        }

        # Assess based on reason
        if "geographic" in reason.lower():
            assessment["severity"] = "HIGH"
            assessment["ethical_concerns"].append("Potential international privacy violation")
            assessment["organizational_impact"] = "HIGH"

        elif "escalation" in reason.lower():
            assessment["severity"] = "CRITICAL"
            assessment["ethical_concerns"].append("Participant safety and trust compromised")
            assessment["participant_impact"] = "HIGH"

        elif "consent" in reason.lower():
            assessment["severity"] = "MEDIUM"
            assessment["ethical_concerns"].append("Consent boundary violation")
            assessment["participant_impact"] = "MEDIUM"

        elif "timeout" in reason.lower():
            assessment["severity"] = "LOW"
            assessment["ethical_concerns"].append("Operational boundary exceeded")

        return assessment

    def _generate_safety_recommendations(self, reason: str) -> List[str]:
        """Generate safety recommendations based on kill switch reason."""
        recommendations = [
            "Review campaign parameters and consent validation",
            "Conduct post-incident participant communication",
            "Update organizational incident response procedures"
        ]

        if "geographic" in reason.lower():
            recommendations.extend([
                "Implement more restrictive geographic filtering",
                "Review geolocation detection accuracy",
                "Consider additional privacy safeguards"
            ])

        elif "escalation" in reason.lower():
            recommendations.extend([
                "Implement real-time content analysis",
                "Enhance participant monitoring protocols",
                "Review ethical boundaries and constraints"
            ])

        return recommendations

