"""Simple test to verify test setup works."""

import pytest

pytestmark = pytest.mark.contract

def test_auth_status_endpoint_exists(client):
    """Test that auth/status endpoint exists."""
    response = client.get("/api/user/auth/status")
    assert response.status_code == 200
    data = response.json()
    assert "authenticated" in data
    assert "auth_mode" in data