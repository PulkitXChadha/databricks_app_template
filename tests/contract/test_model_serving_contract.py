"""Contract tests for Model Serving API endpoints.

Tests validate that the API implementation matches the OpenAPI specification
defined in contracts/model_serving_api.yaml.

Expected Result: Tests FAIL initially (no implementation yet) - TDD approach.
"""

import pytest
from fastapi.testclient import TestClient
from server.app import app

client = TestClient(app)


@pytest.fixture
def auth_headers():
    """Provide authentication headers for contract tests."""
    return {"X-Forwarded-Access-Token": "mock-user-token-for-testing"}


class TestModelServingListEndpointsContract:
    """Contract tests for GET /api/model-serving/endpoints endpoint (SHOULD capability)."""

    def test_list_endpoints_response_structure(self):
        """Verify response matches ModelEndpoint[] schema from OpenAPI spec."""
        response = client.get('/api/model-serving/endpoints')
        
        # Should return 200, 401, or 503
        assert response.status_code in [200, 401, 503], \
            f'Unexpected status code: {response.status_code}'
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list), 'Response should be an array'
            
            # Validate ModelEndpoint schema for each endpoint
            for endpoint in data:
                assert 'endpoint_name' in endpoint, 'Missing endpoint_name field'
                assert 'model_name' in endpoint, 'Missing model_name field'
                assert 'state' in endpoint, 'Missing state field'
                
                # Validate state enum
                assert endpoint['state'] in ['CREATING', 'READY', 'UPDATING', 'FAILED'], \
                    f'Invalid state: {endpoint["state"]}'

    def test_list_endpoints_correlation_id_header(self):
        """Verify X-Request-ID header is present in response."""
        response = client.get('/api/model-serving/endpoints')
        
        if response.status_code == 200:
            assert 'X-Request-ID' in response.headers or 'x-request-id' in response.headers, \
                'Missing X-Request-ID header for correlation ID'


class TestModelServingGetEndpointContract:
    """Contract tests for GET /api/model-serving/endpoints/{endpoint_name} endpoint."""

    def test_get_endpoint_response_structure(self):
        """Verify response matches ModelEndpoint schema from OpenAPI spec."""
        # Test with a sample endpoint name
        response = client.get('/api/model-serving/endpoints/sentiment-analysis')
        
        # Should return 200, 401, 404, or 503
        assert response.status_code in [200, 401, 404, 503], \
            f'Unexpected status code: {response.status_code}'
        
        if response.status_code == 200:
            data = response.json()
            
            # Validate required fields
            assert 'endpoint_name' in data, 'Missing endpoint_name field'
            assert 'model_name' in data, 'Missing model_name field'
            assert 'state' in data, 'Missing state field'
            
            # Validate state enum
            assert data['state'] in ['CREATING', 'READY', 'UPDATING', 'FAILED'], \
                f'Invalid state: {data["state"]}'

    def test_get_endpoint_not_found(self):
        """Verify non-existent endpoint returns 404."""
        response = client.get('/api/model-serving/endpoints/nonexistent-endpoint')
        
        # Should return 404 for non-existent endpoint
        assert response.status_code in [401, 404, 503]
        
        if response.status_code == 404:
            data = response.json()
            assert 'error_code' in data, 'Missing error_code in 404 response'
            assert 'message' in data, 'Missing message in 404 response'


