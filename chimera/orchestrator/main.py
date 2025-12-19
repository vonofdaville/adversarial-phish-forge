"""
CHIMERA FastAPI Orchestrator

Central campaign management system implementing:
- Consent-enforced operations
- Queue-based campaign execution
- Real-time monitoring and control
- Ethical compliance validation

WARNING: This system is designed for AUTHORIZED RED TEAM OPERATIONS ONLY.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import redis.asyncio as redis
import uvicorn

from ..utils.config import config
from ..utils.logger import setup_logging, log_security_event, log_audit_event
from .consent_validator import ConsentValidator
from .campaign_manager import CampaignManager
from .kill_switch import KillSwitch

# Initialize logging
logger = setup_logging(__name__)

# Security scheme
security = HTTPBearer()

# Global instances
consent_validator = ConsentValidator()
campaign_manager = CampaignManager()
kill_switch = KillSwitch()

# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting CHIMERA Orchestrator")
    log_security_event("system_startup", service="orchestrator")

    # Initialize Redis connection
    app.state.redis = redis.from_url(config.redis_url)

    yield

    # Shutdown
    logger.info("Shutting down CHIMERA Orchestrator")
    log_security_event("system_shutdown", service="orchestrator")

    # Close Redis connection
    if hasattr(app.state, 'redis'):
        await app.state.redis.close()

# FastAPI app
app = FastAPI(
    title="CHIMERA Orchestrator",
    description="Cognitive Heuristic Intelligence for Multi-stage Engagement Research & Assessment",
    version=config.app_version,
    lifespan=lifespan,
    docs_url="/docs" if config.debug else None,
    redoc_url="/redoc" if config.debug else None,
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.chimera.local"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://chimera.local"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models

class ConsentValidationRequest(BaseModel):
    """Request model for consent validation."""
    participant_id: UUID
    campaign_type: Optional[str] = None


class ConsentRegistrationRequest(BaseModel):
    """Request model for consent registration."""
    participant_email: EmailStr
    participant_role: str
    campaign_types_allowed: List[str]
    geographic_restrictions: List[str] = ["US", "CA", "GB", "DE"]
    expiration_days: int = 365
    legal_signoff_officer: str
    created_by: str


class CampaignCreationRequest(BaseModel):
    """Request model for campaign creation."""
    name: str
    description: Optional[str] = None
    campaign_type: str
    target_participants: List[UUID]
    pretext_template: Optional[str] = None
    ethical_constraints: Dict[str, bool] = {
        "no_threats": True,
        "include_opt_out": True,
        "no_personal_data": True,
        "educational_content": True
    }
    created_by: str


class KillSwitchRequest(BaseModel):
    """Request model for kill switch activation."""
    campaign_id: UUID
    reason: str
    triggered_by: str
    affected_participants: Optional[int] = None


# Authentication dependency
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token (simplified for development)."""
    # In production, implement proper JWT validation
    # For now, accept any token as valid
    return credentials.credentials


# Routes

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "chimera-orchestrator",
        "version": config.app_version,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/consent/validate")
async def validate_consent(
    request: ConsentValidationRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_token)
):
    """Validate participant consent before any operation."""
    try:
        # Validate consent
        result = consent_validator.validate_consent(
            participant_id=request.participant_id,
            campaign_type=request.campaign_type
        )

        # Log the validation
        log_audit_event(
            action="consent_validation",
            participant_id=str(request.participant_id),
            campaign_type=request.campaign_type,
            result=result["valid"]
        )

        if not result["valid"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Consent validation failed",
                    "reason": result.get("reason"),
                    "gates": result.get("gates")
                }
            )

        return {
            "valid": True,
            "participant_id": str(request.participant_id),
            "organization_id": result.get("organization_id"),
            "expiration_date": result.get("expiration_date"),
            "campaign_types_allowed": result.get("campaign_types_allowed"),
            "gates": result.get("gates")
        }

    except Exception as e:
        logger.error(f"Consent validation error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/consent/register")
