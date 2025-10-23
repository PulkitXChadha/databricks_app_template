"""Integration test fixtures for multi-user OBO authentication scenarios.

This conftest.py provides fixtures for testing with real user tokens from
multiple Databricks CLI profiles, enabling validation of user-level permission
enforcement and data isolation.
"""

# CRITICAL: Set this BEFORE any model imports to disable schema for SQLite
import os

os.environ['USE_DB_SCHEMA'] = 'false'

import subprocess
from typing import Any, Dict

import pytest

# ============================================================================
# Real User Token Utilities
# ============================================================================


def get_test_user_token(profile: str = 'default') -> str:
  """Get real user token from Databricks CLI.

  This utility is used in integration tests to obtain valid user tokens
  for testing OBO authentication with real Databricks API calls.

  Args:
      profile: Databricks CLI profile name (default: "default")

  Returns:
      str: Valid user access token from Databricks CLI

  Raises:
      RuntimeError: If Databricks CLI is not installed or authentication fails

  Example:
      token = get_test_user_token("default")
      token_b = get_test_user_token("test-user-b")
  """
  try:
    result = subprocess.run(
      ['databricks', 'auth', 'token', '--profile', profile],
      capture_output=True,
      text=True,
      check=True,
      timeout=10,
    )
    token = result.stdout.strip()
    if not token:
      raise RuntimeError(f"Databricks CLI returned empty token for profile '{profile}'")
    return token
  except subprocess.CalledProcessError as e:
    error_msg = e.stderr if e.stderr else str(e)
    raise RuntimeError(
      f"Failed to get user token from Databricks CLI for profile '{profile}': {error_msg}"
    ) from e
  except FileNotFoundError:
    raise RuntimeError(
      'Databricks CLI not found. Install it with: '
      'curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh'
    )
  except subprocess.TimeoutExpired:
    raise RuntimeError(f"Databricks CLI timed out while getting token for profile '{profile}'")


# ============================================================================
# Multi-User Token Fixtures (Real tokens from Databricks CLI)
# ============================================================================


@pytest.fixture(scope='session')
def user_a_token_real():
  """Real user token for User A from Databricks CLI.

  Obtains token using the default Databricks CLI profile.
  This fixture has session scope to avoid repeated CLI calls.

  Requirements:
      - Databricks CLI must be installed
      - User must be authenticated: `databricks auth login`

  Returns:
      str: Valid user access token for User A

  Raises:
      pytest.skip: If Databricks CLI is not available or not authenticated
  """
  try:
    token = get_test_user_token('default')
    return token
  except RuntimeError as e:
    pytest.skip(f'Skipping test: {e}')


@pytest.fixture(scope='session')
def user_b_token_real():
  """Real user token for User B from Databricks CLI.

  Obtains token using the "test-user-b" Databricks CLI profile.
  This fixture enables testing with a second user with different permissions.

  Setup Instructions:
      1. Authenticate as second user:
         databricks auth login --profile test-user-b --host https://your-workspace.cloud.databricks.com

      2. Verify authentication:
         databricks auth token --profile test-user-b

  Requirements:
      - Databricks CLI profile "test-user-b" must be configured
      - User B must have different Unity Catalog permissions than User A

  Returns:
      str: Valid user access token for User B

  Raises:
      pytest.skip: If test-user-b profile is not configured
  """
  try:
    token = get_test_user_token('test-user-b')
    return token
  except RuntimeError as e:
    pytest.skip(f'Skipping test: User B profile not configured. {e}')


@pytest.fixture
def skip_if_no_databricks_cli():
  """Fixture that skips tests if Databricks CLI is not available.

  Use this as a dependency for integration tests that require real tokens:

  Example:
      def test_obo_authentication(skip_if_no_databricks_cli, user_a_token_real):
          # Test will be skipped if CLI not available
          pass
  """
  try:
    get_test_user_token('default')
  except RuntimeError as e:
    pytest.skip(f'Databricks CLI not available: {e}')


# ============================================================================
# Environment Configuration for Integration Tests
# ============================================================================


