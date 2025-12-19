"""
Campaign Manager - Lifecycle Management for CHIMERA Campaigns

Manages the complete lifecycle of adversarial campaigns:
- Creation and validation
- Queue-based execution
- Real-time monitoring
- Adaptive evolution based on feedback

Implements ethical constraints and consent validation at every step.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
import redis.asyncio as redis

from ..utils.config import config
from ..utils.logger import setup_logging, log_security_event, log_audit_event
from .consent_validator import ConsentValidator

logger = setup_logging(__name__)


class CampaignManager:
    """
    Manages adversarial campaigns with ethical constraints.

    Implements the campaign lifecycle:
    1. Creation (with consent validation)
    2. Approval (human oversight)
    3. Execution (queue-based)
    4. Monitoring (real-time)
    5. Evolution (adaptive learning)
    6. Termination (kill switch)
    """

    def __init__(self):
        self.redis = None
        self.consent_validator = ConsentValidator()
        self.active_campaigns: Dict[UUID, Dict[str, Any]] = {}

    async def initialize(self):
        """Initialize Redis connection."""
        if self.redis is None:
            self.redis = redis.from_url(config.redis_url)

    async def create_campaign(
        self,
        name: str,
        description: Optional[str],
        campaign_type: str,
        target_participants: List[UUID],
        pretext_template: Optional[str],
        ethical_constraints: Dict[str, bool],
        created_by: str
    ) -> UUID:
        """
        Create a new campaign with consent validation.

        Args:
            name: Campaign name
            description: Campaign description
            campaign_type: Type of campaign (phishing, vishing, etc.)
            target_participants: List of participant UUIDs
            pretext_template: Pretext template to use
            ethical_constraints: Ethical constraints to apply
            created_by: User who created the campaign

        Returns:
            Campaign UUID

        Raises:
            ValueError: If campaign creation fails
        """
        await self.initialize()

        campaign_id = uuid4()

        # Validate all participants have consent
        validated_participants = []
        for participant_id in target_participants:
            consent_result = self.consent_validator.validate_consent(
                participant_id=participant_id,
                campaign_type=campaign_type
            )

            if not consent_result["valid"]:
                raise ValueError(f"Consent validation failed for participant {participant_id}")

            validated_participants.append({
                "participant_id": participant_id,
                "organization_id": consent_result.get("organization_id"),
                "consent_hash": consent_result.get("consent_record", {}).get("consent_document_hash")
            })

        # Create campaign record
        campaign_data = {
            "campaign_id": str(campaign_id),
            "name": name,
            "description": description,
            "campaign_type": campaign_type,
            "status": "created",
            "target_participants": [p["participant_id"] for p in validated_participants],
            "validated_participants": validated_participants,
            "pretext_template": pretext_template,
            "ethical_constraints": ethical_constraints,
            "created_by": created_by,
            "created_at": datetime.utcnow().isoformat(),
            "requires_approval": True,
            "approved_by": None,
            "approved_at": None,
            "launched_at": None,
            "completed_at": None,
            "kill_switch_activated": False,
            "metrics": {
                "emails_sent": 0,
                "emails_opened": 0,
                "links_clicked": 0,
                "credentials_submitted": 0,
                "reports_to_security": 0
            },
            "evolution_data": {
                "adaptations_made": 0,
                "success_rate": 0.0,
                "last_adaptation": None
            }
        }

        # Store in Redis
        await self.redis.setex(
            f"campaign:{campaign_id}",
            config.campaign_timeout_hours * 3600,  # Auto-expire
            json.dumps(campaign_data)
        )

        # Add to active campaigns
        self.active_campaigns[campaign_id] = campaign_data

        logger.info(f"Campaign created: {campaign_id}")
        return campaign_id

    async def approve_campaign(
        self,
        campaign_id: UUID,
        approved_by: str
    ) -> Dict[str, Any]:
        """
        Approve a campaign for execution.

        Args:
            campaign_id: Campaign UUID
            approved_by: User who approved the campaign

        Returns:
            Approval result
        """
        await self.initialize()

        # Get campaign data
        campaign_data = await self._get_campaign_data(campaign_id)
        if not campaign_data:
            return {"success": False, "reason": "Campaign not found"}

        if campaign_data["status"] != "created":
            return {"success": False, "reason": "Campaign not in created status"}

        # Update campaign status
        campaign_data["status"] = "approved"
        campaign_data["approved_by"] = approved_by
        campaign_data["approved_at"] = datetime.utcnow().isoformat()

        # Store updated data
        await self.redis.setex(
            f"campaign:{campaign_id}",
            config.campaign_timeout_hours * 3600,
            json.dumps(campaign_data)
        )

        # Update active campaigns
        self.active_campaigns[campaign_id] = campaign_data

        log_security_event(
            "campaign_approved",
            campaign_id=str(campaign_id),
            approved_by=approved_by
        )

        return {"success": True, "approved_at": campaign_data["approved_at"]}

    async def launch_campaign(self, campaign_id: UUID):
        """
        Launch an approved campaign.

        Args:
            campaign_id: Campaign UUID
        """
        await self.initialize()

        try:
            # Get campaign data
            campaign_data = await self._get_campaign_data(campaign_id)
            if not campaign_data:
                logger.error(f"Campaign not found for launch: {campaign_id}")
                return

            if campaign_data["status"] != "approved":
                logger.error(f"Campaign not approved for launch: {campaign_id}")
                return

            # Update status to launching
            campaign_data["status"] = "launching"
            campaign_data["launched_at"] = datetime.utcnow().isoformat()

            await self.redis.setex(
                f"campaign:{campaign_id}",
                config.campaign_timeout_hours * 3600,
                json.dumps(campaign_data)
            )

            # Queue campaign execution tasks
            await self._queue_campaign_tasks(campaign_id, campaign_data)

            # Update status to active
            campaign_data["status"] = "active"
            await self.redis.setex(
                f"campaign:{campaign_id}",
                config.campaign_timeout_hours * 3600,
                json.dumps(campaign_data)
            )

            # Update active campaigns
            self.active_campaigns[campaign_id] = campaign_data

            log_security_event(
                "campaign_launched",
                campaign_id=str(campaign_id),
                participant_count=len(campaign_data["target_participants"])
            )

            # Start monitoring task
            asyncio.create_task(self._monitor_campaign(campaign_id))

        except Exception as e:
            logger.error(f"Campaign launch failed: {e}")
            await self._fail_campaign(campaign_id, str(e))

    async def _queue_campaign_tasks(self, campaign_id: UUID, campaign_data: Dict[str, Any]):
        """Queue individual campaign execution tasks."""
        # Queue pretext generation tasks
        for participant in campaign_data["validated_participants"]:
            task_data = {
                "campaign_id": str(campaign_id),
                "participant_id": str(participant["participant_id"]),
                "campaign_type": campaign_data["campaign_type"],
                "pretext_template": campaign_data["pretext_template"],
                "ethical_constraints": campaign_data["ethical_constraints"]
            }

            await self.redis.lpush("campaign_queue", json.dumps(task_data))

        logger.info(f"Queued {len(campaign_data['validated_participants'])} tasks for campaign {campaign_id}")

    async def _monitor_campaign(self, campaign_id: UUID):
        """Monitor campaign progress and adapt as needed."""
        try:
            while True:
                # Get current campaign data
                campaign_data = await self._get_campaign_data(campaign_id)
                if not campaign_data:
                    break

                # Check for kill switch
                if campaign_data.get("kill_switch_activated"):
                    logger.info(f"Kill switch activated for campaign {campaign_id}")
                    break

                # Check campaign timeout
                launched_at = datetime.fromisoformat(campaign_data["launched_at"])
                if datetime.utcnow() - launched_at > timedelta(hours=config.campaign_timeout_hours):
                    logger.info(f"Campaign {campaign_id} timed out")
                    await self._complete_campaign(campaign_id, "timeout")
                    break

                # Check for completion
                if campaign_data["status"] == "completed":
                    break

                # Adaptive evolution logic
                await self._evolve_campaign(campaign_id, campaign_data)

                # Wait before next check
                await asyncio.sleep(60)  # Check every minute

        except Exception as e:
            logger.error(f"Campaign monitoring error: {e}")

    async def _evolve_campaign(self, campaign_id: UUID, campaign_data: Dict[str, Any]):
        """Implement adaptive campaign evolution based on telemetry."""
        # Get recent telemetry data
        telemetry_key = f"telemetry:{campaign_id}"
        recent_events = await self.redis.lrange(telemetry_key, 0, 100)  # Last 100 events

        if not recent_events:
            return

        # Analyze success patterns
        opened_count = 0
        clicked_count = 0
        reported_count = 0

        for event_json in recent_events:
            event = json.loads(event_json)
            if event.get("event_type") == "email_opened":
                opened_count += 1
            elif event.get("event_type") == "link_clicked":
                clicked_count += 1
            elif event.get("event_type") == "reported_to_security":
                reported_count += 1

        # Calculate success rate
        total_sent = len(campaign_data["target_participants"])
        success_rate = (opened_count + clicked_count) / max(total_sent, 1)

        # Evolution logic
        adaptations = []

        if success_rate > 0.5 and reported_count == 0:
            # High success, low detection - increase sophistication
            adaptations.append("increase_personalization")
            adaptations.append("add_urgency_elements")

        elif reported_count > total_sent * 0.1:
            # High detection rate - pivot to honeypot mode
            adaptations.append("convert_to_honeypot")
            adaptations.append("alert_blue_team")

        elif success_rate < 0.1:
            # Low engagement - try alternative approaches
            adaptations.append("change_pretext_angle")
            adaptations.append("modify_timing")

        # Apply adaptations
        if adaptations:
            campaign_data["evolution_data"]["adaptations_made"] += len(adaptations)
            campaign_data["evolution_data"]["success_rate"] = success_rate
            campaign_data["evolution_data"]["last_adaptation"] = datetime.utcnow().isoformat()

            # Store updated campaign data
            await self.redis.setex(
                f"campaign:{campaign_id}",
                config.campaign_timeout_hours * 3600,
                json.dumps(campaign_data)
            )

            log_audit_event(
                "campaign_evolution",
                campaign_id=str(campaign_id),
                adaptations=adaptations,
                success_rate=success_rate
            )

    async def terminate_campaign(
        self,
        campaign_id: UUID,
        reason: str,
        terminated_by: str
    ) -> Dict[str, Any]:
        """Terminate a campaign."""
        campaign_data = await self._get_campaign_data(campaign_id)
        if not campaign_data:
            return {"success": False, "reason": "Campaign not found"}

        campaign_data["status"] = "terminated"
        campaign_data["terminated_at"] = datetime.utcnow().isoformat()
        campaign_data["terminated_by"] = terminated_by
        campaign_data["termination_reason"] = reason

        # Store updated data
        await self.redis.setex(
            f"campaign:{campaign_id}",
            config.campaign_timeout_hours * 3600,
            json.dumps(campaign_data)
        )

        # Remove from active campaigns
        self.active_campaigns.pop(campaign_id, None)

        log_security_event(
            "campaign_terminated",
            campaign_id=str(campaign_id),
            terminated_by=terminated_by,
            reason=reason
        )

        return {"success": True, "terminated_at": campaign_data["terminated_at"]}

    async def get_campaign(self, campaign_id: UUID) -> Optional[Dict[str, Any]]:
        """Get campaign details."""
        return await self._get_campaign_data(campaign_id)

    async def get_statistics(self) -> Dict[str, Any]:
        """Get campaign statistics."""
        await self.initialize()

        # Get all campaign keys
        campaign_keys = await self.redis.keys("campaign:*")
        total_campaigns = len(campaign_keys)
        active_campaigns = len(self.active_campaigns)

        # Aggregate metrics
        total_emails_sent = 0
        total_opened = 0
        total_clicked = 0

        for campaign_data in self.active_campaigns.values():
            metrics = campaign_data.get("metrics", {})
            total_emails_sent += metrics.get("emails_sent", 0)
            total_opened += metrics.get("emails_opened", 0)
            total_clicked += metrics.get("links_clicked", 0)

        return {
            "total_campaigns": total_campaigns,
            "active_campaigns": active_campaigns,
            "total_emails_sent": total_emails_sent,
            "total_emails_opened": total_opened,
            "total_links_clicked": total_clicked,
            "average_open_rate": total_opened / max(total_emails_sent, 1),
            "average_click_rate": total_clicked / max(total_emails_sent, 1)
        }

    async def _get_campaign_data(self, campaign_id: UUID) -> Optional[Dict[str, Any]]:
        """Get campaign data from Redis."""
        await self.initialize()

        data = await self.redis.get(f"campaign:{campaign_id}")
        if data:
            return json.loads(data)

        # Check active campaigns cache
        return self.active_campaigns.get(campaign_id)

    async def _fail_campaign(self, campaign_id: UUID, reason: str):
        """Mark campaign as failed."""
        campaign_data = await self._get_campaign_data(campaign_id)
        if campaign_data:
            campaign_data["status"] = "failed"
            campaign_data["failure_reason"] = reason
            campaign_data["failed_at"] = datetime.utcnow().isoformat()

            await self.redis.setex(
                f"campaign:{campaign_id}",
                config.campaign_timeout_hours * 3600,
                json.dumps(campaign_data)
            )

    async def _complete_campaign(self, campaign_id: UUID, completion_reason: str):
        """Mark campaign as completed."""
        campaign_data = await self._get_campaign_data(campaign_id)
        if campaign_data:
            campaign_data["status"] = "completed"
            campaign_data["completed_at"] = datetime.utcnow().isoformat()
            campaign_data["completion_reason"] = completion_reason

            await self.redis.setex(
                f"campaign:{campaign_id}",
                config.campaign_timeout_hours * 3600,
                json.dumps(campaign_data)
            )

            # Remove from active campaigns
            self.active_campaigns.pop(campaign_id, None)

