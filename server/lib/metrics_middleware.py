"""
FastAPI middleware for automatic performance metric collection.

This middleware captures timing information for all API requests and records
performance metrics to the database. Collection failures do not impact request
processing (graceful degradation per FR-007).
"""

import logging
import time
from fastapi import Request
from server.services.metrics_service import MetricsService
from server.lib.database import get_db_session, is_lakebase_configured

logger = logging.getLogger(__name__)


async def metrics_collection_middleware(request: Request, call_next):
    """
    FastAPI middleware that automatically collects performance metrics.
    
    This middleware:
    1. Captures start time before request processing
    2. Calls the next middleware/endpoint
    3. Calculates response time
    4. Records metric to database (async, non-blocking)
    
    Gracefully degrades if metrics collection fails - errors are logged
    but do not impact the API response.
    
    Implements FR-001 exclusion criteria: Skips metrics collection for
    /health, /ready, /ping, /internal/*, and /admin/system/* paths.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware or endpoint in chain
        
    Returns:
        Response from the endpoint
    """
    # Capture start time
    start_time = time.time()
    
    # Process request through middleware chain and endpoint
    response = await call_next(request)
    
    # Calculate response time in milliseconds
    response_time_ms = (time.time() - start_time) * 1000
    
    # Extract request information
    endpoint = request.url.path
    method = request.method
    status_code = response.status_code
    
    # Support for unauthenticated requests (T048.5)
    # Set user_id to None if not present (validates edge case from spec.md:L148-150)
    user_id = getattr(request.state, 'user_id', None)  # From auth middleware
    
    # FR-001: Skip metrics collection for excluded paths
    excluded_paths = ['/health', '/ready', '/ping']
    excluded_prefixes = ['/internal/', '/admin/system/']
    
    # Check if path should be excluded
    if endpoint in excluded_paths or any(endpoint.startswith(prefix) for prefix in excluded_prefixes):
        return response
    
    # Classify errors
    error_type = None
    if status_code >= 400:
        if status_code < 500:
            error_type = f'CLIENT_ERROR_{status_code}'
        else:
            error_type = f'SERVER_ERROR_{status_code}'
    
    # Record metric (graceful degradation - don't block response)
    # Skip metrics collection if Lakebase is not configured
    if not is_lakebase_configured():
        logger.debug(
            f'Skipping performance metric collection for {method} {endpoint} - '
            f'Lakebase not configured'
        )
        return response
    
    try:
        # Get database session
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            metrics_service = MetricsService(db)
            
            # Record performance metric
            metrics_service.record_performance_metric({
                'endpoint': endpoint,
                'method': method,
                'status_code': status_code,
                'response_time_ms': response_time_ms,
                'user_id': user_id,
                'error_type': error_type,
            })
        finally:
            # Ensure session is closed properly
            try:
                next(db_gen, None)
            except StopIteration:
                pass
        
    except Exception as e:
        # Log error but don't fail the request
        # Suppress verbose stack traces for database connection errors
        if "Database instance is not found" in str(e):
            logger.warning(
                f'Skipping performance metric collection for {method} {endpoint} - '
                f'Lakebase instance not available'
            )
        else:
            logger.error(
                f'Failed to record performance metric for {method} {endpoint}: {e}'
            )
        # Continue - graceful degradation per FR-007
    
    return response