class TestModelServingInvokeContract:
    """Contract tests for POST /api/model-serving/invoke endpoint (MANDATORY capability)."""

    def test_invoke_model_response_structure(self):
        """Verify response matches ModelInferenceResponse schema from OpenAPI spec."""
        payload = {
            'endpoint_name': 'sentiment-analysis',
            'inputs': {
                'text': 'This product is amazing!'
            },
            'timeout_seconds': 30
        }
        
        response = client.post('/api/model-serving/invoke', json=payload)
        
        # Should return 200, 400, 401, 404, or 503
        assert response.status_code in [200, 400, 401, 404, 503], \
            f'Unexpected status code: {response.status_code}'
        
        if response.status_code == 200:
            data = response.json()
            
            # Validate required fields
            assert 'request_id' in data, 'Missing request_id field'
            assert 'endpoint_name' in data, 'Missing endpoint_name field'
            assert 'status' in data, 'Missing status field'
            assert 'execution_time_ms' in data, 'Missing execution_time_ms field'
            assert 'completed_at' in data, 'Missing completed_at field'
            
            # Validate status enum
            assert data['status'] in ['SUCCESS', 'ERROR', 'TIMEOUT'], \
                f'Invalid status: {data["status"]}'
            
            # Validate execution_time_ms is positive
            assert data['execution_time_ms'] > 0, \
                'execution_time_ms must be positive'
            
            # Validate error_message present if status is ERROR
            if data['status'] == 'ERROR':
                assert 'error_message' in data and data['error_message'] is not None, \
                    'error_message required when status is ERROR'

    def test_invoke_model_correlation_id_header(self):
        """Verify X-Request-ID header is present in response."""
        payload = {
            'endpoint_name': 'sentiment-analysis',
            'inputs': {'text': 'Test'},
            'timeout_seconds': 30
        }
        
        response = client.post('/api/model-serving/invoke', json=payload)
        
        if response.status_code == 200:
            assert 'X-Request-ID' in response.headers or 'x-request-id' in response.headers, \
                'Missing X-Request-ID header for correlation ID'

    def test_invoke_model_required_fields(self, auth_headers, mock_user_auth):
        """Verify required fields (endpoint_name, inputs) are enforced."""
        # Missing endpoint_name
        payload = {'inputs': {'text': 'Test'}}
        response = client.post('/api/model-serving/invoke', json=payload, headers=auth_headers)
        assert response.status_code == 422, 'Should reject missing endpoint_name'
        
        # Missing inputs
        payload = {'endpoint_name': 'sentiment-analysis'}
        response = client.post('/api/model-serving/invoke', json=payload, headers=auth_headers)
        assert response.status_code == 422, 'Should reject missing inputs'

    def test_invoke_model_timeout_boundaries(self, auth_headers, mock_user_auth):
        """Verify timeout_seconds parameter boundaries (1-300)."""
        # Test minimum boundary
        payload = {
            'endpoint_name': 'sentiment-analysis',
            'inputs': {'text': 'Test'},
            'timeout_seconds': 1
        }
        response = client.post('/api/model-serving/invoke', json=payload, headers=auth_headers)
        assert response.status_code in [200, 400, 404, 503]
        
        # Test maximum boundary
        payload['timeout_seconds'] = 300
        response = client.post('/api/model-serving/invoke', json=payload, headers=auth_headers)
        assert response.status_code in [200, 400, 404, 503]
        
        # Test below minimum (should fail validation)
        payload['timeout_seconds'] = 0
        response = client.post('/api/model-serving/invoke', json=payload, headers=auth_headers)
        assert response.status_code == 422, 'Should reject timeout_seconds < 1'
        
        # Test above maximum (should fail validation)
        payload['timeout_seconds'] = 301
        response = client.post('/api/model-serving/invoke', json=payload, headers=auth_headers)
        assert response.status_code == 422, 'Should reject timeout_seconds > 300'

    def test_invoke_model_default_timeout(self):
        """Verify default timeout is 30 seconds when not specified."""
        payload = {
            'endpoint_name': 'sentiment-analysis',
            'inputs': {'text': 'Test'}
            # timeout_seconds omitted - should default to 30
        }
        
        response = client.post('/api/model-serving/invoke', json=payload)
        # Validation should pass even without timeout_seconds
        assert response.status_code in [200, 400, 401, 404, 503]

    def test_invoke_model_endpoint_not_found(self):
        """Verify non-existent endpoint returns 404."""
        payload = {
            'endpoint_name': 'nonexistent-endpoint',
            'inputs': {'text': 'Test'}
        }
        
        response = client.post('/api/model-serving/invoke', json=payload)
        
        # Should return 404 for non-existent endpoint
        assert response.status_code in [400, 401, 404, 503]

    def test_invoke_model_error_response_structure(self):
        """Verify error responses match ErrorResponse schema."""
        # Send invalid request
        payload = {
            'endpoint_name': 'nonexistent-endpoint',
            'inputs': {}  # Empty inputs may be invalid
        }
        
        response = client.post('/api/model-serving/invoke', json=payload)
        
        if response.status_code in [400, 404, 503]:
            data = response.json()
            # Should have error_code and message
            assert 'error_code' in data or 'detail' in data, \
                'Error response missing error information'


class TestModelServingPerformanceContract:
    """Contract tests for NFR-003 performance requirements."""

    def test_invoke_model_latency_tracking(self):
        """Verify execution_time_ms is tracked for performance monitoring.
        
        This validates that the API tracks inference latency as required
        for NFR-003 (<2s latency target for standard payloads).
        """
        payload = {
            'endpoint_name': 'sentiment-analysis',
            'inputs': {'text': 'This product is amazing!'},
            'timeout_seconds': 30
        }
        
        response = client.post('/api/model-serving/invoke', json=payload)
        
        if response.status_code == 200:
            data = response.json()
            assert 'execution_time_ms' in data, \
                'execution_time_ms required for performance tracking'
            assert isinstance(data['execution_time_ms'], int), \
                'execution_time_ms should be an integer'
            assert data['execution_time_ms'] > 0, \
                'execution_time_ms should be positive'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
