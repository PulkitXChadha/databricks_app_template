"""Authentication utilities for FastAPI endpoints.

Provides dependency functions for extracting user information from requests,
including middleware, retry logic, and authentication context management.
"""

import os
from typing import Optional
from fastapi import Request, HTTPException
from datetime import datetime, timedelta
import contextvars

from server.services.user_service import UserService
from server.lib.structured_logger import StructuredLogger
from server.models.user_session import AuthenticationContext

logger = StructuredLogger(__name__)

# Context variable for correlation ID tracking
correlation_id_var = contextvars.ContextVar('correlation_id', default=None)


async def get_user_token(request: Request) -> Optional[str]:
    """Extract user access token from request state.

    The token is set by middleware from the X-Forwarded-Access-Token header.
    This enables On-Behalf-Of (OBO) authentication.

    Args:
        request: FastAPI request object

    Returns:
        User access token or None if not available
    """
    return getattr(request.state, 'user_token', None)


async def get_auth_context(request: Request) -> AuthenticationContext:
    """Get full authentication context for the request.

    Extracts all authentication-related information from request state
    that was set by the middleware.

    Args:
        request: FastAPI request object

    Returns:
        AuthenticationContext with token, mode, and correlation ID
    """
    return AuthenticationContext(
        user_token=getattr(request.state, 'user_token', None),
        has_user_token=getattr(request.state, 'has_user_token', False),
        auth_mode=getattr(request.state, 'auth_mode', 'service_principal'),
        correlation_id=getattr(request.state, 'correlation_id', '')
    )


async def get_current_user_id(request: Request) -> str:
    """Extract user ID (email) from authentication context.
    
    Works in multiple scenarios:
    1. Databricks Apps (deployed): Uses user token from X-Forwarded-Access-Token header
    2. Local with OAuth: Uses service principal OAuth credentials via UserService
    3. Local without auth: Falls back to "dev-user@example.com"
    
    Args:
        request: FastAPI request object
        
    Returns:
        User email string
    """
    user_token = await get_user_token(request)
    databricks_host = os.getenv('DATABRICKS_HOST')
    
    # Try to get user info using UserService (works with or without user_token)
    # When user_token is provided (Databricks Apps), it uses OBO authentication
    # When user_token is None (local dev), it uses service principal OAuth if available
    try:
        service = UserService(user_token=user_token)
        user_identity = await service.get_user_info()
        user_email = user_identity.user_id
        
        auth_method = "user_token" if user_token else "service_principal"
        logger.info(
            "Retrieved user information",
            user_id=user_email,
            display_name=user_identity.display_name,
            auth_method=auth_method,
            has_databricks_host=bool(databricks_host),
            path=request.url.path
        )
        
        return user_email
        
    except Exception as e:
        # If we can't get user info, fall back to dev user
        # This happens when:
        # - No Databricks authentication is configured
        # - Network/API errors
        # - Invalid credentials
        logger.warning(
            f"Failed to get user info, falling back to dev user: {str(e)}",
            exc_info=True,
            has_token=bool(user_token),
            has_databricks_host=bool(databricks_host),
            path=request.url.path,
            error_type=type(e).__name__
        )
        return "dev-user@example.com"


# Authentication exceptions
class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    pass


# Circuit breaker for authentication failures (per-instance only)
class CircuitBreaker:
    """Simple per-instance circuit breaker to prevent retry storms.

    This is NOT distributed - each application instance maintains
    its own circuit breaker state in memory.
    """

    def __init__(self, failure_threshold: int = 10, cooldown_seconds: int = 30):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.consecutive_failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def record_success(self):
        """Reset circuit breaker on success."""
        if self.consecutive_failures > 0:
            logger.info(
                "auth.circuit_breaker_state_change",
                old_state=self.state,
                new_state="closed",
                consecutive_failures=0,
                cooldown_seconds=0
            )
        self.consecutive_failures = 0
        self.state = "closed"

    def record_failure(self):
        """Record failure and potentially open circuit."""
        self.consecutive_failures += 1
        self.last_failure_time = datetime.now()

        if self.consecutive_failures >= self.failure_threshold:
            old_state = self.state
            self.state = "open"
            logger.warning(
                "auth.circuit_breaker_state_change",
                old_state=old_state,
                new_state="open",
                consecutive_failures=self.consecutive_failures,
                cooldown_seconds=self.cooldown_seconds
            )

    def is_open(self):
        """Check if circuit should reject requests."""
        if self.state == "open":
            # Check if cooldown period has passed
            if self.last_failure_time and \
               datetime.now() - self.last_failure_time > timedelta(seconds=self.cooldown_seconds):
                self.state = "half-open"  # Allow one test request
                return False
            return True
        return False


# Single per-instance circuit breaker (not shared across processes)
auth_circuit_breaker = CircuitBreaker()


def with_auth_retry(func):
    """Decorator for retry logic with exponential backoff on authentication failures.

    Implements retry logic with:
    - 3 attempts maximum
    - Exponential backoff: 100ms, 200ms, 400ms
    - Circuit breaker integration
    - Rate limit detection (fails immediately on 429)
    - Total timeout < 5 seconds

    Args:
        func: Async function to wrap with retry logic

    Returns:
        Wrapped function with retry capabilities
    """
    import asyncio
    from functools import wraps

    @wraps(func)
    async def wrapper(*args, **kwargs):
        """Wrapper function with retry logic."""
        # Check circuit breaker state (per-instance only)
        if auth_circuit_breaker.is_open():
            raise AuthenticationError("Circuit breaker open - too many failures")

        max_attempts = 3
        delays = [0.1, 0.2, 0.4]  # 100ms, 200ms, 400ms

        for attempt in range(max_attempts):
            try:
                # Call the original function
                result = await func(*args, **kwargs)
                auth_circuit_breaker.record_success()
                return result

            except Exception as e:
                # Check if it's a rate limit error (should fail immediately)
                if hasattr(e, 'status_code') and e.status_code == 429:
                    auth_circuit_breaker.record_failure()
                    raise RateLimitError("Platform rate limit exceeded") from e

                # Check if error code indicates rate limiting
                if hasattr(e, 'error_code') and e.error_code == "RESOURCE_EXHAUSTED":
                    auth_circuit_breaker.record_failure()
                    raise RateLimitError("Platform rate limit exceeded") from e

                # Record failure and check if we should retry
                auth_circuit_breaker.record_failure()

                # Log the retry attempt
                logger.warning(
                    "auth.retry_attempt",
                    error=str(e),
                    attempt=attempt + 1,
                    max_attempts=max_attempts,
                    correlation_id=correlation_id_var.get()
                )

                # If this is not the last attempt, wait before retrying
                if attempt < max_attempts - 1:
                    await asyncio.sleep(delays[attempt])
                else:
                    # Last attempt failed, raise the error
                    raise AuthenticationError(f"Authentication failed after {max_attempts} attempts: {e}") from e

        # Should not reach here, but just in case
        raise AuthenticationError("Authentication failed - unexpected retry loop exit")

    return wrapper

