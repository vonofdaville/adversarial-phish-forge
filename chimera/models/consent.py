"""
Consent Database Models

Implements the NSA "Three Gates" authorization model:
1. Legal Clearance
2. Participant Consent
3. Operational Review
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, DECIMAL, JSON, ARRAY, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, EmailStr, Field, validator

Base = declarative_base()

# SQLAlchemy Models

class ConsentRegistryDB(Base):
    """NSA-style consent registry with cryptographic audit trail."""
    __tablename__ = "consent_registry"

    participant_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(PGUUID(as_uuid=True), nullable=False)
    consent_timestamp = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    consent_document_hash = Column(String(64), nullable=False)  # SHA256 hash
    legal_signoff_officer = Column(String(255))
    expiration_date = Column(TIMESTAMP(timezone=True), nullable=False)
    revocation_status = Column(Boolean, default=False)
    revocation_timestamp = Column(TIMESTAMP(timezone=True))
    revocation_reason = Column(Text)

    # Audit trail
    created_by = Column(String(255))
    classification_level = Column(String(50), default="UNCLASSIFIED//FOUO")
    last_modified = Column(TIMESTAMP(timezone=True), default=func.now())
    modification_audit = Column(JSONB, default=list)

    # Additional metadata
    participant_email = Column(String(255))
    participant_role = Column(String(100))
    campaign_types_allowed = Column(ARRAY(String), default=list)
    geographic_restrictions = Column(ARRAY(String), default=list)
    contact_preferences = Column(JSONB, default=dict)


class OrganizationDB(Base):
    """Organization entity with legal compliance metadata."""
    __tablename__ = "organizations"

    organization_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_name = Column(String(255), nullable=False)
    legal_entity_name = Column(String(255))
    primary_contact_email = Column(String(255))
    primary_contact_phone = Column(String(50))
    insurance_policy_number = Column(String(100))
    cyber_liability_coverage = Column(DECIMAL(15, 2))
    created_at = Column(TIMESTAMP(timezone=True), default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now())


class CampaignAuditDB(Base):
    """Comprehensive audit log for all campaign actions."""
    __tablename__ = "campaign_audit_log"

    audit_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    campaign_id = Column(PGUUID(as_uuid=True), nullable=False)
    participant_id = Column(PGUUID(as_uuid=True))
    action = Column(String(100), nullable=False)
    action_timestamp = Column(TIMESTAMP(timezone=True), default=func.now())
    action_details = Column(JSONB)
    ip_address = Column(String(45))  # Support IPv4 and IPv6
    user_agent = Column(Text)
    consent_verified = Column(Boolean, default=True)


class KillSwitchEventDB(Base):
    """Kill switch activation events with incident reporting."""
    __tablename__ = "kill_switch_events"

    event_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    campaign_id = Column(PGUUID(as_uuid=True), nullable=False)
    trigger_reason = Column(String(100), nullable=False)
    trigger_timestamp = Column(TIMESTAMP(timezone=True), default=func.now())
    triggered_by = Column(String(255))
    affected_participants = Column(Integer)
    incident_report = Column(JSONB)


class EthicsIncidentDB(Base):
    """Ethics hotline incident tracking."""
    __tablename__ = "ethics_incidents"

    incident_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    reporter_email = Column(String(255))
    incident_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    severity_level = Column(String(20), default="MEDIUM")
    reported_at = Column(TIMESTAMP(timezone=True), default=func.now())
    resolved_at = Column(TIMESTAMP(timezone=True))
    resolution_notes = Column(Text)
    escalation_required = Column(Boolean, default=False)

# Pydantic Models for API

class ConsentRegistry(BaseModel):
    """Pydantic model for consent registry operations."""
    participant_id: UUID = Field(default_factory=uuid4)
    organization_id: UUID
    consent_document_hash: str = Field(..., min_length=64, max_length=64)
    legal_signoff_officer: Optional[str] = None
    expiration_date: datetime
    participant_email: EmailStr
    participant_role: str
    campaign_types_allowed: List[str] = Field(default_factory=list)
    geographic_restrictions: List[str] = Field(default_factory=list)
    contact_preferences: Dict[str, Any] = Field(default_factory=dict)
    created_by: str

    @validator('consent_document_hash')
    def validate_hash(cls, v):
        if len(v) != 64 or not all(c in '0123456789abcdef' for c in v.lower()):
            raise ValueError('Must be a valid SHA256 hash')
        return v.lower()

    class Config:
        from_attributes = True


class Organization(BaseModel):
    """Pydantic model for organization operations."""
    organization_id: UUID = Field(default_factory=uuid4)
    organization_name: str
    legal_entity_name: Optional[str] = None
    primary_contact_email: EmailStr
    primary_contact_phone: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    cyber_liability_coverage: Optional[float] = None

    class Config:
        from_attributes = True


class CampaignAudit(BaseModel):
    """Pydantic model for audit logging."""
    audit_id: UUID = Field(default_factory=uuid4)
    campaign_id: UUID
    participant_id: Optional[UUID] = None
    action: str
    action_details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    consent_verified: bool = True

    class Config:
        from_attributes = True


class KillSwitchEvent(BaseModel):
    """Pydantic model for kill switch events."""
    event_id: UUID = Field(default_factory=uuid4)
    campaign_id: UUID
    trigger_reason: str
    triggered_by: str
    affected_participants: Optional[int] = None
    incident_report: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class EthicsIncident(BaseModel):
    """Pydantic model for ethics incidents."""
    incident_id: UUID = Field(default_factory=uuid4)
    reporter_email: Optional[EmailStr] = None
    incident_type: str
    description: str
    severity_level: str = "MEDIUM"
    resolution_notes: Optional[str] = None
    escalation_required: bool = False

    class Config:
        from_attributes = True


# Request/Response Models

class ConsentRequest(BaseModel):
    """Request model for creating consent records."""
    organization_id: UUID
    participant_email: EmailStr
    participant_role: str
    campaign_types_allowed: List[str]
    geographic_restrictions: List[str] = Field(default_factory=lambda: ["US", "CA", "GB", "DE"])
    expiration_days: int = 365
    legal_signoff_officer: str
    created_by: str


class ConsentRevocationRequest(BaseModel):
    """Request model for revoking consent."""
    reason: str
    revoked_by: str


class EthicsReportRequest(BaseModel):
    """Request model for ethics hotline reports."""
    incident_type: str
    description: str
    severity_level: str = "MEDIUM"
    reporter_email: Optional[EmailStr] = None

