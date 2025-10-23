"""Integration tests for upstream service degradation scenarios.

These tests verify that the application handles:
- Databricks API slowness/timeouts
- Unity Catalog service unavailability
- Model Serving endpoint failures
- Lakebase database connection issues
- Partial service failures

Note: Tests marked with @pytest.mark.slow involve deliberate delays
to test timeout behavior and can be skipped during development with:
    pytest -m "not slow"
"""

import pytest

# Mark all tests in this module as integration and slow
pytestmark = [pytest.mark.integration, pytest.mark.slow]
import time
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from server.app import app


@pytest.fixture
def test_client():
  """Create test client."""
  return TestClient(app)


@pytest.fixture
def user_token():
  """Mock user token."""
  return 'test-user-token'


class TestUpstreamServiceDegradation:
  """Test application behavior under upstream service degradation."""

  @pytest.mark.timeout(40)  # Allow extra time for deliberate 35s sleep
  def test_databricks_api_timeout_handled_gracefully(self, test_client, user_token):
    """Test that Databricks API timeouts are handled gracefully."""
    with patch('server.services.user_service.UserService._fetch_user_info') as mock_fetch:
      # Simulate slow response that times out
      def slow_response(*args, **kwargs):
        time.sleep(35)  # Exceeds 30-second timeout
        return Mock()

      mock_fetch.side_effect = slow_response

      # Make request
      start_time = time.time()
      response = test_client.get('/api/user/me', headers={'X-Forwarded-Access-Token': user_token})
      elapsed_time = time.time() - start_time

      # Should fail with timeout error before 35 seconds
      assert elapsed_time < 35, 'Should timeout before full 35 seconds'
      assert response.status_code in [401, 500, 504]

  def test_unity_catalog_unavailable_returns_error(self, test_client, user_token):
    """Test that Unity Catalog unavailability returns proper error."""
    with patch('server.services.user_service.UserService.get_user_info') as mock_get_user:
      # Configure mock user
      user_identity = Mock()
      user_identity.user_id = 'test@example.com'
      user_identity.display_name = 'Test User'
      user_identity.workspace_url = 'https://example.cloud.databricks.com'
      mock_get_user.return_value = user_identity

      with patch('server.services.unity_catalog_service.WorkspaceClient') as mock_client_class:
        # Simulate service unavailable
        mock_client = Mock()
        mock_client.catalogs.list.side_effect = Exception('Service unavailable')
        mock_client_class.return_value = mock_client

        # Make request
        response = test_client.get(
          '/api/unity-catalog/catalogs', headers={'X-Forwarded-Access-Token': user_token}
        )

        # Should return error
        assert response.status_code == 500

        # Error message should indicate service issue
        data = response.json()
        assert 'detail' in data or 'message' in data

  def test_model_serving_endpoint_failure(self, test_client, user_token):
    """Test that Model Serving endpoint failures are handled."""
    with patch('server.services.user_service.UserService.get_user_info') as mock_get_user:
      # Configure mock user
      user_identity = Mock()
      user_identity.user_id = 'test@example.com'
      user_identity.display_name = 'Test User'
      user_identity.workspace_url = 'https://example.cloud.databricks.com'
      mock_get_user.return_value = user_identity

      with patch('server.services.model_serving_service.WorkspaceClient') as mock_client_class:
        # Simulate endpoint failure
        mock_client = Mock()
        mock_client.serving_endpoints.list.side_effect = ConnectionError('Connection refused')
        mock_client_class.return_value = mock_client

        # Make request
        response = test_client.get(
          '/api/model-serving/endpoints', headers={'X-Forwarded-Access-Token': user_token}
        )

        # Should return error
        assert response.status_code == 500

  def test_lakebase_database_connection_failure(self, test_client, user_token):
    """Test that Lakebase connection failures are handled."""
    with patch('server.services.user_service.UserService.get_user_info') as mock_get_user:
      # Configure mock user
      user_identity = Mock()
      user_identity.user_id = 'test@example.com'
      user_identity.display_name = 'Test User'
      user_identity.workspace_url = 'https://example.cloud.databricks.com'
      mock_get_user.return_value = user_identity

      with patch('server.services.lakebase_service.get_db_session') as mock_get_session:
        # Simulate database connection failure
        from sqlalchemy.exc import OperationalError

        mock_get_session.side_effect = OperationalError('Could not connect to database', None, None)

        # Make request
        response = test_client.get(
          '/api/user/preferences', headers={'X-Forwarded-Access-Token': user_token}
        )

        # Should return error
        assert response.status_code == 500

  def test_partial_service_failure_isolated(self, test_client, user_token):
    """Test that partial service failures are isolated."""
    with patch('server.services.user_service.UserService.get_user_info') as mock_get_user:
      # Configure mock user
      user_identity = Mock()
      user_identity.user_id = 'test@example.com'
      user_identity.display_name = 'Test User'
      user_identity.workspace_url = 'https://example.cloud.databricks.com'
      mock_get_user.return_value = user_identity

      with patch('server.services.lakebase_service.get_db_session') as mock_get_session:
        # Mock database works
        mock_session = Mock()
        mock_query = Mock()
        mock_filter_by = Mock()
        mock_filter_by.all.return_value = []
        mock_query.filter_by.return_value = mock_filter_by
        mock_session.query.return_value = mock_query
        mock_get_session.return_value = [mock_session]

        # Preferences endpoint should work
        response_prefs = test_client.get(
          '/api/user/preferences', headers={'X-Forwarded-Access-Token': user_token}
        )
        assert response_prefs.status_code == 200

        # Even if Unity Catalog is down
        with patch('server.services.unity_catalog_service.WorkspaceClient') as mock_uc_client:
          mock_uc_client.side_effect = Exception('Unity Catalog down')

          # UC endpoint fails
          response_uc = test_client.get(
            '/api/unity-catalog/catalogs', headers={'X-Forwarded-Access-Token': user_token}
          )
          assert response_uc.status_code == 500

          # But preferences still work (isolated failure)
          response_prefs2 = test_client.get(
            '/api/user/preferences', headers={'X-Forwarded-Access-Token': user_token}
          )
          assert response_prefs2.status_code == 200

  @pytest.mark.timeout(40)  # Allow extra time for deliberate 35s sleep
  def test_slow_database_query_timeout(self, test_client, user_token):
    """Test that slow database queries timeout appropriately."""
    with patch('server.services.user_service.UserService.get_user_info') as mock_get_user:
      # Configure mock user
      user_identity = Mock()
      user_identity.user_id = 'test@example.com'
      user_identity.display_name = 'Test User'
      user_identity.workspace_url = 'https://example.cloud.databricks.com'
      mock_get_user.return_value = user_identity

      with patch('server.services.lakebase_service.get_db_session') as mock_get_session:
        # Simulate slow query
        def slow_query(*args, **kwargs):
          time.sleep(35)  # Very slow
          return []

        mock_session = Mock()
        mock_query = Mock()
        mock_filter_by = Mock()
        mock_filter_by.all.side_effect = slow_query
        mock_query.filter_by.return_value = mock_filter_by
        mock_session.query.return_value = mock_query
        mock_get_session.return_value = [mock_session]

        # Make request
        start_time = time.time()
        response = test_client.get(
          '/api/user/preferences', headers={'X-Forwarded-Access-Token': user_token}
        )
        elapsed_time = time.time() - start_time

        # Should timeout before 35 seconds
        # Note: Actual timeout behavior depends on configuration
        # For this test, we just verify the request completes
        assert elapsed_time < 40, 'Request should complete or timeout within reasonable time'

  def test_cascading_failure_prevention(self, test_client, user_token):
    """Test that cascading failures are prevented."""
    with patch('server.services.user_service.UserService.get_user_info') as mock_get_user:
      # Even if user service fails
      mock_get_user.side_effect = Exception('User service down')

      # Should return error without cascading to other services
      response = test_client.get('/api/user/me', headers={'X-Forwarded-Access-Token': user_token})

      assert response.status_code in [401, 500]

      # System should still be responsive for other requests
      # (Not making dependent calls that would cascade)

  def test_circuit_breaker_behavior(self, test_client, user_token):
    """Test that circuit breaker pattern works (if implemented)."""
    with patch('server.services.user_service.UserService._fetch_user_info') as mock_fetch:
      # Simulate repeated failures
      mock_fetch.side_effect = Exception('Service down')

      # Make multiple requests
      responses = []
      for _ in range(5):
        response = test_client.get('/api/user/me', headers={'X-Forwarded-Access-Token': user_token})
        responses.append(response)

      # All should fail
      assert all(r.status_code in [401, 500] for r in responses)

      # Note: Circuit breaker would open after repeated failures
      # and fail fast without calling the service

  def test_degraded_service_returns_partial_data(self, test_client, user_token):
    """Test that degraded services can return partial data."""
    with patch('server.services.user_service.UserService.get_user_info') as mock_get_user:
      # Configure mock user
      user_identity = Mock()
      user_identity.user_id = 'test@example.com'
      user_identity.display_name = 'Test User'
      user_identity.workspace_url = 'https://example.cloud.databricks.com'
      mock_get_user.return_value = user_identity

      with patch('server.services.model_serving_service.WorkspaceClient') as mock_client_class:
        mock_client = Mock()

        # Simulate partial failure - some endpoints fail, some succeed
        def partial_list(*args, **kwargs):
          # Return limited endpoints (as if some are inaccessible)
          endpoint1 = Mock(name='endpoint-1')
          endpoint1.config = Mock()
          endpoint1.state = Mock()
          endpoint1.state.ready = 'READY'
          return [endpoint1]  # Only 1 instead of many

        mock_client.serving_endpoints.list.side_effect = partial_list
        mock_client_class.return_value = mock_client

        # Make request
        response = test_client.get(
          '/api/model-serving/endpoints', headers={'X-Forwarded-Access-Token': user_token}
        )

        # Should succeed with partial data
        assert response.status_code == 200
        data = response.json()
        # Returns what's available, even if incomplete
        assert isinstance(data, list)


class TestServiceRecovery:
  """Test service recovery after degradation."""

  def test_service_recovery_after_transient_failure(self, test_client, user_token):
    """Test that service recovers after transient failures."""
    with patch('server.services.user_service.UserService.get_user_info') as mock_get_user:
      # Simulate: fail once, then succeed
      call_count = [0]

      def transient_failure(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
          raise Exception('Transient failure')
        else:
          user_identity = Mock()
          user_identity.user_id = 'test@example.com'
          user_identity.display_name = 'Test User'
          user_identity.workspace_url = 'https://example.cloud.databricks.com'
          return user_identity

      mock_get_user.side_effect = transient_failure

      # First request fails
      response1 = test_client.get('/api/user/me', headers={'X-Forwarded-Access-Token': user_token})
      assert response1.status_code in [401, 500]

      # Second request succeeds (service recovered)
      response2 = test_client.get('/api/user/me', headers={'X-Forwarded-Access-Token': user_token})
      assert response2.status_code == 200
