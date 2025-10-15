"""Integration tests for OBO-only authentication enforcement.

These tests validate that the application enforces OBO-only authentication:
- API endpoints return HTTP 401 when X-Forwarded-Access-Token is missing
- No service principal fallback behavior occurs
- Structured AUTH_MISSING error responses are returned
- No fallback log events are present

Test Requirements:
- T007: API endpoints return 401 without token
- T008: No service principal fallback in logs
"""

import pytest
from fastapi.testclient import TestClient
from server.app import app

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestOBOOnlyEndpoints:
    """Test that API endpoints require user token and return 401 without it."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_user_me_endpoint_returns_401_without_token(self, client):
        """Test /api/user/me returns HTTP 401 with AUTH_MISSING when token is missing."""
        response = client.get("/api/user/me")
        
        assert response.status_code == 401, "Should return 401 when token is missing"
        
        # Verify structured error response
        error_data = response.json()
        assert "error_code" in error_data, "Error response should have error_code"
        assert error_data["error_code"] == "AUTH_MISSING", "Error code should be AUTH_MISSING"
        assert "message" in error_data, "Error response should have message"
        assert "authentication required" in error_data["message"].lower(), \
            "Message should indicate authentication is required"
    
    def test_user_me_endpoint_returns_401_with_empty_token(self, client):
        """Test /api/user/me returns HTTP 401 when token header is empty."""
        response = client.get(
            "/api/user/me",
            headers={"X-Forwarded-Access-Token": ""}
        )
        
        assert response.status_code == 401, "Should return 401 when token is empty"
        
        error_data = response.json()
        assert error_data["error_code"] == "AUTH_MISSING", \
            "Empty token should be treated same as missing token"
    
    def test_unity_catalog_catalogs_returns_401_without_token(self, client):
        """Test /api/unity-catalog/catalogs returns HTTP 401 without token."""
        response = client.get("/api/unity-catalog/catalogs")
        
        assert response.status_code == 401, "Should return 401 when token is missing"
        
        error_data = response.json()
        assert error_data["error_code"] == "AUTH_MISSING"
        assert "authentication required" in error_data["message"].lower()
    
    def test_unity_catalog_schemas_returns_401_without_token(self, client):
        """Test /api/unity-catalog/catalogs/{catalog}/schemas returns HTTP 401 without token."""
        response = client.get("/api/unity-catalog/catalogs/main/schemas")
        
        assert response.status_code == 401, "Should return 401 when token is missing"
        
        error_data = response.json()
        assert error_data["error_code"] == "AUTH_MISSING"
    
    def test_model_serving_endpoints_returns_401_without_token(self, client):
        """Test /api/model-serving/endpoints returns HTTP 401 without token."""
        response = client.get("/api/model-serving/endpoints")
        
        assert response.status_code == 401, "Should return 401 when token is missing"
        
        error_data = response.json()
        assert error_data["error_code"] == "AUTH_MISSING"
        assert "authentication required" in error_data["message"].lower()
    
    def test_lakebase_preferences_returns_401_without_token(self, client):
        """Test /api/preferences returns HTTP 401 without token."""
        response = client.get("/api/preferences")
        
        assert response.status_code == 401, "Should return 401 when token is missing"
        
        error_data = response.json()
        assert error_data["error_code"] == "AUTH_MISSING"


class TestNoServicePrincipalFallback:
    """Test that no service principal fallback occurs in OBO-only mode."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_no_fallback_to_service_principal_on_missing_token(self, client, caplog):
        """Test that missing token does not trigger service principal fallback.
        
        This test verifies that:
        1. No auth.fallback_triggered log events are emitted
        2. No auth.mode events show mode="service_principal"
        3. Request fails immediately with AUTH_MISSING
        """
        import logging
        caplog.set_level(logging.INFO)
        
        # Make request without token
        response = client.get("/api/user/me")
        
        # Verify 401 response (no fallback)
        assert response.status_code == 401
        
        # Check logs for fallback events
        log_records = [record for record in caplog.records]
        
        # Verify NO fallback events
        fallback_events = [
            record for record in log_records 
            if "fallback" in record.message.lower() or 
               (hasattr(record, 'event') and record.event == 'auth.fallback_triggered')
        ]
        assert len(fallback_events) == 0, \
            "Should not trigger service principal fallback"
        
        # Verify NO service principal mode in logs
        for record in log_records:
            if hasattr(record, 'mode'):
                assert record.mode != "service_principal", \
                    "auth.mode should never be 'service_principal' in OBO-only"
                # If mode is present, it should be "obo"
                if record.mode:
                    assert record.mode == "obo", \
                        "auth.mode should always be 'obo' when present"
    
    def test_auth_mode_logs_always_show_obo(self, client, caplog):
        """Test that auth.mode log events always show mode='obo' (never service_principal)."""
        import logging
        caplog.set_level(logging.INFO)
        
        # Make request without token (should fail fast)
        response = client.get("/api/user/me")
        assert response.status_code == 401
        
        # Check for auth.mode events in logs
        auth_mode_events = [
            record for record in caplog.records 
            if hasattr(record, 'event') and record.event == 'auth.mode'
        ]
        
        # If auth.mode events exist, they should all be "obo"
        for event in auth_mode_events:
            if hasattr(event, 'mode'):
                assert event.mode == "obo", \
                    f"auth.mode should be 'obo', got '{event.mode}'"
                assert event.mode != "service_principal", \
                    "auth.mode should never be 'service_principal'"


