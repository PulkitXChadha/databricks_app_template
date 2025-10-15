"""Contract tests for UnityCatalogService OBO-only authentication.

These tests validate that UnityCatalogService correctly implements OBO-only authentication:
- Service REQUIRES user_token parameter (not Optional)
- Service raises ValueError if user_token is None or empty
- Service creates WorkspaceClient with auth_type='pat' only

Test Requirements (from contracts/service_authentication.yaml):
- UnityCatalogService(user_token=None) raises ValueError
- UnityCatalogService(user_token="mock-token") succeeds with OBO client
- list_catalogs() returns different results for different users
- No service principal fallback
"""

import os
import pytest
from unittest.mock import Mock, patch, AsyncMock
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import CatalogInfo

from server.services.unity_catalog_service import UnityCatalogService

# Mark all tests in this module as contract tests
pytestmark = pytest.mark.contract


class TestUnityCatalogServiceAuthentication:
    """Test UnityCatalogService OBO-only authentication patterns."""
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Set up environment variables for testing."""
        monkeypatch.setenv('DATABRICKS_HOST', 'https://test.cloud.databricks.com')
        monkeypatch.setenv('DATABRICKS_WAREHOUSE_ID', 'test-warehouse-id')
    
    def test_service_requires_user_token_raises_value_error_on_none(self, mock_env):
        """Test that UnityCatalogService raises ValueError when user_token is None."""
        with pytest.raises(ValueError, match="user_token is required"):
            UnityCatalogService(user_token=None)
    
    def test_service_requires_user_token_raises_value_error_on_empty_string(self, mock_env):
        """Test that UnityCatalogService raises ValueError when user_token is empty string."""
        with pytest.raises(ValueError, match="user_token is required"):
            UnityCatalogService(user_token="")
    
    def test_service_initialization_succeeds_with_valid_token(self, mock_env):
        """Test that UnityCatalogService initializes successfully with valid token."""
        with patch('server.services.unity_catalog_service.WorkspaceClient') as mock_client_class:
            mock_client = Mock(spec=WorkspaceClient)
            mock_client_class.return_value = mock_client
            
            # Should not raise exception
            service = UnityCatalogService(user_token="mock-token-12345")
            
            assert service.user_token == "mock-token-12345"
            assert service.workspace_url == 'https://test.cloud.databricks.com'
    
    def test_service_creates_workspace_client_with_obo_auth(self, mock_env):
        """Test that UnityCatalogService creates WorkspaceClient with auth_type='pat' only."""
        user_token = "test-user-token-12345"
        
        with patch('server.services.unity_catalog_service.WorkspaceClient') as mock_client_class:
            # Create mock client instance
            mock_client = Mock(spec=WorkspaceClient)
            mock_client_class.return_value = mock_client
            
            # Initialize service with user token
            service = UnityCatalogService(user_token=user_token)
            
            # Verify WorkspaceClient was created with correct parameters
            mock_client_class.assert_called_once()
            call_kwargs = mock_client_class.call_args[1]
            
            # Verify OBO authentication parameters
            assert 'host' in call_kwargs, "host parameter required"
            assert call_kwargs['host'] == 'https://test.cloud.databricks.com'
            assert 'token' in call_kwargs, "token parameter required"
            assert call_kwargs['token'] == user_token
            assert 'auth_type' in call_kwargs, "auth_type parameter required"
            assert call_kwargs['auth_type'] == "pat", "auth_type must be 'pat' for OBO"
            
            # Verify NO service principal parameters present
            assert 'client_id' not in call_kwargs, "client_id should not be present (no service principal)"
            assert 'client_secret' not in call_kwargs, "client_secret should not be present (no service principal)"
    
    @pytest.mark.asyncio
    async def test_list_catalogs_respects_user_permissions(self, mock_env):
        """Test that list_catalogs() returns different results for different users (permission enforcement)."""
        with patch('server.services.unity_catalog_service.WorkspaceClient') as mock_client_class:
            # Create mock client instances for two different users
            mock_client_user_a = Mock(spec=WorkspaceClient)
            mock_client_user_b = Mock(spec=WorkspaceClient)
            
            # Mock catalog lists for two different users
            # User A has access to 'main' and 'shared' catalogs
            mock_client_user_a.catalogs.list.return_value = [
                CatalogInfo(name='main'),
                CatalogInfo(name='shared')
            ]
            
            # User B only has access to 'main' catalog
            mock_client_user_b.catalogs.list.return_value = [
                CatalogInfo(name='main')
            ]
            
            # Test User A
            mock_client_class.return_value = mock_client_user_a
            service_a = UnityCatalogService(user_token="user-a-token")
            catalogs_a = await service_a.list_catalogs(user_id="user-a@example.com")
            
            assert len(catalogs_a) == 2, "User A should see 2 catalogs"
            assert 'main' in catalogs_a, "User A should see 'main' catalog"
            assert 'shared' in catalogs_a, "User A should see 'shared' catalog"
            
            # Test User B
            mock_client_class.return_value = mock_client_user_b
            service_b = UnityCatalogService(user_token="user-b-token")
            catalogs_b = await service_b.list_catalogs(user_id="user-b@example.com")
            
            assert len(catalogs_b) == 1, "User B should see only 1 catalog"
            assert 'main' in catalogs_b, "User B should see 'main' catalog"
            assert 'shared' not in catalogs_b, "User B should not see 'shared' catalog (no permission)"
            
            # Verify different users get different results
            assert catalogs_a != catalogs_b, "Different users should see different catalog lists"


class TestUnityCatalogServiceQueries:
    """Test that Unity Catalog queries respect user permissions."""
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Set up environment variables for testing."""
        monkeypatch.setenv('DATABRICKS_HOST', 'https://test.cloud.databricks.com')
        monkeypatch.setenv('DATABRICKS_WAREHOUSE_ID', 'test-warehouse-id')
    
    @pytest.mark.asyncio
    async def test_list_schemas_respects_permissions(self, mock_env):
        """Test that list_schemas() only returns schemas the user has access to."""
        from databricks.sdk.service.catalog import SchemaInfo
        
        with patch('server.services.unity_catalog_service.WorkspaceClient') as mock_client_class:
            mock_client = Mock(spec=WorkspaceClient)
            mock_client_class.return_value = mock_client
            
            # Mock schemas that user has access to
            mock_client.schemas.list.return_value = [
                SchemaInfo(name='default'),
                SchemaInfo(name='analytics')
            ]
            
            service = UnityCatalogService(user_token="test-token")
            schemas = await service.list_schemas(catalog='main', user_id='user@example.com')
            
            assert len(schemas) == 2
            assert 'default' in schemas
            assert 'analytics' in schemas
            
            # Verify list was called with correct catalog
            mock_client.schemas.list.assert_called_once_with(catalog_name='main')
    
    @pytest.mark.asyncio
    async def test_list_table_names_respects_permissions(self, mock_env):
        """Test that list_table_names() only returns tables the user has access to."""
        from databricks.sdk.service.catalog import TableInfo
        
        with patch('server.services.unity_catalog_service.WorkspaceClient') as mock_client_class:
            mock_client = Mock(spec=WorkspaceClient)
            mock_client_class.return_value = mock_client
            
            # Mock tables that user has access to
            mock_client.tables.list.return_value = [
                TableInfo(name='users'),
                TableInfo(name='orders')
            ]
            
            service = UnityCatalogService(user_token="test-token")
            tables = await service.list_table_names(
                catalog='main',
                schema='default',
                user_id='user@example.com'
            )
            
            assert len(tables) == 2
            assert 'users' in tables
            assert 'orders' in tables
            
            # Verify list was called with correct parameters
            mock_client.tables.list.assert_called_once_with(
                catalog_name='main',
                schema_name='default'
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

