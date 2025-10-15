"""Integration test fixtures for multi-user OBO authentication scenarios.

This conftest.py provides fixtures for testing with real user tokens from
multiple Databricks CLI profiles, enabling validation of user-level permission
enforcement and data isolation.
"""

import pytest
import os
from tests.conftest import get_test_user_token


# ============================================================================
# Multi-User Token Fixtures (Real tokens from Databricks CLI)
# ============================================================================

@pytest.fixture(scope="session")
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
        token = get_test_user_token("default")
        return token
    except RuntimeError as e:
        pytest.skip(f"Skipping test: {e}")


@pytest.fixture(scope="session")
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
        token = get_test_user_token("test-user-b")
        return token
    except RuntimeError as e:
        pytest.skip(f"Skipping test: User B profile not configured. {e}")


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
        get_test_user_token("default")
    except RuntimeError as e:
        pytest.skip(f"Databricks CLI not available: {e}")


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
    url = os.getenv("DATABRICKS_HOST")
    if not url:
        pytest.skip("DATABRICKS_HOST environment variable not set")
    return url


@pytest.fixture
def databricks_warehouse_id():
    """Get SQL Warehouse ID from environment.
    
    Returns:
        str: Warehouse ID from DATABRICKS_WAREHOUSE_ID environment variable
        
    Raises:
        pytest.skip: If DATABRICKS_WAREHOUSE_ID is not set
    """
    warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
    if not warehouse_id:
        pytest.skip("DATABRICKS_WAREHOUSE_ID environment variable not set")
    return warehouse_id


# ============================================================================
# Test Markers and Configuration
# ============================================================================

def pytest_configure(config):
    """Register custom markers for integration tests."""
    config.addinivalue_line(
        "markers",
        "requires_cli: Tests that require Databricks CLI authentication"
    )
    config.addinivalue_line(
        "markers",
        "multi_user: Tests that require multiple user accounts with different permissions"
    )
    config.addinivalue_line(
        "markers",
        "obo_only: Tests that validate OBO-only authentication (no fallback)"
    )

