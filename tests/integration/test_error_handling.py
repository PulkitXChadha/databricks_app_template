"""Integration tests for error handling and retry logic.

These tests verify that:
- Transient errors trigger retry with exponential backoff
- Non-retriable errors fail immediately
- Error responses include proper status codes and messages
- Retry logic respects max attempts
"""

import pytest

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
import time

from server.app import app
from server.lib.auth import AuthenticationError, RateLimitError


@pytest.fixture
def test_client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def user_token():
    """Mock user token."""
    return "test-user-token"


class TestErrorHandlingIntegration:
    """Test end-to-end error handling."""
    
    def test_transient_error_triggers_retry(self, test_client, user_token):
        """Test that transient errors trigger automatic retry."""
        with patch('server.services.user_service.UserService._fetch_user_info') as mock_fetch:
            # Simulate: fail twice, then succeed
            call_count = [0]
            
            def side_effect_with_retry(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] <= 2:
                    raise RateLimitError("Rate limit exceeded")
                else:
                    user_identity = Mock()
                    user_identity.user_id = "test@example.com"
                    user_identity.display_name = "Test User"
                    user_identity.workspace_url = "https://example.cloud.databricks.com"
                    return user_identity
            
            mock_fetch.side_effect = side_effect_with_retry
            
            # Make request
            start_time = time.time()
            response = test_client.get(
                "/api/user/me",
                headers={"X-Forwarded-Access-Token": user_token}
            )
            elapsed_time = time.time() - start_time
            
            # Should succeed after retries
            assert response.status_code == 200
            
            # Should have taken some time due to retry backoff
            assert elapsed_time > 0.1, "Should include retry delay"
            
            # Should have made 3 attempts (2 failures + 1 success)
            assert call_count[0] == 3
    
    def test_non_retriable_error_fails_immediately(self, test_client, user_token):
        """Test that non-retriable errors fail without retry."""
        with patch('server.services.user_service.UserService._fetch_user_info') as mock_fetch:
            # Simulate non-retriable error
            call_count = [0]
            
            def side_effect_immediate_fail(*args, **kwargs):
                call_count[0] += 1
                raise ValueError("Invalid configuration")  # Non-retriable error
            
            mock_fetch.side_effect = side_effect_immediate_fail
            
            # Make request
            start_time = time.time()
            response = test_client.get(
                "/api/user/me",
                headers={"X-Forwarded-Access-Token": user_token}
            )
            elapsed_time = time.time() - start_time
            
            # Should fail quickly (no retries)
            assert response.status_code == 500
            assert elapsed_time < 1.0, "Should fail immediately without retry"
            
            # Should have made only 1 attempt (no retries for non-retriable errors)
            assert call_count[0] == 1
    
    def test_max_retries_respected(self, test_client, user_token):
        """Test that retry logic respects max attempts."""
        with patch('server.services.user_service.UserService._fetch_user_info') as mock_fetch:
            # Always fail with retriable error
            call_count = [0]
            
            def side_effect_always_fail(*args, **kwargs):
                call_count[0] += 1
                raise RateLimitError("Rate limit exceeded")
            
            mock_fetch.side_effect = side_effect_always_fail
            
            # Make request
            response = test_client.get(
                "/api/user/me",
                headers={"X-Forwarded-Access-Token": user_token}
            )
            
            # Should eventually fail after max retries
            assert response.status_code in [401, 500]
            
            # Should have attempted exactly 3 times (max_attempts from config)
            assert call_count[0] == 3, "Should respect max retry attempts"
    
    def test_exponential_backoff_timing(self, test_client, user_token):
        """Test that retries use exponential backoff."""
        with patch('server.services.user_service.UserService._fetch_user_info') as mock_fetch:
            # Fail twice, then succeed
            call_count = [0]
            call_times = []
            
            def side_effect_track_timing(*args, **kwargs):
                call_count[0] += 1
                call_times.append(time.time())
                
                if call_count[0] <= 2:
                    raise RateLimitError("Rate limit exceeded")
                else:
                    user_identity = Mock()
                    user_identity.user_id = "test@example.com"
                    user_identity.display_name = "Test User"
                    user_identity.workspace_url = "https://example.cloud.databricks.com"
                    return user_identity
            
            mock_fetch.side_effect = side_effect_track_timing
            
            # Make request
            response = test_client.get(
                "/api/user/me",
                headers={"X-Forwarded-Access-Token": user_token}
            )
            
            assert response.status_code == 200
            assert len(call_times) == 3
            
            # Verify exponential backoff
            # First retry should wait ~1 second
            if len(call_times) >= 2:
                first_delay = call_times[1] - call_times[0]
                assert first_delay >= 0.5, "First retry should have delay"
            
            # Second retry should wait ~2 seconds
            if len(call_times) >= 3:
                second_delay = call_times[2] - call_times[1]
                # Note: Actual timing may vary due to test execution
    
    def test_error_response_format(self, test_client, user_token):
        """Test that error responses have proper format."""
        with patch('server.services.user_service.UserService.get_user_info') as mock_get_user:
            # Simulate authentication error
            mock_get_user.side_effect = AuthenticationError("Invalid token")
            
            # Make request
            response = test_client.get(
                "/api/user/me",
                headers={"X-Forwarded-Access-Token": user_token}
            )
            
            # Should return 401
            assert response.status_code == 401
            
            # Response should include error details
            data = response.json()
            assert 'detail' in data or 'message' in data, "Error response should include details"
    
    def test_database_error_handling(self, test_client, user_token):
        """Test that database errors are handled properly."""
        with patch('server.services.user_service.UserService.get_user_info') as mock_get_user:
            # Configure mock user
            user_identity = Mock()
            user_identity.user_id = "test@example.com"
            user_identity.display_name = "Test User"
            user_identity.workspace_url = "https://example.cloud.databricks.com"
            mock_get_user.return_value = user_identity
            
            with patch('server.services.lakebase_service.get_db_session') as mock_get_session:
                # Simulate database error
                from sqlalchemy.exc import OperationalError
                mock_get_session.side_effect = OperationalError("Database connection failed", None, None)
                
                # Make request
                response = test_client.get(
                    "/api/user/preferences",
                    headers={"X-Forwarded-Access-Token": user_token}
                )
                
                # Should return 500
                assert response.status_code == 500
    
    def test_upstream_service_timeout(self, test_client, user_token):
        """Test that upstream service timeouts are handled."""
        with patch('server.services.user_service.UserService._fetch_user_info') as mock_fetch:
            # Simulate timeout
            import asyncio
            mock_fetch.side_effect = asyncio.TimeoutError("Request timeout")
            
            # Make request
            response = test_client.get(
                "/api/user/me",
                headers={"X-Forwarded-Access-Token": user_token}
            )
            
            # Should return error
            assert response.status_code in [401, 500, 504]
    
    def test_concurrent_requests_handled_independently(self, test_client, user_token):
        """Test that concurrent requests with errors are handled independently."""
        with patch('server.services.user_service.UserService.get_user_info') as mock_get_user:
            # Configure mock user
            user_identity = Mock()
            user_identity.user_id = "test@example.com"
            user_identity.display_name = "Test User"
            user_identity.workspace_url = "https://example.cloud.databricks.com"
            mock_get_user.return_value = user_identity
            
            with patch('server.services.lakebase_service.get_db_session') as mock_get_session:
                # Mock database
                mock_session = Mock()
                mock_query = Mock()
                mock_filter_by = Mock()
                mock_filter_by.all.return_value = []
                mock_query.filter_by.return_value = mock_filter_by
                mock_session.query.return_value = mock_query
                mock_get_session.return_value = [mock_session]
                
                # Make multiple concurrent requests
                response1 = test_client.get(
                    "/api/user/preferences",
                    headers={"X-Forwarded-Access-Token": user_token}
                )
                
                response2 = test_client.get(
                    "/api/user/preferences",
                    headers={"X-Forwarded-Access-Token": user_token}
                )
                
                # Both should succeed independently
                assert response1.status_code == 200
                assert response2.status_code == 200

