# CHIMERA Framework - Rate Limiting & Abuse Prevention
# Version: 1.0.0
# Created: December 2025
# Purpose: Multi-tier rate limiting to prevent mass-scale misuse

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque

import redis.asyncio as redis
from pydantic import BaseModel, validator

# ===========================================
# CONFIGURATION
# ===========================================

class RateLimitConfig:
    """Configuration for rate limiting system."""

    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 3  # Separate DB for rate limiting

    # Rate limit definitions
    PER_TENANT_EMAILS_PER_HOUR: int = 100
    PER_CAMPAIGN_MAX_RECIPIENTS: int = 1000
    API_REQUESTS_PER_HOUR: int = 1000
    TRACKING_REQUESTS_PER_MINUTE: int = 1000

    # Burst allowances (percentage above base rate)
    BURST_ALLOWANCE: float = 1.2

    # Window sizes
    SLIDING_WINDOW_MINUTES: int = 15  # For sliding window calculations

    # Abuse detection
    SUSPICIOUS_ACTIVITY_THRESHOLD: int = 10  # Failed requests per minute
    BLOCK_DURATION_MINUTES: int = 60

    # Whitelist settings
    TRUSTED_ORGANIZATIONS: Set[str] = set()  # Organization IDs that bypass limits

    # Monitoring
    ALERT_THRESHOLD: float = 0.8  # Alert when 80% of limit reached

# ===========================================
# DATA MODELS
# ===========================================

class RateLimitScope(Enum):
    """Scopes for rate limiting."""
    TENANT = "tenant"           # Per organization/tenant
    CAMPAIGN = "campaign"       # Per campaign
    API = "api"                # General API usage
    TRACKING = "tracking"      # Tracking pixel requests
    IP_ADDRESS = "ip"          # Per IP address

class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"

@dataclass
class RateLimitRule:
    """Definition of a rate limit rule."""
    scope: RateLimitScope
    key_template: str  # Template for Redis key (e.g., "tenant:{tenant_id}:emails")
    limit: int
    window_seconds: int
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET
    burst_multiplier: float = 1.2

@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_time: datetime
    limit: int
    retry_after: Optional[int] = None

@dataclass
class AbusePattern:
    """Detected abuse pattern."""
    pattern_type: str
    severity: str
    affected_scope: RateLimitScope
    scope_key: str
    evidence: Dict
    detected_at: datetime = field(default_factory=datetime.utcnow)

