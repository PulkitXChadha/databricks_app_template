"""
Integration tests for metrics aggregation job.

Tests verify that the daily aggregation job correctly processes 7-day-old raw metrics
into hourly summaries and deletes raw records atomically.
Following TDD RED-GREEN-REFACTOR: These tests MUST FAIL initially.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from server.models.performance_metric import PerformanceMetric
from server.models.usage_event import UsageEvent
from server.models.aggregated_metric import AggregatedMetric
from server.lib.database import get_db_session


# ============================================================================
# T041: Integration test for metrics aggregation job
# ============================================================================

def test_7_day_old_metrics_aggregated_and_deleted(test_db_session):
    """
    Test that 7-day-old metrics are aggregated into hourly buckets and raw records deleted.
    
    Expected to FAIL initially (RED phase) - aggregation logic doesn't exist.
    """
    now = datetime.utcnow()
    cutoff_date = now - timedelta(days=7)
    
    # Create metrics that are 8 days old (should be aggregated)
    old_metrics = [
        PerformanceMetric(
            timestamp=cutoff_date - timedelta(days=1, hours=i % 24),
            endpoint="/api/v1/test",
            method="GET",
            status_code=200,
            response_time_ms=100.0 + (i * 10),
            user_id="test@example.com"
        )
        for i in range(48)  # 2 days of hourly data
    ]
    
    # Create metrics that are 5 days old (should NOT be aggregated yet)
    recent_metrics = [
        PerformanceMetric(
            timestamp=now - timedelta(days=5, hours=i),
            endpoint="/api/v1/test",
            method="GET",
            status_code=200,
            response_time_ms=150.0,
            user_id="test@example.com"
        )
        for i in range(12)  # 12 hours of data
    ]
    
    for metric in old_metrics + recent_metrics:
        test_db_session.add(metric)
    test_db_session.commit()
    
    # Run aggregation job
    from scripts.aggregate_metrics import aggregate_performance_metrics
    
    aggregated_count = aggregate_performance_metrics(test_db_session, cutoff_date)
    
    # Verify aggregated records created
    aggregated_metrics = test_db_session.query(AggregatedMetric).filter(
        AggregatedMetric.metric_type == "performance"
    ).all()
    
    assert len(aggregated_metrics) > 0, "Should create aggregated records"
    assert aggregated_count > 0, "Should return count of aggregated buckets"
    
    # Verify old raw metrics deleted
    remaining_old = test_db_session.query(PerformanceMetric).filter(
        PerformanceMetric.timestamp < cutoff_date
    ).count()
    
    assert remaining_old == 0, "Old raw metrics should be deleted after aggregation"
    
    # Verify recent metrics still exist
    remaining_recent = test_db_session.query(PerformanceMetric).filter(
        PerformanceMetric.timestamp >= cutoff_date
    ).count()
    
    assert remaining_recent == len(recent_metrics), "Recent metrics should not be deleted"


# ============================================================================
# T053.7: Integration test for 90-day cleanup
# ============================================================================

def test_90_day_old_aggregated_metrics_deleted(test_db_session):
    """
    Test that aggregated metrics older than 90 days are deleted by cleanup job.
    
    Validates SC-007 automated cleanup requirement.
    
    Expected to FAIL initially (RED phase) - cleanup logic doesn't exist.
    """
    now = datetime.utcnow()
    
    # Create aggregated metrics that are 100 days old (should be deleted)
    very_old_aggregated = [
        AggregatedMetric(
            time_bucket=now - timedelta(days=100, hours=i),
            metric_type="performance",
            endpoint_path="/api/v1/test",
            aggregated_values={
                "avg_response_time_ms": 100.0,
                "total_requests": 50,
                "error_count": 0,
                "error_rate": 0.0
            },
            sample_count=50
        )
        for i in range(24)  # 24 hourly buckets
    ]
    
    # Create aggregated metrics that are 80 days old (should NOT be deleted)
    old_aggregated = [
        AggregatedMetric(
            time_bucket=now - timedelta(days=80, hours=i),
            metric_type="performance",
            endpoint_path="/api/v1/test",
            aggregated_values={
                "avg_response_time_ms": 120.0,
                "total_requests": 60,
                "error_count": 1,
                "error_rate": 0.0167
            },
            sample_count=60
        )
        for i in range(24)
    ]
    
    for metric in very_old_aggregated + old_aggregated:
        test_db_session.add(metric)
    test_db_session.commit()
    
    # Run cleanup job
    from scripts.aggregate_metrics import cleanup_old_aggregated_metrics
    
    deleted_count = cleanup_old_aggregated_metrics(test_db_session)
    
    # Verify very old aggregated metrics deleted
    remaining_very_old = test_db_session.query(AggregatedMetric).filter(
        AggregatedMetric.time_bucket < now - timedelta(days=90)
    ).count()
    
    assert remaining_very_old == 0, "Aggregated metrics older than 90 days should be deleted"
    assert deleted_count == len(very_old_aggregated), f"Should delete {len(very_old_aggregated)} records"
    
    # Verify 80-day-old metrics still exist
    remaining_old = test_db_session.query(AggregatedMetric).filter(
        AggregatedMetric.time_bucket >= now - timedelta(days=90)
    ).count()
    
    assert remaining_old == len(old_aggregated), "Aggregated metrics within 90 days should remain"


# ============================================================================
# T053.8: Integration test for SC-007 database size monitoring and SC-009 alert prefix
# ============================================================================

def test_database_size_monitoring_thresholds_and_alert_prefix(test_db_session, caplog):
    """
    Test database size monitoring with WARNING at 800K and ERROR with "ALERT:" prefix at 1M.
    
    TWO TEST SCENARIOS:
    1. 800K threshold test: Verify WARNING log emitted with record count
    2. 1M threshold test: Verify ERROR log with EXACT "ALERT:" prefix per SC-009
    
    Validates SC-007 success criterion and SC-009 alert prefix requirement explicitly.
    
    Expected to FAIL initially (RED phase) - monitoring logic doesn't exist.
    """
    import logging
    caplog.set_level(logging.WARNING)
    
    from scripts.aggregate_metrics import check_database_size_and_alert
    
    # Scenario 1: Test 800K threshold (WARNING)
    warning_result = check_database_size_and_alert(test_db_session, total_count=800000)
    
    # Verify WARNING log emitted
    assert any(
        record.levelname == "WARNING" and "800" in record.message
        for record in caplog.records
    ), "Should log WARNING at 800K threshold"
    
    # Scenario 2: Test 1M threshold (ERROR with ALERT: prefix)
    caplog.clear()
    caplog.set_level(logging.ERROR)
    
    error_result = check_database_size_and_alert(test_db_session, total_count=1000000)
    
    # CRITICAL: Verify ERROR log has EXACT "ALERT:" prefix per SC-009
    alert_logs = [
        record for record in caplog.records
        if record.levelname == "ERROR" and record.message.startswith("ALERT:")
    ]
    
    assert len(alert_logs) > 0, \
        "Should log ERROR with 'ALERT:' prefix when exceeding 1M threshold"
    
    assert "ALERT: Database size exceeded 1M threshold" in alert_logs[0].message, \
        "ERROR log must explicitly start with 'ALERT:' prefix per SC-009 requirement"
    
    # Verify emergency aggregation was triggered
    assert error_result.get("emergency_aggregation_triggered") is True, \
        "Should trigger emergency aggregation at 1M threshold"


# ============================================================================
# T053: Integration test for aggregation idempotency
# ============================================================================

def test_aggregation_job_is_idempotent(test_db_session):
    """
    Test that aggregation job can be safely re-run on same data without duplicates.
    
    Validates FR-008 idempotency requirement via check-before-insert pattern.
    
    Expected to FAIL initially (RED phase) - idempotency logic doesn't exist.
    """
    now = datetime.utcnow()
    cutoff_date = now - timedelta(days=7)
    
    # Create metrics that are 8 days old
    old_metrics = [
        PerformanceMetric(
            timestamp=cutoff_date - timedelta(days=1, hours=i),
            endpoint="/api/v1/test",
            method="GET",
            status_code=200,
            response_time_ms=100.0 + (i * 5),
            user_id="test@example.com"
        )
        for i in range(24)  # 24 hours of data
    ]
    
    for metric in old_metrics:
        test_db_session.add(metric)
    test_db_session.commit()
    
    # Run aggregation job first time
    from scripts.aggregate_metrics import aggregate_performance_metrics
    
    first_run_count = aggregate_performance_metrics(test_db_session, cutoff_date)
    
    # Count aggregated records
    aggregated_count_after_first = test_db_session.query(AggregatedMetric).filter(
        AggregatedMetric.metric_type == "performance"
    ).count()
    
    # Add same old metrics again (simulating re-run scenario)
    for metric in old_metrics:
        test_db_session.add(PerformanceMetric(
            timestamp=metric.timestamp,
            endpoint=metric.endpoint,
            method=metric.method,
            status_code=metric.status_code,
            response_time_ms=metric.response_time_ms,
            user_id=metric.user_id
        ))
    test_db_session.commit()
    
    # Run aggregation job second time (should be idempotent)
    second_run_count = aggregate_performance_metrics(test_db_session, cutoff_date)
    
    # Count aggregated records again
    aggregated_count_after_second = test_db_session.query(AggregatedMetric).count()
    
    # Verify no duplicate aggregated records created
    assert aggregated_count_after_second == aggregated_count_after_first, \
        "Idempotent aggregation should not create duplicate aggregated records"


# ============================================================================
# T051: Integration test for percentile pre-computation
# ============================================================================

def test_aggregation_precomputes_percentiles(test_db_session):
    """
    Test that aggregation job pre-computes p50/p95/p99 percentiles using PostgreSQL percentile_cont.
    
    Expected to FAIL initially (RED phase) - percentile computation doesn't exist.
    """
    now = datetime.utcnow()
    cutoff_date = now - timedelta(days=7)
    
    # Create metrics with varying response times for percentile calculation
    response_times = [10, 20, 30, 40, 50, 100, 150, 200, 300, 500, 800, 1000]
    old_metrics = [
        PerformanceMetric(
            timestamp=cutoff_date - timedelta(days=1, hours=1),  # Same hour for aggregation
            endpoint="/api/v1/test",
            method="GET",
            status_code=200,
            response_time_ms=float(rt),
            user_id="test@example.com"
        )
        for rt in response_times
    ]
    
    for metric in old_metrics:
        test_db_session.add(metric)
    test_db_session.commit()
    
    # Run aggregation job
    from scripts.aggregate_metrics import aggregate_performance_metrics
    
    aggregate_performance_metrics(test_db_session, cutoff_date)
    
    # Verify aggregated record has pre-computed percentiles
    aggregated = test_db_session.query(AggregatedMetric).filter(
        AggregatedMetric.metric_type == "performance",
        AggregatedMetric.endpoint_path == "/api/v1/test"
    ).first()
    
    assert aggregated is not None, "Should create aggregated record"
    
    values = aggregated.aggregated_values
    assert "p50_response_time_ms" in values, "Should pre-compute p50"
    assert "p95_response_time_ms" in values, "Should pre-compute p95"
    assert "p99_response_time_ms" in values, "Should pre-compute p99"
    
    # Verify percentile values are reasonable
    assert values["p50_response_time_ms"] < values["p95_response_time_ms"]
    assert values["p95_response_time_ms"] < values["p99_response_time_ms"]


# ============================================================================
# T052: Integration test for atomic transaction (aggregation + deletion)
# ============================================================================

def test_aggregation_and_deletion_atomic_transaction(test_db_session):
    """
    Test that aggregation and raw data deletion occur in same transaction.
    
    If aggregation fails, raw data should not be deleted (rollback).
    
    Expected to FAIL initially (RED phase) - transaction handling may not be atomic.
    """
    now = datetime.utcnow()
    cutoff_date = now - timedelta(days=7)
    
    # Create old metrics
    old_metrics = [
        PerformanceMetric(
            timestamp=cutoff_date - timedelta(days=1, hours=i),
            endpoint="/api/v1/test",
            method="GET",
            status_code=200,
            response_time_ms=100.0,
            user_id="test@example.com"
        )
        for i in range(24)
    ]
    
    for metric in old_metrics:
        test_db_session.add(metric)
    test_db_session.commit()
    
    initial_raw_count = test_db_session.query(PerformanceMetric).filter(
        PerformanceMetric.timestamp < cutoff_date
    ).count()
    
    # Simulate aggregation failure
    from scripts.aggregate_metrics import aggregate_performance_metrics
    
    try:
        # This should fail and rollback
        with test_db_session.begin_nested():
            aggregate_performance_metrics(test_db_session, cutoff_date)
            # Force an error
            raise Exception("Simulated aggregation failure")
    except Exception:
        test_db_session.rollback()
    
    # Verify raw data was NOT deleted (rollback worked)
    remaining_raw_count = test_db_session.query(PerformanceMetric).filter(
        PerformanceMetric.timestamp < cutoff_date
    ).count()
    
    assert remaining_raw_count == initial_raw_count, \
        "Raw data should not be deleted if aggregation fails (atomic transaction)"


# ============================================================================
# Pytest Fixtures
# ============================================================================

@pytest.fixture
def test_db_session():
    """Fixture to provide clean in-memory SQLite database session for each test"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from server.lib.database import Base
    
    # Create in-memory SQLite database for testing
    engine = create_engine('sqlite:///:memory:', echo=False)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    
    yield db
    
    # Clean up
    db.close()
    engine.dispose()

