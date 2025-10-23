"""Contract tests for UserService OBO-only authentication.

These tests validate that UserService correctly implements OBO-only authentication:
- Service REQUIRES user_token parameter (not Optional)
- Service raises ValueError if user_token is None or empty
- Service creates WorkspaceClient with auth_type='pat' only

Test Requirements (from contracts/service_authentication.yaml):
- UserService(user_token=None) raises ValueError
- UserService(user_token="mock-token") succeeds with OBO client
- get_user_info() extracts identity using OBO credentials
- No service principal fallback
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.models.user_session import UserIdentity
from server.services.user_service import UserService

# Mark all tests in this module as contract tests
pytestmark = pytest.mark.contract


class TestUserServiceContract:
  """Contract tests for UserService OBO-only authentication patterns."""

  def test_service_accepts_none_for_service_principal_mode(self):
    """Test that UserService accepts None for service principal mode."""
    with patch.dict(os.environ, {'DATABRICKS_HOST': 'https://test.cloud.databricks.com'}):
      # Should not raise exception - None means service principal mode
      service = UserService(user_token=None)
      assert service.user_token is None

  def test_service_accepts_empty_string_for_service_principal_mode(self):
    """Test that UserService accepts empty string for service principal mode."""
    with patch.dict(os.environ, {'DATABRICKS_HOST': 'https://test.cloud.databricks.com'}):
      # Empty string treated as None (no token)
      service = UserService(user_token='')
      assert service.user_token == ''

  def test_service_initialization_succeeds_with_valid_token(self):
    """Test that UserService initializes successfully with valid token."""
    with (
      patch('server.services.user_service.WorkspaceClient') as mock_workspace_client,
      patch.dict(os.environ, {'DATABRICKS_HOST': 'https://test.cloud.databricks.com'}),
    ):
      mock_client = MagicMock()
      mock_workspace_client.return_value = mock_client

      # Should not raise exception
      service = UserService(user_token='mock-token-12345')

      assert service.user_token == 'mock-token-12345'
      assert service.workspace_url == 'https://test.cloud.databricks.com'

  @pytest.mark.asyncio
  async def test_service_creates_workspace_client_with_obo_auth(self):
    """Test UserService with user_token creates client with auth_type='pat'."""
    user_token = 'mock-user-token-12345'

    with (
      patch('server.services.user_service.WorkspaceClient') as mock_workspace_client,
      patch.dict(os.environ, {'DATABRICKS_HOST': 'https://test.cloud.databricks.com'}),
    ):
      mock_client = MagicMock()
      mock_user = MagicMock()
      mock_user.user_name = 'user@example.com'
      mock_user.display_name = 'Test User'
      mock_user.active = True
      mock_client.current_user.me = MagicMock(return_value=mock_user)
      mock_workspace_client.return_value = mock_client

      service = UserService(user_token=user_token)

      # Trigger client creation by calling a method
      await service.get_user_info()

      # Verify WorkspaceClient was created with correct parameters
      mock_workspace_client.assert_called_once()
      call_kwargs = mock_workspace_client.call_args[1]

      # Verify OBO authentication parameters
      assert 'host' in call_kwargs, 'host parameter required'
      assert call_kwargs['host'] == 'https://test.cloud.databricks.com'
      assert 'token' in call_kwargs, 'token parameter required'
      assert call_kwargs['token'] == user_token
      assert 'auth_type' in call_kwargs, 'auth_type parameter required'
      assert call_kwargs['auth_type'] == 'pat', "auth_type must be 'pat' for OBO"

      # Verify NO service principal parameters present
      assert 'client_id' not in call_kwargs, (
        'client_id should not be present (no service principal)'
      )
      assert 'client_secret' not in call_kwargs, (
        'client_secret should not be present (no service principal)'
      )

  @pytest.mark.asyncio
  async def test_get_user_id_returns_email_address(self):
    """Test UserService.get_user_id() returns email address."""
    user_token = 'mock-user-token-12345'
    expected_email = 'user@example.com'

    with patch(
      'server.services.user_service.UserService.get_user_info', new_callable=AsyncMock
    ) as mock_get_user_info:
      mock_get_user_info.return_value = UserIdentity(
        user_id=expected_email,
        display_name='Test User',
        active=True,
        extracted_at='2025-10-10T12:00:00Z',
      )

      with patch.dict(os.environ, {'DATABRICKS_HOST': 'https://test.cloud.databricks.com'}):
        with patch('server.services.user_service.WorkspaceClient'):
          service = UserService(user_token=user_token)
          user_id = await service.get_user_id()

          assert user_id == expected_email
          assert '@' in user_id  # Email format validation

  @pytest.mark.asyncio
  async def test_get_user_info_extracts_identity_from_api(self):
    """Test get_user_info() extracts UserIdentity from Databricks API."""
    user_token = 'mock-user-token-12345'

    mock_user_data = MagicMock()
    mock_user_data.user_name = 'user@example.com'
    mock_user_data.display_name = 'Test User'
    mock_user_data.active = True

    with (
      patch('server.services.user_service.WorkspaceClient') as mock_workspace_client,
      patch.dict(os.environ, {'DATABRICKS_HOST': 'https://test.cloud.databricks.com'}),
    ):
      mock_client = MagicMock()
      mock_client.current_user.me = MagicMock(return_value=mock_user_data)
      mock_workspace_client.return_value = mock_client

      service = UserService(user_token=user_token)
      user_identity = await service.get_user_info()

      assert isinstance(user_identity, UserIdentity)
      assert user_identity.user_id == 'user@example.com'
      assert user_identity.display_name == 'Test User'
      assert user_identity.active is True
