"""Prometheus-compatible metrics for authentication and performance monitoring.

Implements NFR-011, NFR-012 from spec.md.
"""

from prometheus_client import Counter, Histogram, Gauge


# Authentication metrics
auth_requests_total = Counter(
    'auth_requests_total',
    'Total authentication attempts',
    ['endpoint', 'mode', 'status']
)

auth_retry_total = Counter(
    'auth_retry_total',
    'Total authentication retry attempts',
    ['endpoint', 'attempt_number']
)

# Performance metrics
request_duration_seconds = Histogram(
    'request_duration_seconds',
    'Request duration in seconds',
    ['endpoint', 'method', 'status'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0]
)

auth_overhead_seconds = Histogram(
    'auth_overhead_seconds',
    'Authentication overhead in seconds',
    ['mode'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1]
)

upstream_api_duration_seconds = Histogram(
    'upstream_api_duration_seconds',
    'Upstream API call duration',
    ['service', 'operation'],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0]
)

# User metrics
active_users_gauge = Gauge(
    'active_users',
    'Number of active users in last 5 minutes'
)


def record_auth_request(endpoint: str, mode: str, status: str):
    """Record an authentication request attempt.

    Args:
        endpoint: API endpoint path
        mode: Authentication mode ('obo' only - always OBO authentication)
        status: Request status ('success' or 'failure')
    """
    auth_requests_total.labels(
        endpoint=endpoint,
        mode=mode,
        status=status
    ).inc()


def record_auth_retry(endpoint: str, attempt_number: int):
    """Record an authentication retry attempt.

    Args:
        endpoint: API endpoint path
        attempt_number: Retry attempt number (1, 2, 3, ...)
    """
    auth_retry_total.labels(
        endpoint=endpoint,
        attempt_number=str(attempt_number)
    ).inc()


def record_request_duration(endpoint: str, method: str, status: int, duration_seconds: float):
    """Record overall request duration.

    Args:
        endpoint: API endpoint path
        method: HTTP method (GET, POST, etc.)
        status: HTTP status code
        duration_seconds: Request duration in seconds
    """
    request_duration_seconds.labels(
        endpoint=endpoint,
        method=method,
        status=str(status)
    ).observe(duration_seconds)


def record_auth_overhead(mode: str, overhead_seconds: float):
    """Record authentication overhead.

    Args:
        mode: Authentication mode ('obo' only - always OBO authentication)
        overhead_seconds: Authentication overhead in seconds
    """
    auth_overhead_seconds.labels(mode=mode).observe(overhead_seconds)


def record_upstream_api_call(service: str, operation: str, duration_seconds: float):
    """Record upstream API call duration.

    Args:
        service: Service name ('databricks', 'unity_catalog', 'model_serving', etc.)
        operation: Operation name ('get_user_info', 'list_catalogs', etc.)
        duration_seconds: API call duration in seconds
    """
    upstream_api_duration_seconds.labels(
        service=service,
        operation=operation
    ).observe(duration_seconds)


def update_active_users_count(count: int):
    """Update the active users gauge.

    Args:
        count: Number of active users in the last 5 minutes
    """
    active_users_gauge.set(count)

