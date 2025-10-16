"""Shared test fixtures and utilities for all tests.

This conftest.py provides reusable fixtures that can be used across
unit, contract, and integration tests to reduce duplication and improve
test performance.
"""

import sys
import os
from pathlib import Path

# CRITICAL: Ensure the correct project root is first in sys.path
# This prevents importing from other projects with similar module names
project_root = str(Path(__file__).parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)
elif sys.path[0] != project_root:
    sys.path.remove(project_root)
    sys.path.insert(0, project_root)

import pytest
from unittest.mock import Mock, MagicMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from uuid import uuid4
import time
import subprocess
from typing import Optional


# ============================================================================
# FastAPI Application Fixtures
# ============================================================================

def create_test_app() -> FastAPI:
    """Create a FastAPI app with middleware configured for testing."""
    app = FastAPI()

    # Add the same middleware as the main app
    @app.middleware("http")
    async def add_correlation_id(request: Request, call_next):
        """Inject correlation ID and authentication context into request (OBO-only)."""
        # Extract correlation ID from X-Correlation-ID header or generate new UUID
        correlation_id = request.headers.get('X-Correlation-ID', str(uuid4()))

        # Store correlation ID in request state for access in endpoints
        request.state.correlation_id = correlation_id

        # Extract user access token from Databricks Apps header
        user_token = request.headers.get('X-Forwarded-Access-Token')

        # Set authentication context in request state (OBO-only)
        request.state.user_token = user_token
        request.state.user_id = None  # Will be set by endpoints if needed
        
        # Set auth mode based on token presence
        if user_token:
            request.state.auth_mode = "obo"
            request.state.has_user_token = True
        else:
            request.state.auth_mode = "service_principal"
            request.state.has_user_token = False

        # Track request start time
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Add correlation ID to response headers
        response.headers['X-Correlation-ID'] = correlation_id

        return response

    # Add health endpoint (public, no auth required)
    @app.get('/health')
    async def health():
        """Health check endpoint."""
        return {'status': 'healthy'}
    
    @app.get('/api/health')
    async def health_api():
        """Health check endpoint under /api prefix."""
        return {'status': 'healthy'}
    
    # Add metrics endpoint (requires auth)
    @app.get('/metrics')
    async def metrics(request: Request):
        """Prometheus metrics endpoint."""
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        from fastapi.responses import Response
        from server.lib.auth import get_user_token
        
        # Require authentication for metrics endpoint
        user_token = await get_user_token(request)
        
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    
    @app.get('/api/metrics')
    async def metrics_api(request: Request):
        """Prometheus metrics endpoint under /api prefix."""
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        from fastapi.responses import Response
        from server.lib.auth import get_user_token
        
        # Require authentication for metrics endpoint
        user_token = await get_user_token(request)
        
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    
    # Include the routers with the correct structure - matching main app
    from server.routers import router
    app.include_router(router, prefix='/api', tags=['api'])

    return app


@pytest.fixture
def app():
    """Fixture that provides the real FastAPI app for testing."""
    # Use create_test_app() which includes all the same routes but without static files
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
# Real User Token Utilities (for integration tests)
# ============================================================================

def get_test_user_token(profile: str = "default") -> str:
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
            ["databricks", "auth", "token", "--profile", profile],
            capture_output=True,
            text=True,
            check=True,
            timeout=10
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
            "Databricks CLI not found. Install it with: "
            "curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"Databricks CLI timed out while getting token for profile '{profile}'"
        )


@pytest.fixture
def get_test_user_token_fixture():
    """Pytest fixture that provides the get_test_user_token utility function.
    
    Use this fixture when you need to dynamically obtain tokens in tests:
    
    Example:
        def test_something(get_test_user_token_fixture):
            token = get_test_user_token_fixture("my-profile")
    """
    return get_test_user_token


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

@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    """Reset the circuit breaker before each test."""
    from server.lib.auth import auth_circuit_breaker
    auth_circuit_breaker.consecutive_failures = 0
    auth_circuit_breaker.state = "closed"
    auth_circuit_breaker.last_failure_time = None
    yield


@pytest.fixture
def correlation_id():
    """Generate a unique correlation ID for testing."""
    return str(uuid4())


@pytest.fixture
def mock_auth_headers():
    """Provide mock authentication headers for contract tests.
    
    This fixture provides the X-Forwarded-Access-Token header that would
    normally be provided by Databricks Apps in production.
    """
    return {
        "X-Forwarded-Access-Token": "mock-user-token-for-testing"
    }


@pytest.fixture
def mock_user_auth(monkeypatch):
    """Mock user authentication for contract tests.
    
    This fixture mocks the entire authentication flow so contract tests
    can focus on testing API validation and business logic without
    needing real Databricks credentials.
    """
    from unittest.mock import AsyncMock, Mock
    from server.models.user_session import UserIdentity
    from datetime import datetime
    
    # Mock UserService.get_user_info to return a test user
    async def mock_get_user_info(self):
        return UserIdentity(
            user_id="test@example.com",
            display_name="Test User",
            active=True,
            extracted_at=datetime.utcnow()
        )
    
    # Mock UserService.get_user_id to return test user ID
    async def mock_get_user_id(self):
        if not self.user_token:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="User authentication required")
        return "test@example.com"
    
    # Mock is_lakebase_configured to return True for tests
    def mock_is_lakebase_configured():
        return True
    
    # Patch the methods
    monkeypatch.setattr(
        "server.services.user_service.UserService.get_user_info",
        mock_get_user_info
    )
    monkeypatch.setattr(
        "server.services.user_service.UserService.get_user_id",
        mock_get_user_id
    )
    monkeypatch.setattr(
        "server.lib.database.is_lakebase_configured",
        mock_is_lakebase_configured
    )
    
    # Set Lakebase environment variables for tests
    monkeypatch.setenv("PGHOST", "test-lakebase-host")
    monkeypatch.setenv("LAKEBASE_DATABASE", "test_database")
    
    yield


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

