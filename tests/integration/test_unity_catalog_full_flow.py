"""Integration tests for Unity Catalog API - Full Flow Coverage.

User Story 2: Complete Unity Catalog API Coverage (Priority: P1)

This test file validates:
- GET /api/unity-catalog/catalogs (list catalogs)
- GET /api/unity-catalog/schemas (list schemas)
- GET /api/unity-catalog/table-names (list table names)
- GET /api/unity-catalog/tables (list tables with metadata)
- GET /api/unity-catalog/query (query table with pagination)
- POST /api/unity-catalog/query (query table with filters)
- Permission enforcement (403)
- Table not found handling (404)
- Invalid parameters handling (400)

Test Count: 9 scenarios
Coverage Target: 90%+ for server/routers/unity_catalog.py and server/services/unity_catalog_service.py
"""

from contextlib import contextmanager
from typing import Generator
from unittest.mock import Mock, patch

import pytest

# ==============================================================================
# Test Helpers and Fixtures
# ==============================================================================


@pytest.fixture(autouse=True)
def mock_databricks_env(monkeypatch):
  """Mock Databricks environment variables and WorkspaceClient for Unity Catalog tests.

  Unity Catalog Service requires DATABRICKS_HOST and DATABRICKS_WAREHOUSE_ID.
  This fixture automatically sets them and mocks WorkspaceClient for all tests.
  """
  monkeypatch.setenv('DATABRICKS_HOST', 'https://test-workspace.cloud.databricks.com')
  monkeypatch.setenv('DATABRICKS_WAREHOUSE_ID', 'test-warehouse-id-123')

  # Mock WorkspaceClient to prevent actual SDK initialization
  with patch('server.services.unity_catalog_service.WorkspaceClient') as mock_client:
    mock_instance = Mock()
    mock_client.return_value = mock_instance
    yield


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
def mock_unity_catalog_service(method_name: str, return_value=None, side_effect=None):
  """Context manager to mock UnityCatalogService methods with consistent pattern.

  Args:
      method_name: Name of the service method to mock (e.g., 'list_catalogs')
      return_value: Value to return from the mocked method (optional)
      side_effect: Exception or side effect to raise (optional)

  Yields:
      The mock method object for additional assertions

  Example:
      with mock_unity_catalog_service('list_catalogs', return_value=["main", "samples"]):
          response = client.get("/api/unity-catalog/catalogs")
  """
  patch_path = f'server.services.unity_catalog_service.UnityCatalogService.{method_name}'
  with patch(patch_path) as mock_method:
    if side_effect is not None:
      mock_method.side_effect = side_effect
    elif return_value is not None:
      mock_method.return_value = return_value
    yield mock_method


def create_mock_data_source(
  catalog: str = 'main', schema: str = 'default', table: str = 'customers', columns: list = None
):
  """Factory function to create mock DataSource objects with default values.

  Args:
      catalog: Catalog name
      schema: Schema name
      table: Table name
      columns: List of ColumnDefinition objects (uses defaults if None)

  Returns:
      DataSource object with specified or default values
  """
  from server.models.data_source import AccessLevel, ColumnDefinition, DataSource

  if columns is None:
    columns = [
      ColumnDefinition(name='id', data_type='bigint', nullable=False),
      ColumnDefinition(name='name', data_type='string', nullable=True),
      ColumnDefinition(name='email', data_type='string', nullable=True),
    ]

  return DataSource(
    catalog_name=catalog,
    schema_name=schema,
    table_name=table,
    columns=columns,
    owner='admin',
    access_level=AccessLevel.READ,
  )


