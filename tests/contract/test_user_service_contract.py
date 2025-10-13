"""Contract tests for UserService authentication patterns.

Tests FR-002, FR-003, FR-004 from spec.md.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from server.services.user_service import UserService

# Mark all tests in this module as contract tests
pytestmark = pytest.mark.contract
from server.models.user_session import UserIdentity
from fastapi import HTTPException
import os


class TestUserServiceContract:
    """Contract tests for UserService authentication patterns."""

    @pytest.mark.asyncio
    async def test_user_service_with_user_token_creates_client_with_pat_auth_type(self):
        """Test UserService with user_token creates client with auth_type='pat'."""
        user_token = "mock-user-token-12345"
        
        with patch('server.services.user_service.WorkspaceClient') as mock_workspace_client, \
             patch.dict(os.environ, {"DATABRICKS_HOST": "https://test.cloud.databricks.com"}):
            
            service = UserService(user_token=user_token)
            
            # Access _get_client() to trigger client creation
            client = service._get_client()
            
            # Verify WorkspaceClient was called with correct auth_type
            mock_workspace_client.assert_called_once()
            call_kwargs = mock_workspace_client.call_args[1]
            
            assert call_kwargs["auth_type"] == "pat"
            assert call_kwargs["token"] == user_token
            assert call_kwargs["host"] == "https://test.cloud.databricks.com"

    @pytest.mark.asyncio
    async def test_user_service_without_user_token_creates_client_with_oauth_m2m_auth_type(self):
        """Test UserService without user_token creates client with auth_type='oauth-m2m'."""
        with patch('server.services.user_service.WorkspaceClient') as mock_workspace_client, \
             patch.dict(os.environ, {
                 "DATABRICKS_HOST": "https://test.cloud.databricks.com",
                 "DATABRICKS_CLIENT_ID": "test-client-id",
                 "DATABRICKS_CLIENT_SECRET": "test-client-secret"
             }):
            
            service = UserService(user_token=None)
            
            # Access _get_client() to trigger client creation
            client = service._get_client()
            
            # Verify WorkspaceClient was called with correct auth_type
            mock_workspace_client.assert_called_once()
            call_kwargs = mock_workspace_client.call_args[1]
            
            assert call_kwargs["auth_type"] == "oauth-m2m"
            assert call_kwargs["client_id"] == "test-client-id"
            assert call_kwargs["client_secret"] == "test-client-secret"
            assert call_kwargs["host"] == "https://test.cloud.databricks.com"

    @pytest.mark.asyncio
    async def test_get_user_id_returns_email_address(self):
        """Test UserService.get_user_id() returns email address."""
        user_token = "mock-user-token-12345"
        expected_email = "user@example.com"
        
        with patch('server.services.user_service.UserService.get_user_info', new_callable=AsyncMock) as mock_get_user_info:
            mock_get_user_info.return_value = UserIdentity(
                user_id=expected_email,
                display_name="Test User",
                active=True,
                extracted_at="2025-10-10T12:00:00Z"
            )
            
            service = UserService(user_token=user_token)
            user_id = await service.get_user_id()
            
            assert user_id == expected_email
            assert "@" in user_id  # Email format validation

    @pytest.mark.asyncio
    async def test_get_user_id_raises_401_when_user_token_missing(self):
        """Test UserService.get_user_id() raises 401 when user_token missing."""
        service = UserService(user_token=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await service.get_user_id()
        
        assert exc_info.value.status_code == 401
        assert "authentication required" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_client_creation_logs_correct_auth_mode(self):
        """Test that client creation logs correct auth_mode."""
        user_token = "mock-user-token-12345"
        
        with patch('server.services.user_service.WorkspaceClient') as mock_workspace_client, \
             patch('server.services.user_service.logger') as mock_logger, \
             patch.dict(os.environ, {"DATABRICKS_HOST": "https://test.cloud.databricks.com"}):
            
            service = UserService(user_token=user_token)
            client = service._get_client()
            
            # Verify logger was called with correct auth mode
            mock_logger.info.assert_called()
            log_calls = [call[0] for call in mock_logger.info.call_args_list]
            
            # Should have logged "auth.mode" event
            assert any("auth.mode" in str(call) for call in log_calls)
            
            # Check log context includes mode and auth_type
            for call in mock_logger.info.call_args_list:
                if len(call[0]) > 1 and isinstance(call[0][1], dict):
                    context = call[0][1]
                    if "mode" in context:
                        assert context["mode"] == "obo"
                        assert context["auth_type"] == "pat"

    @pytest.mark.asyncio
    async def test_get_user_info_extracts_identity_from_api(self):
        """Test get_user_info() extracts UserIdentity from Databricks API."""
        user_token = "mock-user-token-12345"
        
        mock_user_data = MagicMock()
        mock_user_data.user_name = "user@example.com"
        mock_user_data.display_name = "Test User"
        mock_user_data.active = True
        
        with patch('server.services.user_service.WorkspaceClient') as mock_workspace_client, \
             patch.dict(os.environ, {"DATABRICKS_HOST": "https://test.cloud.databricks.com"}):
            
            mock_client = MagicMock()
            mock_client.current_user.me = AsyncMock(return_value=mock_user_data)
            mock_workspace_client.return_value = mock_client
            
            service = UserService(user_token=user_token)
            user_identity = await service.get_user_info()
            
            assert isinstance(user_identity, UserIdentity)
            assert user_identity.user_id == "user@example.com"
            assert user_identity.display_name == "Test User"
            assert user_identity.active is True

    @pytest.mark.asyncio
    async def test_service_principal_fallback_works_without_token(self):
        """Test that service falls back to service principal when token is None."""
        with patch('server.services.user_service.WorkspaceClient') as mock_workspace_client, \
             patch.dict(os.environ, {
                 "DATABRICKS_HOST": "https://test.cloud.databricks.com",
                 "DATABRICKS_CLIENT_ID": "test-client-id",
                 "DATABRICKS_CLIENT_SECRET": "test-client-secret"
             }):
            
            # Create service without user token
            service = UserService(user_token=None)
            client = service._get_client()
            
            # Verify service principal auth was used
            mock_workspace_client.assert_called_once()
            call_kwargs = mock_workspace_client.call_args[1]
            
            assert call_kwargs["auth_type"] == "oauth-m2m"
            assert "client_id" in call_kwargs
            assert "client_secret" in call_kwargs

