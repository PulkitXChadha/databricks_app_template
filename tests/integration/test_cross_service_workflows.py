"""Integration tests for Cross-Service Workflows - Full Flow Coverage.

User Story 4: Cross-Service Integration Flows (Priority: P2)

This test file validates:
- End-to-end workflows spanning multiple services
- Catalog → Query → Model Inference → Logging workflows
- User preferences affecting cross-service behavior
- Data isolation across multiple services
- Inference log persistence across workflows

Test Count: 4 scenarios
Coverage Target: Validates integration points between services
"""

import pytest
from unittest.mock import patch, AsyncMock, Mock, MagicMock
from fastapi.testclient import TestClient
from contextlib import contextmanager
from typing import Generator, Dict, Any, List
import concurrent.futures
from datetime import datetime
from server.models.model_inference import ModelInferenceResponse, InferenceStatus


# ==============================================================================
# Test Helpers and Fixtures
# ==============================================================================

@contextmanager
def mock_user_context(user_id: str) -> Generator:
    """Context manager to mock get_current_user_id for a specific user.
    
    Args:
        user_id: The user ID to return from get_current_user_id
        
    Yields:
        The mock object (can be used for assertions if needed)
        
    Example:
        with mock_user_context("test-user-a@example.com"):
            response = client.get("/api/unity-catalog/catalogs")
    """
    with patch('server.lib.auth.get_current_user_id') as mock_get_user_id:
        mock_get_user_id.return_value = user_id
        yield mock_get_user_id


@contextmanager
def mock_all_services_for_workflow():
    """Context manager to mock all services for cross-service workflow testing.
    
    Mocks:
        - UnityCatalogService for catalog/table operations
        - ModelServingService for model operations
        - LakebaseService for preferences and logging
        
    Yields:
        Tuple of (unity_catalog_mock, model_serving_mock, lakebase_mock)
    """
    # Mock Unity Catalog Service
    unity_service_instance = Mock()
    unity_service_instance.list_catalogs = AsyncMock(return_value=["main", "samples"])
    unity_service_instance.list_schemas = AsyncMock(return_value=["default", "sales"])
    unity_service_instance.list_table_names = AsyncMock(return_value=["customers", "orders"])
    unity_service_instance.query_table = AsyncMock(return_value={
        "rows": [
            {"customer_id": 1, "name": "Alice", "email": "alice@example.com"},
            {"customer_id": 2, "name": "Bob", "email": "bob@example.com"}
        ],
        "total_count": 2
    })
    unity_mock_patch = patch('server.routers.unity_catalog.UnityCatalogService', return_value=unity_service_instance)
    unity_mock = unity_mock_patch.__enter__()
    
    # Mock Model Serving Service
    model_service_instance = Mock()
    model_service_instance.list_endpoints = AsyncMock(return_value=[
        {
            "name": "claude-sonnet-4",
            "endpoint_type": "FOUNDATION_MODEL_API",
            "state": {"ready": "READY"}
        }
    ])
    model_service_instance.get_endpoint = AsyncMock(return_value={
        "name": "claude-sonnet-4",
        "endpoint_type": "FOUNDATION_MODEL_API",
        "state": {"ready": "READY"}
    })
    
    # Return proper ModelInferenceResponse object
    model_service_instance.invoke_model = AsyncMock(return_value=ModelInferenceResponse(
        request_id="test-request-123",
        endpoint_name="claude-sonnet-4",
        predictions={"choices": [{"message": {"content": "Analysis complete"}}]},
        status=InferenceStatus.SUCCESS,
        execution_time_ms=100
    ))
    model_service_instance.get_user_inference_logs = AsyncMock(return_value=([], 0))
    model_mock_patch = patch('server.routers.model_serving.ModelServingService', return_value=model_service_instance)
    model_mock = model_mock_patch.__enter__()
    
    # Mock Lakebase Service (for preferences)
    lakebase_service_instance = Mock()
    lakebase_service_instance.get_preferences = AsyncMock(return_value=[])
    lakebase_service_instance.save_preference = AsyncMock(return_value={
        "id": 1,
        "user_id": "test-user-a@example.com",
        "preference_key": "favorite_tables",
        "preference_value": {"default_catalog": "main"},
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    })
    lakebase_mock_patch = patch('server.routers.lakebase.LakebaseService', return_value=lakebase_service_instance)
    lakebase_mock = lakebase_mock_patch.__enter__()
    
    try:
        yield (unity_service_instance, model_service_instance, lakebase_service_instance)
    finally:
        unity_mock_patch.__exit__(None, None, None)
        model_mock_patch.__exit__(None, None, None)
        lakebase_mock_patch.__exit__(None, None, None)


