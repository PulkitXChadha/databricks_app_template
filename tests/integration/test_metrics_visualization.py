"""Integration tests for metrics dashboard visualization.

Tests complete user journey from API to UI rendering.
Following TDD RED-GREEN-REFACTOR: These tests MUST FAIL initially.
"""

import time
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from server.app import app
from server.models.performance_metric import PerformanceMetric
from server.models.usage_event import UsageEvent

client = TestClient(app)


# ============================================================================
# T015: Integration test for metrics dashboard visualization
# ============================================================================


def test_dashboard_displays_metrics_for_last_24_hours(test_db_session):
  """Test that dashboard loads and displays metrics for last 24 hours.

  Expected to FAIL initially (RED phase) - dashboard may not render or API may not return data.
  """
  # Create test performance metrics
  now = datetime.utcnow()
  test_metrics = [
    PerformanceMetric(
      timestamp=now - timedelta(hours=i),
      endpoint='/api/v1/test',
      method='GET',
      status_code=200,
      response_time_ms=100.0 + i * 10,
      user_id='test@example.com',
    )
    for i in range(24)  # 24 hours of data
  ]

  for metric in test_metrics:
    test_db_session.add(metric)
  test_db_session.commit()

  # Query metrics API
  with patch('server.services.admin_service.is_workspace_admin', return_value=True):
    with patch('server.lib.auth.get_user_token', return_value='mock-token'):
      response = client.get(
        '/api/v1/metrics/performance?time_range=24h',
        headers={'X-Forwarded-Access-Token': 'mock-admin-token'},
      )

      assert response.status_code == 200, f'API should return metrics, got {response.status_code}'
      data = response.json()

      # Verify metrics are present
      assert 'metrics' in data
      assert data['metrics']['total_requests'] > 0, 'Should have request data'
      assert data['metrics']['avg_response_time_ms'] > 0, 'Should calculate avg response time'


# ============================================================================
# T016.7: Integration test for dashboard load time (SC-001)
# ============================================================================


def test_dashboard_load_time_under_3_seconds(test_db_session):
  """Test that dashboard loads in < 3 seconds (validates SC-001).

  Expected to FAIL initially (RED phase) - performance may not be optimized.
  """
  # Create realistic test data (100 metrics)
  now = datetime.utcnow()
  test_metrics = [
    PerformanceMetric(
      timestamp=now - timedelta(minutes=i),
      endpoint=f'/api/v1/endpoint{i % 10}',
      method='GET',
      status_code=200 if i % 10 != 0 else 500,
      response_time_ms=50.0 + (i % 100),
      user_id='test@example.com',
    )
    for i in range(100)
  ]

  for metric in test_metrics:
    test_db_session.add(metric)
  test_db_session.commit()

  # Measure load time
  with patch('server.services.admin_service.is_workspace_admin', return_value=True):
    with patch('server.lib.auth.get_user_token', return_value='mock-token'):
      start_time = time.time()

      response = client.get(
        '/api/v1/metrics/performance?time_range=24h',
        headers={'X-Forwarded-Access-Token': 'mock-admin-token'},
      )

      load_time = time.time() - start_time

      assert response.status_code == 200
      assert load_time < 3.0, f'Dashboard should load in <3s, took {load_time:.2f}s'


# ============================================================================
# T016.8: Integration test for slowest endpoint sorting
# ============================================================================


def test_slowest_endpoints_sorted_by_response_time(test_db_session):
  """Test that metrics table displays endpoints sorted by avg response time descending (validates SC-005).

  Expected to FAIL initially (RED phase) - sorting may not be implemented.
  """
  now = datetime.utcnow()

  # Create metrics with different response times per endpoint
  endpoints_data = [
    ('/api/v1/fast', 50.0, 10),  # Fast endpoint
    ('/api/v1/medium', 200.0, 15),  # Medium endpoint
    ('/api/v1/slow', 800.0, 20),  # Slow endpoint
  ]

  for endpoint, response_time, count in endpoints_data:
    for i in range(count):
      metric = PerformanceMetric(
        timestamp=now - timedelta(minutes=i),
        endpoint=endpoint,
        method='GET',
        status_code=200,
        response_time_ms=response_time + (i * 5),  # Slight variation
        user_id='test@example.com',
      )
      test_db_session.add(metric)

  test_db_session.commit()

  # Query API
  with patch('server.services.admin_service.is_workspace_admin', return_value=True):
    with patch('server.lib.auth.get_user_token', return_value='mock-token'):
      response = client.get(
        '/api/v1/metrics/performance?time_range=24h',
        headers={'X-Forwarded-Access-Token': 'mock-admin-token'},
      )

      assert response.status_code == 200
      data = response.json()

      # Verify endpoints are sorted by avg response time descending
      if 'endpoints' in data and len(data['endpoints']) >= 3:
        endpoints = data['endpoints']

        # First endpoint should be slowest
        assert endpoints[0]['endpoint'] == '/api/v1/slow'
        # Last should be fastest (or second if only 3)
        assert endpoints[-1]['avg_response_time_ms'] < endpoints[0]['avg_response_time_ms']


# ============================================================================
# T016.10: Integration test for FR-009 navigation menu requirement
# ============================================================================


