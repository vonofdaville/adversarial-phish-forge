# CHIMERA Framework - Consent Verification Middleware
# Version: 1.0.0
# Created: December 2025
# Purpose: FastAPI middleware for real-time consent verification

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator
import asyncpg
import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential

# ===========================================
# CONFIGURATION
# ===========================================

class ConsentConfig:
    """Configuration for consent verification system."""

    # Database settings
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "chimera_consent"
    DB_USER: str = "chimera_service"
    DB_PASSWORD: str = ""

    # Redis settings for caching
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 1

    # Consent verification settings
    CONSENT_CACHE_TTL: int = 300  # 5 minutes
    MAX_RETRY_ATTEMPTS: int = 3
    CIRCUIT_BREAKER_THRESHOLD: int = 5
    CIRCUIT_BREAKER_TIMEOUT: int = 60

    # Emergency override settings
    EMERGENCY_OVERRIDE_ENABLED: bool = True
    EMERGENCY_OVERRIDE_CACHE_TTL: int = 60  # 1 minute

# ===========================================
# DATA MODELS
# ===========================================

class ConsentStatus(Enum):
    """Enumeration of possible consent verification results."""
    VALID = "valid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    NOT_FOUND = "not_found"
    EMERGENCY_OVERRIDE = "emergency_override"
    DATABASE_UNAVAILABLE = "database_unavailable"
    INVALID_REQUEST = "invalid_request"

@dataclass
class ConsentResult:
    """Result of a consent verification operation."""
    status: ConsentStatus
    participant_id: Optional[str] = None
    organization_id: Optional[str] = None
    expiration_date: Optional[datetime] = None
    days_remaining: Optional[int] = None
    message: Optional[str] = None
    verified_at: datetime = None

    def __post_init__(self):
        if self.verified_at is None:
            self.verified_at = datetime.utcnow()

class ConsentRequest(BaseModel):
    """Request model for consent verification."""
    participant_ids: List[str]
    organization_id: Optional[str] = None
    operation: str = "email_send"  # email_send, tracking_access, telemetry_collect

    @validator('participant_ids')
    def validate_participant_ids(cls, v):
        if not v:
            raise ValueError('participant_ids cannot be empty')
        if len(v) > 1000:  # Reasonable limit
            raise ValueError('Too many participant IDs (max 1000)')
        return v

    @validator('operation')
    def validate_operation(cls, v):
        valid_operations = {'email_send', 'tracking_access', 'telemetry_collect', 'campaign_create'}
        if v not in valid_operations:
            raise ValueError(f'Invalid operation: {v}')
        return v

# ===========================================
# EXCEPTIONS
# ===========================================

class ConsentException(Exception):
    """Base exception for consent-related errors."""
    def __init__(self, message: str, status_code: int = 403):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class ConsentMissingException(ConsentException):
    """Exception raised when consent is missing."""
    def __init__(self, participant_id: str):
        super().__init__(
            f"Consent not found for participant {participant_id}",
            status_code=403
        )

class ConsentExpiredException(ConsentException):
    """Exception raised when consent has expired."""
    def __init__(self, participant_id: str, expiration_date: datetime):
        super().__init__(
            f"Consent expired for participant {participant_id} on {expiration_date.isoformat()}",
            status_code=403
        )

class ConsentRevokedException(ConsentException):
    """Exception raised when consent has been revoked."""
    def __init__(self, participant_id: str, revocation_date: datetime):
        super().__init__(
            f"Consent revoked for participant {participant_id} on {revocation_date.isoformat()}",
            status_code=403
        )

class DatabaseUnavailableException(ConsentException):
    """Exception raised when consent database is unavailable."""
    def __init__(self):
        super().__init__(
            "Consent verification service temporarily unavailable",
            status_code=503
        )

# ===========================================
# DATABASE INTERFACE
# ===========================================