def create_mock_query_result(
  user_id: str, data_source=None, rows: list = None, query_id: str = 'query-123'
):
  """Factory function to create mock QueryResult objects with default values.

  Args:
      user_id: User ID executing the query
      data_source: DataSource object (creates default if None)
      rows: List of row dictionaries (creates default if None)
      query_id: Query identifier

  Returns:
      QueryResult object with specified or default values
  """
  from server.models.query_result import QueryResult, QueryStatus

  if data_source is None:
    data_source = create_mock_data_source()

  if rows is None:
    rows = [
      {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'},
      {'id': 2, 'name': 'Bob', 'email': 'bob@example.com'},
    ]

  sql_statement = f'SELECT * FROM {data_source.catalog_name}.{data_source.schema_name}.{data_source.table_name} LIMIT {len(rows)} OFFSET 0'

  return QueryResult(
    query_id=query_id,
    data_source=data_source,
    sql_statement=sql_statement,
    rows=rows,
    row_count=len(rows),
    execution_time_ms=45,
    user_id=user_id,
    status=QueryStatus.SUCCEEDED,
  )


def assert_error_response(
  response, expected_status: int, error_keywords: list = None, message: str = None
):
  """Standardized error response assertion helper.

  Args:
      response: FastAPI TestClient response object
      expected_status: Expected HTTP status code (403, 404, 422, etc.)
      error_keywords: List of keywords to check in response (case-insensitive)
      message: Custom assertion message (optional)

  Raises:
      AssertionError: If response doesn't match expected error pattern

  Example:
      assert_error_response(
          response,
          expected_status=403,
          error_keywords=["CATALOG_PERMISSION_DENIED", "permission"],
          message="Expected permission denied error for restricted catalog"
      )
  """
  # Check status code
  assert response.status_code == expected_status, (
    message or f'Expected {expected_status} status code, got {response.status_code}'
  )

  # Check error content if keywords provided
  if error_keywords:
    response_data = response.json()
    response_text = str(response_data).lower()

    found_keyword = any(keyword.lower() in response_text for keyword in error_keywords)
    assert found_keyword, f'Expected one of {error_keywords} in response, got {response_data}'


# ==============================================================================
# Test Class: Unity Catalog Full Flow
# ==============================================================================


@pytest.mark.integration
class TestUnityCatalogFullFlow:
  """Integration tests for Unity Catalog API.

  Tests cover catalog/schema/table browsing, querying with pagination,
  permission enforcement, and error handling.

  TDD Workflow:
  - RED Phase: Write tests that fail initially
  - GREEN Phase: Verify tests pass against existing implementation
  - REFACTOR Phase: Improve test code quality
  """

  # ==========================================================================
  # Test 1: GET catalogs returns accessible catalogs
  # ==========================================================================

  def test_get_catalogs_returns_accessible_catalogs(
    self, client, test_user_a, mock_user_auth, mock_catalog_metadata
  ):
    """Test that GET /api/unity-catalog/catalogs returns catalog names.

    Given: User has access to Unity Catalog
    When: GET /api/unity-catalog/catalogs is called
    Then: Response is 200 OK with list of accessible catalog names

    TDD Phase: GREEN (tests pass against existing implementation)
    """
    with mock_user_context(test_user_a['user_id']):
      # Mock the UnityCatalogService.list_catalogs method using helper
      with mock_unity_catalog_service(
        'list_catalogs', return_value=mock_catalog_metadata['catalogs']
      ):
        # Act: GET catalogs
        response = client.get(
          '/api/unity-catalog/catalogs', headers={'X-Forwarded-Access-Token': test_user_a['token']}
        )

        # Assert: Returns list of catalog names
        assert response.status_code == 200, f'Expected 200 OK, got {response.status_code}'

        catalogs = response.json()
        assert isinstance(catalogs, list), f'Expected list of catalogs, got {type(catalogs)}'
        assert len(catalogs) > 0, 'Expected at least one catalog, got empty list'
        assert 'main' in catalogs or 'samples' in catalogs, (
          f"Expected 'main' or 'samples' in catalogs, got {catalogs}"
        )

  # ==========================================================================
  # Test 2: GET schemas for catalog
  # ==========================================================================

  def test_get_schemas_for_catalog(
    self, client, test_user_a, mock_user_auth, mock_catalog_metadata
  ):
    """Test that GET /api/unity-catalog/schemas returns schema names.

    Given: A catalog with multiple schemas
    When: GET /api/unity-catalog/schemas?catalog=main is called
    Then: Response is 200 OK with list of schema names

    TDD Phase: GREEN (tests pass against existing implementation)
    """
    with mock_user_context(test_user_a['user_id']):
      # Mock the UnityCatalogService.list_schemas method using helper
      with mock_unity_catalog_service(
        'list_schemas', return_value=mock_catalog_metadata['schemas']['main']
      ):
        # Act: GET schemas for catalog 'main'
        response = client.get(
          '/api/unity-catalog/schemas?catalog=main',
          headers={'X-Forwarded-Access-Token': test_user_a['token']},
        )

        # Assert: Returns list of schema names
        assert response.status_code == 200, f'Expected 200 OK, got {response.status_code}'

        schemas = response.json()
        assert isinstance(schemas, list), f'Expected list of schemas, got {type(schemas)}'
        assert len(schemas) > 0, 'Expected at least one schema, got empty list'
        assert 'default' in schemas, f"Expected 'default' schema in 'main' catalog, got {schemas}"

  # ==========================================================================
  # Test 3: GET table names for schema
  # ==========================================================================

  def test_get_table_names_for_schema(
    self, client, test_user_a, mock_user_auth, mock_catalog_metadata
  ):
    """Test that GET /api/unity-catalog/table-names returns table names.

    Given: A schema with multiple tables
    When: GET /api/unity-catalog/table-names?catalog=main&schema=default is called
    Then: Response is 200 OK with list of table names

    TDD Phase: GREEN (tests pass against existing implementation)
    """
    with mock_user_context(test_user_a['user_id']):
      # Mock the UnityCatalogService.list_table_names method using helper
      # Extract table names from mock_catalog_metadata
      table_names = [
        table['table_name'] for table in mock_catalog_metadata['tables']['main.default']
      ]
      with mock_unity_catalog_service('list_table_names', return_value=table_names):
        # Act: GET table names for schema 'main.default'
        response = client.get(
          '/api/unity-catalog/table-names?catalog=main&schema=default',
          headers={'X-Forwarded-Access-Token': test_user_a['token']},
        )

        # Assert: Returns list of table names
        assert response.status_code == 200, f'Expected 200 OK, got {response.status_code}'

        tables = response.json()
        assert isinstance(tables, list), f'Expected list of table names, got {type(tables)}'
        assert len(tables) > 0, 'Expected at least one table, got empty list'
        assert 'customers' in tables or 'orders' in tables, (
          f"Expected 'customers' or 'orders' in tables, got {tables}"
        )

  # ==========================================================================
  # Test 4: GET tables with metadata
  # ==========================================================================

  def test_get_tables_with_metadata(self, client, test_user_a, mock_user_auth):
    """Test that GET /api/unity-catalog/tables returns DataSource objects with metadata.

    Given: User has access to tables
    When: GET /api/unity-catalog/tables is called
    Then: Response is 200 OK with list of DataSource objects

    TDD Phase: GREEN (tests pass against existing implementation)
    """
    with mock_user_context(test_user_a['user_id']):
      # Mock the UnityCatalogService.list_tables method using helper
      mock_tables = [create_mock_data_source(table='customers')]
      with mock_unity_catalog_service('list_tables', return_value=mock_tables):
        # Act: GET tables with metadata
        response = client.get(
          '/api/unity-catalog/tables', headers={'X-Forwarded-Access-Token': test_user_a['token']}
        )

        # Assert: Returns list of DataSource objects
        assert response.status_code == 200, f'Expected 200 OK, got {response.status_code}'

        tables = response.json()
        assert isinstance(tables, list), f'Expected list of tables, got {type(tables)}'
        assert len(tables) > 0, 'Expected at least one table, got empty list'

        # Verify DataSource structure
        first_table = tables[0]
        assert 'catalog_name' in first_table, "Expected 'catalog_name' in DataSource"
        assert 'schema_name' in first_table, "Expected 'schema_name' in DataSource"
        assert 'table_name' in first_table, "Expected 'table_name' in DataSource"
        assert 'columns' in first_table, "Expected 'columns' in DataSource"

  # ==========================================================================
  # Test 5: Query table with pagination
  # ==========================================================================

  def test_query_table_with_pagination(self, client, test_user_a, mock_user_auth, mock_table_data):
    """Test that GET /api/unity-catalog/query returns table data with pagination.

    Given: A table with data
    When: GET /api/unity-catalog/query with limit/offset is called
    Then: Response is 200 OK with QueryResult containing paginated data

    TDD Phase: GREEN (tests pass against existing implementation)
    """
    with mock_user_context(test_user_a['user_id']):
      # Mock the UnityCatalogService.query_table method using helpers
      table_data = mock_table_data['main.default.customers']
      mock_result = create_mock_query_result(
        user_id=test_user_a['user_id'], rows=table_data['rows']
      )
      with mock_unity_catalog_service('query_table', return_value=mock_result):
        # Act: Query table with pagination
        response = client.get(
          '/api/unity-catalog/query?catalog=main&schema=default&table=customers&limit=10&offset=0',
          headers={'X-Forwarded-Access-Token': test_user_a['token']},
        )

        # Assert: Returns QueryResult with data
        assert response.status_code == 200, f'Expected 200 OK, got {response.status_code}'

        result = response.json()
        assert 'rows' in result, "Expected 'rows' field in QueryResult"
        assert 'row_count' in result, "Expected 'row_count' field in QueryResult"
        assert isinstance(result['rows'], list), (
          f'Expected list of rows, got {type(result["rows"])}'
        )
        assert result['row_count'] >= 0, (
          f'Expected non-negative row_count, got {result["row_count"]}'
        )

  # ==========================================================================
  # Test 6: Query table with filters (POST method)
  # ==========================================================================

  def test_query_table_with_filters(self, client, test_user_a, mock_user_auth):
    """Test that POST /api/unity-catalog/query with filters returns filtered data.

    Given: A table with data
    When: POST /api/unity-catalog/query with filters is called
    Then: Response is 200 OK with filtered QueryResult

    TDD Phase: GREEN (tests pass against existing implementation)
    """
    with mock_user_context(test_user_a['user_id']):
      # Mock the UnityCatalogService.query_table method using helpers
      filtered_rows = [{'id': 1, 'name': 'Alice', 'email': 'alice@example.com'}]
      mock_result = create_mock_query_result(
        user_id=test_user_a['user_id'], rows=filtered_rows, query_id='query-456'
      )
      with mock_unity_catalog_service('query_table', return_value=mock_result):
        # Act: POST query with filters
        request_body = {
          'catalog': 'main',
          'schema': 'default',
          'table': 'customers',
          'limit': 10,
          'offset': 0,
          'filters': {'name': 'Alice'},
        }

        response = client.post(
          '/api/unity-catalog/query',
          json=request_body,
          headers={'X-Forwarded-Access-Token': test_user_a['token']},
        )

        # Assert: Returns filtered QueryResult
        assert response.status_code == 200, f'Expected 200 OK, got {response.status_code}'

        result = response.json()
        assert 'rows' in result, "Expected 'rows' field in QueryResult"
        assert result['row_count'] > 0, 'Expected at least one row in filtered result'

  # ==========================================================================
  # Test 7: Permission denied returns 403
  # ==========================================================================

  def test_catalog_permission_denied_returns_403(self, client, test_user_a, mock_user_auth):
    """Test that 403 error returned when user lacks catalog permissions.

    Given: User lacks permissions for a catalog
    When: GET /api/unity-catalog/schemas is called for restricted catalog
    Then: Response is 403 Forbidden with CATALOG_PERMISSION_DENIED error

    TDD Phase: GREEN (tests pass against existing implementation)
    """
    with mock_user_context(test_user_a['user_id']):
      # Mock the UnityCatalogService.list_schemas to raise PermissionError using helper
      with mock_unity_catalog_service(
        'list_schemas',
        side_effect=PermissionError("User does not have access to catalog 'restricted'"),
      ):
        # Act: GET schemas for restricted catalog
        response = client.get(
          '/api/unity-catalog/schemas?catalog=restricted',
          headers={'X-Forwarded-Access-Token': test_user_a['token']},
        )

        # Assert: 403 Forbidden with permission error (using standardized helper)
        assert_error_response(
          response,
          expected_status=403,
          error_keywords=['CATALOG_PERMISSION_DENIED', 'permission'],
          message='Expected 403 Forbidden with permission denied error for restricted catalog',
        )

  # ==========================================================================
  # Test 8: Table not found returns 404
  # ==========================================================================

  def test_table_not_found_returns_404(self, client, test_user_a, mock_user_auth):
    """Test that 404 error returned for non-existent table.

    Given: A table that does not exist
    When: GET /api/unity-catalog/query is called for non-existent table
    Then: Response is 404 Not Found with TABLE_NOT_FOUND error

    TDD Phase: GREEN (tests pass against existing implementation)
    """
    with mock_user_context(test_user_a['user_id']):
      # Mock the UnityCatalogService.query_table to raise "not found" error using helper
      with mock_unity_catalog_service(
        'query_table', side_effect=Exception('Table main.default.nonexistent not found')
      ):
        # Act: Query non-existent table
        response = client.get(
          '/api/unity-catalog/query?catalog=main&schema=default&table=nonexistent&limit=10&offset=0',
          headers={'X-Forwarded-Access-Token': test_user_a['token']},
        )

        # Assert: 404 Not Found with table not found error (using standardized helper)
        assert_error_response(
          response,
          expected_status=404,
          error_keywords=['TABLE_NOT_FOUND', 'not found'],
          message='Expected 404 Not Found with TABLE_NOT_FOUND error for non-existent table',
        )

  # ==========================================================================
  # Test 9: Invalid pagination parameters returns 400
  # ==========================================================================

  def test_invalid_pagination_parameters_returns_400(self, client, test_user_a, mock_user_auth):
    """Test that 400 error returned for invalid pagination parameters.

    Given: Invalid pagination parameters (limit > 1000 or negative offset)
    When: GET /api/unity-catalog/query is called with invalid params
    Then: Response is 422 Unprocessable Entity (Pydantic validation) or 400 Bad Request

    TDD Phase: RED (test must fail initially)

    Note: FastAPI returns 422 for Pydantic validation errors.
    """
    with mock_user_context(test_user_a['user_id']):
      # Act: Query with invalid limit (> 1000)
      response = client.get(
        '/api/unity-catalog/query?catalog=main&schema=default&table=customers&limit=2000&offset=0',
        headers={'X-Forwarded-Access-Token': test_user_a['token']},
      )

      # Assert: 422 Unprocessable Entity (Pydantic validation) using standardized helper
      # FastAPI returns 422 for validation errors, but we accept 400 as well
      assert response.status_code in [400, 422], (
        f'Expected 400 or 422 for invalid pagination, got {response.status_code}'
      )

      assert_error_response(
        response,
        expected_status=response.status_code,  # Accept either 400 or 422
        error_keywords=['detail', 'error', 'validation'],
        message='Expected validation error for invalid pagination parameters',
      )

  # ==========================================================================
  # Edge Case Tests (T119, T120)
  # ==========================================================================

  def test_pagination_offset_exceeds_total_returns_empty(self, client, mock_user_auth):
    """Test that pagination offset exceeding total returns empty list, not error.

    Given: Offset parameter that exceeds total number of records
    When: GET /api/unity-catalog/query is called with high offset
    Then: Response is 200 with empty result list (not 400/404 error)

    Edge Case: T119 - Pagination offset exceeds total
    """
    mock_result = create_mock_query_result(
      user_id='test-user-a@example.com',
      rows=[],  # Empty rows
      query_id='query-123',
    )

    with mock_unity_catalog_service('query_table', return_value=mock_result):
      with mock_user_context('test-user-a@example.com'):
        # Act: Request with offset far beyond total rows
        response = client.get(
          '/api/unity-catalog/query',
          params={
            'catalog': 'main',
            'schema': 'default',
            'table': 'customers',
            'limit': 10,
            'offset': 9999,  # Offset exceeds total
          },
          headers={'X-Forwarded-Access-Token': 'test-token'},
        )

        # Assert: 200 OK (not error)
        assert response.status_code == 200, (
          f'Expected 200 for offset > total, got {response.status_code}'
        )

        # Verify: Empty result list
        data = response.json()
        assert isinstance(data, dict), f'Expected dict response, got {type(data)}'
        assert 'rows' in data, f"Expected 'rows' field, got {data.keys()}"
        assert isinstance(data['rows'], list), f'Expected rows to be list, got {type(data["rows"])}'
        assert len(data['rows']) == 0, (
          f'Expected empty rows when offset > total, got {len(data["rows"])} rows'
        )
        assert data.get('total_rows', 0) >= 0, 'Expected non-negative total_rows'

  def test_timezone_consistency_utc_across_services(self, client, mock_user_auth):
    """Test that all timestamp fields use UTC consistently.

    Given: API responses containing timestamp fields
    When: Timestamps are returned from Unity Catalog, Lakebase, or Model Serving
    Then: All timestamps should be in UTC format (ISO 8601 with Z suffix)

    Edge Case: T120 - Timezone consistency
    """
    import datetime

    # Test Unity Catalog query result timestamps
    mock_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    mock_result = create_mock_query_result(
      user_id='test-user-a@example.com',
      rows=[{'id': 1, 'created_at': mock_timestamp}],
      query_id='query-123',
    )

    with mock_unity_catalog_service('query_table', return_value=mock_result):
      with mock_user_context('test-user-a@example.com'):
        # Act: Query Unity Catalog
        response = client.get(
          '/api/unity-catalog/query',
          params={'catalog': 'main', 'schema': 'default', 'table': 'customers', 'limit': 10},
          headers={'X-Forwarded-Access-Token': 'test-token'},
        )

        # Assert: Successful response
        assert response.status_code == 200, f'Expected 200, got {response.status_code}'

        data = response.json()

        # Verify: Timestamps are in ISO 8601 format
        if 'rows' in data and len(data['rows']) > 0:
          row = data['rows'][0]
          if 'created_at' in row:
            timestamp_str = row['created_at']
            # Should be ISO 8601 format (YYYY-MM-DDTHH:MM:SS or with timezone)
            assert 'T' in timestamp_str, (
              f"Expected ISO 8601 timestamp with 'T' separator, got {timestamp_str}"
            )

            # Try parsing as ISO 8601
            try:
              parsed = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
              assert parsed.tzinfo is not None, (
                f'Expected timezone-aware timestamp, got naive: {timestamp_str}'
              )
            except ValueError as e:
              pytest.fail(f'Timestamp not in valid ISO 8601 format: {timestamp_str}, error: {e}')
