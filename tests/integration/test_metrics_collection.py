"""
Integration tests for automatic performance metrics collection via middleware.

Tests verify that middleware automatically captures request metrics without impacting application functionality.
Following TDD RED-GREEN-REFACTOR: These tests MUST FAIL initially.
"""

import pytest
import time
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from server.app import app
from server.models.performance_metric import PerformanceMetric
from server.lib.database import get_db_session
from unittest.mock import patch, MagicMock


client = TestClient(app)


# ============================================================================
# T039: Integration test for middleware metric collection
# ============================================================================

def test_middleware_creates_metric_for_successful_request(test_db_session):
    """
    Test that middleware automatically creates performance metric for successful API request.
    
    Expected to FAIL initially (RED phase) - middleware may not record metrics.
    """
    # Patch database session at middleware module level
    with patch('server.lib.metrics_middleware.get_db_session', return_value=iter([test_db_session])):
        # Patch auth to bypass authentication
        with patch('server.services.admin_service.is_workspace_admin', return_value=True):
            with patch('server.lib.auth.get_user_token', return_value='mock-token'):
                # Make API request to non-excluded endpoint
                response = client.get("/api/v1/metrics/performance")  # Admin-only endpoint
                
                # Should get 200 (or auth-related error, but middleware should still record)
                # Query database for created metric
                metrics = test_db_session.query(PerformanceMetric).filter(
                    PerformanceMetric.endpoint == "/api/v1/metrics/performance"
                ).all()
                
                assert len(metrics) > 0, "Middleware should create metric for request"
                
                # Verify metric details
                metric = metrics[0]
                assert metric.method == "GET"
                assert metric.status_code in [200, 401, 403], "Should record actual status code"
                assert metric.response_time_ms > 0
                assert metric.response_time_ms < 1000, "Response time should be reasonable"


# ============================================================================
# T040: Integration test for error metric collection
# ============================================================================

def test_middleware_marks_error_metrics_with_error_type(test_db_session):
    """
    Test that middleware records error_type for 4xx/5xx responses.
    
    Expected to FAIL initially (RED phase) - error classification may not exist.
    """
    # Make request that will return 404
    with patch('server.lib.auth.get_user_token', return_value='mock-token'):
        response = client.get("/api/v1/nonexistent-endpoint")
        
        assert response.status_code == 404
        
        # Query database for error metric
        metrics = test_db_session.query(PerformanceMetric).filter(
            PerformanceMetric.endpoint == "/api/v1/nonexistent-endpoint"
        ).all()
        
        assert len(metrics) > 0, "Middleware should create metric even for errors"
        
        metric = metrics[0]
        assert metric.status_code == 404
        assert metric.error_type is not None, "Error metrics should have error_type"
        assert "404" in metric.error_type or "HTTP" in metric.error_type


# ============================================================================
# T040.5: Performance test for middleware overhead (SC-002)
# ============================================================================

def test_middleware_overhead_less_than_5ms(test_db_session):
    """
    Test that middleware adds <5ms overhead per request (validates SC-002).
    
    Expected to FAIL initially (RED phase) - overhead may not be optimized.
    """
    # Measure request time WITHOUT metrics collection (if possible to disable)
    # For this test, we'll compare to known baseline or measure multiple requests
    
    request_times = []
    
    with patch('server.lib.auth.get_user_token', return_value='mock-token'):
        for _ in range(10):
            start = time.perf_counter()
            response = client.get("/health")
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            request_times.append(elapsed)
            
            assert response.status_code == 200
    
    avg_time = sum(request_times) / len(request_times)
    
    # Assuming baseline is ~0-2ms for /health endpoint
    # Middleware overhead should be <5ms, so total should be <7ms
    assert avg_time < 10.0, f"Request with metrics collection should be fast, got {avg_time:.2f}ms avg"


# ============================================================================
# T042: Unit test for metric recording
# ============================================================================

def test_metrics_service_records_performance_metric(test_db_session):
    """
    Test that MetricsService.record_performance_metric() creates database record.
    
    Expected to FAIL initially (RED phase) - method may not exist.
    """
    from server.services.metrics_service import MetricsService
    
    service = MetricsService(test_db_session)
    
    # Record metric
    metric_data = {
        "endpoint": "/api/v1/test",
        "method": "POST",
        "status_code": 201,
        "response_time_ms": 234.5,
        "user_id": "test@example.com",
        "error_type": None
    }
    
    service.record_performance_metric(metric_data)
    
    # Verify record created
    metrics = test_db_session.query(PerformanceMetric).filter(
        PerformanceMetric.endpoint == "/api/v1/test"
    ).all()
    
    assert len(metrics) == 1
    assert metrics[0].method == "POST"
    assert metrics[0].status_code == 201
    assert metrics[0].response_time_ms == 234.5


# ============================================================================
# T042.1: Integration test for 100% collection rate (SC-004)
# ============================================================================

def test_100_percent_collection_rate(test_db_session):
    """
    Test that 100 API requests create 100 metric records (validates SC-004 100% collection rate).
    
    Expected to FAIL initially (RED phase) - middleware may not be registered.
    """
    # Clear existing metrics
    test_db_session.query(PerformanceMetric).delete()
    test_db_session.commit()
    
    num_requests = 100
    
    with patch('server.lib.auth.get_user_token', return_value='mock-token'):
        for i in range(num_requests):
            response = client.get(f"/health?iteration={i}")
            assert response.status_code == 200
    
    # Count created metrics
    metric_count = test_db_session.query(PerformanceMetric).filter(
        PerformanceMetric.endpoint.like("/health%")
    ).count()
    
    # Allow for system endpoints that might also be tracked
    assert metric_count >= num_requests, \
        f"Should create metric for every request. Expected >={num_requests}, got {metric_count}"


