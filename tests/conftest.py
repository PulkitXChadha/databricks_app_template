"""Shared test fixtures and utilities for all tests.

This conftest.py provides reusable fixtures that can be used across
unit, contract, and integration tests to reduce duplication and improve
test performance.
"""

import pytest
from unittest.mock import Mock, MagicMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from uuid import uuid4
import time


# ============================================================================
# FastAPI Application Fixtures
# ============================================================================

def create_test_app() -> FastAPI:
    """Create a FastAPI app with middleware configured for testing."""
    app = FastAPI()

    # Add the same middleware as the main app
    @app.middleware("http")
    async def add_correlation_id(request: Request, call_next):
        """Inject correlation ID and authentication context into request."""
        # Extract correlation ID from X-Correlation-ID header or generate new UUID
        correlation_id = request.headers.get('X-Correlation-ID', str(uuid4()))

        # Store correlation ID in request state for access in endpoints
        request.state.correlation_id = correlation_id

        # Extract user access token from Databricks Apps header
        user_token = request.headers.get('X-Forwarded-Access-Token')

        # Set authentication context in request state
        request.state.user_token = user_token
        request.state.has_user_token = user_token is not None
        request.state.auth_mode = "obo" if user_token else "service_principal"
        request.state.user_id = None  # Will be set by endpoints if needed

        # Track request start time
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Add correlation ID to response headers
        response.headers['X-Correlation-ID'] = correlation_id

        return response

    # Include the routers with the correct structure - matching main app
    from server.routers import router
    app.include_router(router, prefix='/api', tags=['api'])

    return app


@pytest.fixture
def app():
    """Fixture that provides a configured FastAPI test app."""
    return create_test_app()


@pytest.fixture
def client(app):
    """Fixture that provides a test client for the app."""
    return TestClient(app)


@pytest.fixture
def test_client(app):
    """Alias for client fixture - provides test client for the app."""
    return TestClient(app)


# ============================================================================
# Mock Database Fixtures
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Reusable mock database session for Lakebase tests.
    
    Returns a fully configured mock session with query/filter_by/all chain.
    """
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_filter_by = MagicMock()
    mock_filter_by.all.return_value = []
    mock_filter_by.first.return_value = None
    mock_query.filter_by.return_value = mock_filter_by
    mock_session.query.return_value = mock_query
    return mock_session


@pytest.fixture
def mock_db_session_with_data():
    """Mock database session that returns sample preference data."""
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_filter_by = MagicMock()
    
    # Create mock preferences
    mock_pref1 = Mock()
    mock_pref1.to_dict.return_value = {
        'preference_key': 'theme',
        'preference_value': {'color': 'dark'}
    }
    mock_pref2 = Mock()
    mock_pref2.to_dict.return_value = {
        'preference_key': 'language',
        'preference_value': {'lang': 'en'}
    }
    
    mock_filter_by.all.return_value = [mock_pref1, mock_pref2]
    mock_filter_by.first.return_value = mock_pref1
    mock_query.filter_by.return_value = mock_filter_by
    mock_session.query.return_value = mock_query
    return mock_session


# ============================================================================
# Mock User Identity Fixtures
# ============================================================================

@pytest.fixture
def mock_user_identity():
    """Reusable mock user identity for testing.
    
    Returns a mock with standard user attributes.
    """
    user = Mock()
    user.user_id = "test@example.com"
    user.display_name = "Test User"
    user.workspace_url = "https://example.cloud.databricks.com"
    user.active = True
    return user


@pytest.fixture
def mock_user_identity_a():
    """Mock user identity for User A (for multi-user tests)."""
    user = Mock()
    user.user_id = "userA@example.com"
    user.display_name = "User A"
    user.workspace_url = "https://example.cloud.databricks.com"
    user.active = True
    return user


@pytest.fixture
def mock_user_identity_b():
    """Mock user identity for User B (for multi-user tests)."""
    user = Mock()
    user.user_id = "userB@example.com"
    user.display_name = "User B"
    user.workspace_url = "https://example.cloud.databricks.com"
    user.active = True
    return user


# ============================================================================
# Authentication Token Fixtures
# ============================================================================

@pytest.fixture
def user_token():
    """Mock user access token for testing."""
    return "test-user-token"


@pytest.fixture
def user_a_token():
    """Mock token for User A."""
    return "user-a-test-token"


@pytest.fixture
def user_b_token():
    """Mock token for User B."""
    return "user-b-test-token"


# ============================================================================
# Environment Configuration Fixtures
# ============================================================================

@pytest.fixture
def mock_env(monkeypatch):
    """Set up environment variables for Lakebase connection."""
    monkeypatch.setenv('PGHOST', 'test.lakebase.com')
    monkeypatch.setenv('PGDATABASE', 'test_db')
    monkeypatch.setenv('PGUSER', 'test_user')
    monkeypatch.setenv('PGPORT', '5432')
    monkeypatch.setenv('PGSSLMODE', 'require')


# ============================================================================
# Mock Databricks SDK Fixtures
# ============================================================================

@pytest.fixture
def mock_workspace_client():
    """Mock Databricks WorkspaceClient for testing."""
    client = Mock()
    client.current_user = Mock()
    client.current_user.me.return_value = Mock(
        user_name="test@example.com",
        display_name="Test User",
        active=True
    )
    return client


@pytest.fixture
def mock_model_serving_client():
    """Mock Databricks Model Serving client."""
    client = Mock()
    client.serving_endpoints = Mock()
    return client


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def correlation_id():
    """Generate a unique correlation ID for testing."""
    return str(uuid4())


@pytest.fixture
def sample_preferences():
    """Sample user preferences data for testing."""
    return [
        {
            'preference_key': 'theme',
            'preference_value': {'color': 'dark', 'mode': 'auto'}
        },
        {
            'preference_key': 'language',
            'preference_value': {'lang': 'en', 'region': 'US'}
        },
        {
            'preference_key': 'notifications',
            'preference_value': {'email': True, 'push': False}
        }
    ]

