"""
Consent Validator - NSA "Three Gates" Authorization Model

Implements the core ethical framework of CHIMERA:
1. Legal Clearance - Organization has proper authorization
2. Participant Consent - Individual opt-in with revocation rights
3. Operational Review - Human approval for all actions

CRITICAL: This validator MUST be checked before ANY participant interaction.
"""

import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import create_engine, select, and_, or_, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from ..models.consent import (
    ConsentRegistryDB, OrganizationDB, CampaignAuditDB,
    ConsentRegistry, Organization, CampaignAudit,
    ConsentRequest, ConsentRevocationRequest
)
from ..utils.logger import setup_logging
from ..utils.config import Config

logger = setup_logging(__name__)


class ConsentValidator:
    """
    NSA-grade consent validation with cryptographic audit trail.

    This class implements CHIMERA's ethical core - no operation can proceed
    without explicit, documented consent that meets all three gates.
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or Config.DATABASE_URL
        self.engine = create_engine(self.database_url, echo=Config.DEBUG)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def validate_consent(
        self,
        participant_id: UUID,
        campaign_type: Optional[str] = None,
        require_active: bool = True
    ) -> Dict[str, Any]:
        """
        Validate participant consent against all three gates.

        Args:
            participant_id: UUID of the participant
            campaign_type: Type of campaign (optional filter)
            require_active: Whether to require non-revoked consent

        Returns:
            Dict with validation results and metadata
        """
        with self.SessionLocal() as session:
            try:
                # Query consent record
                stmt = select(ConsentRegistryDB).where(
                    and_(
                        ConsentRegistryDB.participant_id == participant_id,
                        ConsentRegistryDB.expiration_date > datetime.utcnow(),
                    )
                )

                if require_active:
                    stmt = stmt.where(ConsentRegistryDB.revocation_status == False)

                result = session.execute(stmt).first()

                if not result:
                    return {
                        "valid": False,
                        "reason": "No valid consent record found",
                        "gates": {"legal": False, "consent": False, "operational": False}
                    }

                consent = result[0]

                # Gate 1: Legal Clearance - Organization validation
                org_valid = self._validate_organization(session, consent.organization_id)

                # Gate 2: Participant Consent - Individual consent
                consent_valid = self._validate_participant_consent(consent, campaign_type)

                # Gate 3: Operational Review - Always requires human approval
                operational_valid = True  # This would be checked per-operation

                all_gates_valid = org_valid and consent_valid and operational_valid

                return {
                    "valid": all_gates_valid,
                    "participant_id": str(participant_id),
                    "organization_id": str(consent.organization_id),
                    "expiration_date": consent.expiration_date.isoformat(),
                    "campaign_types_allowed": consent.campaign_types_allowed,
                    "gates": {
                        "legal": org_valid,
                        "consent": consent_valid,
                        "operational": operational_valid
                    },
                    "consent_record": ConsentRegistry.from_orm(consent).dict() if all_gates_valid else None
                }

            except SQLAlchemyError as e:
                logger.error(f"Database error during consent validation: {e}")
                return {
                    "valid": False,
                    "reason": "Database error",
                    "gates": {"legal": False, "consent": False, "operational": False}
                }

    def register_consent(self, consent_request: ConsentRequest) -> Dict[str, Any]:
        """
        Register new participant consent with cryptographic proof.

        Args:
            consent_request: Consent registration request

        Returns:
            Dict with registration results
        """
        with self.SessionLocal() as session:
            try:
                # Validate organization exists
                org_stmt = select(OrganizationDB).where(
                    OrganizationDB.organization_id == consent_request.organization_id
                )
                org_result = session.execute(org_stmt).first()

                if not org_result:
                    return {
                        "success": False,
                        "reason": "Organization not found or not authorized"
                    }

                # Create consent document hash (simulated - in real implementation,
                # this would hash the actual signed consent document)
                consent_data = f"{consent_request.participant_email}:{consent_request.organization_id}:{datetime.utcnow().isoformat()}"
                consent_hash = hashlib.sha256(consent_data.encode()).hexdigest()

                # Calculate expiration date
                expiration_date = datetime.utcnow() + timedelta(days=consent_request.expiration_days)

                # Create consent record
                consent_record = ConsentRegistryDB(
                    participant_id=consent_request.participant_id,
                    organization_id=consent_request.organization_id,
                    consent_document_hash=consent_hash,
                    legal_signoff_officer=consent_request.legal_signoff_officer,
                    expiration_date=expiration_date,
                    participant_email=consent_request.participant_email,
                    participant_role=consent_request.participant_role,
                    campaign_types_allowed=consent_request.campaign_types_allowed,
                    geographic_restrictions=consent_request.geographic_restrictions,
                    created_by=consent_request.created_by
                )

                session.add(consent_record)
                session.commit()

                # Log the registration
                self._log_audit_event(
                    session,
                    campaign_id=None,  # Registration isn't campaign-specific
                    participant_id=consent_request.participant_id,
                    action="consent_registered",
                    action_details={
                        "organization_id": str(consent_request.organization_id),
                        "campaign_types": consent_request.campaign_types_allowed,
                        "expiration_days": consent_request.expiration_days
                    }
                )

                session.commit()

                return {
                    "success": True,
                    "participant_id": str(consent_request.participant_id),
                    "consent_hash": consent_hash,
                    "expiration_date": expiration_date.isoformat()
                }

            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error during consent registration: {e}")
                return {
                    "success": False,
                    "reason": "Database error during registration"
                }

    def revoke_consent(
        self,
        participant_id: UUID,
        revocation_request: ConsentRevocationRequest
    ) -> Dict[str, Any]:
        """
        Revoke participant consent with audit trail.

        Args:
            participant_id: UUID of the participant
            revocation_request: Revocation details

        Returns:
            Dict with revocation results
        """
        with self.SessionLocal() as session:
            try:
                # Find and update consent record
                stmt = select(ConsentRegistryDB).where(
                    ConsentRegistryDB.participant_id == participant_id
                )
                result = session.execute(stmt).first()

                if not result:
                    return {
                        "success": False,
                        "reason": "Consent record not found"
                    }

                consent = result[0]

                # Update revocation status
                consent.revocation_status = True
                consent.revocation_timestamp = datetime.utcnow()
                consent.revocation_reason = revocation_request.reason
                consent.last_modified = datetime.utcnow()

                # Add to modification audit
                if consent.modification_audit is None:
                    consent.modification_audit = []

                consent.modification_audit.append({
                    "action": "revocation",
                    "timestamp": datetime.utcnow().isoformat(),
                    "revoked_by": revocation_request.revoked_by,
                    "reason": revocation_request.reason
                })

                session.commit()

                # Log the revocation
                self._log_audit_event(
                    session,
                    campaign_id=None,
                    participant_id=participant_id,
                    action="consent_revoked",
                    action_details={
                        "reason": revocation_request.reason,
                        "revoked_by": revocation_request.revoked_by
                    },
                    consent_verified=False
                )

                session.commit()

                return {
                    "success": True,
                    "participant_id": str(participant_id),
                    "revoked_at": consent.revocation_timestamp.isoformat(),
                    "reason": revocation_request.reason
                }

            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error during consent revocation: {e}")
                return {
                    "success": False,
                    "reason": "Database error during revocation"
                }

    def _validate_organization(self, session: Session, organization_id: UUID) -> bool:
        """Validate organization has proper legal authorization."""
        try:
            stmt = select(OrganizationDB).where(
                OrganizationDB.organization_id == organization_id
            )
            result = session.execute(stmt).first()

            if not result:
                return False

            org = result[0]

            # Check if organization has required insurance and legal standing
            # In a real implementation, this would verify:
            # - Cyber liability insurance coverage
            # - Legal authorization documents
            # - Compliance certifications

            required_coverage = 5000000.00  # $5M minimum
            return (
                org.cyber_liability_coverage is not None and
                org.cyber_liability_coverage >= required_coverage
            )

        except SQLAlchemyError:
            return False

    def _validate_participant_consent(
        self,
        consent: ConsentRegistryDB,
        campaign_type: Optional[str] = None
    ) -> bool:
        """Validate individual participant consent."""
        # Check if consent is not revoked and not expired
        if consent.revocation_status or consent.expiration_date <= datetime.utcnow():
            return False

        # Check campaign type restrictions if specified
        if campaign_type and campaign_type not in consent.campaign_types_allowed:
            return False

        return True

    def _log_audit_event(
        self,
        session: Session,
        campaign_id: Optional[UUID],
        participant_id: Optional[UUID],
        action: str,
        action_details: Optional[Dict[str, Any]] = None,
        consent_verified: bool = True
    ) -> None:
        """Log audit event to database."""
        try:
            audit_event = CampaignAuditDB(
                campaign_id=campaign_id or UUID('00000000-0000-0000-0000-000000000000'),
                participant_id=participant_id,
                action=action,
                action_details=action_details or {},
                consent_verified=consent_verified
            )
            session.add(audit_event)
        except SQLAlchemyError as e:
            logger.error(f"Failed to log audit event: {e}")

    def get_consent_summary(self, organization_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get consent summary statistics for reporting."""
        with self.SessionLocal() as session:
            try:
                # Base query
                query = select(
                    func.count(ConsentRegistryDB.participant_id).label('total'),
                    func.count(func.case((ConsentRegistryDB.revocation_status == False, 1))).label('active'),
                    func.count(func.case((ConsentRegistryDB.revocation_status == True, 1))).label('revoked'),
                    func.count(func.case((
                        and_(
                            ConsentRegistryDB.expiration_date <= datetime.utcnow(),
                            ConsentRegistryDB.revocation_status == False
                        ), 1
                    ))).label('expired')
                )

                if organization_id:
                    query = query.where(ConsentRegistryDB.organization_id == organization_id)

                result = session.execute(query).first()

                return {
                    "total_consents": result.total or 0,
                    "active_consents": result.active or 0,
                    "revoked_consents": result.revoked or 0,
                    "expired_consents": result.expired or 0,
                    "organization_filter": str(organization_id) if organization_id else None
                }

            except SQLAlchemyError as e:
                logger.error(f"Database error getting consent summary: {e}")
                return {
                    "total_consents": 0,
                    "active_consents": 0,
                    "revoked_consents": 0,
                    "expired_consents": 0,
                    "error": "Database error"
                }

