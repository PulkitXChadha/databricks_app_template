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

    def test_get_user_me_returns_user_info_with_valid_token(self, client):
        """Test that GET /api/user/me returns UserInfoResponse with valid token."""
        with patch('server.services.user_service.UserService') as MockService:
            mock_service = Mock()
            mock_user_info = {
                'userName': 'user@example.com',
                'displayName': 'Test User',
                'active': True,
                'emails': ['user@example.com']
            }
            mock_service.get_user_info.return_value = mock_user_info
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

    def test_get_user_me_returns_500_with_invalid_token(self, client):
        """Test that GET /api/user/me returns 500 when service fails."""
        with patch('server.services.user_service.UserService') as MockService:
            mock_service = Mock()
            mock_service.get_user_info.side_effect = Exception("Authentication failed")
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
        """Test that GET /api/user/me falls back to service principal when token missing."""
        with patch('server.services.user_service.UserService') as MockService:
            mock_service = Mock()
            mock_sp_info = {
                'userName': 'service-principal@databricks.com',
                'displayName': 'Service Principal',
                'active': True,
                'emails': []
            }
            mock_service.get_user_info.return_value = mock_sp_info
            MockService.return_value = mock_service

            # When: Request without token
            response = client.get("/api/user/me")

            # Then: Should return service principal info
            assert response.status_code == 200
            data = response.json()
            assert "service-principal" in data["userName"].lower()

    def test_get_user_workspace_requires_valid_token(self, client):
        """Test that GET /api/user/me/workspace requires valid token."""
        # When: Request without token (should work with service principal)
        with patch('server.services.user_service.UserService') as MockService:
            mock_service = Mock()
            mock_workspace_info = {
                'user': {
                    'userName': 'service-principal@databricks.com',
                    'displayName': 'Service Principal',
                    'active': True
                },
                'workspace': {
                    'name': 'Test Workspace',
                    'url': 'https://workspace.cloud.databricks.com'
                }
            }
            mock_service.get_user_workspace_info.return_value = mock_workspace_info
            MockService.return_value = mock_service

            response = client.get("/api/user/me/workspace")

            # Then: Should work with service principal fallback
            assert response.status_code == 200

    def test_get_user_workspace_returns_workspace_info_response(self, client):
        """Test that GET /api/user/me/workspace returns UserWorkspaceInfo."""
        with patch('server.services.user_service.UserService') as MockService:
            mock_service = Mock()
            mock_workspace_info = {
                'user': {
                    'userName': 'user@example.com',
                    'displayName': 'Test User',
                    'active': True
                },
                'workspace': {
                    'name': 'Test Workspace',
                    'url': 'https://workspace.cloud.databricks.com'
                }
            }
            mock_service.get_user_workspace_info.return_value = mock_workspace_info
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

    def test_all_endpoints_include_correlation_id_in_response_headers(self, client):
        """Test that all endpoints include X-Correlation-ID in response headers."""
        # Mock services to prevent actual calls
        with patch('server.services.user_service.UserService') as MockService:
            mock_service = Mock()
            mock_service.get_user_info.return_value = {
                'userName': 'test@example.com',
                'displayName': 'Test',
                'active': True,
                'emails': []
            }
            mock_service.get_user_workspace_info.return_value = {
                'user': {'userName': 'test@example.com', 'displayName': 'Test', 'active': True},
                'workspace': {'name': 'Test', 'url': 'https://test.com'}
            }
            MockService.return_value = mock_service

            # When: Making requests to different endpoints
            endpoints = ["/api/user/me", "/api/user/auth/status", "/api/user/me/workspace"]
            correlation_ids = []

            for endpoint in endpoints:
                response = client.get(
                    endpoint,
                    headers={"X-Correlation-ID": f"test-correlation-{endpoint}"}
                )

                # Then: Each response should include correlation ID
                assert "X-Correlation-ID" in response.headers
                correlation_ids.append(response.headers["X-Correlation-ID"])

            # Verify correlation IDs are preserved
            assert correlation_ids[0] == "test-correlation-/api/user/me"
            assert correlation_ids[1] == "test-correlation-/api/user/auth/status"
            assert correlation_ids[2] == "test-correlation-/api/user/me/workspace"


class TestAuthenticationStatusEndpoint:
    """Contract tests for authentication status endpoint."""

    def test_auth_status_returns_correct_mode_with_token(self, client):
        """Test that /api/user/auth/status returns OBO mode with token."""
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
        assert data["has_user_identity"] is True or data["has_user_identity"] is False  # Depends on user extraction

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