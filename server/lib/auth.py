"""Authentication utilities for FastAPI endpoints.

Provides dependency functions for extracting user information from requests,
including middleware, retry logic, and authentication context management.
"""

import contextvars
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, Request

from server.lib.structured_logger import StructuredLogger
from server.models.user_session import AuthenticationContext
from server.services.user_service import UserService

logger = StructuredLogger(__name__)

# Context variable for correlation ID tracking
correlation_id_var = contextvars.ContextVar('correlation_id', default=None)


async def get_user_token(request: Request) -> str:
  """Extract required user access token from request state.

  The token is set by middleware from the X-Forwarded-Access-Token header.
  This enables On-Behalf-Of (OBO) authentication.

  Args:
      request: FastAPI request object

  Returns:
      User access token

  Raises:
      HTTPException: 401 if token is missing or empty
  """
  user_token = getattr(request.state, 'user_token', None)

  if not user_token:
    raise HTTPException(
      status_code=401,
      detail={
        'error_code': 'AUTH_MISSING',
        'message': 'User authentication required. Please provide a valid user access token.',
      },
    )

  return user_token


async def get_user_token_optional(request: Request) -> Optional[str]:
  """Extract optional user access token from request state.

  This function does NOT raise an exception if the token is missing.
  Use this ONLY for endpoints that support unauthenticated access,
  such as /health (public monitoring endpoint).

  Args:
      request: FastAPI request object

  Returns:
      User access token or None if not available
  """
  return getattr(request.state, 'user_token', None)


async def get_auth_context(request: Request) -> AuthenticationContext:
  """Get full authentication context for the request (OBO-only).

  Extracts authentication-related information from request state
  that was set by the middleware.

  Args:
      request: FastAPI request object

  Returns:
      AuthenticationContext with token and correlation ID

  Raises:
      HTTPException: 401 if user_token is missing
  """
  user_token = getattr(request.state, 'user_token', None)

  if not user_token:
    raise HTTPException(
      status_code=401,
      detail={
        'error_code': 'AUTH_MISSING',
        'message': 'User authentication required. Please provide a valid user access token.',
      },
    )

  return AuthenticationContext(
    user_token=user_token, correlation_id=getattr(request.state, 'correlation_id', '')
  )


async def get_current_user_id(request: Request) -> str:
  """Extract user ID (email) from authentication context using OBO-only.

  Requires valid user token for authentication. No fallback to service principal.

  Args:
      request: FastAPI request object

  Returns:
      User email string

  Raises:
      HTTPException: 401 if user_token is missing or authentication fails
  """
  # get_user_token will raise 401 if token is missing
  user_token = await get_user_token(request)

  # Get user info using UserService with OBO authentication
  service = UserService(user_token=user_token)
  user_identity = await service.get_user_info()
  user_email = user_identity.user_id

  logger.info(
    'Retrieved user information',
    user_id=user_email,
    display_name=user_identity.display_name,
    auth_method='obo',
    path=request.url.path,
  )

  return user_email


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
    self.state = 'closed'  # closed, open, half-open

  def record_success(self):
    """Reset circuit breaker on success."""
    if self.consecutive_failures > 0:
      logger.info(
        'auth.circuit_breaker_state_change',
        old_state=self.state,
        new_state='closed',
        consecutive_failures=0,
        cooldown_seconds=0,
      )
    self.consecutive_failures = 0
    self.state = 'closed'

  def record_failure(self):
    """Record failure and potentially open circuit."""
    self.consecutive_failures += 1
    self.last_failure_time = datetime.now()

    if self.consecutive_failures >= self.failure_threshold:
      old_state = self.state
      self.state = 'open'
      logger.warning(
        'auth.circuit_breaker_state_change',
        old_state=old_state,
        new_state='open',
        consecutive_failures=self.consecutive_failures,
        cooldown_seconds=self.cooldown_seconds,
      )

  def is_open(self):
    """Check if circuit should reject requests."""
    if self.state == 'open':
      # Check if cooldown period has passed
      if self.last_failure_time and datetime.now() - self.last_failure_time > timedelta(
        seconds=self.cooldown_seconds
      ):
        self.state = 'half-open'  # Allow one test request
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
      raise AuthenticationError('Circuit breaker open - too many failures')

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
          raise RateLimitError('Platform rate limit exceeded') from e

        # Check if error code indicates rate limiting
        if hasattr(e, 'error_code') and e.error_code == 'RESOURCE_EXHAUSTED':
          auth_circuit_breaker.record_failure()
          raise RateLimitError('Platform rate limit exceeded') from e

        # Record failure and check if we should retry
        auth_circuit_breaker.record_failure()

        # Log the retry attempt
        logger.warning(
          'auth.retry_attempt',
          error=str(e),
          attempt=attempt + 1,
          max_attempts=max_attempts,
          correlation_id=correlation_id_var.get(),
        )

        # If this is not the last attempt, wait before retrying
        if attempt < max_attempts - 1:
          await asyncio.sleep(delays[attempt])
        else:
          # Last attempt failed, raise the error
          raise AuthenticationError(
            f'Authentication failed after {max_attempts} attempts: {e}'
          ) from e

    # Should not reach here, but just in case
    raise AuthenticationError('Authentication failed - unexpected retry loop exit')

  return wrapper


async def get_admin_user(request: Request) -> dict:
  """FastAPI dependency that enforces admin-only access.

  This function checks if the authenticated user has Databricks workspace
  admin privileges. Non-admin users receive a 403 Forbidden response.

  Args:
      request: FastAPI request object

  Returns:
      Dictionary with user_id and email if user is admin

  Raises:
      HTTPException: 401 if token is missing
      HTTPException: 403 if user is not admin
      HTTPException: 503 if admin check API call fails
  """
  from databricks.sdk import WorkspaceClient

  from server.services.admin_service import is_workspace_admin_async

  # Extract user token (raises 401 if missing)
  user_token = await get_user_token(request)

  try:
    # Get user information
    client = WorkspaceClient(token=user_token)
    user = client.current_user.me()
    user_id = user.user_name

    # Check admin status (with 5-minute caching)
    if not await is_workspace_admin_async(user_token, user_id):
      logger.warning(f'Access denied for non-admin user: {user_id}', path=request.url.path)
      raise HTTPException(
        status_code=403,
        detail={
          'error': 'Access Denied',
          'message': 'Administrator privileges required to access metrics',
          'status_code': 403,
        },
      )

    logger.info(f'Admin access granted for user: {user_id}', path=request.url.path)
    return {'user_id': user_id, 'email': user.user_name}

  except HTTPException:
    # Re-raise HTTP exceptions (401, 403, 503)
    raise
  except Exception as e:
    logger.error(f'Admin check failed with unexpected error: {e}', exc_info=True)
    raise HTTPException(status_code=503, detail='Service unavailable') from e