class RateLimitViolation(BaseModel):
    """Record of a rate limit violation."""
    scope: str
    key: str
    requested: int
    limit: int
    timestamp: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]

    @validator('timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        return v or datetime.utcnow()

# ===========================================
# EXCEPTIONS
# ===========================================

class RateLimitException(Exception):
    """Exception raised when rate limit is exceeded."""
    def __init__(self, result: RateLimitResult, scope: str):
        self.result = result
        self.scope = scope
        super().__init__(f"Rate limit exceeded for {scope}")

class AbuseDetectedException(Exception):
    """Exception raised when abuse patterns are detected."""
    def __init__(self, pattern: AbusePattern):
        self.pattern = pattern
        super().__init__(f"Abuse pattern detected: {pattern.pattern_type}")

# ===========================================
# RATE LIMITING ALGORITHMS
# ===========================================

class RateLimitAlgorithmBase:
    """Base class for rate limiting algorithms."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def check_limit(self, key: str, limit: int, window_seconds: int,
                         burst_multiplier: float = 1.0) -> RateLimitResult:
        """Check if request should be allowed. Override in subclasses."""
        raise NotImplementedError

class TokenBucketAlgorithm(RateLimitAlgorithmBase):
    """Token bucket algorithm implementation."""

    async def check_limit(self, key: str, limit: int, window_seconds: int,
                         burst_multiplier: float = 1.0) -> RateLimitResult:
        """Check token bucket limit."""
        burst_limit = int(limit * burst_multiplier)

        # Get current tokens and last refill time
        tokens_key = f"{key}:tokens"
        last_refill_key = f"{key}:last_refill"

        current_time = time.time()
        tokens, last_refill = await asyncio.gather(
            self.redis.get(tokens_key),
            self.redis.get(last_refill_key)
        )

        tokens = int(tokens) if tokens else burst_limit
        last_refill = float(last_refill) if last_refill else current_time

        # Calculate token refill
        elapsed = current_time - last_refill
        refill_rate = limit / window_seconds  # tokens per second
        new_tokens = min(burst_limit, tokens + (elapsed * refill_rate))

        # Check if we can allow this request
        if new_tokens >= 1:
            new_tokens -= 1
            allowed = True
        else:
            allowed = False

        # Update Redis
        await asyncio.gather(
            self.redis.set(tokens_key, new_tokens),
            self.redis.set(last_refill_key, current_time),
            self.redis.expire(tokens_key, window_seconds * 2),
            self.redis.expire(last_refill_key, window_seconds * 2)
        )

        reset_time = datetime.utcnow() + timedelta(seconds=window_seconds)

        return RateLimitResult(
            allowed=allowed,
            remaining=int(new_tokens),
            reset_time=reset_time,
            limit=limit
        )

class FixedWindowAlgorithm(RateLimitAlgorithmBase):
    """Fixed window algorithm implementation."""

    async def check_limit(self, key: str, limit: int, window_seconds: int,
                         burst_multiplier: float = 1.0) -> RateLimitResult:
        """Check fixed window limit."""
        # Create window key with current time window
        current_window = int(time.time() / window_seconds)
        window_key = f"{key}:{current_window}"

        # Get current count
        count = await self.redis.get(window_key)
        count = int(count) if count else 0

        # Check if limit exceeded
        allowed = count < limit
        new_count = count + 1 if allowed else count

        # Update count
        await self.redis.setex(window_key, window_seconds, new_count)

        reset_time = datetime.fromtimestamp((current_window + 1) * window_seconds)

        return RateLimitResult(
            allowed=allowed,
            remaining=max(0, limit - new_count),
            reset_time=reset_time,
            limit=limit
        )

# ===========================================
# ABUSE DETECTION
# ===========================================

class AbuseDetector:
    """Detects abuse patterns and suspicious activity."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._recent_violations: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

    def detect_patterns(self, violation: RateLimitViolation) -> Optional[AbusePattern]:
        """Analyze violation for abuse patterns."""

        # Track recent violations for this scope/key
        key = f"{violation.scope}:{violation.key}"
        self._recent_violations[key].append(violation.timestamp)

        # Clean old entries (keep only last 5 minutes)
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        while self._recent_violations[key] and self._recent_violations[key][0] < cutoff:
            self._recent_violations[key].popleft()

        # Check for rapid violations (potential DoS)
        recent_count = len([
            ts for ts in self._recent_violations[key]
            if ts > datetime.utcnow() - timedelta(minutes=1)
        ])

        if recent_count >= self.config.SUSPICIOUS_ACTIVITY_THRESHOLD:
            return AbusePattern(
                pattern_type="rapid_violations",
                severity="high",
                affected_scope=RateLimitScope(violation.scope),
                scope_key=violation.key,
                evidence={
                    "violation_count": recent_count,
                    "time_window": "1_minute",
                    "threshold": self.config.SUSPICIOUS_ACTIVITY_THRESHOLD
                }
            )

        # Check for consistent violations over time (potential bot)
        if len(self._recent_violations[key]) >= 50:
            time_span = self._recent_violations[key][-1] - self._recent_violations[key][0]
            if time_span.total_seconds() < 300:  # 5 minutes
                return AbusePattern(
                    pattern_type="sustained_violations",
                    severity="medium",
                    affected_scope=RateLimitScope(violation.scope),
                    scope_key=violation.key,
                    evidence={
                        "violation_count": len(self._recent_violations[key]),
                        "time_span_seconds": time_span.total_seconds(),
                        "pattern": "consistent_high_frequency"
                    }
                )

        return None

# ===========================================
# MAIN RATE LIMITER
# ===========================================

class RateLimiter:
    """Main rate limiting system."""

    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.redis: Optional[redis.Redis] = None
        self.abuse_detector = AbuseDetector(self.config)

        # Define rate limit rules
        self.rules = [
            RateLimitRule(
                scope=RateLimitScope.TENANT,
                key_template="tenant:{tenant_id}:emails",
                limit=self.config.PER_TENANT_EMAILS_PER_HOUR,
                window_seconds=3600,  # 1 hour
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
                burst_multiplier=self.config.BURST_ALLOWANCE
            ),
            RateLimitRule(
                scope=RateLimitScope.CAMPAIGN,
                key_template="campaign:{campaign_id}:recipients",
                limit=self.config.PER_CAMPAIGN_MAX_RECIPIENTS,
                window_seconds=86400,  # 24 hours (hard cap)
                algorithm=RateLimitAlgorithm.FIXED_WINDOW
            ),
            RateLimitRule(
                scope=RateLimitScope.API,
                key_template="api:{api_key}:requests",
                limit=self.config.API_REQUESTS_PER_HOUR,
                window_seconds=3600,
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
                burst_multiplier=self.config.BURST_ALLOWANCE
            ),
            RateLimitRule(
                scope=RateLimitScope.TRACKING,
                key_template="tracking:{campaign_id}:requests",
                limit=self.config.TRACKING_REQUESTS_PER_MINUTE,
                window_seconds=60,
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET
            ),
            RateLimitRule(
                scope=RateLimitScope.IP_ADDRESS,
                key_template="ip:{ip_address}:requests",
                limit=100,  # 100 requests per minute per IP
                window_seconds=60,
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET
            )
        ]

        # Initialize algorithms
        self.algorithms = {
            RateLimitAlgorithm.TOKEN_BUCKET: TokenBucketAlgorithm,
            RateLimitAlgorithm.FIXED_WINDOW: FixedWindowAlgorithm
        }

        self._initialized = False

    async def initialize(self):
        """Initialize Redis connection."""
        if not self._initialized:
            self.redis = redis.Redis(
                host=self.config.REDIS_HOST,
                port=self.config.REDIS_PORT,
                db=self.config.REDIS_DB,
                decode_responses=True
            )

            # Initialize algorithm instances
            for rule in self.rules:
                if rule.algorithm not in self.algorithms:
                    continue
                algorithm_class = self.algorithms[rule.algorithm]
                setattr(self, f"{rule.algorithm.value}_impl", algorithm_class(self.redis))

            self._initialized = True

    async def shutdown(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            self.redis = None
        self._initialized = False

    async def check_limit(self, scope: RateLimitScope, key_values: Dict[str, str],
                         ip_address: Optional[str] = None) -> RateLimitResult:
        """Check rate limit for a specific scope and parameters."""
        await self.initialize()

        # Find applicable rule
        rule = None
        for r in self.rules:
            if r.scope == scope:
                rule = r
                break

        if not rule:
            # Default: allow if no rule defined
            return RateLimitResult(
                allowed=True,
                remaining=999,
                reset_time=datetime.utcnow() + timedelta(hours=1),
                limit=1000
            )

        # Format key
        key = rule.key_template.format(**key_values)

        # Check if organization is whitelisted
        if scope == RateLimitScope.TENANT and key_values.get('tenant_id') in self.config.TRUSTED_ORGANIZATIONS:
            return RateLimitResult(
                allowed=True,
                remaining=999999,
                reset_time=datetime.utcnow() + timedelta(hours=24),
                limit=1000000
            )

        # Get algorithm implementation
        algorithm_impl = getattr(self, f"{rule.algorithm.value}_impl")
        if not algorithm_impl:
            return RateLimitResult(
                allowed=True,
                remaining=999,
                reset_time=datetime.utcnow() + timedelta(hours=1),
                limit=1000
            )

        # Check limit
        result = await algorithm_impl.check_limit(
            key, rule.limit, rule.window_seconds, rule.burst_multiplier
        )

        # Log violation if not allowed
        if not result.allowed:
            violation = RateLimitViolation(
                scope=scope.value,
                key=key,
                requested=1,
                limit=rule.limit,
                ip_address=ip_address
            )

            # Check for abuse patterns
            abuse_pattern = self.abuse_detector.detect_patterns(violation)
            if abuse_pattern:
                logging.warning(f"Abuse pattern detected: {abuse_pattern.pattern_type} for {key}")
                # Could trigger kill switch or other actions here

            # Log violation
            await self._log_violation(violation)

        return result

    async def _log_violation(self, violation: RateLimitViolation):
        """Log rate limit violation."""
        try:
            # Store in Redis for monitoring
            violation_key = f"violations:{violation.scope}:{violation.key}"
            await self.redis.lpush(violation_key, violation.json())
            await self.redis.expire(violation_key, 86400)  # Keep for 24 hours
        except Exception as e:
            logging.error(f"Failed to log violation: {e}")

    async def get_limit_status(self, scope: RateLimitScope, key_values: Dict[str, str]) -> Dict:
        """Get current limit status without consuming tokens."""
        await self.initialize()

        rule = None
        for r in self.rules:
            if r.scope == scope:
                rule = r
                break

        if not rule:
            return {"limit": 1000, "remaining": 1000, "reset_time": None}

        key = rule.key_template.format(**key_values)

        # Try to get current status from Redis
        try:
            if rule.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
                tokens_key = f"{key}:tokens"
                tokens = await self.redis.get(tokens_key)
                tokens = int(tokens) if tokens else rule.limit

                return {
                    "limit": rule.limit,
                    "remaining": tokens,
                    "reset_time": datetime.utcnow() + timedelta(seconds=rule.window_seconds)
                }
            elif rule.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
                current_window = int(time.time() / rule.window_seconds)
                window_key = f"{key}:{current_window}"
                count = await self.redis.get(window_key)
                count = int(count) if count else 0

                return {
                    "limit": rule.limit,
                    "remaining": max(0, rule.limit - count),
                    "reset_time": datetime.fromtimestamp((current_window + 1) * rule.window_seconds)
                }
        except Exception as e:
            logging.error(f"Failed to get limit status: {e}")

        return {"limit": rule.limit, "remaining": rule.limit, "reset_time": None}

    async def reset_limits(self, scope: RateLimitScope, key_values: Dict[str, str]):
        """Reset rate limits for a specific scope/key."""
        await self.initialize()

        rule = None
        for r in self.rules:
            if r.scope == scope:
                rule = r
                break

        if rule:
            key = rule.key_template.format(**key_values)
            # Delete all related keys
            keys_to_delete = []
            if rule.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
                keys_to_delete = [f"{key}:tokens", f"{key}:last_refill"]
            elif rule.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
                # This is trickier - we'd need to find all window keys
                # For simplicity, we'll skip this for now
                pass

            if keys_to_delete:
                await self.redis.delete(*keys_to_delete)

# ===========================================
# FASTAPI INTEGRATION
# ===========================================

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

class RateLimitMiddleware:
    """FastAPI middleware for rate limiting."""

    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter

    async def __call__(self, request: Request, call_next):
        # Extract rate limiting context
        tenant_id = self._extract_tenant_id(request)
        campaign_id = self._extract_campaign_id(request)
        api_key = self._extract_api_key(request)
        ip_address = self._extract_ip_address(request)

        # Check applicable limits
        checks = []

        # API-wide limit
        if api_key:
            checks.append((
                RateLimitScope.API,
                {"api_key": api_key},
                ip_address
            ))

        # IP-based limit
        if ip_address:
            checks.append((
                RateLimitScope.IP_ADDRESS,
                {"ip_address": ip_address},
                ip_address
            ))

        # Tenant-specific limits
        if tenant_id:
            # Check email sending limits
            if "/email" in request.url.path or "/send" in request.url.path:
                checks.append((
                    RateLimitScope.TENANT,
                    {"tenant_id": tenant_id},
                    ip_address
                ))

        # Campaign-specific limits
        if campaign_id:
            checks.append((
                RateLimitScope.CAMPAIGN,
                {"campaign_id": campaign_id},
                ip_address
            ))

        # Execute rate limit checks
        for scope, key_values, ip in checks:
            try:
                result = await self.rate_limiter.check_limit(scope, key_values, ip)
                if not result.allowed:
                    # Return rate limit exceeded response
                    return JSONResponse(
                        status_code=429,
                        headers={
                            "X-RateLimit-Limit": str(result.limit),
                            "X-RateLimit-Remaining": str(result.remaining),
                            "X-RateLimit-Reset": str(int(result.reset_time.timestamp())),
                            "Retry-After": str(result.retry_after or 60)
                        },
                        content={
                            "error": "Rate limit exceeded",
                            "message": f"Too many requests. Try again after {result.reset_time.isoformat()}",
                            "retry_after": result.retry_after or 60
                        }
                    )
            except Exception as e:
                logging.error(f"Rate limit check failed: {e}")
                # Continue without rate limiting if check fails

        # Add rate limit headers to successful response
        response = await call_next(request)

        # Add rate limit headers
        if tenant_id:
            status = await self.rate_limiter.get_limit_status(
                RateLimitScope.TENANT, {"tenant_id": tenant_id}
            )
            response.headers["X-RateLimit-Limit"] = str(status["limit"])
            response.headers["X-RateLimit-Remaining"] = str(status["remaining"])

        return response

    def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request."""
        # Check headers
        tenant_id = request.headers.get("X-Tenant-ID") or request.headers.get("X-Organization-ID")
        if tenant_id:
            return tenant_id

        # Check query parameters
        tenant_id = request.query_params.get("tenant_id") or request.query_params.get("org_id")
        if tenant_id:
            return tenant_id

        # Check JWT token or session (would need authentication integration)
        return None

    def _extract_campaign_id(self, request: Request) -> Optional[str]:
        """Extract campaign ID from request."""
        # Check path parameters
        campaign_id = request.path_params.get("campaign_id")
        if campaign_id:
            return campaign_id

        # Check body (for POST requests)
        if hasattr(request, 'json'):
            try:
                body = request.json()
                if isinstance(body, dict):
                    return body.get("campaign_id")
            except:
                pass

        # Check query parameters
        return request.query_params.get("campaign_id")

    def _extract_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from request."""
        # Check headers
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")
        if api_key and api_key.startswith("Bearer "):
            api_key = api_key[7:]  # Remove "Bearer " prefix
        return api_key

    def _extract_ip_address(self, request: Request) -> Optional[str]:
        """Extract IP address from request."""
        # Check X-Forwarded-For header (for proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take first IP in case of multiple
            return forwarded_for.split(",")[0].strip()

        # Fall back to direct client IP
        return getattr(request.client, 'host', None) if request.client else None

# ===========================================
# UTILITY FUNCTIONS
# ===========================================

async def create_rate_limiter(config: RateLimitConfig = None) -> RateLimiter:
    """Factory function to create and initialize rate limiter."""
    rate_limiter = RateLimiter(config)
    await rate_limiter.initialize()
    return rate_limiter

def create_rate_limit_middleware(rate_limiter: RateLimiter) -> RateLimitMiddleware:
    """Factory function to create rate limiting middleware."""
    return RateLimitMiddleware(rate_limiter)

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