@pytest.fixture
def databricks_workspace_url():
  """Get Databricks workspace URL from environment.

  Returns:
      str: Workspace URL from DATABRICKS_HOST environment variable

  Raises:
      pytest.skip: If DATABRICKS_HOST is not set
  """
  url = os.getenv('DATABRICKS_HOST')
  if not url:
    pytest.skip('DATABRICKS_HOST environment variable not set')
  return url


@pytest.fixture
def databricks_warehouse_id():
  """Get SQL Warehouse ID from environment.

  Returns:
      str: Warehouse ID from DATABRICKS_WAREHOUSE_ID environment variable

  Raises:
      pytest.skip: If DATABRICKS_WAREHOUSE_ID is not set
  """
  warehouse_id = os.getenv('DATABRICKS_WAREHOUSE_ID')
  if not warehouse_id:
    pytest.skip('DATABRICKS_WAREHOUSE_ID environment variable not set')
  return warehouse_id


# ============================================================================
# Database Cleanup Fixtures (Autouse, Function-Scoped)
# ============================================================================


@pytest.fixture(autouse=True)
def cleanup_test_preferences():
  """Clean up test preferences before and after each test (function-scoped).

  This fixture automatically runs for every test to ensure user preferences
  created by test users are cleaned up, maintaining test isolation.

  Note: If database connection fails, cleanup is skipped gracefully.
  """
  try:
    from sqlalchemy.orm import Session

    from server.lib.database import get_db_session, is_lakebase_configured
    from server.models.user_preference import UserPreference
  except Exception:
    # If imports fail, skip cleanup
    yield
    return

  # Check if Lakebase is configured before attempting cleanup
  if not is_lakebase_configured():
    yield
    return

  # Define test user IDs
  test_user_ids = ['test-user-a@example.com', 'test-user-b@example.com']

  # Get database session
  try:
    session: Session = next(get_db_session())
  except Exception:
    # If database connection fails, skip cleanup
    yield
    return

  try:
    # Cleanup before test
    try:
      session.query(UserPreference).filter(UserPreference.user_id.in_(test_user_ids)).delete(
        synchronize_session=False
      )
      session.commit()
    except Exception:
      # Rollback and continue if cleanup fails
      session.rollback()

    yield  # Run test
  finally:
    # Cleanup after test
    try:
      session.query(UserPreference).filter(UserPreference.user_id.in_(test_user_ids)).delete(
        synchronize_session=False
      )
      session.commit()
    except Exception:
      # Rollback on error
      try:
        session.rollback()
      except Exception:
        pass
    finally:
      try:
        session.close()
      except Exception:
        pass


@pytest.fixture(autouse=True)
def cleanup_inference_logs():
  """Clean up inference logs before and after each test (function-scoped).

  This fixture automatically runs for every test to ensure model inference
  logs created by test users are cleaned up, maintaining test isolation.

  Note: If ModelInferenceLog database model doesn't exist yet or database
  connection fails, cleanup is skipped gracefully.
  """
  try:
    from sqlalchemy.orm import Session

    from server.lib.database import get_db_session, is_lakebase_configured

    # Try to import the model - skip cleanup if it doesn't exist
    try:
      from server.models.model_inference import ModelInferenceLog
    except (ImportError, AttributeError):
      # Model doesn't exist yet, skip cleanup
      yield
      return
  except Exception:
    # Database not configured, skip cleanup
    yield
    return

  # Check if Lakebase is configured before attempting cleanup
  if not is_lakebase_configured():
    yield
    return

  # Define test user IDs
  test_user_ids = ['test-user-a@example.com', 'test-user-b@example.com']

  # Get database session
  try:
    session: Session = next(get_db_session())
  except Exception:
    # If database connection fails, skip cleanup
    yield
    return

  try:
    # Cleanup before test
    try:
      session.query(ModelInferenceLog).filter(ModelInferenceLog.user_id.in_(test_user_ids)).delete(
        synchronize_session=False
      )
      session.commit()
    except Exception:
      # Rollback and continue if cleanup fails
      session.rollback()

    yield  # Run test
  finally:
    # Cleanup after test
    try:
      session.query(ModelInferenceLog).filter(ModelInferenceLog.user_id.in_(test_user_ids)).delete(
        synchronize_session=False
      )
      session.commit()
    except Exception:
      # Rollback on error
      try:
        session.rollback()
      except Exception:
        pass
    finally:
      try:
        session.close()
      except Exception:
        pass


