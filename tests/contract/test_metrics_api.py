"""
Contract tests for metrics API endpoints.

Tests API contracts from specs/006-app-metrics/contracts/metrics-api.yaml
Following TDD RED-GREEN-REFACTOR: These tests MUST FAIL initially.
"""

import pytest
from fastapi.testclient import TestClient
from server.app import app
from unittest.mock import patch, MagicMock

client = TestClient(app)


# ============================================================================
# T013: Contract test for GET /api/v1/metrics/performance endpoint
# ============================================================================

def test_get_performance_metrics_endpoint_returns_200_for_admin(mock_admin_check_true, mock_databricks_admin_client, mock_db_for_metrics):                                           
    """
    Test that performance metrics endpoint returns 200 for admin users.
    
    Expected to FAIL initially (RED phase) - endpoint may not exist or return correct schema.                                                                   
    """
    response = client.get(
        "/api/v1/metrics/performance",
        headers={"X-Forwarded-Access-Token": "mock-admin-token"}
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"                                                                             
    
    # Validate response schema
    data = response.json()
    assert "time_range" in data
    assert "metrics" in data
    assert "avg_response_time_ms" in data["metrics"]
    assert "error_rate" in data["metrics"]
    
    # FR-003: Verify error_rate is numeric decimal ratio (0.0-1.0), not string or percentage >1.0                                                               
    error_rate = data["metrics"]["error_rate"]
    assert isinstance(error_rate, (int, float)), f"error_rate must be numeric, got {type(error_rate)}"                                                          
    assert 0.0 <= error_rate <= 1.0, f"error_rate must be decimal ratio 0.0-1.0, got {error_rate}"


def test_get_performance_metrics_accepts_time_range_param(mock_admin_check_true, mock_databricks_admin_client, mock_db_for_metrics):                                                 
    """Test that endpoint accepts time_range query parameter"""
    for time_range in ["24h", "7d", "30d", "90d"]:
        response = client.get(
            f"/api/v1/metrics/performance?time_range={time_range}",
            headers={"X-Forwarded-Access-Token": "mock-admin-token"}
        )
        assert response.status_code == 200, f"Should handle {time_range} parameter"                                                                             


def test_get_performance_metrics_accepts_endpoint_filter(mock_admin_check_true, mock_databricks_admin_client, mock_db_for_metrics):                                                  
    """Test that endpoint accepts endpoint query parameter for filtering"""
    response = client.get(
        "/api/v1/metrics/performance?endpoint=/api/v1/lakebase/sources",
        headers={"X-Forwarded-Access-Token": "mock-admin-token"}
    )
    assert response.status_code == 200


# ============================================================================
# T014: Contract test for admin privilege check
# ============================================================================

def test_get_performance_metrics_returns_403_for_non_admin(mock_admin_check_false, mock_databricks_non_admin_client):
    """
    Test that non-admin users receive 403 Forbidden with correct error message.
    
    Expected to FAIL initially (RED phase) - admin check may not be implemented.
    """
    response = client.get(
        "/api/v1/metrics/performance",
        headers={"X-Forwarded-Access-Token": "mock-non-admin-token"}
    )
    
    assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
    
    # Validate error response structure
    data = response.json()
    assert "detail" in data or "error" in data, "Error response should contain detail or error field"


def test_get_performance_metrics_returns_401_for_unauthenticated():
    """Test that unauthenticated requests receive 401"""
    response = client.get("/api/v1/metrics/performance")
    assert response.status_code in [401, 403], "Should require authentication"


# ============================================================================
# T061: Contract test for POST /api/v1/metrics/usage-events endpoint (US3)
# ============================================================================

def test_post_usage_events_accepts_batch():
    """
    Test that usage events endpoint accepts batch submissions and returns 202.
    
    Expected to FAIL initially (RED phase) - endpoint may not exist.
    """
    with patch('server.lib.auth.get_user_token', return_value='mock-token'):
        with patch('databricks.sdk.WorkspaceClient') as mock_client:
            mock_user = MagicMock()
            mock_user.user_name = "test@example.com"
            mock_client.return_value.current_user.me.return_value = mock_user
            
            events = [
                {
                    "event_type": "page_view",
                    "page_name": "/metrics",
                    "timestamp": "2025-10-20T12:00:00Z"
                },
                {
                    "event_type": "button_click",
                    "page_name": "/metrics",
                    "element_id": "refresh-button",
                    "timestamp": "2025-10-20T12:01:00Z"
                }
            ]
            
            response = client.post(
                "/api/v1/metrics/usage-events",
                json={"events": events},
                headers={"X-Forwarded-Access-Token": "mock-token"}
            )
            
            assert response.status_code == 202, f"Expected 202 Accepted, got {response.status_code}"
            data = response.json()
            assert "events_received" in data or "message" in data


def test_post_usage_events_returns_401_for_unauthenticated():
    """Test that unauthenticated requests are rejected"""
    response = client.post(
        "/api/v1/metrics/usage-events",
        json={"events": []}
    )
    assert response.status_code == 401, "Should require authentication"


# ============================================================================
# T062: Contract test for GET /api/v1/metrics/usage endpoint
# ============================================================================

def test_get_usage_metrics_endpoint_exists(mock_admin_check_true, mock_databricks_admin_client, mock_db_for_metrics):
    """
    Test that usage metrics endpoint returns data for admin users.
    
    Expected to FAIL initially (RED phase).
    """
    response = client.get(
        "/api/v1/metrics/usage",
        headers={"X-Forwarded-Access-Token": "mock-admin-token"}
    )
    
    assert response.status_code == 200, "Endpoint should return 200 for admin"                                                          


def test_get_usage_metrics_returns_403_for_non_admin(mock_admin_check_false, mock_databricks_non_admin_client, mock_db_for_metrics):
    """Test that non-admin users receive 403 for usage metrics"""
    response = client.get(
        "/api/v1/metrics/usage",
        headers={"X-Forwarded-Access-Token": "mock-token"}
    )
    assert response.status_code == 403


# ============================================================================
# T064.5: Contract test for batch size limit enforcement (FR-012)
# ============================================================================

def test_post_usage_events_rejects_oversized_batch():
    """
    Test that batches exceeding 1000 events are rejected with 413 Payload Too Large.
    
    Expected to FAIL initially (RED phase) - validation may not exist.
    """
    with patch('server.lib.auth.get_user_token', return_value='mock-token'):
        # Create 1001 events (exceeds max batch size of 1000)
        oversized_batch = [
            {
                "event_type": "page_view",
                "page_name": "/test",
                "timestamp": f"2025-10-20T12:{i:02d}:00Z"
            }
            for i in range(1001)
        ]
        
        response = client.post(
            "/api/v1/metrics/usage-events",
            json={"events": oversized_batch},
            headers={"X-Forwarded-Access-Token": "mock-token"}
        )
        
        assert response.status_code == 413, f"Expected 413 for oversized batch, got {response.status_code}"


# ============================================================================
# T064.6: Contract test for FR-013 custom exception handler
# ============================================================================

def test_post_usage_events_returns_structured_error_for_oversized_batch():
    """
    Test that oversized batch returns 413 (not 422) with structured error body.
    Validates FR-013 custom exception handler.
    
    Expected to FAIL initially (RED phase).
    """
    with patch('server.lib.auth.get_user_token', return_value='mock-token'):
        oversized_batch = [
            {"event_type": "page_view", "page_name": "/test", "timestamp": f"2025-10-20T12:00:{i:02d}Z"}
            for i in range(1001)
        ]
        
        response = client.post(
            "/api/v1/metrics/usage-events",
            json={"events": oversized_batch},
            headers={"X-Forwarded-Access-Token": "mock-token"}
        )
        
        # FR-013: Must return 413, not 422
        assert response.status_code == 413, f"Expected 413 (not 422), got {response.status_code}"
        
        # Validate structured error body
        data = response.json()
        assert "detail" in data
        assert "max_batch_size" in data, "Error should include max_batch_size field"
        assert data["max_batch_size"] == 1000
        assert "received" in data, "Error should include received count"
        assert data["received"] == 1001


# ============================================================================
# T092: Contract test for GET /api/v1/metrics/time-series endpoint (US4)
# ============================================================================

def test_get_time_series_endpoint_returns_200_for_admin(mock_admin_check_true, mock_databricks_admin_client, mock_db_for_metrics):
    """
    Test that time-series endpoint returns hourly data points.
    
    Expected to FAIL initially (RED phase) - US4 not implemented yet.
    """
    response = client.get(
        "/api/v1/metrics/time-series?time_range=7d&metric_type=performance",
        headers={"X-Forwarded-Access-Token": "mock-admin-token"}
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    # Validate response schema per OpenAPI spec
    data = response.json()
    assert "time_range" in data, "Response must include time_range"
    assert "interval" in data, "Response must include interval"
    assert "data_points" in data, "Response must include data_points"
    
    # Validate data_points is array of hourly buckets
    assert isinstance(data["data_points"], list), "data_points must be array"
    if len(data["data_points"]) > 0:
        point = data["data_points"][0]
        assert "timestamp" in point, "Each data point must have timestamp"


def test_get_time_series_requires_metric_type_parameter(mock_admin_check_true, mock_databricks_admin_client, mock_db_for_metrics):
    """Test that metric_type parameter is required"""
    response = client.get(
        "/api/v1/metrics/time-series?time_range=7d",
        headers={"X-Forwarded-Access-Token": "mock-admin-token"}
    )
    
    # Should return 422 Unprocessable Entity for missing required parameter
    assert response.status_code in [400, 422], "Should require metric_type parameter"


def test_get_time_series_accepts_metric_type_values(mock_admin_check_true, mock_databricks_admin_client, mock_db_for_metrics):
    """Test that endpoint accepts valid metric_type values"""
    for metric_type in ["performance", "usage", "both"]:
        response = client.get(
            f"/api/v1/metrics/time-series?time_range=24h&metric_type={metric_type}",
            headers={"X-Forwarded-Access-Token": "mock-admin-token"}
        )
        assert response.status_code == 200, f"Should accept metric_type={metric_type}"


def test_get_time_series_returns_5min_interval_for_24h(mock_admin_check_true, mock_databricks_admin_client, mock_db_for_metrics):
    """Test that 24h time range returns 5-minute interval data"""
    response = client.get(
        "/api/v1/metrics/time-series?time_range=24h&metric_type=performance",
        headers={"X-Forwarded-Access-Token": "mock-admin-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["interval"] == "5min", "24h range should use 5-minute intervals for higher granularity"


def test_get_time_series_returns_hourly_interval_for_7d_and_longer(mock_admin_check_true, mock_databricks_admin_client, mock_db_for_metrics):
    """Test that 7d, 30d, 90d time ranges return hourly interval data"""
    for time_range in ["7d", "30d", "90d"]:
        response = client.get(
            f"/api/v1/metrics/time-series?time_range={time_range}&metric_type=performance",
            headers={"X-Forwarded-Access-Token": "mock-admin-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["interval"] == "hourly", f"{time_range} range should use hourly intervals"


def test_get_time_series_returns_403_for_non_admin(mock_admin_check_false, mock_databricks_non_admin_client):
    """Test that non-admin users receive 403"""
    response = client.get(
        "/api/v1/metrics/time-series?time_range=7d&metric_type=performance",
        headers={"X-Forwarded-Access-Token": "mock-non-admin-token"}
    )
    
    assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"


# ============================================================================
# T082.6: Contract test for GET /api/v1/metrics/usage/count endpoint
# ============================================================================

def test_get_usage_count_endpoint_returns_count(mock_databricks_admin_client, mock_db_for_metrics):
    """
    Test that usage count endpoint returns count for authenticated user.
    
    Expected to FAIL initially (RED phase) - endpoint doesn't exist yet.
    """
    response = client.get(
        "/api/v1/metrics/usage/count?time_range=24h",
        headers={"X-Forwarded-Access-Token": "mock-token"}
    )
    
    assert response.status_code == 200, "Endpoint should return 200 for authenticated user"                                                          
    
    data = response.json()
    assert "count" in data, "Response should include count field"
    assert isinstance(data["count"], int), "Count must be integer"


def test_get_usage_count_returns_401_for_unauthenticated():
    """Test that unauthenticated requests are rejected"""
    response = client.get("/api/v1/metrics/usage/count")
    assert response.status_code == 401


# Fixtures are now in tests/conftest.py for shared use across all test modules

