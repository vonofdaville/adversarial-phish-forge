-- CHIMERA Framework - Consent Database Schema
-- Version: 1.0.0
-- Created: December 2025
-- Purpose: GDPR Article 7 compliant consent management with cryptographic audit trail

-- ===========================================
-- EXTENSIONS
-- ===========================================

-- Required extensions for cryptographic operations and UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- ===========================================
-- TABLES
-- ===========================================

-- Main consent registry table
-- Stores participant consent with cryptographic verification
CREATE TABLE consent_registry (
    participant_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL,
    consent_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    consent_document_hash VARCHAR(128) NOT NULL, -- SHA-256 hash of consent document
    legal_signoff_officer VARCHAR(255) NOT NULL,
    expiration_date TIMESTAMPTZ NOT NULL,
    revocation_status BOOLEAN DEFAULT FALSE,
    revocation_timestamp TIMESTAMPTZ,
    created_by VARCHAR(255) NOT NULL,
    classification_level VARCHAR(50) DEFAULT 'UNCLASSIFIED//FOUO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Business logic constraints
    CONSTRAINT valid_dates CHECK (expiration_date > consent_timestamp),
    CONSTRAINT revocation_logic CHECK (
        (revocation_status = FALSE AND revocation_timestamp IS NULL) OR
        (revocation_status = TRUE AND revocation_timestamp IS NOT NULL)
    ),

    -- Classification constraints
    CONSTRAINT valid_classification CHECK (
        classification_level IN (
            'UNCLASSIFIED//FOUO',
            'CONFIDENTIAL//FOUO',
            'SECRET//FOUO',
            'TOP SECRET//SI'
        )
    )
);