@pytest.fixture(autouse=True)
def cleanup_schema_events():
  """Clean up schema detection events before and after each test (function-scoped).

  This fixture automatically runs for every test to ensure schema detection
  events created by test users are cleaned up, maintaining test isolation.

  Note: If database connection fails, cleanup is skipped gracefully.
  """
  try:
    from sqlalchemy.orm import Session

    from server.lib.database import get_db_session, is_lakebase_configured
    from server.models.schema_detection_event import SchemaDetectionEvent
  except Exception:
    # If imports fail, skip cleanup
    yield
    return

  # Check if Lakebase is configured before attempting cleanup
  if not is_lakebase_configured():
    yield
    return

  # Define test user IDs
  test_user_ids = ['test-user-a@example.com', 'test-user-b@example.com']

  # Get database session
  try:
    session: Session = next(get_db_session())
  except Exception:
    # If database connection fails, skip cleanup
    yield
    return

  try:
    # Cleanup before test
    try:
      session.query(SchemaDetectionEvent).filter(
        SchemaDetectionEvent.user_id.in_(test_user_ids)
      ).delete(synchronize_session=False)
      session.commit()
    except Exception:
      # Rollback and continue if cleanup fails
      session.rollback()

    yield  # Run test
  finally:
    # Cleanup after test
    try:
      session.query(SchemaDetectionEvent).filter(
        SchemaDetectionEvent.user_id.in_(test_user_ids)
      ).delete(synchronize_session=False)
      session.commit()
    except Exception:
      # Rollback on error
      try:
        session.rollback()
      except Exception:
        pass
    finally:
      try:
        session.close()
      except Exception:
        pass


# ============================================================================
# Test Database Setup (In-Memory SQLite for Integration Tests)
# ============================================================================


@pytest.fixture(scope='session')
def test_db_engine():
  """Create an in-memory SQLite database engine for integration tests.

  This provides a real database for integration testing without requiring
  Lakebase configuration. Tables are created from SQLAlchemy models.

  Uses shared cache mode so all connections see the same database.

  Returns:
      SQLAlchemy Engine configured for in-memory SQLite
  """
  from sqlalchemy import create_engine, pool

  from server.models.user_preference import Base as PreferenceBase

  # CRITICAL: Use file::memory:?cache=shared to share in-memory DB across connections
  # Also use StaticPool to ensure all sessions use the same connection
  engine = create_engine(
    'sqlite:///:memory:',
    connect_args={'check_same_thread': False},
    poolclass=pool.StaticPool,  # CRITICAL: Reuse same connection for all sessions
    echo=False,  # Set to True for SQL debugging
  )

  # Create all tables from models
  PreferenceBase.metadata.create_all(engine)

  # Try to create other model tables if they exist
  try:
    from server.models.model_inference import Base as InferenceBase

    InferenceBase.metadata.create_all(engine)
  except (ImportError, AttributeError):
    pass

  try:
    from server.models.schema_detection_event import Base as SchemaBase

    SchemaBase.metadata.create_all(engine)
  except (ImportError, AttributeError):
    pass

  yield engine

  # Cleanup
  engine.dispose()


@pytest.fixture(scope='function')
def test_db_session(test_db_engine):
  """Create a database session for each test function.

  Args:
      test_db_engine: Session-scoped test database engine

  Yields:
      SQLAlchemy Session for test
  """
  from sqlalchemy.orm import sessionmaker

  SessionFactory = sessionmaker(bind=test_db_engine)
  session = SessionFactory()

  yield session

  # Rollback and close after test
  session.rollback()
  session.close()


@pytest.fixture(autouse=True)
def mock_get_db_session(test_db_session, monkeypatch):
  """Mock get_db_session to return test database session.

  This fixture automatically patches the database session for all integration tests,
  allowing them to use the in-memory test database instead of Lakebase.

  Args:
      test_db_session: Function-scoped test database session
      monkeypatch: Pytest monkeypatch fixture
  """
  from server.lib import database

  def mock_session_generator():
    """Generator that yields the test session."""
    yield test_db_session

  # Patch get_db_session to return our test session
  monkeypatch.setattr(database, 'get_db_session', mock_session_generator)

  # Also mock is_lakebase_configured to return True (so service doesn't skip)
  monkeypatch.setattr(database, 'is_lakebase_configured', lambda: True)


