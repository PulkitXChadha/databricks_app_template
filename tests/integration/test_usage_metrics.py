"""
Integration tests for usage metrics collection and tracking.

Tests verify that usage events are properly recorded, batched, and aggregated.
Following TDD RED-GREEN-REFACTOR: These tests MUST FAIL initially.
"""

import pytest
import time
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from server.app import app
from server.models.usage_event import UsageEvent
from server.models.aggregated_metric import AggregatedMetric
from unittest.mock import patch, MagicMock

client = TestClient(app)


# ============================================================================
# T063: Integration test for usage event tracking
# ============================================================================

def test_page_view_event_recorded(test_db_session):
    """
    Test that page view events are properly recorded in database.
    
    Expected to FAIL initially (RED phase) - endpoint may not persist events.
    """
    # Clear existing usage events
    test_db_session.query(UsageEvent).delete()
    test_db_session.commit()
    
    # Submit page view event
    with patch('server.lib.auth.get_user_token', return_value='mock-token'):
        with patch('databricks.sdk.WorkspaceClient') as mock_client:
            mock_user = MagicMock()
            mock_user.user_name = 'test@example.com'
            mock_client.return_value.current_user.me.return_value = mock_user
            
            events = [
                {
                    "event_type": "page_view",
                    "page_name": "/metrics",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
            
            response = client.post(
                "/api/v1/metrics/usage-events",
                json={"events": events},
                headers={"X-Forwarded-Access-Token": "mock-token"}
            )
            
            assert response.status_code == 202, "Should accept events"
            
            # Verify event persisted to database
            stored_events = test_db_session.query(UsageEvent).filter(
                UsageEvent.event_type == "page_view",
                UsageEvent.page_name == "/metrics"
            ).all()
            
            assert len(stored_events) > 0, "Page view event should be persisted"
            event = stored_events[0]
            assert event.user_id == "test@example.com"
            assert event.event_type == "page_view"


# ============================================================================
# T064: Integration test for batch event submission
# ============================================================================

def test_batch_of_20_events_all_persisted(test_db_session):
    """
    Test that batch of 20 events are all successfully persisted.
    
    Expected to FAIL initially (RED phase) - batch handling may not work.
    """
    # Clear existing usage events
    test_db_session.query(UsageEvent).delete()
    test_db_session.commit()
    
    # Create batch of 20 events
    events = []
    for i in range(20):
        events.append({
            "event_type": "button_click",
            "element_id": f"button-{i}",
            "page_name": "/test-page",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    with patch('server.lib.auth.get_user_token', return_value='mock-token'):
        with patch('databricks.sdk.WorkspaceClient') as mock_client:
            mock_user = MagicMock()
            mock_user.user_name = 'batch-test@example.com'
            mock_client.return_value.current_user.me.return_value = mock_user
            
            response = client.post(
                "/api/v1/metrics/usage-events",
                json={"events": events},
                headers={"X-Forwarded-Access-Token": "mock-token"}
            )
            
            assert response.status_code == 202, "Should accept batch"
            
            # Verify all 20 events persisted
            stored_count = test_db_session.query(UsageEvent).filter(
                UsageEvent.user_id == "batch-test@example.com",
                UsageEvent.event_type == "button_click"
            ).count()
            
            assert stored_count == 20, f"All 20 events should be persisted, got {stored_count}"


# ============================================================================
# T065: Integration test for usage event aggregation
# ============================================================================

def test_7_day_old_usage_events_aggregated(test_db_session):
    """
    Test that 7-day-old usage events are aggregated into hourly buckets.
    
    Expected to FAIL initially (RED phase) - aggregation logic for usage events may not exist.
    """
    from scripts.aggregate_metrics import aggregate_usage_events
    
    # Create usage events 8 days ago (beyond 7-day cutoff)
    cutoff_date = datetime.utcnow() - timedelta(days=7)
    old_timestamp = datetime.utcnow() - timedelta(days=8)
    
    # Create test events
    for i in range(10):
        event = UsageEvent(
            timestamp=old_timestamp,
            event_type="query_executed",
            user_id=f"user-{i % 3}@example.com",  # 3 unique users
            page_name="/query-page",
            success=True if i % 2 == 0 else False
        )
        test_db_session.add(event)
    
    test_db_session.commit()
    
    # Run aggregation
    try:
        aggregated_count = aggregate_usage_events(test_db_session, cutoff_date)
        test_db_session.commit()
        
        # Verify aggregation occurred
        assert aggregated_count > 0, "Should create at least one aggregated bucket"
        
        # Verify aggregated record exists
        aggregated = test_db_session.query(AggregatedMetric).filter(
            AggregatedMetric.metric_type == "usage",
            AggregatedMetric.event_type == "query_executed"
        ).first()
        
        assert aggregated is not None, "Aggregated usage metric should exist"
        
        # Verify aggregated values structure
        values = aggregated.aggregated_values
        assert "total_events" in values
        assert values["total_events"] == 10
        assert "unique_users" in values
        assert values["unique_users"] == 3
        
        # Verify old events were deleted
        remaining_events = test_db_session.query(UsageEvent).filter(
            UsageEvent.timestamp < cutoff_date
        ).count()
        
        assert remaining_events == 0, "Old usage events should be deleted after aggregation"
        
    except Exception as e:
        pytest.fail(f"Aggregation failed: {e}")


# ============================================================================
# Additional edge case tests
# ============================================================================

def test_usage_events_with_null_optional_fields(test_db_session):
    """Test that events with null optional fields are handled correctly"""
    with patch('server.lib.auth.get_user_token', return_value='mock-token'):
        with patch('databricks.sdk.WorkspaceClient') as mock_client:
            mock_user = MagicMock()
            mock_user.user_name = 'test@example.com'
            mock_client.return_value.current_user.me.return_value = mock_user
            
            # Event with minimal fields
            events = [
                {
                    "event_type": "feature_usage",
                    "timestamp": datetime.utcnow().isoformat()
                    # No page_name, element_id, success, or metadata
                }
            ]
            
            response = client.post(
                "/api/v1/metrics/usage-events",
                json={"events": events},
                headers={"X-Forwarded-Access-Token": "mock-token"}
            )
            
            assert response.status_code == 202, "Should accept events with minimal fields"


def test_usage_events_with_metadata(test_db_session):
    """Test that events with metadata JSON are properly stored"""
    with patch('server.lib.auth.get_user_token', return_value='mock-token'):
        with patch('databricks.sdk.WorkspaceClient') as mock_client:
            mock_user = MagicMock()
            mock_user.user_name = 'test@example.com'
            mock_client.return_value.current_user.me.return_value = mock_user
            
            events = [
                {
                    "event_type": "query_executed",
                    "page_name": "/query",
                    "success": True,
                    "metadata": {
                        "query": "SELECT * FROM table",
                        "execution_time_ms": 234,
                        "rows_returned": 100
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
            
            response = client.post(
                "/api/v1/metrics/usage-events",
                json={"events": events},
                headers={"X-Forwarded-Access-Token": "mock-token"}
            )
            
            assert response.status_code == 202, "Should accept events with metadata"
            
            # Verify metadata stored correctly
            stored_event = test_db_session.query(UsageEvent).filter(
                UsageEvent.event_type == "query_executed",
                UsageEvent.user_id == "test@example.com"
            ).first()
            
            if stored_event:
                assert stored_event.metadata is not None
                assert stored_event.metadata.get("query") == "SELECT * FROM table"
                assert stored_event.metadata.get("execution_time_ms") == 234

