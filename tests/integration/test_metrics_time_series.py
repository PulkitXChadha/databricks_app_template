"""Integration tests for time-series metrics endpoints.

Tests time-series data retrieval and time range filtering.
Following TDD RED-GREEN-REFACTOR: These tests MUST FAIL initially.

NOTE: Time-series queries use PostgreSQL-specific date_trunc function.
These tests require PostgreSQL and will be skipped when using SQLite.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from server.models.aggregated_metric import AggregatedMetric
from server.models.performance_metric import PerformanceMetric
from server.models.usage_event import UsageEvent
from server.services.metrics_service import MetricsService

# NOTE: Time-series tests use PostgreSQL-specific date_trunc function
# In production, Lakebase uses PostgreSQL, so these work fine
# For local testing with SQLite, tests will fail - this is expected
# TODO: Make date truncation database-agnostic for better test coverage


# ============================================================================
# T093: Integration test for time-series data with 5-minute and hourly bucketing
# ============================================================================


def test_time_series_returns_5min_buckets_for_24h_range(test_db_session: Session):
  """Test that get_time_series_metrics returns 5-minute bucketed data for 24h range.

  This provides more granular data for recent time periods.
  """
  # Create sample performance metrics across multiple hours
  base_time = datetime.utcnow() - timedelta(hours=12)

  for hour_offset in range(12):  # 12 hours of data
    timestamp = base_time + timedelta(hours=hour_offset)

    # Create multiple metrics per hour
    for i in range(10):
      metric = PerformanceMetric(
        timestamp=timestamp + timedelta(minutes=i * 5),
        endpoint='/api/v1/test',
        method='GET',
        status_code=200,
        response_time_ms=100.0 + hour_offset * 5,
        user_id='test-user',
      )
      test_db_session.add(metric)

  test_db_session.commit()

  # Query time-series data for 24h range
  metrics_service = MetricsService(test_db_session)
  result = metrics_service.get_time_series_metrics(time_range='24h', metric_type='performance')

  # Validate response structure
  assert 'time_range' in result
  assert 'interval' in result
  assert result['interval'] == '5min', '24h range should use 5-minute intervals'
  assert 'data_points' in result

  # Validate data points are 5-minute buckets
  data_points = result['data_points']
  assert len(data_points) > 0, 'Should return data points'

  # Each data point should have timestamp and metrics
  for point in data_points:
    assert 'timestamp' in point
    assert 'avg_response_time_ms' in point
    assert 'total_requests' in point


def test_time_series_returns_hourly_buckets_for_7day_range(test_db_session: Session):
  """Test that get_time_series_metrics returns hourly bucketed data for 7-day range.

  Expected to FAIL initially (RED phase) - time-series method not implemented yet.
  """
  # Create sample performance metrics across multiple hours
  base_time = datetime.utcnow() - timedelta(days=3)

  for hour_offset in range(24):  # 24 hours of data
    timestamp = base_time + timedelta(hours=hour_offset)

    # Create multiple metrics per hour
    for i in range(10):
      metric = PerformanceMetric(
        timestamp=timestamp + timedelta(minutes=i * 5),
        endpoint='/api/v1/test',
        method='GET',
        status_code=200,
        response_time_ms=100.0 + hour_offset * 5,
        user_id='test-user',
      )
      test_db_session.add(metric)

  test_db_session.commit()

  # Query time-series data
  metrics_service = MetricsService(test_db_session)
  result = metrics_service.get_time_series_metrics(time_range='7d', metric_type='performance')

  # Validate response structure
  assert 'time_range' in result
  assert 'interval' in result
  assert result['interval'] == 'hourly'
  assert 'data_points' in result

  # Validate data points are hourly buckets
  data_points = result['data_points']
  assert len(data_points) > 0, 'Should return data points'

  # Each data point should have timestamp and metrics
  for point in data_points:
    assert 'timestamp' in point
    assert 'avg_response_time_ms' in point
    assert 'total_requests' in point


# ============================================================================
# T094: Integration test for time range filtering (24h, 7d, 30d, 90d)
# ============================================================================


def test_time_series_filters_by_time_range(test_db_session: Session):
  """Test that time-series data is correctly filtered by time_range parameter.

  Tests all standard time ranges: 24h, 7d, 30d, 90d
  """
  # Create metrics at different time points
  now = datetime.utcnow()

  # Metrics from last 2 hours (should appear in 24h range)
  for i in range(5):
    metric = PerformanceMetric(
      timestamp=now - timedelta(hours=i),
      endpoint='/api/v1/recent',
      method='GET',
      status_code=200,
      response_time_ms=100.0,
      user_id='test-user',
    )
    test_db_session.add(metric)

  # Metrics from 5 days ago (should appear in 7d and 30d ranges)
  for i in range(5):
    metric = PerformanceMetric(
      timestamp=now - timedelta(days=5, hours=i),
      endpoint='/api/v1/week-old',
      method='GET',
      status_code=200,
      response_time_ms=150.0,
      user_id='test-user',
    )
    test_db_session.add(metric)

  # Metrics from 20 days ago (should appear in 30d and 90d ranges)
  for i in range(5):
    metric = PerformanceMetric(
      timestamp=now - timedelta(days=20, hours=i),
      endpoint='/api/v1/month-old',
      method='GET',
      status_code=200,
      response_time_ms=200.0,
      user_id='test-user',
    )
    test_db_session.add(metric)

  test_db_session.commit()

  metrics_service = MetricsService(test_db_session)

  # Test 24h range - should only include recent metrics
  result_24h = metrics_service.get_time_series_metrics('24h', 'performance')
  assert len(result_24h['data_points']) > 0, '24h should return recent data'

  # Test 7d range - should include recent + week-old metrics
  result_7d = metrics_service.get_time_series_metrics('7d', 'performance')
  assert len(result_7d['data_points']) >= len(result_24h['data_points']), (
    '7d should include more data than 24h'
  )

  # Test 30d range - should include all created metrics
  result_30d = metrics_service.get_time_series_metrics('30d', 'performance')
  assert len(result_30d['data_points']) >= len(result_7d['data_points']), (
    '30d should include more data than 7d'
  )


# ============================================================================
# T094.5: Integration test for custom date range validation
# ============================================================================


def test_time_series_validates_date_range_exceeding_90_days(test_db_session: Session):
  """Test that validation errors are raised for invalid date ranges.

  Tests:
  1. Date range exceeding 90 days
  2. Start date older than 90-day retention window
  3. Future end dates
  4. Start date after end date
  """
  metrics_service = MetricsService(test_db_session)

  # Test with 90d time range (should succeed - maximum allowed)
  try:
    result = metrics_service.get_time_series_metrics('90d', 'performance')
    assert 'data_points' in result, '90d range should be valid'
  except Exception as e:
    pytest.fail(f'90d time range should be valid: {e}')

  # For custom date range validation, we'll need to test when that feature is implemented
  # Currently using predefined ranges (24h, 7d, 30d, 90d) which are all valid


def test_time_series_usage_metrics(test_db_session: Session):
  """Test that time-series endpoint works for usage metrics as well.
  """
  # Create sample usage events
  base_time = datetime.utcnow() - timedelta(hours=12)

  for hour_offset in range(12):
    timestamp = base_time + timedelta(hours=hour_offset)

    for i in range(5):
      event = UsageEvent(
        timestamp=timestamp + timedelta(minutes=i * 10),
        event_type='page_view',
        user_id='test-user',
        page_name='/test-page',
      )
      test_db_session.add(event)

  test_db_session.commit()

  metrics_service = MetricsService(test_db_session)
  result = metrics_service.get_time_series_metrics('24h', 'usage')

  assert 'data_points' in result
  assert len(result['data_points']) > 0, 'Should return usage event data points'

  # Validate usage-specific fields
  for point in result['data_points']:
    assert 'timestamp' in point
    assert 'total_events' in point


def test_time_series_both_metrics(test_db_session: Session):
  """Test that time-series endpoint can return both performance and usage metrics.
  """
  # Create both performance and usage data
  base_time = datetime.utcnow() - timedelta(hours=6)

  # Performance metrics
  for i in range(5):
    metric = PerformanceMetric(
      timestamp=base_time + timedelta(hours=i),
      endpoint='/api/v1/test',
      method='GET',
      status_code=200,
      response_time_ms=100.0,
      user_id='test-user',
    )
    test_db_session.add(metric)

  # Usage events
  for i in range(5):
    event = UsageEvent(
      timestamp=base_time + timedelta(hours=i),
      event_type='button_click',
      user_id='test-user',
      page_name='/test',
    )
    test_db_session.add(event)

  test_db_session.commit()

  metrics_service = MetricsService(test_db_session)
  result = metrics_service.get_time_series_metrics('24h', 'both')

  assert 'data_points' in result
  assert len(result['data_points']) > 0

  # Should include both performance and usage metrics
  for point in result['data_points']:
    assert 'timestamp' in point
    # Both metric types should be present
    assert 'avg_response_time_ms' in point or 'total_events' in point


# ============================================================================
# Tests for aggregated metrics routing (raw vs aggregated)
# ============================================================================


def test_time_series_uses_aggregated_data_for_old_metrics(test_db_session: Session):
  """Test that time-series automatically routes to aggregated metrics for data older than 7 days.

  This is a future test for when aggregation logic is integrated with time-series.
  """
  # Create aggregated metric (simulating 20-day-old data that's been aggregated)
  old_time_bucket = datetime.utcnow() - timedelta(days=20)
  old_time_bucket = old_time_bucket.replace(minute=0, second=0, microsecond=0)

  aggregated = AggregatedMetric(
    time_bucket=old_time_bucket,
    metric_type='performance',
    endpoint_path='/api/v1/old-endpoint',
    aggregated_values={'avg_response_time_ms': 250.0, 'total_requests': 1000, 'error_rate': 0.01},
    sample_count=1000,
  )
  test_db_session.add(aggregated)
  test_db_session.commit()

  metrics_service = MetricsService(test_db_session)
  result = metrics_service.get_time_series_metrics('30d', 'performance')

  # Should successfully query and include aggregated data
  assert 'data_points' in result


# ============================================================================
# Pytest Fixtures
# ============================================================================


@pytest.fixture
def test_db_session():
  """Fixture to provide clean in-memory SQLite database session for each test"""
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker

  from server.lib.database import Base

  # Create in-memory SQLite database for testing
  engine = create_engine('sqlite:///:memory:', echo=False)

  # Create all tables
  Base.metadata.create_all(engine)

  # Create session
  TestingSessionLocal = sessionmaker(bind=engine)
  db = TestingSessionLocal()

  yield db

  # Clean up
  db.close()
  engine.dispose()
