"""Contract tests for Unity Catalog API endpoints.

Tests validate that the API implementation matches the OpenAPI specification
defined in contracts/unity_catalog_api.yaml.

Expected Result: Tests FAIL initially (no implementation yet) - TDD approach.
"""

import pytest
from fastapi.testclient import TestClient
from server.app import app

client = TestClient(app)


class TestUnityCatalogListTablesContract:
    """Contract tests for GET /api/unity-catalog/tables endpoint."""

    def test_list_tables_response_structure(self):
        """Verify response matches DataSource[] schema from OpenAPI spec."""
        response = client.get('/api/unity-catalog/tables')
        
        # Should return 200, 401, 403, or 503
        assert response.status_code in [200, 401, 403, 503], \
            f'Unexpected status code: {response.status_code}'
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list), 'Response should be an array'
            
            # Validate DataSource schema for each table
            for table in data:
                assert 'catalog_name' in table, 'Missing catalog_name field'
                assert 'schema_name' in table, 'Missing schema_name field'
                assert 'table_name' in table, 'Missing table_name field'
                assert 'full_name' in table, 'Missing full_name field'
                assert 'columns' in table, 'Missing columns field'
                assert 'owner' in table, 'Missing owner field'
                assert 'access_level' in table, 'Missing access_level field'
                assert 'last_refreshed' in table, 'Missing last_refreshed field'
                
                # Validate access_level enum
                assert table['access_level'] in ['READ', 'WRITE', 'NONE'], \
                    f'Invalid access_level: {table["access_level"]}'
                
                # Validate columns array
                assert isinstance(table['columns'], list), 'columns should be an array'
                assert len(table['columns']) > 0, 'columns array should not be empty'
                for column in table['columns']:
                    assert 'name' in column, 'Column missing name'
                    assert 'data_type' in column, 'Column missing data_type'
                    assert 'nullable' in column, 'Column missing nullable'

    def test_list_tables_correlation_id_header(self):
        """Verify X-Request-ID header is present in response."""
        response = client.get('/api/unity-catalog/tables')
        
        if response.status_code == 200:
            assert 'X-Request-ID' in response.headers or 'x-request-id' in response.headers, \
                'Missing X-Request-ID header for correlation ID'

    def test_list_tables_with_catalog_filter(self):
        """Verify catalog query parameter works correctly."""
        response = client.get('/api/unity-catalog/tables?catalog=main')
        
        assert response.status_code in [200, 401, 403, 503]
        
        if response.status_code == 200:
            data = response.json()
            for table in data:
                assert table['catalog_name'] == 'main', \
                    'Catalog filter not applied correctly'

    def test_list_tables_with_schema_filter(self):
        """Verify schema query parameter works correctly."""
        response = client.get('/api/unity-catalog/tables?catalog=main&schema=samples')
        
        assert response.status_code in [200, 401, 403, 503]
        
        if response.status_code == 200:
            data = response.json()
            for table in data:
                assert table['catalog_name'] == 'main'
                assert table['schema_name'] == 'samples'


class TestUnityCatalogQueryContract:
    """Contract tests for POST /api/unity-catalog/query endpoint."""

    def test_query_table_response_structure(self):
        """Verify response matches QueryResult schema from OpenAPI spec."""
        payload = {
            'catalog': 'main',
            'schema': 'samples',
            'table': 'demo_data',
            'limit': 10,
            'offset': 0
        }
        
        response = client.post('/api/unity-catalog/query', json=payload)
        
        # Should return 200, 400, 403, 404, or 503
        assert response.status_code in [200, 400, 403, 404, 503], \
            f'Unexpected status code: {response.status_code}'
        
        if response.status_code == 200:
            data = response.json()
            
            # Validate required fields
            assert 'query_id' in data, 'Missing query_id field'
            assert 'rows' in data, 'Missing rows field'
            assert 'row_count' in data, 'Missing row_count field'
            assert 'execution_time_ms' in data, 'Missing execution_time_ms field'
            assert 'user_id' in data, 'Missing user_id field'
            assert 'executed_at' in data, 'Missing executed_at field'
            assert 'status' in data, 'Missing status field'
            
            # Validate status enum
            assert data['status'] in ['PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED'], \
                f'Invalid status: {data["status"]}'
            
            # Validate rows array
            assert isinstance(data['rows'], list), 'rows should be an array'
            
            # Validate row_count matches rows length
            assert data['row_count'] == len(data['rows']), \
                'row_count must equal len(rows)'
            
            # Validate execution_time_ms is positive
            assert data['execution_time_ms'] > 0, \
                'execution_time_ms must be positive'

    def test_query_table_pagination_limits(self):
        """Verify pagination parameters (limit, offset) are respected."""
        payload = {
            'catalog': 'main',
            'schema': 'samples',
            'table': 'demo_data',
            'limit': 5,
            'offset': 0
        }
        
        response = client.post('/api/unity-catalog/query', json=payload)
        
        if response.status_code == 200:
            data = response.json()
            assert data['row_count'] <= 5, 'limit parameter not respected'

    def test_query_table_required_fields(self):
        """Verify required fields (catalog, schema, table) are enforced."""
        # Missing catalog
        payload = {'schema': 'samples', 'table': 'demo_data'}
        response = client.post('/api/unity-catalog/query', json=payload)
        assert response.status_code == 422, 'Should reject missing catalog'
        
        # Missing schema
        payload = {'catalog': 'main', 'table': 'demo_data'}
        response = client.post('/api/unity-catalog/query', json=payload)
        assert response.status_code == 422, 'Should reject missing schema'
        
        # Missing table
        payload = {'catalog': 'main', 'schema': 'samples'}
        response = client.post('/api/unity-catalog/query', json=payload)
        assert response.status_code == 422, 'Should reject missing table'

    def test_query_table_limit_boundaries(self):
        """Verify limit parameter boundaries (1-1000)."""
        # Test minimum boundary
        payload = {
            'catalog': 'main',
            'schema': 'samples',
            'table': 'demo_data',
            'limit': 1
        }
        response = client.post('/api/unity-catalog/query', json=payload)
        assert response.status_code in [200, 400, 403, 404, 503]
        
        # Test maximum boundary
        payload['limit'] = 1000
        response = client.post('/api/unity-catalog/query', json=payload)
        assert response.status_code in [200, 400, 403, 404, 503]
        
        # Test below minimum (should fail validation)
        payload['limit'] = 0
        response = client.post('/api/unity-catalog/query', json=payload)
        assert response.status_code == 422, 'Should reject limit < 1'
        
        # Test above maximum (should fail validation)
        payload['limit'] = 1001
        response = client.post('/api/unity-catalog/query', json=payload)
        assert response.status_code == 422, 'Should reject limit > 1000'

    def test_query_table_error_response_structure(self):
        """Verify error responses match ErrorResponse schema."""
        # Query non-existent table
        payload = {
            'catalog': 'main',
            'schema': 'samples',
            'table': 'nonexistent_table'
        }
        
        response = client.post('/api/unity-catalog/query', json=payload)
        
        if response.status_code in [400, 403, 404, 503]:
            data = response.json()
            assert 'error_code' in data, 'Error response missing error_code'
            assert 'message' in data, 'Error response missing message'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
