"""Distributed Tracing with Correlation IDs.

Provides correlation-ID based request tracking using Python contextvars.
"""

import contextvars
from uuid import uuid4

# Context variable for correlation ID (request_id)
# This is async-safe and automatically propagates through async calls
correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
  'request_id', default='no-request-id'
)


def get_correlation_id() -> str:
  """Retrieve the current request's correlation ID.

  Returns:
      Current correlation ID (request_id) or 'no-request-id' if not set

  Usage:
      request_id = get_correlation_id()
      logger.info(f"Processing request {request_id}")
  """
  return correlation_id.get()


def set_correlation_id(request_id: str) -> None:
  """Set the correlation ID for the current request context.

  Args:
      request_id: Unique request identifier (usually UUID or X-Request-ID header)

  Usage:
      # In middleware or at request start
      set_correlation_id(str(uuid4()))
  """
  correlation_id.set(request_id)


def generate_correlation_id() -> str:
  """Generate a new correlation ID and set it in context.

  Returns:
      Generated correlation ID (UUID)

  Usage:
      # Auto-generate and set correlation ID
      request_id = generate_correlation_id()
  """
  request_id = str(uuid4())
  set_correlation_id(request_id)
  return request_id


def reset_correlation_id() -> None:
  """Reset correlation ID to default value.

  Useful for testing or cleanup after request processing.
  """
  correlation_id.set('no-request-id')
