"""
CHIMERA Configuration Management

Centralized configuration with environment variable support and validation.
Implements security best practices for sensitive configuration handling.
"""

import os
import secrets
from typing import List, Optional
from urllib.parse import urlparse

from pydantic import BaseSettings, validator, Field


class Config(BaseSettings):
    """
    CHIMERA Configuration Settings

    All configuration is loaded from environment variables with validation.
    Sensitive values are handled securely with appropriate masking in logs.
    """

    # Application Settings
    app_name: str = "CHIMERA"
    app_version: str = "1.0.0-BLACKBOX"
    debug: bool = False
    log_level: str = "INFO"

    # Database URLs
    database_url: str = Field(..., env="DATABASE_URL")
    neo4j_uri: str = Field(..., env="NEO4J_URI")
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")

    # Neo4j Configuration
    neo4j_user: str = Field("neo4j", env="NEO4J_USER")
    neo4j_password: str = Field(..., env="NEO4J_PASSWORD")
    neo4j_database: str = Field("chimera", env="NEO4J_DATABASE")

    # ClickHouse Configuration
    clickhouse_host: str = Field("localhost", env="CLICKHOUSE_HOST")
    clickhouse_port: int = Field(9000, env="CLICKHOUSE_PORT")
    clickhouse_user: str = Field("default", env="CLICKHOUSE_USER")
    clickhouse_password: str = Field("", env="CLICKHOUSE_PASSWORD")

    # OpenAI Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_organization: Optional[str] = Field(None, env="OPENAI_ORGANIZATION")
    openai_model: str = Field("gpt-4-turbo-preview", env="OPENAI_MODEL")

    # Security Settings
    secret_key: str = Field(..., env="SECRET_KEY")
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")

    # Email Configuration
    smtp_host: str = Field("localhost", env="SMTP_HOST")
    smtp_port: int = Field(587, env="SMTP_PORT")
    smtp_user: str = Field(..., env="SMTP_USER")
    smtp_password: str = Field(..., env="SMTP_PASSWORD")
    smtp_tls: bool = Field(True, env="SMTP_TLS")

    # DKIM Configuration
    dkim_private_key_path: Optional[str] = Field(None, env="DKIM_PRIVATE_KEY_PATH")
    dkim_selector: str = Field("chimera", env="DKIM_SELECTOR")

    # Consent and Ethics Configuration
    consent_retention_days: int = Field(365, env="CONSENT_RETENTION_DAYS")
    telemetry_retention_days: int = Field(180, env="TELEMETRY_RETENTION_DAYS")
    email_content_retention_days: int = Field(90, env="EMAIL_CONTENT_RETENTION_DAYS")

    # Ethics Hotline
    ethics_hotline_email: str = Field("ethics@chimera-project.org", env="ETHICS_HOTLINE_EMAIL")
    ethics_hotline_phone: str = Field("+1-555-CHIMERA", env="ETHICS_HOTLINE_PHONE")

    # Tracking Server
    tracking_server_host: str = Field("0.0.0.0", env="TRACKING_SERVER_HOST")
    tracking_server_port: int = Field(8080, env="TRACKING_SERVER_PORT")
    tracking_base_url: str = Field("https://tracking.chimera.local", env="TRACKING_BASE_URL")

    # Kill Switch Configuration
    campaign_timeout_hours: int = Field(72, env="CAMPAIGN_TIMEOUT_HOURS")
    geolocation_whitelist: List[str] = Field(["US", "CA", "GB", "DE"], env="GEOLOCATION_WHITELIST")

    # API Rate Limiting
    openai_rate_limit_requests: int = Field(50, env="OPENAI_RATE_LIMIT_REQUESTS")
    openai_rate_limit_window: int = Field(60, env="OPENAI_RATE_LIMIT_WINDOW")

    # Privacy Configuration
    differential_privacy_epsilon: float = Field(1.0, env="DIFFERENTIAL_PRIVACY_EPSILON")
    fingerprint_hash_salt: str = Field(..., env="FINGERPRINT_HASH_SALT")

    class Config:
        env_file = ".env"
        case_sensitive = False

    @validator('database_url')
    def validate_database_url(cls, v):
        """Validate database URL format."""
        try:
            parsed = urlparse(v)
            if parsed.scheme not in ['postgresql', 'postgres']:
                raise ValueError('Must be a PostgreSQL URL')
            return v
        except Exception:
            raise ValueError('Invalid database URL format')

    @validator('neo4j_uri')
    def validate_neo4j_uri(cls, v):
        """Validate Neo4j URI format."""
        try:
            parsed = urlparse(v)
            if parsed.scheme not in ['neo4j', 'neo4j+s', 'neo4j+ssc', 'bolt', 'bolt+s', 'bolt+ssc']:
                raise ValueError('Must be a valid Neo4j URI')
            return v
        except Exception:
            raise ValueError('Invalid Neo4j URI format')

    @validator('redis_url')
    def validate_redis_url(cls, v):
        """Validate Redis URL format."""
        try:
            parsed = urlparse(v)
            if parsed.scheme not in ['redis', 'rediss', 'unix']:
                raise ValueError('Must be a valid Redis URL')
            return v
        except Exception:
            raise ValueError('Invalid Redis URL format')

    @validator('openai_api_key')
    def validate_openai_key(cls, v):
        """Validate OpenAI API key format."""
        if not v or len(v.strip()) < 20:
            raise ValueError('Invalid OpenAI API key')
        return v.strip()

    @validator('secret_key')
    def validate_secret_key(cls, v):
        """Ensure secret key is strong."""
        if len(v) < 32:
            raise ValueError('Secret key must be at least 32 characters')
        return v

    @validator('jwt_secret_key')
    def validate_jwt_secret(cls, v):
        """Ensure JWT secret is strong."""
        if len(v) < 32:
            raise ValueError('JWT secret key must be at least 32 characters')
        return v

    @validator('fingerprint_hash_salt')
    def validate_fingerprint_salt(cls, v):
        """Ensure fingerprint salt is strong."""
        if len(v) < 16:
            raise ValueError('Fingerprint hash salt must be at least 16 characters')
        return v

    @validator('geolocation_whitelist')
    def validate_geolocations(cls, v):
        """Validate geolocation codes."""
        valid_codes = ['US', 'CA', 'GB', 'DE', 'FR', 'AU', 'JP', 'KR']
        for code in v:
            if code.upper() not in valid_codes:
                raise ValueError(f'Invalid geolocation code: {code}')
        return [code.upper() for code in v]

    @property
    def database_config(self) -> dict:
        """Get database configuration dict."""
        return {
            'url': self.database_url,
            'pool_pre_ping': True,
            'echo': self.debug,
        }

    @property
    def neo4j_config(self) -> dict:
        """Get Neo4j configuration dict."""
        return {
            'uri': self.neo4j_uri,
            'user': self.neo4j_user,
            'password': self.neo4j_password,
            'database': self.neo4j_database,
        }

    @property
    def clickhouse_config(self) -> dict:
        """Get ClickHouse configuration dict."""
        return {
            'host': self.clickhouse_host,
            'port': self.clickhouse_port,
            'user': self.clickhouse_user,
            'password': self.clickhouse_password,
        }

    @property
    def smtp_config(self) -> dict:
        """Get SMTP configuration dict."""
        return {
            'host': self.smtp_host,
            'port': self.smtp_port,
            'user': self.smtp_user,
            'password': self.smtp_password,
            'tls': self.smtp_tls,
        }

    def get_masked_config(self) -> dict:
        """Get configuration with sensitive values masked for logging."""
        config_dict = self.dict()
        sensitive_keys = [
            'openai_api_key', 'secret_key', 'jwt_secret_key',
            'smtp_password', 'neo4j_password', 'fingerprint_hash_salt'
        ]

        for key in sensitive_keys:
            if key in config_dict and config_dict[key]:
                config_dict[key] = '*' * 8

        return config_dict


# Global configuration instance
config = Config()


def generate_secure_secret(length: int = 32) -> str:
    """Generate a cryptographically secure random secret."""
    return secrets.token_urlsafe(length)


def validate_config() -> List[str]:
    """Validate configuration and return list of issues."""
    issues = []

    # Check required environment variables
    required_vars = [
        'DATABASE_URL', 'OPENAI_API_KEY', 'SECRET_KEY',
        'JWT_SECRET_KEY', 'FINGERPRINT_HASH_SALT'
    ]

    for var in required_vars:
        if not os.getenv(var):
            issues.append(f"Missing required environment variable: {var}")

    # Check database connectivity (would be implemented)
    # Check API key validity (would be implemented)

    return issues