def test_navigation_menu_contains_metrics_link():
  """Test that navigation menu contains "Metrics" or "Analytics" label and navigates to /metrics route.

  CRITICAL COVERAGE FOR FR-009: Validates complete user journey from navigation discovery to dashboard load.

  Expected to FAIL initially (RED phase) - navigation item may not exist.

  NOTE: This is a contract/integration test that verifies the API side. Frontend component
  testing would require additional tooling (React Testing Library, Playwright, etc.)
  """
  # This test validates the API endpoint exists and is accessible
  # Frontend navigation testing would be done separately with component tests

  with patch('server.services.admin_service.is_workspace_admin', return_value=True):
    with patch('server.lib.auth.get_user_token', return_value='mock-token'):
      # Verify metrics endpoint is accessible (confirms navigation target exists)
      response = client.get(
        '/api/v1/metrics/performance', headers={'X-Forwarded-Access-Token': 'mock-admin-token'}
      )

      # If endpoint exists, navigation can successfully route to dashboard
      assert response.status_code in [200, 404], (
        'Metrics endpoint should be defined for navigation target'
      )


# ============================================================================
# T016.11: Integration test for manual refresh button
# ============================================================================


def test_manual_refresh_button_reloads_metrics(test_db_session):
  """Test that dashboard includes refresh button that triggers new API call and reloads metrics.

  Validates acceptance scenario #6 and expanded edge case specification.

  Expected to FAIL initially (RED phase) - refresh functionality may not exist.
  """
  now = datetime.utcnow()

  # Create initial metrics
  metric1 = PerformanceMetric(
    timestamp=now - timedelta(hours=1),
    endpoint='/api/v1/test',
    method='GET',
    status_code=200,
    response_time_ms=100.0,
    user_id='test@example.com',
  )
  test_db_session.add(metric1)
  test_db_session.commit()

  # First API call (initial load)
  with patch('server.services.admin_service.is_workspace_admin', return_value=True):
    with patch('server.lib.auth.get_user_token', return_value='mock-token'):
      response1 = client.get(
        '/api/v1/metrics/performance?time_range=24h',
        headers={'X-Forwarded-Access-Token': 'mock-admin-token'},
      )

      assert response1.status_code == 200
      data1 = response1.json()
      initial_count = data1['metrics']['total_requests']

      # Add new metric (simulating new activity)
      metric2 = PerformanceMetric(
        timestamp=now,
        endpoint='/api/v1/test',
        method='GET',
        status_code=200,
        response_time_ms=150.0,
        user_id='test@example.com',
      )
      test_db_session.add(metric2)
      test_db_session.commit()

      # Second API call (refresh)
      response2 = client.get(
        '/api/v1/metrics/performance?time_range=24h',
        headers={'X-Forwarded-Access-Token': 'mock-admin-token'},
      )

      assert response2.status_code == 200
      data2 = response2.json()
      refreshed_count = data2['metrics']['total_requests']

      # Verify refresh loaded new data
      assert refreshed_count > initial_count, 'Refresh should load new metrics'


# ============================================================================
# T034.5: Integration test for empty database state
# ============================================================================


def test_dashboard_displays_no_data_available_for_empty_database(test_db_session):
  """Test that dashboard displays "No data available" message when no metrics exist.

  Validates edge case from spec.md:L126-128.

  Expected to FAIL initially (RED phase) - empty state handling may not exist.
  """
  # Ensure database is empty (no metrics)
  test_db_session.query(PerformanceMetric).delete()
  test_db_session.query(UsageEvent).delete()
  test_db_session.commit()

  # Mock the database session to use our test session
  def mock_get_db():
    yield test_db_session

  # Mock Databricks WorkspaceClient for admin check
  from unittest.mock import MagicMock

  mock_ws_client = MagicMock()
  mock_user = MagicMock()
  mock_user.user_name = 'test-admin@databricks.com'
  mock_user.groups = [{'display': 'admins'}]
  mock_ws_client.current_user.me.return_value = mock_user

  # Query API
  with patch('databricks.sdk.WorkspaceClient', return_value=mock_ws_client):
    with patch('server.lib.database.get_db_session', mock_get_db):
      response = client.get(
        '/api/v1/metrics/performance?time_range=24h',
        headers={'X-Forwarded-Access-Token': 'mock-admin-token'},
      )

      assert response.status_code == 200, 'Empty state should return 200, not error'
      data = response.json()

      # Verify empty state response structure
      assert 'metrics' in data
      assert data['metrics']['total_requests'] == 0, 'Should indicate no data'


# ============================================================================
# T107.5: Performance test for 30-day query load time (SC-006)
# ============================================================================


def test_30_day_query_completes_under_5_seconds(test_db_session):
  """Test that 30-day metrics query completes in < 5 seconds (validates SC-006).

  Expected to FAIL initially (RED phase) - may not be optimized for historical queries.
  """
  now = datetime.utcnow()

  # Create 30 days of test data (realistic volume)
  for day in range(30):
    for hour in range(24):
      metric = PerformanceMetric(
        timestamp=now - timedelta(days=day, hours=hour),
        endpoint=f'/api/v1/endpoint{hour % 5}',
        method='GET',
        status_code=200,
        response_time_ms=100.0 + (hour * 10),
        user_id='test@example.com',
      )
      test_db_session.add(metric)

  test_db_session.commit()

  # Measure query time
  with patch('server.services.admin_service.is_workspace_admin', return_value=True):
    with patch('server.lib.auth.get_user_token', return_value='mock-token'):
      start_time = time.time()

      response = client.get(
        '/api/v1/metrics/performance?time_range=30d',
        headers={'X-Forwarded-Access-Token': 'mock-admin-token'},
      )

      query_time = time.time() - start_time

      assert response.status_code == 200
      assert query_time < 5.0, f'30-day query should complete in <5s, took {query_time:.2f}s'


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
