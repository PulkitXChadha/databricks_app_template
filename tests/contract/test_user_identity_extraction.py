"""Contract tests for user identity extraction.

These tests verify the UserService.get_user_info() and user_id extraction functionality.
Tests follow TDD approach - written before implementation.
"""

from dataclasses import dataclass
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException


@dataclass
class UserIdentity:
  """Mock user identity for testing."""

  user_id: str  # Email address
  display_name: str
  active: bool


class TestUserIdentityExtraction:
  """Contract tests for extracting user identity from Databricks API."""

  @pytest.mark.asyncio
  async def test_get_user_info_returns_user_identity_with_valid_token(self):
    """Test that get_user_info() returns UserIdentity with valid token."""
    # Given: UserService with valid user token
    from server.services.user_service import UserService

    user_token = 'valid-user-token-12345'
    service = UserService(user_token=user_token)

    # Mock the Databricks API response
    with patch.object(service, '_get_client') as mock_client:
      mock_user = Mock()
      mock_user.user_name = 'user@example.com'
      mock_user.display_name = 'Test User'
      mock_user.active = True

      mock_client.return_value.current_user.me = Mock(return_value=mock_user)

      # When: get_user_info() is called
      result = await service.get_user_info()

      # Then: Should return UserIdentity with correct fields
      assert result.user_id == 'user@example.com'
      assert result.display_name == 'Test User'
      assert result.active is True

  @pytest.mark.asyncio
  async def test_get_user_info_raises_401_with_invalid_token(self):
    """Test that get_user_info() raises 401 with invalid token."""
    # Given: UserService with invalid token
    from server.services.user_service import UserService

    user_token = 'invalid-token-12345'
    service = UserService(user_token=user_token)

    # Mock the Databricks API to raise authentication error
    with patch.object(service, '_get_client') as mock_client:
      mock_client.return_value.current_user.me = Mock(
        side_effect=Exception('Invalid authentication credentials')
      )

      # When/Then: get_user_info() should raise HTTPException with 401
      with pytest.raises(HTTPException) as exc_info:
        await service.get_user_info()

      assert exc_info.value.status_code == 401
      assert 'Failed to extract user identity' in str(exc_info.value.detail)

  @pytest.mark.asyncio
  async def test_get_user_info_raises_401_with_expired_token(self):
    """Test that get_user_info() raises 401 with expired token."""
    # Given: UserService with expired token
    from server.services.user_service import UserService

    user_token = 'expired-token-12345'
    service = UserService(user_token=user_token)

    # Mock the Databricks API to raise expired token error
    with patch.object(service, '_get_client') as mock_client:
      mock_client.return_value.current_user.me = Mock(side_effect=Exception('Token has expired'))

      # When/Then: get_user_info() should raise HTTPException with 401
      with pytest.raises(HTTPException) as exc_info:
        await service.get_user_info()

      assert exc_info.value.status_code == 401

  @pytest.mark.asyncio
  async def test_get_user_id_returns_email_address(self):
    """Test that get_user_id() returns email address from user identity."""
    # Given: UserService with valid token
    from server.services.user_service import UserService

    user_token = 'valid-token'
    service = UserService(user_token=user_token)

    # Mock get_user_info to return user identity
    mock_user_info = UserIdentity(
      user_id='john.doe@company.com', display_name='John Doe', active=True
    )

    with patch.object(service, 'get_user_info', return_value=mock_user_info):
      # When: get_user_id() is called
      user_id = await service.get_user_id()

      # Then: Should return email address
      assert user_id == 'john.doe@company.com'

  @pytest.mark.asyncio
  async def test_get_user_id_raises_401_when_token_missing(self):
    """Test that get_user_id() raises 401 when token missing."""
    # Given: UserService without token
    from server.services.user_service import UserService

    service = UserService(user_token=None)

    # When/Then: get_user_id() should raise HTTPException with 401
    with pytest.raises(HTTPException) as exc_info:
      await service.get_user_id()

    assert exc_info.value.status_code == 401
    assert 'User authentication required' in str(exc_info.value.detail)

  @pytest.mark.asyncio
  async def test_user_identity_has_correct_fields(self):
    """Test that UserIdentity has correct fields (user_id, display_name, active)."""
    # Given: A UserIdentity object
    from server.models.user_session import UserIdentity as ActualUserIdentity

    # When: Creating a UserIdentity
    user_identity = ActualUserIdentity(
      user_id='test@example.com', display_name='Test User', active=True
    )

    # Then: Should have all required fields
    assert hasattr(user_identity, 'user_id')
    assert hasattr(user_identity, 'display_name')
    assert hasattr(user_identity, 'active')
    assert user_identity.user_id == 'test@example.com'
    assert user_identity.display_name == 'Test User'
    assert user_identity.active is True

  @pytest.mark.asyncio
  async def test_user_identity_validates_email_format(self):
    """Test that user_id must be valid email format."""
    # Given: UserIdentity with invalid email
    from pydantic import ValidationError

    from server.models.user_session import UserIdentity as ActualUserIdentity

    # When/Then: Creating UserIdentity with invalid email should raise ValidationError
    with pytest.raises(ValidationError) as exc_info:
      ActualUserIdentity(user_id='not-an-email', display_name='Test User', active=True)

    # Error should be about email validation
    assert 'valid email address' in str(exc_info.value).lower()

  @pytest.mark.asyncio
  async def test_service_principal_fallback_when_token_missing(self):
    """Test that service uses service principal when token missing."""
    # Given: UserService without token
    from server.services.user_service import UserService

    service = UserService(user_token=None)

    # Mock the service principal client
    with patch.object(service, '_get_client') as mock_client:
      mock_sp_user = Mock()
      mock_sp_user.user_name = 'service-principal@databricks.com'
      mock_sp_user.display_name = 'Service Principal'
      mock_sp_user.active = True

      mock_client.return_value.current_user.me = Mock(return_value=mock_sp_user)

      # When: get_user_info() is called without token
      result = await service.get_user_info()

      # Then: Should return service principal identity
      assert result.user_id == 'service-principal@databricks.com'
      assert result.display_name == 'Service Principal'
