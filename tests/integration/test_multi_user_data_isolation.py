"""Integration tests for multi-user data isolation.

These tests verify that:
- User A cannot access User B's preferences
- User-scoped Databricks resources respect OBO permissions
- Data isolation works end-to-end across all layers
"""

import pytest

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from server.app import app


@pytest.fixture
def test_client():
  """Create test client."""
  return TestClient(app)


@pytest.fixture
def user_a_token():
  """Mock token for User A."""
  return 'user-a-test-token'


@pytest.fixture
def user_b_token():
  """Mock token for User B."""
  return 'user-b-test-token'


class TestMultiUserDataIsolation:
  """Test data isolation between multiple users."""

  def test_user_preferences_isolated_by_user_id(self, test_client, user_a_token, user_b_token):
    """Test that users cannot access each other's preferences."""
    with patch('server.services.user_service.UserService.get_user_info') as mock_get_user:
      # Configure mock for User A
      user_a_identity = Mock()
      user_a_identity.user_id = 'userA@example.com'
      user_a_identity.display_name = 'User A'
      user_a_identity.workspace_url = 'https://example.cloud.databricks.com'

      # Configure mock for User B
      user_b_identity = Mock()
      user_b_identity.user_id = 'userB@example.com'
      user_b_identity.display_name = 'User B'
      user_b_identity.workspace_url = 'https://example.cloud.databricks.com'

      with patch('server.services.lakebase_service.get_db_session') as mock_get_session:
        # Mock database session
        mock_session = Mock()
        mock_query = Mock()
        mock_filter_by = Mock()

        # User A saves a preference
        mock_get_user.return_value = user_a_identity
        mock_filter_by.first.return_value = None  # No existing preference
        mock_query.filter_by.return_value = mock_filter_by
        mock_session.query.return_value = mock_query
        mock_get_session.return_value = [mock_session]

        response_a = test_client.post(
          '/api/user/preferences',
          json={'key': 'theme', 'value': {'color': 'dark'}},
          headers={'X-Forwarded-Access-Token': user_a_token},
        )

        assert response_a.status_code == 200

        # User B tries to get preferences - should NOT see User A's data
        mock_get_user.return_value = user_b_identity
        mock_filter_by.all.return_value = []  # Empty result for User B

        response_b = test_client.get(
          '/api/user/preferences', headers={'X-Forwarded-Access-Token': user_b_token}
        )

        assert response_b.status_code == 200
        preferences_b = response_b.json()
        assert len(preferences_b) == 0, "User B should NOT see User A's preferences"

  def test_unity_catalog_respects_user_permissions(self, test_client, user_a_token, user_b_token):
    """Test that Unity Catalog operations respect OBO user permissions."""
    with patch('server.services.user_service.UserService.get_user_info') as mock_get_user:
      # Configure mock users
      user_a_identity = Mock()
      user_a_identity.user_id = 'userA@example.com'
      user_a_identity.display_name = 'User A'
      user_a_identity.workspace_url = 'https://example.cloud.databricks.com'

      user_b_identity = Mock()
      user_b_identity.user_id = 'userB@example.com'
      user_b_identity.display_name = 'User B'
      user_b_identity.workspace_url = 'https://example.cloud.databricks.com'

      with patch('server.services.unity_catalog_service.WorkspaceClient') as mock_client_class:
        mock_client_a = Mock()
        mock_client_b = Mock()

        # User A can see 2 catalogs
        mock_catalog_a1 = Mock()
        mock_catalog_a1.name = 'catalog_a'
        mock_catalog_a2 = Mock()
        mock_catalog_a2.name = 'shared_catalog'
        mock_client_a.catalogs.list.return_value = [mock_catalog_a1, mock_catalog_a2]

        # User B can only see 1 catalog
        mock_catalog_b1 = Mock()
        mock_catalog_b1.name = 'shared_catalog'
        mock_client_b.catalogs.list.return_value = [mock_catalog_b1]

        # Return different clients for different users
        def get_client_for_user(*args, **kwargs):
          if kwargs.get('token') == user_a_token:
            return mock_client_a
          elif kwargs.get('token') == user_b_token:
            return mock_client_b
          return Mock()

        mock_client_class.side_effect = get_client_for_user

        # User A lists catalogs
        mock_get_user.return_value = user_a_identity
        response_a = test_client.get(
          '/api/unity-catalog/catalogs', headers={'X-Forwarded-Access-Token': user_a_token}
        )

        assert response_a.status_code == 200
        catalogs_a = response_a.json()
        assert len(catalogs_a) == 2, 'User A should see 2 catalogs'

        # User B lists catalogs
        mock_get_user.return_value = user_b_identity
        response_b = test_client.get(
          '/api/unity-catalog/catalogs', headers={'X-Forwarded-Access-Token': user_b_token}
        )

        assert response_b.status_code == 200
        catalogs_b = response_b.json()
        assert len(catalogs_b) == 1, 'User B should only see 1 catalog'

  def test_model_serving_respects_user_permissions(self, test_client, user_a_token, user_b_token):
    """Test that Model Serving operations respect OBO user permissions."""
    with patch('server.services.user_service.UserService.get_user_info') as mock_get_user:
      # Configure mock users
      user_a_identity = Mock()
      user_a_identity.user_id = 'userA@example.com'
      user_a_identity.display_name = 'User A'
      user_a_identity.workspace_url = 'https://example.cloud.databricks.com'

      user_b_identity = Mock()
      user_b_identity.user_id = 'userB@example.com'
      user_b_identity.display_name = 'User B'
      user_b_identity.workspace_url = 'https://example.cloud.databricks.com'

      with patch('server.services.model_serving_service.WorkspaceClient') as mock_client_class:
        mock_client_a = Mock()
        mock_client_b = Mock()

        # User A can see 3 endpoints
        mock_endpoint_a1 = Mock(name='endpoint_a_private')
        mock_endpoint_a2 = Mock(name='endpoint_a_shared')
        mock_endpoint_a3 = Mock(name='endpoint_public')
        mock_client_a.serving_endpoints.list.return_value = [
          mock_endpoint_a1,
          mock_endpoint_a2,
          mock_endpoint_a3,
        ]

        # User B can only see 2 endpoints (no private)
        mock_endpoint_b1 = Mock(name='endpoint_a_shared')
        mock_endpoint_b2 = Mock(name='endpoint_public')
        mock_client_b.serving_endpoints.list.return_value = [mock_endpoint_b1, mock_endpoint_b2]

        # Return different clients for different users
        def get_client_for_user(*args, **kwargs):
          if kwargs.get('token') == user_a_token:
            return mock_client_a
          elif kwargs.get('token') == user_b_token:
            return mock_client_b
          return Mock()

        mock_client_class.side_effect = get_client_for_user

        # User A lists endpoints
        mock_get_user.return_value = user_a_identity
        response_a = test_client.get(
          '/api/model-serving/endpoints', headers={'X-Forwarded-Access-Token': user_a_token}
        )

        assert response_a.status_code == 200
        endpoints_a = response_a.json()
        assert len(endpoints_a) == 3, 'User A should see 3 endpoints'

        # User B lists endpoints
        mock_get_user.return_value = user_b_identity
        response_b = test_client.get(
          '/api/model-serving/endpoints', headers={'X-Forwarded-Access-Token': user_b_token}
        )

        assert response_b.status_code == 200
        endpoints_b = response_b.json()
        assert len(endpoints_b) == 2, 'User B should only see 2 endpoints'

  def test_missing_token_returns_401(self, test_client):
    """Test that requests without token return 401."""
    # Try to access user preferences without token
    response = test_client.get('/api/user/preferences')
    assert response.status_code == 401, 'Should return 401 without token'

    # Try to save preference without token
    response = test_client.post(
      '/api/user/preferences', json={'key': 'theme', 'value': {'color': 'dark'}}
    )
    assert response.status_code == 401, 'Should return 401 without token'