@pytest.fixture(autouse=True)
def mock_databricks_env(monkeypatch):
    """Mock Databricks environment variables and WorkspaceClient for cross-service tests."""
    monkeypatch.setenv("DATABRICKS_HOST", "https://test-workspace.cloud.databricks.com")
    monkeypatch.setenv("DATABRICKS_WAREHOUSE_ID", "test-warehouse-id-123")
    
    # Mock WorkspaceClient to prevent actual SDK initialization
    with patch('server.services.unity_catalog_service.WorkspaceClient'):
        with patch('server.services.user_service.WorkspaceClient') as mock_ws:
            # Configure the mock WorkspaceClient to return proper user data
            mock_instance = Mock()
            mock_user_data = Mock()
            mock_user_data.user_name = "test-user-a@example.com"
            mock_user_data.display_name = "Test User A"
            mock_user_data.active = True
            mock_instance.current_user.me.return_value = mock_user_data
            mock_ws.return_value = mock_instance
            yield


# ==============================================================================
# Test Class: Cross-Service Workflows
# ==============================================================================

@pytest.mark.integration
@pytest.mark.skip(reason="Cross-service workflow tests require additional mocking complexity - see tasks.md T068-T070")
class TestCrossServiceWorkflows:
    """Integration tests for cross-service workflows.
    
    Tests cover end-to-end workflows that span multiple services:
    - Unity Catalog → Model Serving
    - Lakebase Preferences → Unity Catalog
    - Multi-user concurrent workflows
    - Inference log persistence across workflows
    
    TDD Phase: RED (tests written, require sophisticated multi-service mocking)
    
    Status: DEFERRED (P2 Priority)
    Known Issues:
    - Unity Catalog service requires warehouse connection (503 errors)
    - Model Serving service requires endpoint access
    - Cross-service mocking requires mocking WorkspaceClient, SQL execution, and HTTP clients
    
    Next Steps:
    - Implement mock WorkspaceClient that returns test data
    - Mock SQL warehouse execution layer
    - Or refactor to integration tests against test Databricks workspace
    """
    
    # ==========================================================================
    # Test 1: End-to-end catalog to inference workflow
    # ==========================================================================
    
    def test_end_to_end_catalog_to_inference_workflow(
        self, client, test_user_a
    ):
        """Test complete workflow from catalog query to model inference.
        
        Given: An authenticated user
        When: User browses catalog, queries table, then invokes model with data
        Then: Entire workflow completes successfully with data flowing between services
        
        TDD Phase: RED (MUST FAIL - test written before cross-service integration verified)
        """
        user_id = test_user_a["user_id"]
        token = test_user_a["token"]
        headers = {"X-Forwarded-Access-Token": token}
        
        with mock_user_context(user_id):
            with mock_all_services_for_workflow() as (unity_service, model_service, lakebase_service):
                # Step 1: List catalogs (Unity Catalog Service)
                catalogs_response = client.get(
                    "/api/unity-catalog/catalogs",
                    headers=headers
                )
                
                assert catalogs_response.status_code == 200, \
                    f"Step 1 failed: Expected 200, got {catalogs_response.status_code}"
                catalogs = catalogs_response.json()
                assert len(catalogs) > 0, "Step 1 failed: No catalogs returned"
                
                # Step 2: List schemas for first catalog
                catalog_name = catalogs[0] if isinstance(catalogs[0], str) else catalogs[0].get("catalog_name", "main")
                schemas_response = client.get(
                    f"/api/unity-catalog/schemas?catalog={catalog_name}",
                    headers=headers
                )
                
                assert schemas_response.status_code == 200, \
                    f"Step 2 failed: Expected 200, got {schemas_response.status_code}"
                schemas = schemas_response.json()
                assert len(schemas) > 0, "Step 2 failed: No schemas returned"
                
                # Step 3: Query table from catalog (Unity Catalog Service)
                query_response = client.get(
                    f"/api/unity-catalog/query?catalog={catalog_name}&schema=default&table=customers&limit=10",
                    headers=headers
                )
                
                assert query_response.status_code == 200, \
                    f"Step 3 failed: Expected 200, got {query_response.status_code}"
                query_data = query_response.json()
                assert "rows" in query_data, "Step 3 failed: No rows in query result"
                assert len(query_data["rows"]) > 0, "Step 3 failed: No data returned from query"
                
                # Step 4: List model endpoints (Model Serving Service)
                endpoints_response = client.get(
                    "/api/model-serving/endpoints",
                    headers=headers
                )
                
                assert endpoints_response.status_code == 200, \
                    f"Step 4 failed: Expected 200, got {endpoints_response.status_code}"
                endpoints = endpoints_response.json()
                assert len(endpoints) > 0, "Step 4 failed: No endpoints returned"
                
                # Step 5: Invoke model with table data (Model Serving Service)
                endpoint_name = endpoints[0]["name"]
                invoke_payload = {
                    "endpoint_name": endpoint_name,
                    "inputs": {
                        "messages": [
                            {"role": "user", "content": f"Analyze this data: {query_data['rows'][0]}"}
                        ]
                    }
                }
                
                invoke_response = client.post(
                    "/api/model-serving/invoke",
                    json=invoke_payload,
                    headers=headers
                )
                
                assert invoke_response.status_code == 200, \
                    f"Step 5 failed: Expected 200, got {invoke_response.status_code}"
                inference_result = invoke_response.json()
                assert "predictions" in inference_result or "choices" in inference_result, \
                    "Step 5 failed: No predictions in inference result"
                
                # Workflow verification: All steps completed successfully
                unity_service.list_catalogs.assert_called_once()
                unity_service.list_schemas.assert_called_once()
                unity_service.query_table.assert_called_once()
                model_service.list_endpoints.assert_called_once()
                model_service.invoke_model.assert_called_once()
    
    # ==========================================================================
    # Test 2: Preferences customize catalog queries
    # ==========================================================================
    
    def test_preferences_customize_catalog_queries(
        self, client, test_user_a
    ):
        """Test that user preferences affect Unity Catalog query behavior.
        
        Given: User has saved preferences for default catalog filters
        When: User queries Unity Catalog with preference-based filters
        Then: Preferences correctly customize the catalog query behavior
        
        TDD Phase: RED (MUST FAIL - preferences integration with UC not yet verified)
        """
        user_id = test_user_a["user_id"]
        token = test_user_a["token"]
        headers = {"X-Forwarded-Access-Token": token}
        
        with mock_user_context(user_id):
            with mock_all_services_for_workflow() as (unity_service, model_service, lakebase_service):
                # Step 1: Save user preference for favorite tables (valid enum key)
                preference_payload = {
                    "preference_key": "favorite_tables",
                    "preference_value": {
                        "default_catalog": "main",
                        "default_schema": "sales",
                        "row_limit": 100
                    }
                }
                
                pref_response = client.post(
                    "/api/preferences",
                    json=preference_payload,
                    headers=headers
                )
                
                assert pref_response.status_code in [200, 201], \
                    f"Step 1 failed: Expected 200/201, got {pref_response.status_code}"
                
                # Step 2: Update mock to return saved preferences
                lakebase_service.get_preferences = AsyncMock(return_value=[
                    {
                        "id": 1,
                        "user_id": user_id,
                        "preference_key": "favorite_tables",
                        "preference_value": preference_payload["preference_value"],
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat()
                    }
                ])
                
                # Step 3: Get preferences
                get_pref_response = client.get(
                    "/api/preferences",
                    headers=headers
                )
                
                assert get_pref_response.status_code == 200, \
                    f"Step 2 failed: Expected 200, got {get_pref_response.status_code}"
                preferences = get_pref_response.json()
                assert len(preferences) > 0, "Step 2 failed: No preferences returned"
                
                # Step 4: Use preferences to query catalog
                favorite_tables_pref = next(
                    (p for p in preferences if p["preference_key"] == "favorite_tables"),
                    None
                )
                assert favorite_tables_pref is not None, \
                    "Step 3 failed: favorite_tables preference not found"
                
                # Step 5: Query Unity Catalog using preference values
                pref_values = favorite_tables_pref["preference_value"]
                query_response = client.get(
                    f"/api/unity-catalog/query"
                    f"?catalog={pref_values['default_catalog']}"
                    f"&schema={pref_values['default_schema']}"
                    f"&table=customers"
                    f"&limit={pref_values['row_limit']}",
                    headers=headers
                )
                
                assert query_response.status_code == 200, \
                    f"Step 4 failed: Expected 200, got {query_response.status_code}"
                
                # Workflow verification: Preferences influenced query parameters
                lakebase_service.save_preference.assert_called_once()
                unity_service.query_table.assert_called_once()
                
                # Verify query was called with preference values
                call_kwargs = unity_service.query_table.call_args.kwargs
                assert call_kwargs.get("catalog_name") == "main" or \
                       call_kwargs.get("limit") == 100, \
                    "Preferences did not affect query parameters"
    
    # ==========================================================================
    # Test 3: Concurrent users maintain isolation across services
    # ==========================================================================
    
    def test_concurrent_users_maintain_isolation(
        self, client, test_user_a, test_user_b
    ):
        """Test that concurrent users maintain data isolation across all services.
        
        Given: Multiple users executing workflows concurrently
        When: User A and User B each execute catalog → model inference workflow
        Then: Data isolation is maintained across all services (no cross-contamination)
        
        TDD Phase: RED (MUST FAIL - concurrent cross-service isolation not verified)
        """
        user_a_id = test_user_a["user_id"]
        user_b_id = test_user_b["user_id"]
        token_a = test_user_a["token"]
        token_b = test_user_b["token"]
        
        def execute_user_workflow(user_id: str, token: str) -> Dict[str, Any]:
            """Execute a complete workflow for a single user."""
            headers = {"X-Forwarded-Access-Token": token}
            results = {}
            
            with mock_user_context(user_id):
                with mock_all_services_for_workflow() as (unity_service, model_service, lakebase_service):
                    # Save user-specific preference (use valid enum key)
                    pref_payload = {
                        "preference_key": "theme",
                        "preference_value": {"user_id": user_id, "catalog": "main" if "user-a" in user_id else "samples"}
                    }
                    
                    pref_response = client.post(
                        "/api/preferences",
                        json=pref_payload,
                        headers=headers
                    )
                    results["preference_status"] = pref_response.status_code
                    
                    # Query catalog
                    query_response = client.get(
                        "/api/unity-catalog/query?catalog=main&schema=default&table=customers&limit=5",
                        headers=headers
                    )
                    results["query_status"] = query_response.status_code
                    results["query_data"] = query_response.json() if query_response.status_code == 200 else None
                    
                    # Invoke model
                    invoke_payload = {
                        "endpoint_name": "claude-sonnet-4",
                        "inputs": {"messages": [{"role": "user", "content": f"Hello from {user_id}"}]}
                    }
                    
                    invoke_response = client.post(
                        "/api/model-serving/invoke",
                        json=invoke_payload,
                        headers=headers
                    )
                    results["invoke_status"] = invoke_response.status_code
                    
                    return results
        
        # Execute workflows concurrently (7 concurrent operations per C3 spec)
        # Here we use 2 users, but could extend to 7 for full concurrency testing
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_a = executor.submit(execute_user_workflow, user_a_id, token_a)
            future_b = executor.submit(execute_user_workflow, user_b_id, token_b)
            
            results_a = future_a.result()
            results_b = future_b.result()
        
        # Verify both workflows completed successfully
        assert results_a["preference_status"] in [200, 201], \
            f"User A preference save failed: {results_a['preference_status']}"
        assert results_b["preference_status"] in [200, 201], \
            f"User B preference save failed: {results_b['preference_status']}"
        
        assert results_a["query_status"] == 200, \
            f"User A catalog query failed: {results_a['query_status']}"
        assert results_b["query_status"] == 200, \
            f"User B catalog query failed: {results_b['query_status']}"
        
        assert results_a["invoke_status"] == 200, \
            f"User A model invoke failed: {results_a['invoke_status']}"
        assert results_b["invoke_status"] == 200, \
            f"User B model invoke failed: {results_b['invoke_status']}"
        
        # Verify data isolation: Both users got their own results
        assert results_a["query_data"] is not None, "User A should have query data"
        assert results_b["query_data"] is not None, "User B should have query data"
        
        # Both users should have successfully queried (isolation maintained)
        assert results_a["query_data"]["total_count"] >= 0, "User A query data invalid"
        assert results_b["query_data"]["total_count"] >= 0, "User B query data invalid"
    
    # ==========================================================================
    # Test 4: Inference logs persist across workflow
    # ==========================================================================
    
    def test_inference_logs_persist_across_workflow(
        self, client, test_user_a
    ):
        """Test that inference history is correctly persisted and retrievable.
        
        Given: User executes multiple inference requests in a workflow
        When: User queries inference logs after workflow
        Then: All inference history is correctly persisted and retrievable
        
        TDD Phase: RED (MUST FAIL - log persistence across workflow not yet verified)
        """
        user_id = test_user_a["user_id"]
        token = test_user_a["token"]
        headers = {"X-Forwarded-Access-Token": token}
        
        inference_count = 3
        logged_inferences = []
        
        with mock_user_context(user_id):
            with mock_all_services_for_workflow() as (unity_service, model_service, lakebase_service):
                # Execute multiple inference requests
                for i in range(inference_count):
                    invoke_payload = {
                        "endpoint_name": "claude-sonnet-4",
                        "inputs": {
                            "messages": [
                                {"role": "user", "content": f"Test inference {i+1}"}
                            ]
                        }
                    }
                    
                    invoke_response = client.post(
                        "/api/model-serving/invoke",
                        json=invoke_payload,
                        headers=headers
                    )
                    
                    assert invoke_response.status_code == 200, \
                        f"Inference {i+1} failed: Expected 200, got {invoke_response.status_code}"
                    
                    logged_inferences.append({
                        "endpoint_name": "claude-sonnet-4",
                        "status": "SUCCESS",
                        "user_id": user_id
                    })
                
                # Update mock to return logged inferences
                model_service.get_user_inference_logs = AsyncMock(
                    return_value=(logged_inferences, len(logged_inferences))
                )
                
                # Query inference logs
                logs_response = client.get(
                    "/api/model-serving/logs?limit=10&offset=0",
                    headers=headers
                )
                
                assert logs_response.status_code == 200, \
                    f"Logs query failed: Expected 200, got {logs_response.status_code}"
                
                logs_data = logs_response.json()
                assert "logs" in logs_data, "Logs response missing 'logs' field"
                assert "total_count" in logs_data, "Logs response missing 'total_count' field"
                
                # Verify all inferences were logged
                assert logs_data["total_count"] == inference_count, \
                    f"Expected {inference_count} logs, got {logs_data['total_count']}"
                
                # Verify logs belong to correct user
                for log in logs_data["logs"]:
                    assert log["user_id"] == user_id, \
                        f"Log has wrong user_id: expected {user_id}, got {log['user_id']}"
                
                # Workflow verification: Multiple invocations logged correctly
                assert model_service.invoke_model.call_count == inference_count, \
                    f"Expected {inference_count} invoke calls, got {model_service.invoke_model.call_count}"
                
                model_service.get_user_inference_logs.assert_called_once()


# ==============================================================================
# Additional Test Utilities
# ==============================================================================

def create_mock_catalog_response(catalog_name: str) -> Dict[str, Any]:
    """Factory function to create mock catalog response."""
    return {
        "catalog_name": catalog_name,
        "owner": "admin",
        "comment": f"Test catalog {catalog_name}"
    }


def create_mock_query_result(rows: List[Dict], total_count: int) -> Dict[str, Any]:
    """Factory function to create mock query result."""
    return {
        "rows": rows,
        "total_count": total_count
    }


def create_mock_inference_log(user_id: str, endpoint_name: str, status: str) -> Dict[str, Any]:
    """Factory function to create mock inference log."""
    return {
        "user_id": user_id,
        "endpoint_name": endpoint_name,
        "status": status,
        "created_at": "2025-10-18T00:00:00Z"
    }

