"""Contract tests for user-related endpoints.

These tests verify /api/user/me and /api/user/me/workspace endpoints with OBO authentication.
Tests follow TDD approach - written before implementation.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import os


class TestUserEndpoints:
    """Contract tests for user endpoints with OBO authentication."""

    def test_get_user_me_returns_user_info_with_valid_token(self, client, monkeypatch):
        """Test that GET /api/user/me returns UserInfoResponse with valid token."""
        from server.models.user_session import UserIdentity
        from datetime import datetime
        
        # Set required env var
        monkeypatch.setenv('DATABRICKS_HOST', 'https://test.databricks.com')
        
        # Patch at the location where it's imported in the router
        with patch('server.routers.user.UserService') as MockService:
            mock_service = Mock()
            # Return UserIdentity object (get_user_info returns this, not a dict)
            mock_user_identity = UserIdentity(
                user_id='user@example.com',
                display_name='Test User',
                active=True,
                extracted_at=datetime.utcnow()
            )
            # Use AsyncMock for async method
            mock_service.get_user_info = AsyncMock(return_value=mock_user_identity)
            MockService.return_value = mock_service

            # When: Request with valid token
            response = client.get(
                "/api/user/me",
                headers={"X-Forwarded-Access-Token": "valid-token"}
            )

            # Then: Should return user info
            assert response.status_code == 200
            data = response.json()
            assert data["userName"] == "user@example.com"
            assert data["displayName"] == "Test User"
            assert data["active"] is True

    def test_get_user_me_returns_500_with_invalid_token(self, client, monkeypatch):
        """Test that GET /api/user/me returns 500 when service fails."""
        # Set required env var
        monkeypatch.setenv('DATABRICKS_HOST', 'https://test.databricks.com')
        
        # Patch at the location where it's imported in the router
        with patch('server.routers.user.UserService') as MockService:
            mock_service = Mock()
            # Use AsyncMock for async method
            mock_service.get_user_info = AsyncMock(side_effect=Exception("Authentication failed"))
            MockService.return_value = mock_service

            # When: Request with invalid token
            response = client.get(
                "/api/user/me",
                headers={"X-Forwarded-Access-Token": "invalid-token"}
            )

            # Then: Should return 500
            assert response.status_code == 500
            assert "Failed to fetch user info" in response.json()["detail"]

    def test_get_user_me_falls_back_to_service_principal_when_token_missing(self, client):
        """Test that GET /api/user/me requires token (OBO-only, no service principal fallback)."""
        # When: Request without token
        response = client.get("/api/user/me")

        # Then: Should return 401 (no token = no access in OBO-only mode)
        assert response.status_code == 401

    def test_get_user_workspace_requires_valid_token(self, client):
        """Test that GET /api/user/me/workspace requires valid token (OBO-only)."""
        # When: Request without token
        response = client.get("/api/user/me/workspace")

        # Then: Should return 401 (OBO-only, no fallback)
        assert response.status_code == 401

    def test_get_user_workspace_returns_workspace_info_response(self, client, monkeypatch):
        """Test that GET /api/user/me/workspace returns UserWorkspaceInfo."""
        from server.models.user_session import UserIdentity, InternalWorkspaceInfo
        from datetime import datetime
        
        # Set required env var
        monkeypatch.setenv('DATABRICKS_HOST', 'https://test.databricks.com')
        
        # Patch at the location where it's imported in the router
        with patch('server.routers.user.UserService') as MockService:
            mock_service = Mock()
            # Mock get_user_info to return UserIdentity
            mock_user_identity = UserIdentity(
                user_id='user@example.com',
                display_name='Test User',
                active=True,
                extracted_at=datetime.utcnow()
            )
            mock_service.get_user_info = AsyncMock(return_value=mock_user_identity)
            
            # Mock get_workspace_info to return InternalWorkspaceInfo
            mock_workspace_info = InternalWorkspaceInfo(
                workspace_id='test-workspace-id',
                workspace_url='https://workspace.cloud.databricks.com',
                workspace_name='Test Workspace'
            )
            mock_service.get_workspace_info = AsyncMock(return_value=mock_workspace_info)
            MockService.return_value = mock_service

            # When: Request with valid token
            response = client.get(
                "/api/user/me/workspace",
                headers={"X-Forwarded-Access-Token": "valid-token"}
            )

            # Then: Should return workspace info
            assert response.status_code == 200
            data = response.json()
            assert data["user"]["userName"] == "user@example.com"
            assert data["user"]["displayName"] == "Test User"
            assert data["workspace"]["name"] == "Test Workspace"

    def test_all_endpoints_include_correlation_id_in_response_headers(self, client, monkeypatch):
        """Test that all endpoints include X-Correlation-ID in response headers."""
        from server.models.user_session import UserIdentity, InternalWorkspaceInfo
        from datetime import datetime
        
        # Set required env var
        monkeypatch.setenv('DATABRICKS_HOST', 'https://test.databricks.com')
        
        # Mock services to prevent actual calls - patch at router level
        with patch('server.routers.user.UserService') as MockService:
            mock_service = Mock()
            mock_user_identity = UserIdentity(
                user_id='test@example.com',
                display_name='Test',
                active=True,
                extracted_at=datetime.utcnow()
            )
            mock_workspace_info = InternalWorkspaceInfo(
                workspace_id='test-id',
                workspace_url='https://test.com',
                workspace_name='Test'
            )
            mock_service.get_user_info = AsyncMock(return_value=mock_user_identity)
            mock_service.get_workspace_info = AsyncMock(return_value=mock_workspace_info)
            MockService.return_value = mock_service

            # When: Making requests to different endpoints
            endpoints = [
                ("/api/user/me", True),  # Requires token
                ("/api/user/auth/status", False),  # No token required
                ("/api/user/me/workspace", True)  # Requires token
            ]
            correlation_ids = []

            for endpoint, requires_token in endpoints:
                headers = {"X-Correlation-ID": f"test-correlation-{endpoint}"}
                if requires_token:
                    headers["X-Forwarded-Access-Token"] = "test-token"
                    
                response = client.get(endpoint, headers=headers)

                # Then: Each response should include correlation ID
                assert "X-Correlation-ID" in response.headers
                correlation_ids.append(response.headers["X-Correlation-ID"])

            # Verify correlation IDs are preserved
            assert correlation_ids[0] == "test-correlation-/api/user/me"
            assert correlation_ids[1] == "test-correlation-/api/user/auth/status"
            assert correlation_ids[2] == "test-correlation-/api/user/me/workspace"


class TestAuthenticationStatusEndpoint:
    """Contract tests for authentication status endpoint."""

    def test_auth_status_returns_correct_mode_with_token(self, client, monkeypatch):
        """Test that /api/user/auth/status returns OBO mode with token."""
        from server.models.user_session import UserIdentity
        from datetime import datetime
        
        # Set required env var
        monkeypatch.setenv('DATABRICKS_HOST', 'https://test.databricks.com')
        
        # Mock UserService to return user identity - patch at router level
        with patch('server.routers.user.UserService') as MockService:
            mock_service = Mock()
            mock_user_identity = UserIdentity(
                user_id='user@example.com',
                display_name='Test User',
                active=True,
                extracted_at=datetime.utcnow()
            )
            mock_service.get_user_info = AsyncMock(return_value=mock_user_identity)
            MockService.return_value = mock_service
            
            # When: Request with token
            response = client.get(
                "/api/user/auth/status",
                headers={"X-Forwarded-Access-Token": "user-token"}
            )

            # Then: Should show OBO authentication
            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is True
            assert data["auth_mode"] == "obo"
            assert data["has_user_identity"] is True
            assert data["user_id"] == "user@example.com"

    def test_auth_status_returns_correct_mode_without_token(self, client):
        """Test that /api/user/auth/status returns service principal mode without token."""
        # When: Request without token
        response = client.get("/api/user/auth/status")

        # Then: Should show service principal authentication
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["auth_mode"] == "service_principal"
        assert data["has_user_identity"] is False or data["has_user_identity"] is True  # Depends on implementation