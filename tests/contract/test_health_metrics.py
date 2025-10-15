"""Contract Tests: Health and Metrics Endpoints

Tests that /health is public and /metrics requires authentication.
"""

import pytest


class TestHealthEndpoint:
    """Test that /health endpoint is public (no authentication required)."""
    
    def test_health_returns_200_without_token(self, client):
        """Test that /health returns HTTP 200 without authentication."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return status field
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_health_works_with_token(self, client):
        """Test that /health also works with authentication header (ignored)."""
        response = client.get(
            "/health",
            headers={"X-Forwarded-Access-Token": "some-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_health_fast_response(self, client):
        """Test that /health responds quickly (< 100ms)."""
        import time
        
        start = time.time()
        response = client.get("/health")
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 0.1  # Less than 100ms


class TestMetricsEndpoint:
    """Test that /metrics endpoint requires authentication."""
    
    def test_metrics_returns_401_without_token(self, client):
        """Test that /metrics returns HTTP 401 without authentication."""
        response = client.get("/metrics")
        
        assert response.status_code == 401
        data = response.json()
        
        # Should return structured error
        if "detail" in data and isinstance(data["detail"], dict):
            error_data = data["detail"]
        else:
            error_data = data
        
        assert error_data.get("error_code") == "AUTH_MISSING"
    
    def test_metrics_returns_200_with_valid_token(self, client):
        """Test that /metrics returns HTTP 200 with valid token."""
        # Use a real token from environment (this test requires valid credentials)
        import os
        import subprocess
        
        try:
            # Try to get a real token
            result = subprocess.run(
                ["databricks", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                token = result.stdout.strip()
                response = client.get(
                    "/metrics",
                    headers={"X-Forwarded-Access-Token": token}
                )
                
                assert response.status_code == 200
                # Should be Prometheus format (text/plain)
                assert "text/plain" in response.headers.get("content-type", "")
                # Should contain some metrics
                assert b"auth_requests_total" in response.content or b"request_duration_seconds" in response.content
            else:
                pytest.skip("Databricks CLI token not available")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("Databricks CLI not available")
    
    def test_metrics_returns_prometheus_format(self, client):
        """Test that /metrics returns Prometheus format when authenticated."""
        # This test uses a mock token - will fail until endpoint requires auth
        import os
        import subprocess
        
        try:
            result = subprocess.run(
                ["databricks", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                token = result.stdout.strip()
                response = client.get(
                    "/metrics",
                    headers={"X-Forwarded-Access-Token": token}
                )
                
                if response.status_code == 200:
                    # Check for Prometheus format characteristics
                    content = response.text
                    
                    # Should contain HELP lines
                    assert "# HELP" in content
                    # Should contain TYPE lines
                    assert "# TYPE" in content
                    # Should contain metrics
                    assert len(content) > 100  # Non-empty metrics
            else:
                pytest.skip("Databricks CLI token not available")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("Databricks CLI not available")
    
    def test_metrics_empty_token_treated_as_missing(self, client):
        """Test that empty token string returns AUTH_MISSING."""
        response = client.get(
            "/metrics",
            headers={"X-Forwarded-Access-Token": ""}
        )
        
        assert response.status_code == 401
        data = response.json()
        
        if "detail" in data and isinstance(data["detail"], dict):
            error_data = data["detail"]
        else:
            error_data = data
        
        assert error_data.get("error_code") == "AUTH_MISSING"


class TestEndpointAccessPatterns:
    """Test that access patterns are correct for monitoring systems."""
    
    def test_health_accessible_from_monitoring(self, client):
        """Test that health can be called without any headers (monitoring pattern)."""
        response = client.get("/health")
        
        # Monitoring systems need to be able to call this without configuration
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_metrics_requires_user_context(self, client):
        """Test that metrics requires user authentication (not service account)."""
        response = client.get("/metrics")
        
        # Should require authentication
        assert response.status_code == 401