class ConsentDatabase:
    """PostgreSQL interface for consent operations."""

    def __init__(self, config: ConsentConfig):
        self.config = config
        self._pool: Optional[asyncpg.Pool] = None
        self._circuit_breaker_count = 0
        self._circuit_breaker_until: Optional[datetime] = None

    async def connect(self):
        """Establish database connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                host=self.config.DB_HOST,
                port=self.config.DB_PORT,
                database=self.config.DB_NAME,
                user=self.config.DB_USER,
                password=self.config.DB_PASSWORD,
                min_size=5,
                max_size=20,
                command_timeout=10
            )

    async def disconnect(self):
        """Close database connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker is active."""
        if self._circuit_breaker_until and datetime.utcnow() < self._circuit_breaker_until:
            return False
        return True

    def _trigger_circuit_breaker(self):
        """Activate circuit breaker on repeated failures."""
        self._circuit_breaker_count += 1
        if self._circuit_breaker_count >= self.config.CIRCUIT_BREAKER_THRESHOLD:
            self._circuit_breaker_until = datetime.utcnow() + timedelta(
                seconds=self.config.CIRCUIT_BREAKER_TIMEOUT
            )
            logging.error(f"Circuit breaker activated for {self.config.CIRCUIT_BREAKER_TIMEOUT} seconds")

    def _reset_circuit_breaker(self):
        """Reset circuit breaker on successful operation."""
        self._circuit_breaker_count = 0
        self._circuit_breaker_until = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.1, max=2.0)
    )
    async def verify_consent(self, participant_id: str, organization_id: Optional[str] = None) -> ConsentResult:
        """Verify consent status for a participant."""
        if not self._check_circuit_breaker():
            return ConsentResult(
                status=ConsentStatus.DATABASE_UNAVAILABLE,
                message="Circuit breaker active - database temporarily unavailable"
            )

        try:
            async with self._pool.acquire() as conn:
                # Call stored procedure
                result = await conn.fetchrow("""
                    SELECT * FROM verify_consent_status($1, $2)
                """, participant_id, organization_id)

                if result['is_valid']:
                    status = ConsentStatus.VALID
                    if result['status_message'] == 'EMERGENCY_OVERRIDE_ACTIVE':
                        status = ConsentStatus.EMERGENCY_OVERRIDE
                else:
                    status_map = {
                        'PARTICIPANT_NOT_FOUND': ConsentStatus.NOT_FOUND,
                        'CONSENT_REVOKED': ConsentStatus.REVOKED,
                        'CONSENT_EXPIRED': ConsentStatus.EXPIRED
                    }
                    status = status_map.get(result['status_message'], ConsentStatus.INVALID_REQUEST)

                self._reset_circuit_breaker()
                return ConsentResult(
                    status=status,
                    participant_id=participant_id,
                    organization_id=organization_id,
                    expiration_date=result['expiration_date'],
                    days_remaining=result['days_remaining'],
                    message=result['status_message']
                )

        except Exception as e:
            logging.error(f"Database error during consent verification: {e}")
            self._trigger_circuit_breaker()
            return ConsentResult(
                status=ConsentStatus.DATABASE_UNAVAILABLE,
                message=f"Database error: {str(e)}"
            )

    async def revoke_consent(self, participant_id: str, actor: str,
                           reason: Optional[str] = None) -> bool:
        """Revoke consent for a participant."""
        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetchval("""
                    SELECT revoke_participant_consent($1, $2, $3)
                """, participant_id, actor, reason)
                return result
        except Exception as e:
            logging.error(f"Failed to revoke consent: {e}")
            return False

# ===========================================
# CACHE INTERFACE
# ===========================================

class ConsentCache:
    """Redis-based cache for consent verification results."""

    def __init__(self, config: ConsentConfig):
        self.config = config
        self._redis: Optional[redis.Redis] = None

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

    async def get_consent_result(self, participant_id: str) -> Optional[ConsentResult]:
        """Get cached consent result."""
        try:
            key = f"consent:{participant_id}"
            data = await self._redis.get(key)
            if data:
                # Deserialize from JSON
                import json
                result_data = json.loads(data)
                return ConsentResult(**result_data)
        except Exception as e:
            logging.warning(f"Cache read error: {e}")
        return None

    async def set_consent_result(self, participant_id: str, result: ConsentResult):
        """Cache consent result."""
        try:
            key = f"consent:{participant_id}"
            # Serialize to JSON
            import json
            data = json.dumps({
                'status': result.status.value,
                'participant_id': result.participant_id,
                'organization_id': result.organization_id,
                'expiration_date': result.expiration_date.isoformat() if result.expiration_date else None,
                'days_remaining': result.days_remaining,
                'message': result.message,
                'verified_at': result.verified_at.isoformat()
            })
            await self._redis.setex(key, self.config.CONSENT_CACHE_TTL, data)
        except Exception as e:
            logging.warning(f"Cache write error: {e}")

    async def invalidate_consent(self, participant_id: str):
        """Remove consent result from cache."""
        try:
            key = f"consent:{participant_id}"
            await self._redis.delete(key)
        except Exception as e:
            logging.warning(f"Cache invalidation error: {e}")

# ===========================================
# CONSENT VERIFIER
# ===========================================

class ConsentVerifier:
    """Main consent verification service."""

    def __init__(self, config: ConsentConfig = None):
        self.config = config or ConsentConfig()
        self.database = ConsentDatabase(self.config)
        self.cache = ConsentCache(self.config)
        self._initialized = False

    async def initialize(self):
        """Initialize database and cache connections."""
        if not self._initialized:
            await self.database.connect()
            await self.cache.connect()
            self._initialized = True

    async def shutdown(self):
        """Shutdown connections."""
        await self.database.disconnect()
        await self.cache.disconnect()
        self._initialized = False

    async def check_consent(self, participant_id: str,
                          organization_id: Optional[str] = None) -> ConsentResult:
        """Check consent status for a single participant."""
        await self.initialize()

        # Try cache first
        cached_result = await self.cache.get_consent_result(participant_id)
        if cached_result and cached_result.status in [ConsentStatus.VALID, ConsentStatus.EMERGENCY_OVERRIDE]:
            # Only trust positive cache results if recent
            if (datetime.utcnow() - cached_result.verified_at).seconds < self.config.CONSENT_CACHE_TTL:
                return cached_result

        # Check database
        result = await self.database.verify_consent(participant_id, organization_id)

        # Cache result if valid
        if result.status in [ConsentStatus.VALID, ConsentStatus.EMERGENCY_OVERRIDE]:
            await self.cache.set_consent_result(participant_id, result)

        return result

    async def verify_consent_before_action(self, participant_ids: List[str],
                                         organization_id: Optional[str] = None,
                                         operation: str = "email_send") -> bool:
        """Verify consent for multiple participants before an action."""
        await self.initialize()

        # Parallel verification for better performance
        tasks = [
            self.check_consent(pid, organization_id)
            for pid in participant_ids
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check all results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logging.error(f"Consent verification error for {participant_ids[i]}: {result}")
                return False

            if result.status not in [ConsentStatus.VALID, ConsentStatus.EMERGENCY_OVERRIDE]:
                logging.warning(
                    f"Consent check failed for {participant_ids[i]}: {result.status} - {result.message}"
                )
                return False

        return True

    async def revoke_consent(self, participant_id: str, reason: str = "User request") -> bool:
        """Revoke consent for a participant."""
        await self.initialize()

        # Clear cache immediately
        await self.cache.invalidate_consent(participant_id)

        # Revoke in database
        success = await self.database.revoke_consent(
            participant_id,
            "system",  # Actor - would come from authentication context
            reason
        )

        return success

    async def get_consent_expiry(self, participant_id: str) -> Optional[datetime]:
        """Get consent expiration date for a participant."""
        result = await self.check_consent(participant_id)
        return result.expiration_date if result.status == ConsentStatus.VALID else None

# ===========================================
# FASTAPI MIDDLEWARE
# ===========================================

class ConsentMiddleware:
    """FastAPI middleware for consent verification."""

    def __init__(self, verifier: ConsentVerifier, exempt_paths: Set[str] = None):
        self.verifier = verifier
        self.exempt_paths = exempt_paths or {
            "/health", "/metrics", "/docs", "/openapi.json", "/redoc"
        }

    async def __call__(self, request: Request, call_next):
        # Skip exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        # Extract participant IDs from request
        participant_ids = self._extract_participant_ids(request)

        if not participant_ids:
            # If no participants specified, allow request (for general endpoints)
            return await call_next(request)

        # Verify consent for all participants
        try:
            consent_valid = await self.verifier.verify_consent_before_action(
                participant_ids,
                organization_id=self._extract_organization_id(request),
                operation=self._extract_operation(request)
            )

            if not consent_valid:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Consent validation failed",
                        "message": "One or more participants have not provided valid consent",
                        "code": "CONSENT_REQUIRED"
                    }
                )

        except DatabaseUnavailableException:
            # In fail-safe mode, deny access if consent service is unavailable
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Service temporarily unavailable",
                    "message": "Consent verification service is currently unavailable",
                    "code": "SERVICE_UNAVAILABLE"
                }
            )

        # Add consent verification header to request
        request.state.consent_verified = True
        request.state.participant_ids = participant_ids

        # Continue with request
        response = await call_next(request)
        return response

    def _extract_participant_ids(self, request: Request) -> List[str]:
        """Extract participant IDs from request."""
        # Check query parameters
        participant_ids = request.query_params.getlist("participant_id")

        # Check JSON body
        if not participant_ids and hasattr(request, 'json'):
            try:
                body = request.json()
                if isinstance(body, dict):
                    participant_ids = body.get("participant_ids", [])
                    if isinstance(participant_ids, str):
                        participant_ids = [participant_ids]
                elif isinstance(body, list):
                    participant_ids = body
            except:
                pass

        # Check path parameters
        if not participant_ids:
            participant_id = request.path_params.get("participant_id")
            if participant_id:
                participant_ids = [participant_id]

        return participant_ids

    def _extract_organization_id(self, request: Request) -> Optional[str]:
        """Extract organization ID from request."""
        return request.query_params.get("organization_id") or \
               request.headers.get("X-Organization-ID")

    def _extract_operation(self, request: Request) -> str:
        """Determine operation type from request."""
        path = request.url.path

        if "/email" in path or "/send" in path:
            return "email_send"
        elif "/tracking" in path or "/pixel" in path:
            return "tracking_access"
        elif "/telemetry" in path:
            return "telemetry_collect"
        else:
            return "general_operation"

# ===========================================
# UTILITY FUNCTIONS
# ===========================================

async def create_consent_verifier(config: ConsentConfig = None) -> ConsentVerifier:
    """Factory function to create and initialize a consent verifier."""
    verifier = ConsentVerifier(config)
    await verifier.initialize()
    return verifier

def create_consent_middleware(verifier: ConsentVerifier,
                            exempt_paths: Set[str] = None) -> ConsentMiddleware:
    """Factory function to create consent middleware."""
    return ConsentMiddleware(verifier, exempt_paths)

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
