"""
Unit tests for admin service workspace admin check.

Tests admin detection logic per FR-011 with various scenarios.
Following TDD RED-GREEN-REFACTOR: These tests MUST FAIL initially.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import os


# ============================================================================
# T016: Unit test for admin service workspace admin check
# ============================================================================

def test_is_workspace_admin_with_default_admin_groups():
    """
    Test admin detection with default ADMIN_GROUPS env var.
    
    Scenario 1: Default admin groups test with three group variations.
    
    Expected to FAIL initially (RED phase) - is_workspace_admin() may not exist.
    """
    from server.services.admin_service import is_workspace_admin
    
    # Test with "admins" group
    user_info_admins = {
        "id": "12345",
        "userName": "admin@example.com",
        "groups": [
            {"display": "users", "value": "group-1"},
            {"display": "admins", "value": "group-2"}  # Should match
        ]
    }
    
    assert is_workspace_admin(user_info_admins) is True, "Should detect 'admins' group"
    
    # Test with "workspace_admins" group
    user_info_workspace_admins = {
        "id": "12345",
        "userName": "admin@example.com",
        "groups": [
            {"display": "users", "value": "group-1"},
            {"display": "workspace_admins", "value": "group-2"}  # Should match
        ]
    }
    
    assert is_workspace_admin(user_info_workspace_admins) is True, "Should detect 'workspace_admins' group"
    
    # Test with "administrators" group
    user_info_administrators = {
        "id": "12345",
        "userName": "admin@example.com",
        "groups": [
            {"display": "users", "value": "group-1"},
            {"display": "administrators", "value": "group-2"}  # Should match
        ]
    }
    
    assert is_workspace_admin(user_info_administrators) is True, "Should detect 'administrators' group"


def test_is_workspace_admin_with_custom_admin_groups():
    """
    Test admin detection with custom ADMIN_GROUPS env var.
    
    Scenario 2: Custom ADMIN_GROUPS test with case-insensitive matching.
    
    Expected to FAIL initially (RED phase) - custom group configuration may not work.
    """
    from server.services.admin_service import is_workspace_admin
    
    # Set custom admin groups
    original_env = os.environ.get('ADMIN_GROUPS')
    os.environ['ADMIN_GROUPS'] = 'custom_admins,super_users'
    
    try:
        # Test with custom admin group
        user_info_custom = {
            "id": "12345",
            "userName": "admin@example.com",
            "groups": [
                {"display": "users", "value": "group-1"},
                {"display": "custom_admins", "value": "group-2"}  # Should match custom group
            ]
        }
        
        assert is_workspace_admin(user_info_custom) is True, "Should detect custom 'custom_admins' group"
        
        # Test with another custom group
        user_info_super = {
            "id": "12345",
            "userName": "admin@example.com",
            "groups": [
                {"display": "super_users", "value": "group-1"}  # Should match
            ]
        }
        
        assert is_workspace_admin(user_info_super) is True, "Should detect custom 'super_users' group"
        
    finally:
        # Restore original env var
        if original_env is not None:
            os.environ['ADMIN_GROUPS'] = original_env
        else:
            os.environ.pop('ADMIN_GROUPS', None)


def test_is_workspace_admin_case_insensitive_matching():
    """
    Test that admin group matching is case-insensitive per FR-011.
    
    Expected to FAIL initially (RED phase) - case-insensitive logic may not exist.
    """
    from server.services.admin_service import is_workspace_admin
    
    # Test with different case variations
    case_variations = ["Admins", "ADMINS", "AdMiNs", "administrators", "ADMINISTRATORS"]
    
    for group_name in case_variations:
        user_info = {
            "id": "12345",
            "userName": "admin@example.com",
            "groups": [
                {"display": group_name, "value": "group-1"}
            ]
        }
        
        assert is_workspace_admin(user_info) is True, f"Should match '{group_name}' (case-insensitive)"


def test_is_workspace_admin_returns_false_for_non_admin():
    """
    Test that non-admin users are correctly identified.
    
    Expected to FAIL initially (RED phase).
    """
    from server.services.admin_service import is_workspace_admin
    
    user_info_non_admin = {
        "id": "12345",
        "userName": "user@example.com",
        "groups": [
            {"display": "users", "value": "group-1"},
            {"display": "developers", "value": "group-2"}
        ]
    }
    
    assert is_workspace_admin(user_info_non_admin) is False, "Should return False for non-admin"


def test_is_workspace_admin_handles_missing_groups():
    """
    Test that missing groups field returns False (safe default).
    
    Expected to FAIL initially (RED phase) - edge case handling may not exist.
    """
    from server.services.admin_service import is_workspace_admin
    
    # Test with missing groups field
    user_info_no_groups = {
        "id": "12345",
        "userName": "user@example.com"
    }
    
    assert is_workspace_admin(user_info_no_groups) is False, "Should return False when groups missing"


def test_is_workspace_admin_handles_empty_groups():
    """
    Test that empty groups array returns False.
    
    Expected to FAIL initially (RED phase).
    """
    from server.services.admin_service import is_workspace_admin
    
    user_info_empty_groups = {
        "id": "12345",
        "userName": "user@example.com",
        "groups": []
    }
    
    assert is_workspace_admin(user_info_empty_groups) is False, "Should return False for empty groups"


def test_is_workspace_admin_handles_missing_display_field():
    """
    Test that groups with missing display field are skipped safely.
    
    Expected to FAIL initially (RED phase).
    """
    from server.services.admin_service import is_workspace_admin
    
    user_info_malformed = {
        "id": "12345",
        "userName": "user@example.com",
        "groups": [
            {"value": "group-1"},  # Missing display field
            {"display": "users", "value": "group-2"}
        ]
    }
    
    assert is_workspace_admin(user_info_malformed) is False, "Should handle missing display field gracefully"


# ============================================================================
# T016.1: Unit test for admin cache TTL expiration
# ============================================================================

@pytest.mark.asyncio
async def test_admin_cache_ttl_expiration():
    """
    Test that cached admin status expires after 5 minutes (300 seconds) and triggers new API call.
    
    Expected to FAIL initially (RED phase) - caching may not be implemented.
    """
    # This test will need to be implemented after the admin service is created
    # For now, we define the expected behavior
    
    # TODO: Implement test once admin service caching is in place
    # Expected behavior:
    # 1. First call: Queries Databricks API, caches result
    # 2. Second call within 5 min: Returns cached result (no API call)
    # 3. Third call after 5 min: Queries API again (cache expired)
    
    pytest.skip("Test requires async admin service implementation")


# ============================================================================
# T016.5: Security test for privilege escalation attempts
# ============================================================================

def test_admin_check_prevents_privilege_escalation():
    """
    Test that non-admin cannot bypass admin check through various attack vectors.
    
    Expected to FAIL initially (RED phase) - security validation may not exist.
    """
    from server.services.admin_service import is_workspace_admin
    
    # Attack vector 1: Token manipulation with fake admin group
    malicious_user_info = {
        "id": "12345",
        "userName": "attacker@example.com",
        "groups": [
            {"display": "users", "value": "group-1"},
            {"display": "fake_admins", "value": "group-2"}  # Should NOT match
        ]
    }
    
    assert is_workspace_admin(malicious_user_info) is False, "Should reject fake admin group"
    
    # Attack vector 2: Injection attempt in group name
    injection_user_info = {
        "id": "12345",
        "userName": "attacker@example.com",
        "groups": [
            {"display": "admins'; DROP TABLE users; --", "value": "group-1"}
        ]
    }
    
    assert is_workspace_admin(injection_user_info) is False, "Should reject SQL injection attempt"


# ============================================================================
# T016.6: Unit test for admin service resilience
# ============================================================================

@pytest.mark.asyncio
async def test_admin_service_returns_503_on_api_failure():
    """
    Test that 503 Service Unavailable is returned when Databricks API call fails.
    
    Validates edge case from spec.md:L152-155.
    
    Expected to FAIL initially (RED phase) - error handling may not exist.
    """
    # This test will verify that API failures are handled gracefully
    # For now, we define the expected behavior
    
    # TODO: Implement test once admin service API integration is complete
    # Expected behavior:
    # 1. Mock Databricks API to raise exception
    # 2. Call admin check
    # 3. Verify HTTPException with status_code=503 is raised
    
    pytest.skip("Test requires async admin service with API integration")


# ============================================================================
# T016.9: Unit test for admin cache failure handling
# ============================================================================

@pytest.mark.asyncio
async def test_admin_cache_does_not_serve_stale_results():
    """
    Test that cache doesn't serve stale results when Databricks API starts returning errors.
    
    Admin status should be re-checked on cache expiry even if previous calls succeeded.
    
    Expected to FAIL initially (RED phase) - cache invalidation may not handle error states.
    """
    # TODO: Implement test once caching with error handling is complete
    # Expected behavior:
    # 1. First call: Returns True (admin), caches result
    # 2. After cache expiry: API fails
    # 3. Should raise error (not return stale cached True)
    
    pytest.skip("Test requires cache with error state handling")


# ============================================================================
# Helper Functions for Testing
# ============================================================================

def create_mock_databricks_user(user_name: str, groups: list) -> dict:
    """Helper to create mock Databricks user info for testing"""
    return {
        "id": "mock-id",
        "userName": user_name,
        "displayName": user_name,
        "active": True,
        "groups": groups
    }

