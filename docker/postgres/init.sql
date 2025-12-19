-- CHIMERA Consent Database Schema
-- NSA-style audit trail with cryptographic proof

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Consent Registry Table (NSA "Three Gates" Model)
CREATE TABLE consent_registry (
    participant_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL,
    consent_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    consent_document_hash SHA256 NOT NULL, -- Cryptographic proof
    legal_signoff_officer VARCHAR(255),
    expiration_date TIMESTAMPTZ NOT NULL,
    revocation_status BOOLEAN DEFAULT FALSE,
    revocation_timestamp TIMESTAMPTZ,
    revocation_reason TEXT,

    -- Audit trail (NSA-grade)
    created_by VARCHAR(255),
    classification_level VARCHAR(50) DEFAULT 'UNCLASSIFIED//FOUO',
    last_modified TIMESTAMPTZ DEFAULT NOW(),
    modification_audit JSONB DEFAULT '[]',

    -- Additional metadata
    participant_email VARCHAR(255),
    participant_role VARCHAR(100),
    campaign_types_allowed TEXT[], -- Array of allowed campaign types
    geographic_restrictions TEXT[], -- Geographic whitelist
    contact_preferences JSONB DEFAULT '{}'
);

-- Organizations Table
CREATE TABLE organizations (
    organization_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_name VARCHAR(255) NOT NULL,
    legal_entity_name VARCHAR(255),
    primary_contact_email VARCHAR(255),
    primary_contact_phone VARCHAR(50),
    insurance_policy_number VARCHAR(100),
    cyber_liability_coverage DECIMAL(15,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Campaign Audit Log
CREATE TABLE campaign_audit_log (
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL,
    participant_id UUID,
    action VARCHAR(100) NOT NULL,
    action_timestamp TIMESTAMPTZ DEFAULT NOW(),
    action_details JSONB,
    ip_address INET,
    user_agent TEXT,
    consent_verified BOOLEAN DEFAULT TRUE
);

-- Kill Switch Events
CREATE TABLE kill_switch_events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL,
    trigger_reason VARCHAR(100) NOT NULL,
    trigger_timestamp TIMESTAMPTZ DEFAULT NOW(),
    triggered_by VARCHAR(255),
    affected_participants INTEGER,
    incident_report JSONB
);

-- Ethics Hotline Incidents
CREATE TABLE ethics_incidents (
    incident_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reporter_email VARCHAR(255),
    incident_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    severity_level VARCHAR(20) DEFAULT 'MEDIUM',
    reported_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    escalation_required BOOLEAN DEFAULT FALSE
);

-- Indexes for performance
CREATE INDEX idx_consent_registry_participant ON consent_registry(participant_id);
CREATE INDEX idx_consent_registry_org ON consent_registry(organization_id);
CREATE INDEX idx_consent_registry_expiration ON consent_registry(expiration_date);
CREATE INDEX idx_consent_registry_revocation ON consent_registry(revocation_status);
CREATE INDEX idx_campaign_audit_campaign ON campaign_audit_log(campaign_id);
CREATE INDEX idx_campaign_audit_timestamp ON campaign_audit_log(action_timestamp);

-- Row Level Security (PostgreSQL RLS)
ALTER TABLE consent_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_audit_log ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY consent_registry_policy ON consent_registry
    FOR ALL USING (revocation_status = FALSE);

CREATE POLICY campaign_audit_policy ON campaign_audit_log
    FOR SELECT USING (consent_verified = TRUE);

-- Functions for consent validation
CREATE OR REPLACE FUNCTION validate_consent(
    p_participant_id UUID,
    p_campaign_type VARCHAR(100) DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    consent_record RECORD;
BEGIN
    SELECT * INTO consent_record
    FROM consent_registry
    WHERE participant_id = p_participant_id
    AND revocation_status = FALSE
    AND expiration_date > NOW();

    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    -- Check campaign type restrictions if specified
    IF p_campaign_type IS NOT NULL THEN
        IF NOT (p_campaign_type = ANY(consent_record.campaign_types_allowed)) THEN
            RETURN FALSE;
        END IF;
    END IF;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to revoke consent
CREATE OR REPLACE FUNCTION revoke_consent(
    p_participant_id UUID,
    p_reason TEXT,
    p_revoked_by VARCHAR(255)
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE consent_registry
    SET
        revocation_status = TRUE,
        revocation_timestamp = NOW(),
        revocation_reason = p_reason,
        last_modified = NOW(),
        modification_audit = modification_audit || jsonb_build_object(
            'action', 'revocation',
            'timestamp', NOW(),
            'revoked_by', p_revoked_by,
            'reason', p_reason
        )
    WHERE participant_id = p_participant_id;

    -- Log the revocation
    INSERT INTO campaign_audit_log (
        campaign_id, participant_id, action, action_details, consent_verified
    ) VALUES (
        '00000000-0000-0000-0000-000000000000'::UUID,
        p_participant_id,
        'consent_revoked',
        jsonb_build_object('reason', p_reason, 'revoked_by', p_revoked_by),
        FALSE
    );

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Insert sample organization for development
INSERT INTO organizations (
    organization_id,
    organization_name,
    legal_entity_name,
    primary_contact_email,
    cyber_liability_coverage
) VALUES (
    '550e8400-e29b-41d4-a716-446655440000'::UUID,
    'CHIMERA Research Lab',
    'Adversarial AI Research Institute',
    'legal@chimera-project.org',
    10000000.00
);