# ============================================================================
# Test Data Factory Functions
# ============================================================================


def create_test_preference(user_id: str, key: str, value: Dict[str, Any]) -> Dict[str, Any]:
  """Factory function to create test preference data.

  Args:
      user_id: User identifier (e.g., "test-user-a@example.com")
      key: Preference key (e.g., "theme", "language")
      value: Preference value as dictionary

  Returns:
      dict: Preference data ready for API request
  """
  return {
    'preference_key': key,
    'preference_value': value,
    # Note: user_id will be injected by service layer from auth context
  }


def create_test_inference_log(
  user_id: str,
  endpoint_name: str,
  request_payload: Dict[str, Any],
  response_payload: Dict[str, Any],
  status: str = 'SUCCESS',
  duration_ms: int = 100,
) -> Dict[str, Any]:
  """Factory function to create test inference log data.

  Args:
      user_id: User identifier
      endpoint_name: Model endpoint name
      request_payload: Input sent to model
      response_payload: Output from model
      status: Request status ("SUCCESS", "ERROR", "TIMEOUT")
      duration_ms: Request duration in milliseconds

  Returns:
      dict: Inference log data ready for database insertion
  """
  return {
    'user_id': user_id,
    'endpoint_name': endpoint_name,
    'request_payload': request_payload,
    'response_payload': response_payload,
    'status': status,
    'duration_ms': duration_ms,
  }


# ============================================================================
# Mock Service Patching Utilities
# ============================================================================


@pytest.fixture
def mock_workspace_client():
  """Mock Databricks WorkspaceClient for integration tests.

  Returns a configured mock client with common methods stubbed.
  """
  from unittest.mock import MagicMock, Mock

  client = Mock()
  client.current_user = Mock()
  client.current_user.me = MagicMock(
    return_value=Mock(user_name='test-user-a@example.com', display_name='Test User A', active=True)
  )
  return client


@pytest.fixture
def mock_lakebase_session():
  """Mock Lakebase database session for testing.

  Returns a configured mock session with query/filter_by/all chain.
  """
  from unittest.mock import MagicMock

  mock_session = MagicMock()
  mock_query = MagicMock()
  mock_filter_by = MagicMock()
  mock_filter_by.all.return_value = []
  mock_filter_by.first.return_value = None
  mock_query.filter_by.return_value = mock_filter_by
  mock_session.query.return_value = mock_query
  return mock_session


# ============================================================================
# Mock Catalog Metadata Fixtures (Session-Scoped)
# ============================================================================


@pytest.fixture(scope='session')
def mock_catalog_metadata():
  """Mock Unity Catalog metadata (session-scoped, read-only).

  Provides catalog, schema, and table structure for testing Unity Catalog
  operations. This data is read-only and shared across all tests.

  Returns:
      dict: Catalog metadata with catalogs, schemas, tables, permissions
  """
  return {
    'catalogs': ['main', 'samples'],
    'schemas': {'main': ['default', 'sales'], 'samples': ['tpch', 'nyctaxi']},
    'tables': {
      'main.default': [
        {
          'catalog_name': 'main',
          'schema_name': 'default',
          'table_name': 'customers',
          'columns': [
            {'name': 'customer_id', 'data_type': 'bigint', 'nullable': False},
            {'name': 'name', 'data_type': 'string', 'nullable': True},
            {'name': 'email', 'data_type': 'string', 'nullable': True},
          ],
          'owner': 'admin',
          'table_type': 'MANAGED',
        },
        {
          'catalog_name': 'main',
          'schema_name': 'default',
          'table_name': 'orders',
          'columns': [
            {'name': 'order_id', 'data_type': 'bigint', 'nullable': False},
            {'name': 'customer_id', 'data_type': 'bigint', 'nullable': False},
            {'name': 'amount', 'data_type': 'decimal(10,2)', 'nullable': True},
          ],
          'owner': 'admin',
          'table_type': 'MANAGED',
        },
      ],
      'samples.tpch': [
        {
          'catalog_name': 'samples',
          'schema_name': 'tpch',
          'table_name': 'nation',
          'columns': [
            {'name': 'n_nationkey', 'data_type': 'bigint', 'nullable': False},
            {'name': 'n_name', 'data_type': 'string', 'nullable': True},
          ],
          'owner': 'system',
          'table_type': 'EXTERNAL',
        }
      ],
    },
    'permissions': {
      'test-user-a@example.com': {'main.default.customers': 'READ', 'main.default.orders': 'READ'},
      'test-user-b@example.com': {'samples.tpch.nation': 'READ'},
    },
  }