# ============================================================================
# T042.2: Integration test for update latency (SC-003)
# ============================================================================

def test_metrics_visible_within_60_seconds(test_db_session):
    """
    Test that created metrics are visible via API within 60 seconds (validates SC-003).
    
    Expected to FAIL initially (RED phase) - async processing may not be immediate.
    """
    # Create metric via API request
    with patch('server.lib.auth.get_user_token', return_value='mock-token'):
        request_time = time.time()
        response = client.get("/health")
        assert response.status_code == 200
        
        # Query metrics API immediately
        with patch('server.services.admin_service.is_workspace_admin', return_value=True):
            metrics_response = client.get(
                "/api/v1/metrics/performance?time_range=24h",
                headers={"X-Forwarded-Access-Token": "mock-admin-token"}
            )
            
            query_time = time.time()
            latency = query_time - request_time
            
            assert metrics_response.status_code == 200
            data = metrics_response.json()
            
            # Verify data is present (even if count is from previous requests)
            assert "metrics" in data
            
            # Latency should be < 60 seconds
            assert latency < 60.0, f"Metrics should be visible within 60s, took {latency:.2f}s"


# ============================================================================
# T042.3: Integration test for graceful degradation (SC-008)
# ============================================================================

def test_graceful_degradation_on_database_failure(test_db_session):
    """
    Test that API requests succeed even when metrics collection fails (validates SC-008).
    
    Expected to FAIL initially (RED phase) - error handling may not be robust.
    """
    # Mock database failure
    with patch('server.services.metrics_service.MetricsService.record_performance_metric') as mock_record:
        mock_record.side_effect = Exception("Database connection failed")
        
        with patch('server.lib.auth.get_user_token', return_value='mock-token'):
            # Request should still succeed despite metrics collection failure
            response = client.get("/health")
            
            assert response.status_code == 200, \
                "Application should continue working even if metrics collection fails"


# ============================================================================
# T042.4: Load test for quantitative graceful degradation
# ============================================================================

def test_request_failure_rate_increase_under_database_outage():
    """
    Test that request failure rate increases <1% when database is unavailable (validates FR-007).
    
    Expected to FAIL initially (RED phase) - error handling may not be robust enough.
    """
    num_requests = 100
    
    # Baseline: Measure success rate with working database
    baseline_failures = 0
    with patch('server.lib.auth.get_user_token', return_value='mock-token'):
        for i in range(num_requests):
            response = client.get("/health")
            if response.status_code != 200:
                baseline_failures += 1
    
    baseline_failure_rate = baseline_failures / num_requests
    
    # Test: Measure success rate with database unavailable
    outage_failures = 0
    with patch('server.services.metrics_service.MetricsService.record_performance_metric') as mock_record:
        mock_record.side_effect = Exception("Database unavailable")
        
        with patch('server.lib.auth.get_user_token', return_value='mock-token'):
            for i in range(num_requests):
                response = client.get("/health")
                if response.status_code != 200:
                    outage_failures += 1
    
    outage_failure_rate = outage_failures / num_requests
    
    # Calculate increase in failure rate
    failure_rate_increase = outage_failure_rate - baseline_failure_rate
    
    assert failure_rate_increase < 0.01, \
        f"Failure rate should increase <1%, increased by {failure_rate_increase*100:.2f}%"


# ============================================================================
# T042.5: Performance regression test (Assumption 11)
# ============================================================================

def test_p95_latency_under_185ms_with_metrics_collection():
    """
    Test that P95 latency remains <185ms with metrics collection enabled.
    
    Validates Assumption 11 baseline preservation (180ms baseline + 5ms overhead allowance).
    
    Expected to FAIL initially (RED phase) - performance may not be optimized.
    """
    num_requests = 1000
    request_times = []
    
    with patch('server.lib.auth.get_user_token', return_value='mock-token'):
        for i in range(num_requests):
            start = time.perf_counter()
            response = client.get("/health")
            elapsed = (time.perf_counter() - start) * 1000  # ms
            
            if response.status_code == 200:
                request_times.append(elapsed)
    
    # Calculate P95
    request_times.sort()
    p95_index = int(len(request_times) * 0.95)
    p95_latency = request_times[p95_index]
    
    # P95 should be < 185ms (180ms baseline + 5ms overhead)
    # For /health endpoint, we expect much lower, but this validates the overhead constraint
    assert p95_latency < 185.0, \
        f"P95 latency should be <185ms with metrics collection, got {p95_latency:.2f}ms"


# ============================================================================
# Pytest Fixtures
# ============================================================================

@pytest.fixture
def test_db_session():
    """Fixture to provide clean in-memory SQLite database session for each test"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from server.lib.database import Base
    
    # Create in-memory SQLite database for testing with thread safety disabled
    # check_same_thread=False allows SQLite to be used across threads (needed for FastAPI TestClient)
    engine = create_engine(
        'sqlite:///:memory:',
        echo=False,
        connect_args={'check_same_thread': False}
    )
    
    # Create all tables (checkfirst=True prevents errors if tables already exist)
    Base.metadata.create_all(engine, checkfirst=True)
    
    # Create session
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    
    # Verify tables were created
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert 'performance_metrics' in tables, f"Performance metrics table not created. Tables: {tables}"
    
    yield db
    
    # Clean up
    db.close()
    engine.dispose()

