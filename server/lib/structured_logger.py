"""Structured Logger with JSON Formatting.

Provides structured logging with JSON output for machine-readable logs.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from server.lib.distributed_tracing import get_correlation_id


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'request_id': get_correlation_id()
        }

        # Add optional context fields
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        if hasattr(record, 'endpoint'):
            log_data['endpoint'] = record.endpoint
        if hasattr(record, 'status_code'):
            log_data['status_code'] = record.status_code

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None
            }

        return json.dumps(log_data)


class StructuredLogger:
    """Structured logger with JSON formatting.

    Usage:
        logger = StructuredLogger(__name__)
        logger.info("API request", extra={"endpoint": "/api/user/me", "duration_ms": 50})
        logger.error("Database error", exc_info=True)
    """

    def __init__(self, name: str):
        """Initialize structured logger.

        Args:
            name: Logger name (typically module name)
        """
        self.logger = logging.getLogger(name)

        # Set log level from environment variable (default to INFO)
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        level = getattr(logging, log_level, logging.INFO)
        self.logger.setLevel(level)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Add JSON formatter
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)

        # Prevent propagation to avoid duplicate logs
        self.logger.propagate = False

    def info(self, message: str, **extra: Any) -> None:
        """Log INFO level message.

        Args:
            message: Log message
            **extra: Additional context (user_id, duration_ms, etc.)
        """
        self.logger.info(message, extra=extra)

    def warning(self, message: str, exc_info: bool = False, **extra: Any) -> None:
        """Log WARNING level message.

        Args:
            message: Log message
            exc_info: Include exception traceback
            **extra: Additional context
        """
        self.logger.warning(message, exc_info=exc_info, extra=extra)

    def error(self, message: str, exc_info: bool = False, **extra: Any) -> None:
        """Log ERROR level message.

        Args:
            message: Log message
            exc_info: Include exception traceback
            **extra: Additional context
        """
        self.logger.error(message, exc_info=exc_info, extra=extra)

    def debug(self, message: str, **extra: Any) -> None:
        """Log DEBUG level message.

        Args:
            message: Log message
            **extra: Additional context
        """
        self.logger.debug(message, extra=extra)

    def log_event(self, event: str, level: str = 'INFO', context: Optional[Dict[str, Any]] = None) -> None:
        """Log structured event with authentication context.

        This method supports event-based logging for authentication and observability.
        Automatically filters sensitive data (tokens, passwords) from logs.

        Args:
            event: Event name (e.g., "auth.token_extraction", "auth.mode")
            level: Log level (INFO, WARNING, ERROR, DEBUG)
            context: Additional context dictionary (filtered for sensitive data)

        Example:
            logger.log_event("auth.token_extraction", context={"has_token": True, "endpoint": "/api/user/me"})
            logger.log_event("auth.retry_attempt", level="WARNING", context={"attempt": 2, "error_type": "AuthenticationError"})
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': level.upper(),
            'event': event,
            'correlation_id': get_correlation_id(),
            **(context or {})
        }

        # Never log sensitive data (per NFR-004)
        sensitive_keys = ['token', 'password', 'user_token', 'client_secret', 'access_token']
        for key in sensitive_keys:
            if key in log_entry:
                del log_entry[key]

        # Output as JSON
        print(json.dumps(log_entry))


# Convenience functions for logging without creating logger instance
def log_info(message: str, **context: Any) -> None:
    """Log INFO level message with correlation ID.

    Args:
        message: Log message
        **context: Additional context fields
    """
    log_data = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'level': 'INFO',
        'message': message,
        'request_id': get_correlation_id(),
        **context
    }
    print(json.dumps(log_data))


def log_error(message: str, error: Exception | None = None, **context: Any) -> None:
    """Log ERROR level message with correlation ID and error details.

    Args:
        message: Log message
        error: Exception instance
        **context: Additional context fields
    """
    log_data = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'level': 'ERROR',
        'message': message,
        'request_id': get_correlation_id(),
        **context
    }

    if error:
        log_data['error_type'] = type(error).__name__
        log_data['error_message'] = str(error)

    print(json.dumps(log_data))


def log_request(endpoint: str, method: str, status_code: int, duration_ms: float, user_id: str | None = None) -> None:
    """Log API request with performance metrics.

    Args:
        endpoint: API endpoint path
        method: HTTP method
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        user_id: Optional user identifier
    """
    log_data = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'level': 'INFO',
        'message': f'{method} {endpoint}',
        'request_id': get_correlation_id(),
        'endpoint': endpoint,
        'method': method,
        'status_code': status_code,
        'duration_ms': duration_ms
    }

    if user_id:
        log_data['user_id'] = user_id

    print(json.dumps(log_data))


def log_event(event: str, level: str = 'INFO', context: Optional[Dict[str, Any]] = None) -> None:
    """Convenience function for event-based logging without creating logger instance.

    Automatically filters sensitive data (tokens, passwords) and includes correlation ID.

    Args:
        event: Event name (e.g., "auth.token_extraction", "auth.mode")
        level: Log level (INFO, WARNING, ERROR, DEBUG)
        context: Additional context dictionary

    Example:
        log_event("auth.token_extraction", context={"has_token": True, "endpoint": "/api/user/me"})
        log_event("auth.mode", context={"mode": "obo", "auth_type": "pat"})
    """
    log_entry = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'level': level.upper(),
        'event': event,
        'correlation_id': get_correlation_id(),
        **(context or {})
    }

    # Never log sensitive data (per NFR-004)
    sensitive_keys = ['token', 'password', 'user_token', 'client_secret', 'access_token']
    for key in sensitive_keys:
        if key in log_entry:
            del log_entry[key]

    print(json.dumps(log_entry))


# Export a default logger instance for module-level use
logger = StructuredLogger(__name__)
