"""Metrics API endpoints for performance and usage metrics.

All metrics retrieval endpoints require administrator privileges.
Usage event submission requires authentication but not admin.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from server.lib.auth import get_admin_user, get_user_token
from server.lib.database import get_db_session, is_lakebase_configured
from server.services.metrics_service import MetricsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v1/metrics', tags=['Metrics'])


# Pydantic models for request/response validation


class UsageEventInput(BaseModel):
  """Individual usage event from frontend."""

  event_type: str = Field(..., description='Type of user interaction')
  page_name: Optional[str] = Field(None, max_length=255, description='Page/route name')
  element_id: Optional[str] = Field(None, max_length=255, description='UI element identifier')
  success: Optional[bool] = Field(None, description='Whether action succeeded')
  metadata: Optional[dict] = Field(None, description='Additional context (flexible JSON)')
  timestamp: str = Field(..., description='Event timestamp (ISO 8601)')


class UsageEventBatchRequest(BaseModel):
  """Batch submission of usage events."""

  events: List[UsageEventInput] = Field(
    ..., min_length=1, description='Array of usage events (max 1000 per batch)'
  )

  @field_validator('events')
  @classmethod
  def validate_batch_size(cls, v):
    """Enforce FR-012: Maximum batch size of 1000 events.

    Raises ValueError with specific message that will be caught by
    custom exception handler (FR-013) and converted to 413 status code.
    """
    if len(v) > 1000:
      raise ValueError(f'Batch size exceeds maximum of 1000 events (received: {len(v)})')
    return v


class UsageEventBatchResponse(BaseModel):
  """Response for batch usage event submission."""

  message: str = Field(..., description='Status message')
  events_received: int = Field(..., description='Number of events accepted')
  status: str = Field(..., description='Processing status')


class TimeSeriesDataPoint(BaseModel):
  """Single data point in time-series."""

  timestamp: str = Field(..., description='Time bucket timestamp (ISO 8601)')
  avg_response_time_ms: Optional[float] = Field(
    None, description='Average response time (performance)'
  )
  total_requests: Optional[int] = Field(None, description='Total requests (performance)')
  error_rate: Optional[float] = Field(None, description='Error rate (performance)')
  total_events: Optional[int] = Field(None, description='Total usage events')
  unique_users: Optional[int] = Field(None, description='Unique users in bucket')


class TimeSeriesMetricsResponse(BaseModel):
  """Response for time-series metrics endpoint."""

  time_range: str = Field(..., description='Time range covered')
  interval: str = Field(..., description='Time bucket interval (hourly, daily)')
  data_points: List[TimeSeriesDataPoint] = Field(..., description='Time-series data points')


@router.get('/performance')
async def get_performance_metrics(
  admin_user=Depends(get_admin_user),  # Admin-only
  time_range: str = Query('24h', pattern='^(24h|7d|30d|90d)$'),
  endpoint: Optional[str] = None,
  db: Session = Depends(get_db_session),
):
  """Get performance metrics (admin only).

  Retrieves aggregated performance metrics for API requests over the
  specified time period. Automatically routes to raw metrics (<7 days)
  or aggregated metrics (8-90 days).

  Args:
      admin_user: Admin user info (from dependency)
      time_range: Time range ("24h", "7d", "30d", "90d")
      endpoint: Optional endpoint path filter
      db: Database session

  Returns:
      Dictionary with performance metrics
  """
  # Check if Lakebase is configured
  if not is_lakebase_configured():
    raise HTTPException(
      status_code=503, detail='Metrics service unavailable: Lakebase database not configured'
    )

  logger.info(
    f'Performance metrics requested by admin user {admin_user["user_id"]} '
    f'(time_range={time_range}, endpoint={endpoint})'
  )

  metrics_service = MetricsService(db)
  return metrics_service.get_performance_metrics(time_range, endpoint)


@router.get('/usage')
async def get_usage_metrics(
  admin_user=Depends(get_admin_user),  # Admin-only
  time_range: str = Query('24h', pattern='^(24h|7d|30d|90d)$'),
  event_type: Optional[str] = None,
  db: Session = Depends(get_db_session),
):
  """Get usage metrics (admin only).

  Retrieves aggregated usage metrics for user interactions over the
  specified time period.

  Args:
      admin_user: Admin user info (from dependency)
      time_range: Time range ("24h", "7d", "30d", "90d")
      event_type: Optional event type filter
      db: Database session

  Returns:
      Dictionary with usage metrics
  """
  # Check if Lakebase is configured
  if not is_lakebase_configured():
    raise HTTPException(
      status_code=503, detail='Metrics service unavailable: Lakebase database not configured'
    )

  logger.info(
    f'Usage metrics requested by admin user {admin_user["user_id"]} '
    f'(time_range={time_range}, event_type={event_type})'
  )

  metrics_service = MetricsService(db)
  return metrics_service.get_usage_metrics(time_range, event_type)


@router.post('/usage-events', status_code=202, response_model=UsageEventBatchResponse)
async def submit_usage_events(
  request: UsageEventBatchRequest,
  user_token: str = Depends(get_user_token),  # Authenticated, not admin-only
  db: Session = Depends(get_db_session),
):
  """Submit batch usage events (any authenticated user).

  Accepts a batch of usage events from the frontend. Events are processed
  asynchronously to avoid blocking the response.

  Args:
      request: Batch of usage events
      user_token: User authentication token
      db: Database session

  Returns:
      Confirmation with count of events received
  """
  # Check if Lakebase is configured
  if not is_lakebase_configured():
    raise HTTPException(
      status_code=503, detail='Metrics service unavailable: Lakebase database not configured'
    )

  from databricks.sdk import WorkspaceClient

  # Get user ID from token
  client = WorkspaceClient(token=user_token)
  user = client.current_user.me()
  user_id = user.user_name

  logger.info(f'Received {len(request.events)} usage events from user {user_id}')

  # Record events
  metrics_service = MetricsService(db)
  events_count = metrics_service.record_usage_events_batch(
    [event.model_dump() for event in request.events], user_id
  )

  return UsageEventBatchResponse(
    message='Events accepted', events_received=events_count, status='processing'
  )


@router.get('/usage/count')
async def get_usage_count(
  user_token: str = Depends(get_user_token),  # Authenticated, not admin-only
  time_range: str = Query('24h', pattern='^(24h|7d|30d|90d)$'),
  db: Session = Depends(get_db_session),
):
  """Get usage event count for authenticated user (T082.6, T082.7).

  Used by frontend UsageTracker to reconcile sent event count with
  backend persisted count for data loss validation (<0.1% threshold).

  Args:
      user_token: User authentication token
      time_range: Time range ("24h", "7d", "30d", "90d")
      db: Database session

  Returns:
      Dictionary with event count and time range details
  """
  # Check if Lakebase is configured
  if not is_lakebase_configured():
    raise HTTPException(
      status_code=503, detail='Metrics service unavailable: Lakebase database not configured'
    )

  from datetime import datetime, timedelta

  from databricks.sdk import WorkspaceClient
  from sqlalchemy import and_

  from server.models.usage_event import UsageEvent

  # Get user ID from token
  client = WorkspaceClient(token=user_token)
  user = client.current_user.me()
  user_id = user.user_name

  # Parse time range
  end_time = datetime.utcnow()
  if time_range == '24h':
    start_time = end_time - timedelta(hours=24)
  elif time_range == '7d':
    start_time = end_time - timedelta(days=7)
  elif time_range == '30d':
    start_time = end_time - timedelta(days=30)
  elif time_range == '90d':
    start_time = end_time - timedelta(days=90)
  else:
    start_time = end_time - timedelta(hours=24)

  # Query usage events count for this user
  count = (
    db.query(UsageEvent)
    .filter(
      and_(
        UsageEvent.user_id == user_id,
        UsageEvent.timestamp >= start_time,
        UsageEvent.timestamp <= end_time,
      )
    )
    .count()
  )

  logger.info(f'Usage count query for user {user_id}: {count} events in {time_range}')

  return {
    'count': count,
    'time_range': time_range,
    'start_time': start_time.isoformat(),
    'end_time': end_time.isoformat(),
  }


@router.get('/time-series', response_model=TimeSeriesMetricsResponse)
async def get_time_series_metrics(
  admin_user=Depends(get_admin_user),  # Admin-only
  time_range: str = Query('24h', pattern='^(24h|7d|30d|90d)$'),
  metric_type: str = Query(..., pattern='^(performance|usage|both)$'),
  db: Session = Depends(get_db_session),
):
  """Get time-series metrics data for chart visualization (admin only).

  Returns hourly data points for the specified time range and metric type.
  Automatically routes to raw metrics (<7 days) or aggregated metrics (8-90 days).

  Args:
      admin_user: Admin user info (from dependency)
      time_range: Time range ("24h", "7d", "30d", "90d")
      metric_type: Type of metrics ("performance", "usage", "both")
      db: Database session

  Returns:
      TimeSeriesMetricsResponse with hourly data points
  """
  # Check if Lakebase is configured
  if not is_lakebase_configured():
    raise HTTPException(
      status_code=503, detail='Metrics service unavailable: Lakebase database not configured'
    )

  logger.info(
    f'Time-series metrics requested by admin user {admin_user["user_id"]} '
    f'(time_range={time_range}, metric_type={metric_type})'
  )

  metrics_service = MetricsService(db)
  return metrics_service.get_time_series_metrics(time_range, metric_type)