async def register_consent(
    request: ConsentRegistrationRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_token)
):
    """Register new participant consent."""
    try:
        # Register consent
        result = consent_validator.register_consent(request)

        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail={"error": "Consent registration failed", "reason": result.get("reason")}
            )

        # Log the registration
        log_security_event(
            "consent_registration",
            participant_id=result["participant_id"],
            organization_id=str(request.organization_id),
            campaign_types=request.campaign_types_allowed
        )

        return {
            "success": True,
            "participant_id": result["participant_id"],
            "consent_hash": result["consent_hash"],
            "expiration_date": result["expiration_date"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Consent registration error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/consent/revoke")
async def revoke_consent(
    participant_id: UUID,
    reason: str,
    revoked_by: str,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_token)
):
    """Revoke participant consent."""
    try:
        # Revoke consent
        result = consent_validator.revoke_consent(
            participant_id=participant_id,
            revocation_request={"reason": reason, "revoked_by": revoked_by}
        )

        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail={"error": "Consent revocation failed", "reason": result.get("reason")}
            )

        # Log the revocation
        log_security_event(
            "consent_revocation",
            participant_id=str(participant_id),
            reason=reason,
            revoked_by=revoked_by
        )

        return {
            "success": True,
            "participant_id": str(participant_id),
            "revoked_at": result["revoked_at"],
            "reason": result["reason"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Consent revocation error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/consent/summary")
async def get_consent_summary(
    organization_id: Optional[UUID] = None,
    token: str = Depends(verify_token)
):
    """Get consent summary statistics."""
    try:
        summary = consent_validator.get_consent_summary(organization_id)
        return summary
    except Exception as e:
        logger.error(f"Consent summary error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/campaigns")
async def create_campaign(
    request: CampaignCreationRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_token)
):
    """Create a new campaign with consent validation."""
    try:
        # Validate consent for all participants
        invalid_participants = []
        for participant_id in request.target_participants:
            result = consent_validator.validate_consent(
                participant_id=participant_id,
                campaign_type=request.campaign_type
            )
            if not result["valid"]:
                invalid_participants.append(str(participant_id))

        if invalid_participants:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Consent validation failed for participants",
                    "invalid_participants": invalid_participants
                }
            )

        # Create campaign
        campaign_id = await campaign_manager.create_campaign(
            name=request.name,
            description=request.description,
            campaign_type=request.campaign_type,
            target_participants=request.target_participants,
            pretext_template=request.pretext_template,
            ethical_constraints=request.ethical_constraints,
            created_by=request.created_by
        )

        # Log campaign creation
        log_security_event(
            "campaign_created",
            campaign_id=str(campaign_id),
            campaign_type=request.campaign_type,
            participant_count=len(request.target_participants),
            created_by=request.created_by
        )

        return {
            "campaign_id": str(campaign_id),
            "status": "created",
            "participant_count": len(request.target_participants),
            "requires_approval": True  # All campaigns require human approval
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Campaign creation error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: UUID,
    token: str = Depends(verify_token)
):
    """Get campaign details."""
    try:
        campaign = await campaign_manager.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        return campaign
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get campaign error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/campaigns/{campaign_id}/approve")
async def approve_campaign(
    campaign_id: UUID,
    approved_by: str,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_token)
):
    """Approve and launch a campaign."""
    try:
        # Approve campaign
        result = await campaign_manager.approve_campaign(
            campaign_id=campaign_id,
            approved_by=approved_by
        )

        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail={"error": "Campaign approval failed", "reason": result.get("reason")}
            )

        # Launch campaign in background
        background_tasks.add_task(campaign_manager.launch_campaign, campaign_id)

        # Log approval
        log_security_event(
            "campaign_approved",
            campaign_id=str(campaign_id),
            approved_by=approved_by
        )

        return {
            "success": True,
            "campaign_id": str(campaign_id),
            "status": "approved_and_launching"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Campaign approval error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/kill-switch")
async def activate_kill_switch(
    request: KillSwitchRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_token)
):
    """Activate kill switch for campaign."""
    try:
        # Activate kill switch
        result = await kill_switch.activate(
            campaign_id=request.campaign_id,
            reason=request.reason,
            triggered_by=request.triggered_by,
            affected_participants=request.affected_participants
        )

        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail={"error": "Kill switch activation failed", "reason": result.get("reason")}
            )

        # Log kill switch activation
        log_security_event(
            "kill_switch_activated",
            campaign_id=str(request.campaign_id),
            reason=request.reason,
            triggered_by=request.triggered_by,
            affected_participants=request.affected_participants
        )

        return {
            "success": True,
            "campaign_id": str(request.campaign_id),
            "terminated_at": result["terminated_at"],
            "affected_participants": result["affected_participants"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Kill switch activation error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/system/status")
async def get_system_status(token: str = Depends(verify_token)):
    """Get system status and health metrics."""
    try:
        # Get consent summary
        consent_summary = consent_validator.get_consent_summary()

        # Get campaign statistics
        campaign_stats = await campaign_manager.get_statistics()

        # Get kill switch status
        kill_switch_status = await kill_switch.get_status()

        return {
            "system": "chimera-orchestrator",
            "version": config.app_version,
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "consent_summary": consent_summary,
            "campaign_statistics": campaign_stats,
            "kill_switch_status": kill_switch_status
        }

    except Exception as e:
        logger.error(f"System status error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with logging."""
    log_security_event(
        "http_error",
        status_code=exc.status_code,
        detail=str(exc.detail),
        path=str(request.url.path)
    )
    return {"error": exc.detail, "status_code": exc.status_code}


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with logging."""
    logger.error(f"Unhandled exception: {exc}")
    log_security_event(
        "system_error",
        error=str(exc),
        path=str(request.url.path)
    )
    return {"error": "Internal server error", "status_code": 500}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.debug,
        log_level=config.log_level.lower()
    )