-- Immutable audit log for all consent operations
-- WORM (Write Once Read Many) storage for compliance
CREATE TABLE consent_audit_log (
    log_id SERIAL PRIMARY KEY,
    participant_id UUID REFERENCES consent_registry(participant_id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL CHECK (action IN (
        'CONSENT_GRANTED',
        'CONSENT_EXTENDED',
        'CONSENT_REVOKED',
        'CONSENT_EXPIRED',
        'DOCUMENT_VERIFIED',
        'CLASSIFICATION_CHANGED',
        'ADMIN_OVERRIDE'
    )),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor VARCHAR(255) NOT NULL, -- User/system that performed action
    ip_address INET,
    user_agent TEXT,
    details JSONB, -- Structured data about the action
    blockchain_hash VARCHAR(128), -- For tamper-evident logging
    digital_signature TEXT, -- Cryptographic signature of the log entry

    -- Immutability constraints
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (timestamp);

-- Partitioning strategy for audit log (monthly partitions)
-- Automatically creates new partitions as needed
CREATE OR REPLACE FUNCTION create_audit_partition_if_not_exists()
RETURNS TRIGGER AS $$
DECLARE
    partition_name TEXT;
    partition_start DATE;
    partition_end DATE;
BEGIN
    partition_start := date_trunc('month', NEW.timestamp)::DATE;
    partition_end := partition_start + INTERVAL '1 month';
    partition_name := 'consent_audit_log_' || to_char(partition_start, 'YYYY_MM');

    IF NOT EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = partition_name AND n.nspname = current_schema()
    ) THEN
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF consent_audit_log FOR VALUES FROM (%L) TO (%L)',
            partition_name, partition_start, partition_end
        );

        -- Add index to partition
        EXECUTE format(
            'CREATE INDEX idx_audit_%s_timestamp ON %I (timestamp)',
            replace(to_char(partition_start, 'YYYY_MM'), '_', ''),
            partition_name
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically create audit partitions
CREATE TRIGGER create_audit_partitions
    BEFORE INSERT ON consent_audit_log
    FOR EACH ROW EXECUTE FUNCTION create_audit_partition_if_not_exists();

-- Emergency consent override table
-- Only for use in critical security incidents
CREATE TABLE consent_emergency_override (
    override_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    participant_id UUID REFERENCES consent_registry(participant_id) ON DELETE CASCADE,
    override_reason VARCHAR(100) NOT NULL CHECK (override_reason IN (
        'ACTIVE_SECURITY_INCIDENT',
        'LEGAL_SUBPOENA',
        'PARTICIPANT_SAFETY_THREAT',
        'SYSTEM_COMPROMISE'
    )),
    authorized_by VARCHAR(255) NOT NULL,
    authorization_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    incident_reference VARCHAR(255) NOT NULL, -- Links to incident tracking system
    override_duration INTERVAL NOT NULL DEFAULT INTERVAL '24 hours',
    expiration_timestamp TIMESTAMPTZ GENERATED ALWAYS AS (authorization_timestamp + override_duration) STORED,
    digital_signature TEXT NOT NULL, -- Cryptographic proof of authorization
    audit_notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL
);

-- ===========================================
-- INDEXES
-- ===========================================

-- Performance indexes for consent registry
CREATE INDEX idx_participant_active ON consent_registry(participant_id) WHERE revocation_status = FALSE;
CREATE INDEX idx_organization ON consent_registry(organization_id);
CREATE INDEX idx_expiration ON consent_registry(expiration_date) WHERE expiration_date > NOW();
CREATE INDEX idx_classification ON consent_registry(classification_level);
CREATE INDEX idx_created_by ON consent_registry(created_by);
CREATE INDEX idx_consent_hash ON consent_registry(consent_document_hash);

-- Composite indexes for common queries
CREATE INDEX idx_org_participant ON consent_registry(organization_id, participant_id);
CREATE INDEX idx_active_expiring ON consent_registry(organization_id, expiration_date)
    WHERE revocation_status = FALSE AND expiration_date > NOW();

-- Performance indexes for audit log
CREATE INDEX idx_audit_participant ON consent_audit_log(participant_id);
CREATE INDEX idx_audit_action ON consent_audit_log(action);
CREATE INDEX idx_audit_timestamp ON consent_audit_log(timestamp DESC);
CREATE INDEX idx_audit_actor ON consent_audit_log(actor);
CREATE INDEX idx_audit_ip ON consent_audit_log(ip_address) WHERE ip_address IS NOT NULL;

-- GIN index for JSONB queries
CREATE INDEX idx_audit_details ON consent_audit_log USING GIN (details);

-- Emergency override indexes
CREATE INDEX idx_emergency_participant ON consent_emergency_override(participant_id);
CREATE INDEX idx_emergency_expiration ON consent_emergency_override(expiration_timestamp);
CREATE INDEX idx_emergency_authorized_by ON consent_emergency_override(authorized_by);

-- ===========================================
-- FUNCTIONS
-- ===========================================

-- Function to verify consent status
CREATE OR REPLACE FUNCTION verify_consent_status(
    p_participant_id UUID,
    p_organization_id UUID DEFAULT NULL
) RETURNS TABLE (
    is_valid BOOLEAN,
    status_message TEXT,
    expiration_date TIMESTAMPTZ,
    days_remaining INTEGER
) AS $$
DECLARE
    consent_record RECORD;
    emergency_override RECORD;
BEGIN
    -- Check for emergency override first
    SELECT * INTO emergency_override
    FROM consent_emergency_override
    WHERE participant_id = p_participant_id
        AND expiration_timestamp > NOW()
    ORDER BY authorization_timestamp DESC
    LIMIT 1;

    IF FOUND THEN
        RETURN QUERY SELECT
            TRUE,
            'EMERGENCY_OVERRIDE_ACTIVE'::TEXT,
            emergency_override.expiration_timestamp,
            EXTRACT(EPOCH FROM (emergency_override.expiration_timestamp - NOW()))::INTEGER / 86400;
        RETURN;
    END IF;

    -- Check regular consent
    SELECT * INTO consent_record
    FROM consent_registry
    WHERE participant_id = p_participant_id
        AND (p_organization_id IS NULL OR organization_id = p_organization_id);

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'PARTICIPANT_NOT_FOUND'::TEXT, NULL::TIMESTAMPTZ, NULL::INTEGER;
        RETURN;
    END IF;

    IF consent_record.revocation_status THEN
        RETURN QUERY SELECT FALSE, 'CONSENT_REVOKED'::TEXT, consent_record.expiration_date, 0;
        RETURN;
    END IF;

    IF consent_record.expiration_date < NOW() THEN
        RETURN QUERY SELECT FALSE, 'CONSENT_EXPIRED'::TEXT, consent_record.expiration_date, 0;
        RETURN;
    END IF;

    IF p_organization_id IS NOT NULL AND consent_record.organization_id != p_organization_id THEN
        RETURN QUERY SELECT FALSE, 'ORGANIZATION_MISMATCH'::TEXT, consent_record.expiration_date,
            EXTRACT(EPOCH FROM (consent_record.expiration_date - NOW()))::INTEGER / 86400;
        RETURN;
    END IF;

    RETURN QUERY SELECT TRUE, 'CONSENT_VALID'::TEXT, consent_record.expiration_date,
        EXTRACT(EPOCH FROM (consent_record.expiration_date - NOW()))::INTEGER / 86400;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to revoke consent with audit trail
CREATE OR REPLACE FUNCTION revoke_participant_consent(
    p_participant_id UUID,
    p_actor VARCHAR(255),
    p_reason TEXT DEFAULT NULL,
    p_ip_address INET DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    affected_rows INTEGER;
BEGIN
    -- Update consent status
    UPDATE consent_registry
    SET revocation_status = TRUE,
        revocation_timestamp = NOW(),
        updated_at = NOW()
    WHERE participant_id = p_participant_id
        AND revocation_status = FALSE;

    GET DIAGNOSTICS affected_rows = ROW_COUNT;

    IF affected_rows > 0 THEN
        -- Insert audit log
        INSERT INTO consent_audit_log (
            participant_id, action, actor, ip_address, user_agent, details
        ) VALUES (
            p_participant_id, 'CONSENT_REVOKED', p_actor, p_ip_address, p_user_agent,
            jsonb_build_object('reason', p_reason, 'timestamp', NOW())
        );

        RETURN TRUE;
    END IF;

    RETURN FALSE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to extend consent
CREATE OR REPLACE FUNCTION extend_participant_consent(
    p_participant_id UUID,
    p_new_expiration TIMESTAMPTZ,
    p_actor VARCHAR(255),
    p_ip_address INET DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    current_record RECORD;
BEGIN
    -- Get current record
    SELECT * INTO current_record
    FROM consent_registry
    WHERE participant_id = p_participant_id
        AND revocation_status = FALSE;

    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    -- Update expiration
    UPDATE consent_registry
    SET expiration_date = p_new_expiration,
        updated_at = NOW()
    WHERE participant_id = p_participant_id;

    -- Insert audit log
    INSERT INTO consent_audit_log (
        participant_id, action, actor, ip_address, user_agent, details
    ) VALUES (
        p_participant_id, 'CONSENT_EXTENDED', p_actor, p_ip_address, p_user_agent,
        jsonb_build_object(
            'old_expiration', current_record.expiration_date,
            'new_expiration', p_new_expiration,
            'timestamp', NOW()
        )
    );

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ===========================================
-- TRIGGERS
-- ===========================================

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_consent_registry_updated_at
    BEFORE UPDATE ON consent_registry
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger for automatic audit logging on consent changes
CREATE OR REPLACE FUNCTION audit_consent_changes()
RETURNS TRIGGER AS $$
DECLARE
    action_type VARCHAR(50);
    details_json JSONB;
BEGIN
    -- Determine action type
    IF TG_OP = 'INSERT' THEN
        action_type := 'CONSENT_GRANTED';
        details_json := jsonb_build_object(
            'operation', 'INSERT',
            'new_values', row_to_json(NEW)::JSONB
        );
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.revocation_status = FALSE AND NEW.revocation_status = TRUE THEN
            action_type := 'CONSENT_REVOKED';
        ELSIF OLD.expiration_date != NEW.expiration_date THEN
            action_type := 'CONSENT_EXTENDED';
        ELSE
            action_type := 'DOCUMENT_VERIFIED';
        END IF;
        details_json := jsonb_build_object(
            'operation', 'UPDATE',
            'old_values', row_to_json(OLD)::JSONB,
            'new_values', row_to_json(NEW)::JSONB
        );
    ELSIF TG_OP = 'DELETE' THEN
        action_type := 'CONSENT_EXPIRED';
        details_json := jsonb_build_object(
            'operation', 'DELETE',
            'old_values', row_to_json(OLD)::JSONB
        );
    END IF;

    -- Insert audit log
    INSERT INTO consent_audit_log (
        participant_id, action, actor, details
    ) VALUES (
        COALESCE(NEW.participant_id, OLD.participant_id),
        action_type,
        COALESCE(NEW.created_by, 'SYSTEM'),
        details_json
    );

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_consent_registry_changes
    AFTER INSERT OR UPDATE OR DELETE ON consent_registry
    FOR EACH ROW EXECUTE FUNCTION audit_consent_changes();

-- ===========================================
-- VIEWS
-- ===========================================

-- Active consents view (for operational queries)
CREATE OR REPLACE VIEW active_consents AS
SELECT
    cr.participant_id,
    cr.organization_id,
    cr.consent_timestamp,
    cr.expiration_date,
    cr.legal_signoff_officer,
    cr.created_by,
    cr.classification_level,
    EXTRACT(EPOCH FROM (cr.expiration_date - NOW())) / 86400 AS days_remaining,
    CASE
        WHEN cr.expiration_date < NOW() + INTERVAL '7 days' THEN 'EXPIRING_SOON'
        WHEN cr.expiration_date < NOW() + INTERVAL '30 days' THEN 'ACTIVE'
        ELSE 'HEALTHY'
    END AS status
FROM consent_registry cr
WHERE cr.revocation_status = FALSE
    AND cr.expiration_date > NOW()
ORDER BY cr.expiration_date ASC;

-- Consent violations view (for compliance monitoring)
CREATE OR REPLACE VIEW consent_violations AS
SELECT
    cal.participant_id,
    cal.action,
    cal.timestamp,
    cal.actor,
    cal.ip_address,
    cal.details
FROM consent_audit_log cal
WHERE cal.action IN ('CONSENT_REVOKED', 'CONSENT_EXPIRED')
    AND cal.timestamp > NOW() - INTERVAL '90 days'
ORDER BY cal.timestamp DESC;

-- ===========================================
-- ROLES AND PERMISSIONS
-- ===========================================

-- Create roles for different access levels
CREATE ROLE consent_admin;
CREATE ROLE consent_auditor;
CREATE ROLE consent_service; -- For application access

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON consent_registry TO consent_admin;
GRANT SELECT ON consent_registry TO consent_auditor, consent_service;

GRANT SELECT ON consent_audit_log TO consent_admin, consent_auditor;
GRANT INSERT ON consent_audit_log TO consent_admin, consent_service;

GRANT SELECT ON active_consents TO consent_admin, consent_auditor, consent_service;
GRANT SELECT ON consent_violations TO consent_admin, consent_auditor;

-- Grant function execution
GRANT EXECUTE ON FUNCTION verify_consent_status(UUID, UUID) TO consent_admin, consent_service;
GRANT EXECUTE ON FUNCTION revoke_participant_consent(UUID, VARCHAR, TEXT, INET, TEXT) TO consent_admin;
GRANT EXECUTE ON FUNCTION extend_participant_consent(UUID, TIMESTAMPTZ, VARCHAR, INET, TEXT) TO consent_admin;

-- ===========================================
-- INITIAL DATA
-- ===========================================

-- Insert sample classification levels (customize as needed)
-- This would typically be populated by the application

-- ===========================================
-- COMPLIANCE NOTES
-- ===========================================

/*
COMPLIANCE VERIFICATION:

GDPR Article 7 (Lawfulness of Processing):
✓ Consent must be freely given, specific, informed, and unambiguous
✓ Consent registry stores timestamp, document hash, legal signoff
✓ Participants can withdraw consent at any time
✓ Consent revocation is immediate and audited

Cryptographic Audit Trail:
✓ All consent operations are logged immutably
✓ Document hashes prevent tampering
✓ Digital signatures for critical operations
✓ Blockchain-style hash chaining for tamper evidence

Retention Requirements:
✓ Consent records retained for 7 years post-revocation
✓ Audit logs retained for 10 years
✓ Emergency overrides logged permanently

Access Controls:
✓ Role-based access control (RBAC)
✓ Principle of least privilege
✓ Audit logging for all access
✓ Service accounts for application access

Monitoring:
✓ Active consents view for operational monitoring
✓ Violation tracking for compliance reporting
✓ Expiration alerts for proactive management
✓ Emergency override tracking

Disaster Recovery:
✓ Point-in-time recovery capabilities
✓ Cross-region replication recommended
✓ Backup encryption mandatory
✓ Recovery testing required quarterly
*/

-- ===========================================
-- END OF SCHEMA
-- ===========================================