class TestHealthEndpointPublic:
    """Test that /health endpoint is public (no authentication required)."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_health_endpoint_accessible_without_token(self, client):
        """Test /health endpoint works without authentication."""
        response = client.get("/health")
        
        # Note: This test may initially fail if health endpoint requires auth
        # It should PASS after health endpoint is made public (T035)
        assert response.status_code == 200, \
            "/health endpoint should be public (no authentication required)"
        
        health_data = response.json()
        assert "status" in health_data, "Health response should have status field"
    
    def test_health_endpoint_ignores_auth_header(self, client):
        """Test /health endpoint works even with invalid token (token is ignored)."""
        response = client.get(
            "/health",
            headers={"X-Forwarded-Access-Token": "invalid-token"}
        )
        
        # Health endpoint should ignore authentication headers
        assert response.status_code == 200, \
            "/health should ignore auth headers and remain public"


class TestErrorResponseStructure:
    """Test that 401 error responses follow structured format."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_401_error_has_required_fields(self, client):
        """Test that 401 errors include required fields: error_code, message."""
        response = client.get("/api/user/me")
        
        assert response.status_code == 401
        
        error_data = response.json()
        
        # Required fields
        assert "error_code" in error_data, "Error must have error_code field"
        assert "message" in error_data, "Error must have message field"
        
        # Verify error_code is valid
        valid_error_codes = [
            "AUTH_MISSING", "AUTH_INVALID", "AUTH_EXPIRED", 
            "AUTH_USER_IDENTITY_FAILED", "AUTH_RATE_LIMITED"
        ]
        assert error_data["error_code"] in valid_error_codes, \
            f"error_code must be one of {valid_error_codes}"
        
        # Verify message is user-friendly (not empty, contains useful info)
        assert len(error_data["message"]) > 0, "Message should not be empty"
        assert isinstance(error_data["message"], str), "Message should be string"
    
    def test_401_error_has_correlation_id_in_logs(self, client, caplog):
        """Test that 401 errors include correlation_id in logs."""
        import logging
        caplog.set_level(logging.INFO)
        
        response = client.get("/api/user/me")
        assert response.status_code == 401
        
        # Check logs for correlation_id
        log_records = [record for record in caplog.records]
        
        # At least one log record should have correlation_id
        correlation_ids = [
            getattr(record, 'correlation_id', None) 
            for record in log_records
        ]
        correlation_ids = [cid for cid in correlation_ids if cid is not None]
        
        assert len(correlation_ids) > 0, \
            "At least one log event should include correlation_id"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

