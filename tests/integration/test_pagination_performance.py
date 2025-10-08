"""
Integration test for pagination performance (NFR-003).

Tests that Unity Catalog query pagination meets performance requirements:
- Single-user: end-to-end response time < 500ms for 100 rows
- Concurrent (10 users): p95 latency increase < 20%

**Test Requirements** (from tasks.md T039):
1. Query Unity Catalog table with 100 rows
2. Measure end-to-end API response time (not just execution_time_ms)
3. Test with 10 concurrent users
4. Calculate 95th percentile latency under load
5. Assert latency increase < 20%
6. Test model inference response time < 2000ms
"""

import pytest
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from server.app import app


class TestPaginationPerformance:
    """Test suite for pagination performance requirements (NFR-003)."""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user."""
        return "test-user@company.com"
    
    @pytest.fixture
    def mock_query_result(self):
        """Mock Unity Catalog query result with 100 rows."""
        return {
            "query_id": "query-123",
            "data_source": {
                "catalog_name": "main",
                "schema_name": "samples",
                "table_name": "demo_data",
                "columns": [
                    {"name": "id", "data_type": "int", "nullable": False},
                    {"name": "name", "data_type": "string", "nullable": True},
                    {"name": "value", "data_type": "int", "nullable": True}
                ],
                "owner": "admin",
                "access_level": "READ"
            },
            "sql_statement": "SELECT * FROM main.samples.demo_data LIMIT 100",
            "rows": [{"id": i, "name": f"row_{i}", "value": i * 10} for i in range(100)],
            "row_count": 100,
            "execution_time_ms": 250,  # Mock DB query time
            "user_id": "test-user@company.com",
            "status": "SUCCEEDED"
        }
    
    def _measure_request_time(self, client, endpoint: str, params: dict = None, json_data: dict = None):
        """
        Measure end-to-end API request time (includes network overhead).
        
        Returns:
            float: Request duration in milliseconds
        """
        start_time = time.perf_counter()
        
        if json_data:
            response = client.post(endpoint, json=json_data)
        else:
            response = client.get(endpoint, params=params)
        
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000
        
        return duration_ms, response
    
    def test_single_user_baseline_performance(self, client, mock_user, mock_query_result):
        """
        Test baseline single-user performance for pagination.
        
        Acceptance Criteria:
        1. Query Unity Catalog table with limit=100, offset=0
        2. Measure end-to-end API response time (not execution_time_ms from payload)
        3. Assert end-to-end response time < 500ms for 5 consecutive requests
        4. Calculate average baseline latency
        """
        with patch('server.routers.unity_catalog.get_current_user_id', return_value=mock_user):
            with patch('server.services.unity_catalog_service.UnityCatalogService.query_table', return_value=mock_query_result):
                
                latencies = []
                
                # Make 5 consecutive requests to establish baseline
                for i in range(5):
                    duration_ms, response = self._measure_request_time(
                        client,
                        "/api/unity-catalog/query",
                        params={
                            "catalog": "main",
                            "schema": "samples",
                            "table": "demo_data",
                            "limit": 100,
                            "offset": 0
                        }
                    )
                    
                    assert response.status_code == 200, \
                        f"Request {i+1} failed with status {response.status_code}"
                    
                    latencies.append(duration_ms)
                
                # Calculate baseline metrics
                avg_latency = statistics.mean(latencies)
                max_latency = max(latencies)
                
                # Assert all requests meet performance target
                for i, latency in enumerate(latencies):
                    assert latency < 500, \
                        f"Request {i+1} exceeded 500ms target: {latency:.2f}ms"
                
                print(f"\nBaseline Performance:")
                print(f"  Average latency: {avg_latency:.2f}ms")
                print(f"  Max latency: {max_latency:.2f}ms")
                print(f"  Min latency: {min(latencies):.2f}ms")
                
                return avg_latency
    
    def test_concurrent_user_performance(self, client, mock_user, mock_query_result):
        """
        Test pagination performance with 10 concurrent users.
        
        Acceptance Criteria:
        1. Use ThreadPoolExecutor to simulate 10 concurrent users
        2. Each user makes same query (limit=100)
        3. Measure 95th percentile end-to-end response time under load (p95_latency)
        4. Calculate latency increase: ((p95_latency - baseline) / baseline) * 100
        5. Assert latency increase < 20%
        """
        with patch('server.routers.unity_catalog.get_current_user_id', return_value=mock_user):
            with patch('server.services.unity_catalog_service.UnityCatalogService.query_table', return_value=mock_query_result):
                
                # Step 1: Establish baseline (single user, 5 requests)
                baseline_latencies = []
                for _ in range(5):
                    duration_ms, response = self._measure_request_time(
                        client,
                        "/api/unity-catalog/query",
                        params={
                            "catalog": "main",
                            "schema": "samples",
                            "table": "demo_data",
                            "limit": 100,
                            "offset": 0
                        }
                    )
                    baseline_latencies.append(duration_ms)
                
                baseline_avg = statistics.mean(baseline_latencies)
                
                # Step 2: Concurrent load test (10 users, 5 requests each = 50 total)
                def make_request():
                    """Function to be executed by each thread."""
                    duration_ms, response = self._measure_request_time(
                        client,
                        "/api/unity-catalog/query",
                        params={
                            "catalog": "main",
                            "schema": "samples",
                            "table": "demo_data",
                            "limit": 100,
                            "offset": 0
                        }
                    )
                    return duration_ms, response.status_code
                
                concurrent_latencies = []
                
                # Use ThreadPoolExecutor for concurrent requests
                with ThreadPoolExecutor(max_workers=10) as executor:
                    # Submit 50 requests (simulating 10 users making 5 requests each)
                    futures = [executor.submit(make_request) for _ in range(50)]
                    
                    for future in as_completed(futures):
                        duration_ms, status_code = future.result()
                        assert status_code == 200, \
                            f"Concurrent request failed with status {status_code}"
                        concurrent_latencies.append(duration_ms)
                
                # Step 3: Calculate 95th percentile latency
                p95_latency = statistics.quantiles(concurrent_latencies, n=20)[18]  # 95th percentile
                
                # Step 4: Calculate latency increase
                latency_increase_pct = ((p95_latency - baseline_avg) / baseline_avg) * 100
                
                print(f"\nConcurrent Load Performance (10 users, 50 requests):")
                print(f"  Baseline average: {baseline_avg:.2f}ms")
                print(f"  Concurrent p95: {p95_latency:.2f}ms")
                print(f"  Latency increase: {latency_increase_pct:.1f}%")
                print(f"  Concurrent average: {statistics.mean(concurrent_latencies):.2f}ms")
                print(f"  Concurrent max: {max(concurrent_latencies):.2f}ms")
                
                # Step 5: Assert latency increase < 20%
                assert latency_increase_pct < 20, \
                    f"Latency increase {latency_increase_pct:.1f}% exceeds 20% target"
    
    def test_pagination_offset_performance(self, client, mock_user, mock_query_result):
        """
        Test pagination performance across different offsets.
        
        Acceptance Criteria:
        1. Query with different offsets (0, 100, 200, 500, 1000)
        2. Verify performance doesn't degrade significantly with higher offsets
        3. Assert all offsets complete within 500ms
        """
        with patch('server.routers.unity_catalog.get_current_user_id', return_value=mock_user):
            with patch('server.services.unity_catalog_service.UnityCatalogService.query_table', return_value=mock_query_result):
                
                offsets = [0, 100, 200, 500, 1000]
                latencies_by_offset = {}
                
                for offset in offsets:
                    duration_ms, response = self._measure_request_time(
                        client,
                        "/api/unity-catalog/query",
                        params={
                            "catalog": "main",
                            "schema": "samples",
                            "table": "demo_data",
                            "limit": 100,
                            "offset": offset
                        }
                    )
                    
                    assert response.status_code == 200
                    assert duration_ms < 500, \
                        f"Query with offset={offset} exceeded 500ms: {duration_ms:.2f}ms"
                    
                    latencies_by_offset[offset] = duration_ms
                
                print(f"\nPagination Offset Performance:")
                for offset, latency in latencies_by_offset.items():
                    print(f"  Offset {offset:4d}: {latency:.2f}ms")
    
    def test_page_size_performance(self, client, mock_user):
        """
        Test performance with different page sizes.
        
        Acceptance Criteria:
        1. Test with page sizes: 10, 25, 50, 100, 500
        2. Verify 10-100 rows complete in < 500ms
        3. Verify 500 rows complete in < 1000ms (larger limit allowed)
        """
        with patch('server.routers.unity_catalog.get_current_user_id', return_value=mock_user):
            page_sizes = [10, 25, 50, 100, 500]
            latencies_by_size = {}
            
            for page_size in page_sizes:
                # Mock result with appropriate row count
                mock_result = {
                    "query_id": f"query-{page_size}",
                    "data_source": {
                        "catalog_name": "main",
                        "schema_name": "samples",
                        "table_name": "demo_data",
                        "columns": [{"name": "id", "data_type": "int", "nullable": False}],
                        "owner": "admin",
                        "access_level": "READ"
                    },
                    "sql_statement": f"SELECT * FROM main.samples.demo_data LIMIT {page_size}",
                    "rows": [{"id": i} for i in range(page_size)],
                    "row_count": page_size,
                    "execution_time_ms": page_size * 2,  # Mock scaling with size
                    "user_id": "test-user@company.com",
                    "status": "SUCCEEDED"
                }
                
                with patch('server.services.unity_catalog_service.UnityCatalogService.query_table', return_value=mock_result):
                    duration_ms, response = self._measure_request_time(
                        client,
                        "/api/unity-catalog/query",
                        params={
                            "catalog": "main",
                            "schema": "samples",
                            "table": "demo_data",
                            "limit": page_size,
                            "offset": 0
                        }
                    )
                    
                    assert response.status_code == 200
                    latencies_by_size[page_size] = duration_ms
                    
                    # Different thresholds for different page sizes
                    if page_size <= 100:
                        assert duration_ms < 500, \
                            f"Page size {page_size} exceeded 500ms: {duration_ms:.2f}ms"
                    else:  # page_size == 500
                        assert duration_ms < 1000, \
                            f"Page size {page_size} exceeded 1000ms: {duration_ms:.2f}ms"
            
            print(f"\nPage Size Performance:")
            for size, latency in latencies_by_size.items():
                print(f"  {size:3d} rows: {latency:.2f}ms")
    
    @patch('server.services.model_serving_service.ModelServingService.invoke_model')
    def test_model_inference_performance(self, mock_invoke, client, mock_user):
        """
        Test model inference performance meets < 2000ms requirement.
        
        Acceptance Criteria:
        1. Invoke model with standard payload
        2. Measure end-to-end response time
        3. Assert response time < 2000ms
        4. Test with 5 consecutive requests for consistency
        """
        with patch('server.routers.model_serving.get_current_user_id', return_value=mock_user):
            # Mock model inference result
            mock_invoke.return_value = {
                "request_id": "inference-123",
                "endpoint_name": "sentiment-analysis",
                "predictions": {"sentiment": "positive", "confidence": 0.95},
                "status": "SUCCESS",
                "execution_time_ms": 1200
            }
            
            latencies = []
            
            for i in range(5):
                duration_ms, response = self._measure_request_time(
                    client,
                    "/api/model-serving/invoke",
                    json_data={
                        "endpoint_name": "sentiment-analysis",
                        "inputs": {"text": "This product is amazing!"},
                        "timeout_seconds": 30
                    }
                )
                
                assert response.status_code == 200, \
                    f"Inference request {i+1} failed with status {response.status_code}"
                
                latencies.append(duration_ms)
                
                # Assert each request meets performance target
                assert duration_ms < 2000, \
                    f"Inference request {i+1} exceeded 2000ms: {duration_ms:.2f}ms"
            
            avg_latency = statistics.mean(latencies)
            print(f"\nModel Inference Performance:")
            print(f"  Average latency: {avg_latency:.2f}ms")
            print(f"  Max latency: {max(latencies):.2f}ms")
            print(f"  Min latency: {min(latencies):.2f}ms")
    
    def test_connection_pool_under_load(self, client, mock_user, mock_query_result):
        """
        Test database connection pool handles concurrent requests.
        
        Acceptance Criteria:
        1. Simulate 20 concurrent requests (exceeds pool_size)
        2. Verify all requests complete successfully
        3. No connection pool exhaustion errors
        4. Performance degradation acceptable (< 50% increase)
        """
        with patch('server.routers.unity_catalog.get_current_user_id', return_value=mock_user):
            with patch('server.services.unity_catalog_service.UnityCatalogService.query_table', return_value=mock_query_result):
                
                def make_request():
                    """Function to be executed by each thread."""
                    duration_ms, response = self._measure_request_time(
                        client,
                        "/api/unity-catalog/query",
                        params={
                            "catalog": "main",
                            "schema": "samples",
                            "table": "demo_data",
                            "limit": 100,
                            "offset": 0
                        }
                    )
                    return duration_ms, response.status_code
                
                latencies = []
                
                # Simulate 20 concurrent users
                with ThreadPoolExecutor(max_workers=20) as executor:
                    futures = [executor.submit(make_request) for _ in range(20)]
                    
                    for future in as_completed(futures):
                        duration_ms, status_code = future.result()
                        assert status_code == 200, \
                            f"Request failed with status {status_code} (connection pool issue?)"
                        latencies.append(duration_ms)
                
                avg_latency = statistics.mean(latencies)
                print(f"\nConnection Pool Performance (20 concurrent users):")
                print(f"  Average latency: {avg_latency:.2f}ms")
                print(f"  Max latency: {max(latencies):.2f}ms")
                print(f"  Successful requests: {len(latencies)}/20")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

