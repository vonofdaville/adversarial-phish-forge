#!/usr/bin/env python3
"""
CHIMERA Consent Database Initialization

Initializes the PostgreSQL database with consent schema and sample data.
This script MUST be run before starting the orchestrator.

Usage:
    python scripts/init_consent_db.py [--drop-existing] [--sample-data]
"""

import argparse
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from chimera.utils.config import config
from chimera.utils.logger import setup_logging

logger = setup_logging(__name__)


def init_database(drop_existing: bool = False, create_sample_data: bool = False):
    """Initialize the consent database."""

    logger.info("Starting CHIMERA consent database initialization")

    try:
        # Create engine
        engine = create_engine(config.database_url, echo=config.debug)

        with engine.connect() as conn:
            # Test connection
            logger.info("Testing database connection...")
            conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")

            # Drop existing tables if requested
            if drop_existing:
                logger.warning("Dropping existing tables...")
                conn.execute(text("""
                    DROP TABLE IF EXISTS ethics_incidents CASCADE;
                    DROP TABLE IF EXISTS kill_switch_events CASCADE;
                    DROP TABLE IF EXISTS campaign_audit_log CASCADE;
                    DROP TABLE IF EXISTS organizations CASCADE;
                    DROP TABLE IF EXISTS consent_registry CASCADE;
                """))
                conn.commit()
                logger.info("Existing tables dropped")

            # Create schema
            logger.info("Creating database schema...")

            # Read and execute schema SQL
            schema_path = project_root / "docker" / "postgres" / "init.sql"
            if not schema_path.exists():
                raise FileNotFoundError(f"Schema file not found: {schema_path}")

            with open(schema_path, 'r') as f:
                schema_sql = f.read()

            # Split into individual statements and execute
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]

            for statement in statements:
                if statement:
                    try:
                        conn.execute(text(statement))
                    except SQLAlchemyError as e:
                        logger.warning(f"Statement execution warning: {e}")
                        # Continue with other statements

            conn.commit()
            logger.info("Database schema created successfully")

            # Create sample data if requested
            if create_sample_data:
                logger.info("Creating sample data...")
                _create_sample_data(conn)

            logger.info("CHIMERA consent database initialization completed successfully")

    except SQLAlchemyError as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during initialization: {e}")
        sys.exit(1)


def _create_sample_data(conn):
    """Create sample data for testing and development."""

    try:
        # Sample organization
        conn.execute(text("""
            INSERT INTO organizations (
                organization_id, organization_name, legal_entity_name,
                primary_contact_email, cyber_liability_coverage
            ) VALUES (
                '550e8400-e29b-41d4-a716-446655440001'::UUID,
                'CHIMERA Research Lab',
                'Adversarial AI Research Institute',
                'legal@chimera-project.org',
                10000000.00
            ) ON CONFLICT (organization_id) DO NOTHING;
        """))

        # Sample consent record (hashed email for privacy)
        import hashlib
        sample_email = "researcher@chimera-project.org"
        email_hash = hashlib.sha256(sample_email.encode()).hexdigest()

        conn.execute(text("""
            INSERT INTO consent_registry (
                participant_id, organization_id, consent_timestamp,
                consent_document_hash, legal_signoff_officer,
                expiration_date, participant_email, participant_role,
                campaign_types_allowed, created_by
            ) VALUES (
                '550e8400-e29b-41d4-a716-446655440002'::UUID,
                '550e8400-e29b-41d4-a716-446655440001'::UUID,
                NOW(),
                :consent_hash,
                'Dr. Lucien Vallois',
                NOW() + INTERVAL '365 days',
                :participant_email,
                'Security Researcher',
                ARRAY['phishing_simulation', 'social_engineering_research'],
                'system_init'
            ) ON CONFLICT (participant_id) DO NOTHING;
        """), {
            'consent_hash': hashlib.sha256(f"{sample_email}:test".encode()).hexdigest(),
            'participant_email': sample_email
        })

        conn.commit()
        logger.info("Sample data created successfully")

    except SQLAlchemyError as e:
        logger.error(f"Failed to create sample data: {e}")
        conn.rollback()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="CHIMERA Consent Database Initialization")
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Drop existing tables before creating new ones"
    )
    parser.add_argument(
        "--sample-data",
        action="store_true",
        help="Create sample data for testing"
    )

    args = parser.parse_args()

    # Warn about dropping data
    if args.drop_existing:
        print("WARNING: --drop-existing will delete all existing data!")
        confirm = input("Are you sure? (type 'yes' to continue): ")
        if confirm.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)

    init_database(drop_existing=args.drop_existing, create_sample_data=args.sample_data)


if __name__ == "__main__":
    main()

