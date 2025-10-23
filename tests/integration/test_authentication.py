"""Integration tests for authentication implementation.

These tests verify OBO authentication works correctly using TestClient
for fast, isolated testing without requiring a running server.

For live server testing, use: pytest -m requires_server
"""

from unittest.mock import patch
from uuid import uuid4

import pytest

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestAuthenticationStatus:
  """Test authentication status endpoint."""

  def test_auth_status_without_token(self, test_client):
    """Test that auth/status returns service principal mode without token."""
    response = test_client.get('/api/user/auth/status')

    assert response.status_code == 200
    data = response.json()

    assert data['authenticated'] is True
    assert data['auth_mode'] == 'service_principal'
    assert data['has_user_identity'] is False
    assert data['user_id'] is None

  def test_auth_status_with_token(self, test_client):
    """Test that auth/status returns OBO mode with token."""
    headers = {'X-Forwarded-Access-Token': 'test-user-token'}
    response = test_client.get('/api/user/auth/status', headers=headers)

    assert response.status_code == 200
    data = response.json()

    assert data['authenticated'] is True
    assert data['auth_mode'] == 'obo'
    # has_user_identity depends on whether user extraction succeeds

  def test_correlation_id_preserved(self, test_client):
    """Test that correlation ID is preserved in response."""
    correlation_id = str(uuid4())
    headers = {'X-Correlation-ID': correlation_id}
    response = test_client.get('/api/user/auth/status', headers=headers)

    assert response.status_code == 200
    assert response.headers.get('X-Correlation-ID') == correlation_id

  def test_correlation_id_generated(self, test_client):
    """Test that correlation ID is generated if not provided."""
    response = test_client.get('/api/user/auth/status')

    assert response.status_code == 200
    assert 'X-Correlation-ID' in response.headers
    assert len(response.headers['X-Correlation-ID']) > 0


class TestUserEndpoints:
  """Test user information endpoints."""

  def test_get_user_me_without_token(self, test_client, mock_user_identity):
    """Test /api/user/me without token uses service principal."""
    with patch('server.services.user_service.UserService.get_user_info') as mock_get_user:
      mock_get_user.return_value = mock_user_identity

      response = test_client.get('/api/user/me')

      assert response.status_code == 200
      data = response.json()

      # Should return user info (service principal fallback)
      assert 'userName' in data
      assert 'displayName' in data
      assert 'active' in data
      assert data['active'] is True

  def test_get_user_me_with_token(self, test_client, user_token, mock_user_identity):
    """Test /api/user/me with token attempts OBO authentication."""
    with patch('server.services.user_service.UserService.get_user_info') as mock_get_user:
      mock_get_user.return_value = mock_user_identity

      headers = {'X-Forwarded-Access-Token': user_token}
      response = test_client.get('/api/user/me', headers=headers)

      assert response.status_code == 200
      data = response.json()
      assert 'userName' in data
      assert 'displayName' in data
      assert 'active' in data

  def test_get_user_workspace_without_token(self, test_client, mock_user_identity):
    """Test /api/user/me/workspace without token."""
    with patch('server.services.user_service.UserService.get_user_info') as mock_get_user:
      mock_get_user.return_value = mock_user_identity

      response = test_client.get('/api/user/me/workspace')

      assert response.status_code == 200
      data = response.json()

      # Should return workspace info
      assert 'user' in data
      assert 'workspace' in data
      assert 'userName' in data['user']
      assert 'displayName' in data['user']

  def test_get_user_workspace_with_token(self, test_client, user_token, mock_user_identity):
    """Test /api/user/me/workspace with token."""
    with patch('server.services.user_service.UserService.get_user_info') as mock_get_user:
      mock_get_user.return_value = mock_user_identity

      headers = {'X-Forwarded-Access-Token': user_token}
      response = test_client.get('/api/user/me/workspace', headers=headers)

      assert response.status_code == 200
      data = response.json()
      assert 'user' in data
      assert 'workspace' in data


class TestAuthenticationModes:
  """Test that services use correct authentication modes."""

  def test_service_endpoints_switch_auth_mode(self, test_client):
    """Test that endpoints correctly switch between OBO and service principal."""
    # Test without token - should use service principal
    response1 = test_client.get('/api/user/auth/status')
    assert response1.json()['auth_mode'] == 'service_principal'

    # Test with token - should use OBO
    headers = {'X-Forwarded-Access-Token': 'user-token'}
    response2 = test_client.get('/api/user/auth/status', headers=headers)
    assert response2.json()['auth_mode'] == 'obo'

  def test_multiple_requests_with_different_modes(self, test_client):
    """Test that multiple requests can use different auth modes."""
    # Make requests with different auth modes in sequence
    responses = []

    # Request 1: No token
    responses.append(test_client.get('/api/user/auth/status'))

    # Request 2: With token
    responses.append(
      test_client.get('/api/user/auth/status', headers={'X-Forwarded-Access-Token': 'token1'})
    )

    # Request 3: No token again
    responses.append(test_client.get('/api/user/auth/status'))

    # Request 4: Different token
    responses.append(
      test_client.get('/api/user/auth/status', headers={'X-Forwarded-Access-Token': 'token2'})
    )

    # Verify all succeeded
    for response in responses:
      assert response.status_code == 200

    # Verify auth modes
    assert responses[0].json()['auth_mode'] == 'service_principal'
    assert responses[1].json()['auth_mode'] == 'obo'
    assert responses[2].json()['auth_mode'] == 'service_principal'
    assert responses[3].json()['auth_mode'] == 'obo'
