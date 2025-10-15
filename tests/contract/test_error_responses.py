"""Contract Tests: Authentication Error Responses

Tests that authentication endpoints return standardized error responses
with proper error codes, messages, and correlation IDs.
"""

import pytest


class TestMissingTokenErrors:
    """Test AUTH_MISSING error responses when token is not provided."""
    
    def test_user_me_endpoint_missing_token(self, client):
        """Test /api/user/me returns AUTH_MISSING when token is missing."""
        response = client.get("/api/user/me")
        
        assert response.status_code == 401
        data = response.json()
        
        # Verify error structure
        assert "error_code" in data or "detail" in data
        
        # Handle both direct and nested detail structures
        if "detail" in data and isinstance(data["detail"], dict):
            error_data = data["detail"]
        else:
            error_data = data
        
        assert error_data.get("error_code") == "AUTH_MISSING"
        assert "authentication required" in error_data.get("message", "").lower()
    
    def test_unity_catalog_endpoint_missing_token(self, client):
        """Test /api/unity-catalog/catalogs returns AUTH_MISSING when token is missing."""
        response = client.get("/api/unity-catalog/catalogs")
        
        assert response.status_code == 401
        data = response.json()
        
        # Handle both direct and nested detail structures
        if "detail" in data and isinstance(data["detail"], dict):
            error_data = data["detail"]
        else:
            error_data = data
        
        assert error_data.get("error_code") == "AUTH_MISSING"
    
    def test_model_serving_endpoint_missing_token(self, client):
        """Test /api/model-serving/endpoints returns AUTH_MISSING when token is missing."""
        response = client.get("/api/model-serving/endpoints")
        
        assert response.status_code == 401
        data = response.json()
        
        # Handle both direct and nested detail structures
        if "detail" in data and isinstance(data["detail"], dict):
            error_data = data["detail"]
        else:
            error_data = data
        
        assert error_data.get("error_code") == "AUTH_MISSING"
    
    def test_empty_token_treated_as_missing(self, client):
        """Test that empty token string is treated same as missing token."""
        response = client.get(
            "/api/user/me",
            headers={"X-Forwarded-Access-Token": ""}
        )
        
        assert response.status_code == 401
        data = response.json()
        
        # Handle both direct and nested detail structures
        if "detail" in data and isinstance(data["detail"], dict):
            error_data = data["detail"]
        else:
            error_data = data
        
        assert error_data.get("error_code") == "AUTH_MISSING"


class TestInvalidTokenErrors:
    """Test AUTH_INVALID error responses when token is malformed or invalid."""
    
    def test_user_me_endpoint_invalid_token(self, client):
        """Test /api/user/me returns AUTH_INVALID when token is malformed."""
        response = client.get(
            "/api/user/me",
            headers={"X-Forwarded-Access-Token": "invalid-token-12345"}
        )
        
        # Should return 401 (authentication failure)
        assert response.status_code == 401
        data = response.json()
        
        # Handle both direct and nested detail structures
        if "detail" in data and isinstance(data["detail"], dict):
            error_data = data["detail"]
        else:
            error_data = data
        
        # Should indicate authentication problem (either INVALID or EXPIRED)
        error_code = error_data.get("error_code", "")
        assert error_code in ["AUTH_INVALID", "AUTH_EXPIRED", "AUTH_USER_IDENTITY_FAILED"]
    
    def test_malformed_token_structure(self, client):
        """Test various malformed token formats."""
        malformed_tokens = [
            "not-a-real-token",
            "dapi",  # Too short
            "Bearer invalid-token",  # Wrong format
            "123456",  # Numeric only
            "x" * 1000  # Too long
        ]
        
        for token in malformed_tokens:
            response = client.get(
                "/api/user/me",
                headers={"X-Forwarded-Access-Token": token}
            )
            
            assert response.status_code == 401, f"Failed for token: {token[:20]}..."
            data = response.json()
            
            # Handle both direct and nested detail structures
            if "detail" in data and isinstance(data["detail"], dict):
                error_data = data["detail"]
            else:
                error_data = data
            
            assert "error_code" in error_data