@pytest.fixture(scope='session')
def mock_model_endpoints():
  """Mock model serving endpoints (session-scoped).

  Provides endpoint configurations for testing Model Serving operations.

  Returns:
      list: List of mock model endpoints with metadata
  """
  return [
    {
      'name': 'claude-sonnet-4',
      'endpoint_type': 'FOUNDATION_MODEL_API',
      'state': {'ready': 'READY'},
      'served_entities': [
        {'name': 'claude-sonnet-4', 'entity_name': 'claude-sonnet-4', 'entity_version': 'latest'}
      ],
      'task': 'llm/v1/chat',
      'creator': 'Databricks',
    },
    {
      'name': 'custom-classifier',
      'endpoint_type': 'MODEL_SERVING',
      'state': {'ready': 'READY'},
      'served_entities': [
        {
          'name': 'custom-classifier-v1',
          'entity_name': 'models:/custom-classifier/1',
          'entity_version': '1',
        }
      ],
      'task': 'custom',
      'creator': 'test-user-a@example.com',
    },
  ]


@pytest.fixture(scope='session')
def mock_detected_schemas():
  """Mock detected model input schemas (session-scoped).

  Provides schema definitions for model endpoints.

  Returns:
      dict: Endpoint name -> schema definition mapping
  """
  return {
    'claude-sonnet-4': {
      'schema_type': 'chat_format',
      'parameters': [
        {
          'name': 'messages',
          'type': 'array',
          'required': True,
          'description': 'Array of chat messages',
        },
        {
          'name': 'max_tokens',
          'type': 'integer',
          'required': False,
          'description': 'Maximum tokens to generate',
        },
      ],
      'example_json': {
        'messages': [{'role': 'user', 'content': 'Hello, world!'}],
        'max_tokens': 1000,
      },
    },
    'custom-classifier': {
      'schema_type': 'mlflow_schema',
      'parameters': [{'name': 'text', 'type': 'string', 'required': True}],
      'example_json': {'inputs': [{'text': 'Sample text for classification'}]},
    },
  }


@pytest.fixture(scope='session')
def mock_table_data():
  """Mock table data for query testing (session-scoped).

  Provides sample rows for table queries.

  Returns:
      dict: Table key -> rows and total count mapping
  """
  return {
    'main.default.customers': {
      'rows': [
        {'customer_id': 1, 'name': 'Alice', 'email': 'alice@example.com'},
        {'customer_id': 2, 'name': 'Bob', 'email': 'bob@example.com'},
        {'customer_id': 3, 'name': 'Charlie', 'email': 'charlie@example.com'},
      ],
      'total_count': 3,
    },
    'samples.tpch.nation': {
      'rows': [
        {'n_nationkey': 0, 'n_name': 'ALGERIA'},
        {'n_nationkey': 1, 'n_name': 'ARGENTINA'},
        {'n_nationkey': 2, 'n_name': 'BRAZIL'},
      ],
      'total_count': 3,
    },
  }


# ============================================================================
# Test Markers and Configuration
# ============================================================================


def pytest_configure(config):
  """Register custom markers for integration tests."""
  config.addinivalue_line(
    'markers', 'requires_cli: Tests that require Databricks CLI authentication'
  )
  config.addinivalue_line(
    'markers', 'multi_user: Tests that require multiple user accounts with different permissions'
  )
  config.addinivalue_line(
    'markers', 'obo_only: Tests that validate OBO-only authentication (no fallback)'
  )
