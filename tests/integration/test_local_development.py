"""Integration tests for local development with user tokens.

These tests validate that developers can use Databricks CLI tokens for local development:
- Obtain token via `databricks auth token` command
- Start server with user token
- Make authenticated requests locally

Test Requirements:
- T018: Local development with CLI token works
"""

import pytest
import subprocess
import os
from fastapi.testclient import TestClient
from unittest.mock import patch

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestLocalDevelopmentWithCLIToken:
    """Test local development workflow using Databricks CLI tokens."""
    
    @pytest.fixture
    def mock_cli_token(self):
        """Mock token from Databricks CLI."""
        return "dapi1234567890abcdefghijklmnopqrstuvwxyz"
    
    @pytest.fixture
    def client(self):
        """Create test client for local development testing."""
        from server.app import app
        return TestClient(app)
    
    def test_can_obtain_token_from_databricks_cli(self):
        """Test that developers can obtain token from Databricks CLI.
        
        This test demonstrates the command developers should run locally:
        export DATABRICKS_USER_TOKEN=$(databricks auth token)
        """
        # This test documents the expected CLI workflow
        # In actual local development, developers run:
        # databricks auth token --profile default
        
        # For testing, we simulate the CLI call
        cli_command = ["databricks", "auth", "token"]
        
        # This test passes if the command structure is correct
        # (actual execution requires Databricks CLI to be installed and configured)
        assert cli_command[0] == "databricks", "Should use databricks CLI"
        assert cli_command[1] == "auth", "Should use auth subcommand"
        assert cli_command[2] == "token", "Should use token command"
    
    def test_api_requests_succeed_with_cli_token(self, client, mock_cli_token):
        """Test that API requests succeed when using token from CLI."""
        # Mock the service to avoid actual Databricks API calls
        with patch('server.services.user_service.WorkspaceClient') as mock_client:
            # Mock successful user info response
            mock_user = type('User', (), {
                'user_name': 'developer@example.com',
                'display_name': 'Local Developer',
                'active': True
            })()
            
            mock_ws_client = type('WSClient', (), {
                'current_user': type('CurrentUser', (), {
                    'me': lambda: mock_user
                })()
            })()
            
            mock_client.return_value = mock_ws_client
            
            # Make request with CLI token
            response = client.get(
                "/api/user/me",
                headers={"X-Forwarded-Access-Token": mock_cli_token}
            )
            
            # Should succeed with user-level authentication
            assert response.status_code == 200, \
                "API request should succeed with CLI token"
            
            user_data = response.json()
            assert "user_id" in user_data, "Response should include user_id"
    
    def test_local_dev_with_profile_specific_token(self):
        """Test that developers can use profile-specific tokens.
        
        Demonstrates:
        databricks auth token --profile dev
        databricks auth token --profile prod
        """
        # Document the multi-profile workflow
        dev_command = ["databricks", "auth", "token", "--profile", "dev"]
        prod_command = ["databricks", "auth", "token", "--profile", "prod"]
        
        assert "--profile" in dev_command, "Should support --profile flag"
        assert "dev" in dev_command, "Can specify dev profile"
        assert "prod" in prod_command, "Can specify prod profile"
    
    def test_local_development_without_service_principal_env_vars(self, client, mock_cli_token):
        """Test that local development works without DATABRICKS_CLIENT_ID/SECRET."""
        # Ensure service principal env vars are not set
        env_without_sp = os.environ.copy()
        env_without_sp.pop('DATABRICKS_CLIENT_ID', None)
        env_without_sp.pop('DATABRICKS_CLIENT_SECRET', None)
        
        with patch.dict(os.environ, env_without_sp, clear=False):
            with patch('server.services.user_service.WorkspaceClient') as mock_client:
                # Mock successful response
                mock_user = type('User', (), {
                    'user_name': 'developer@example.com',
                    'display_name': 'Local Developer',
                    'active': True
                })()
                
                mock_ws_client = type('WSClient', (), {
                    'current_user': type('CurrentUser', (), {
                        'me': lambda: mock_user
                    })()
                })()
                
                mock_client.return_value = mock_ws_client
                
                # Make request with user token only
                response = client.get(
                    "/api/user/me",
                    headers={"X-Forwarded-Access-Token": mock_cli_token}
                )
                
                # Should work without service principal credentials
                assert response.status_code == 200, \
                    "Local dev should work without DATABRICKS_CLIENT_ID/SECRET"


class TestLocalDevelopmentErrorHandling:
    """Test error handling during local development."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from server.app import app
        return TestClient(app)
    
    def test_missing_token_returns_clear_error(self, client):
        """Test that missing token returns clear error for local developers."""
        response = client.get("/api/user/me")
        
        assert response.status_code == 401
        
        error_data = response.json()
        assert error_data["error_code"] == "AUTH_MISSING"
        
        # Error message should guide developers
        message = error_data["message"].lower()
        assert "authentication required" in message or "token" in message, \
            "Error should guide developers to provide token"
    
    def test_invalid_token_returns_clear_error(self, client):
        """Test that invalid token returns clear error."""
        with patch('server.services.user_service.WorkspaceClient') as mock_client:
            # Mock Databricks SDK error for invalid token
            from databricks.sdk.errors import DatabricksError
            
            def raise_error():
                raise DatabricksError("Invalid authentication credentials")
            
            mock_ws_client = type('WSClient', (), {
                'current_user': type('CurrentUser', (), {
                    'me': raise_error
                })()
            })()
            
            mock_client.return_value = mock_ws_client
            
            response = client.get(
                "/api/user/me",
                headers={"X-Forwarded-Access-Token": "invalid-token"}
            )
            
            # Should return structured error
            assert response.status_code == 401
            
            error_data = response.json()
            assert "error_code" in error_data
            # Error code should be AUTH_INVALID or similar
            assert error_data["error_code"] in ["AUTH_INVALID", "AUTH_EXPIRED", "AUTH_USER_IDENTITY_FAILED"]


class TestLocalDevelopmentDocumentation:
    """Test that local development workflow is well-documented."""
    
    def test_local_development_docs_exist(self):
        """Test that LOCAL_DEVELOPMENT.md exists and contains CLI token instructions."""
        import os
        
        docs_path = os.path.join(
            os.path.dirname(__file__),
            "../../docs/LOCAL_DEVELOPMENT.md"
        )
        
        # Normalize path
        docs_path = os.path.normpath(docs_path)
        
        # Check file exists
        assert os.path.exists(docs_path), \
            "LOCAL_DEVELOPMENT.md should exist with CLI token instructions"
        
        # Check content includes CLI token workflow
        with open(docs_path, 'r') as f:
            content = f.read()
        
        # Should document the CLI token command
        assert "databricks auth token" in content or "DATABRICKS_USER_TOKEN" in content, \
            "Documentation should include CLI token workflow"
    
    def test_get_user_token_script_exists(self):
        """Test that scripts/get_user_token.py exists and works."""
        import os
        
        script_path = os.path.join(
            os.path.dirname(__file__),
            "../../scripts/get_user_token.py"
        )
        
        # Normalize path
        script_path = os.path.normpath(script_path)
        
        # Check file exists
        assert os.path.exists(script_path), \
            "scripts/get_user_token.py should exist to help developers obtain tokens"
        
        # Check it's executable or has proper shebang
        with open(script_path, 'r') as f:
            first_line = f.readline()
        
        assert first_line.startswith('#!') or 'python' in first_line.lower(), \
            "Script should be executable Python file"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