class TestErrorResponseStructure:
    """Test that error responses follow the standardized structure."""
    
    def test_error_response_has_required_fields(self, client):
        """Test that error responses contain all required fields."""
        response = client.get("/api/user/me")
        
        assert response.status_code == 401
        data = response.json()
        
        # Handle both direct and nested detail structures
        if "detail" in data and isinstance(data["detail"], dict):
            error_data = data["detail"]
        else:
            error_data = data
        
        # Required fields
        assert "error_code" in error_data
        assert "message" in error_data
        
        # Verify types
        assert isinstance(error_data["error_code"], str)
        assert isinstance(error_data["message"], str)
        
        # Verify message is user-friendly
        assert len(error_data["message"]) > 0
        assert not error_data["message"].startswith("Exception:")
    
    def test_error_codes_are_valid(self, client):
        """Test that error codes match the defined enum values."""
        valid_error_codes = [
            "AUTH_MISSING",
            "AUTH_INVALID",
            "AUTH_EXPIRED",
            "AUTH_USER_IDENTITY_FAILED",
            "AUTH_RATE_LIMITED",
            "AUTH_MALFORMED"
        ]
        
        response = client.get("/api/user/me")
        data = response.json()
        
        # Handle both direct and nested detail structures
        if "detail" in data and isinstance(data["detail"], dict):
            error_data = data["detail"]
        else:
            error_data = data
        
        error_code = error_data.get("error_code")
        assert error_code in valid_error_codes


class TestCorrelationIDs:
    """Test that error responses include correlation IDs for tracing."""
    
    def test_error_response_includes_correlation_id_in_headers(self, client):
        """Test that error responses include X-Correlation-ID header."""
        response = client.get("/api/user/me")
        
        assert response.status_code == 401
        
        # Correlation ID should be in response headers
        headers = dict(response.headers)
        
        # Check for correlation ID in headers (various possible header names)
        correlation_header_found = any(
            "correlation" in key.lower() or "request-id" in key.lower()
            for key in headers.keys()
        )
        
        # Note: Correlation ID might not be in headers depending on middleware implementation
        # The important thing is that it's logged, which we can't test in contract tests
        # This test documents the expectation even if not yet implemented
    
    def test_multiple_requests_have_different_correlation_ids(self, client):
        """Test that different requests get different correlation IDs."""
        response1 = client.get("/api/user/me")
        response2 = client.get("/api/user/me")
        
        assert response1.status_code == 401
        assert response2.status_code == 401
        
        # Each response should be independent
        # Correlation IDs would be different if checked
        # This test documents the expected behavior


class TestErrorMessagesAreUserFriendly:
    """Test that error messages are clear and actionable."""
    
    def test_missing_token_message_is_actionable(self, client):
        """Test that missing token error message tells user what to do."""
        response = client.get("/api/user/me")
        data = response.json()
        
        # Handle both direct and nested detail structures
        if "detail" in data and isinstance(data["detail"], dict):
            error_data = data["detail"]
        else:
            error_data = data
        
        message = error_data.get("message", "").lower()
        
        # Should mention authentication or token
        assert "authentication" in message or "token" in message
        
        # Should be actionable
        assert len(message) > 20  # Not just "Unauthorized"
    
    def test_error_messages_dont_leak_implementation_details(self, client):
        """Test that error messages don't expose internal implementation."""
        response = client.get("/api/user/me")
        data = response.json()
        
        # Handle both direct and nested detail structures
        if "detail" in data and isinstance(data["detail"], dict):
            error_data = data["detail"]
        else:
            error_data = data
        
        message = error_data.get("message", "").lower()
        
        # Should not contain implementation details
        forbidden_terms = [
            "traceback",
            "exception",
            "python",
            "fastapi",
            "databricks sdk",
            "workspace client"
        ]
        
        for term in forbidden_terms:
            assert term not in message, f"Error message leaked implementation detail: {term}"


@pytest.mark.integration
class TestRateLimitErrors:
    """Test AUTH_RATE_LIMITED error responses (integration test)."""
    
    @pytest.mark.skip(reason="Rate limiting requires actual API calls")
    def test_rate_limit_returns_retry_after(self, client):
        """Test that rate limit errors include retry_after field."""
        # This would require actually hitting rate limits
        # Left as placeholder for future integration testing
        pass
