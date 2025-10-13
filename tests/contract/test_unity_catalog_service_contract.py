"""Contract tests for UnityCatalogService authentication patterns.

These tests validate that UnityCatalogService correctly implements dual authentication:
- Pattern A: Service Principal (when user_token is None)
- Pattern B: On-Behalf-Of-User (when user_token is provided)

Test Requirements (from contracts/service_layers.yaml):
- UnityCatalogService with user_token uses OBO (respects user permissions)
- UnityCatalogService without user_token uses service principal
- list_catalogs() returns different results for different users
- Client creation uses correct auth_type
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
    """Test UnityCatalogService authentication patterns."""
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Set up environment variables for testing."""
        monkeypatch.setenv('DATABRICKS_HOST', 'https://test.cloud.databricks.com')
        monkeypatch.setenv('DATABRICKS_CLIENT_ID', 'test-client-id')
        monkeypatch.setenv('DATABRICKS_CLIENT_SECRET', 'test-client-secret')
        monkeypatch.setenv('DATABRICKS_WAREHOUSE_ID', 'test-warehouse-id')
    
    @pytest.mark.asyncio
    async def test_with_user_token_uses_obo_auth(self, mock_env):
        """Test that UnityCatalogService with user_token creates client with auth_type='pat'."""
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
            
            # Extract Config object and verify its properties
            config = call_kwargs.get('config')
            assert config is not None, "Config object not passed to WorkspaceClient"
            assert config.token == user_token, "Config should use user token"
            assert config.auth_type == "pat", "auth_type should be 'pat' for OBO authentication"
            assert config.timeout == 30, "timeout should be 30 seconds per NFR-010"
            assert config.retry_timeout == 30, "retry_timeout should be 30 seconds"
            
            # Verify service uses OBO mode
            assert service.auth_mode == "user", "Service should be in user (OBO) mode"
    
    @pytest.mark.asyncio
    async def test_without_user_token_uses_service_principal(self, mock_env):
        """Test that UnityCatalogService without user_token uses service principal with auth_type='oauth-m2m'."""
        with patch('server.services.unity_catalog_service.WorkspaceClient') as mock_client_class:
            # Create mock client instance
            mock_client = Mock(spec=WorkspaceClient)
            mock_client_class.return_value = mock_client
            
            # Initialize service without user token (service principal mode)
            service = UnityCatalogService(user_token=None)
            
            # Verify WorkspaceClient was created with correct parameters
            mock_client_class.assert_called_once()
            call_kwargs = mock_client_class.call_args[1]
            
            # Extract Config object and verify its properties
            config = call_kwargs.get('config')
            assert config is not None, "Config object not passed to WorkspaceClient"
            assert config.client_id == 'test-client-id', "Config should use service principal client_id"
            assert config.client_secret == 'test-client-secret', "Config should use service principal client_secret"
            assert config.auth_type == "oauth-m2m", "auth_type should be 'oauth-m2m' for service principal"
            assert config.timeout == 30, "timeout should be 30 seconds per NFR-010"
            assert config.retry_timeout == 30, "retry_timeout should be 30 seconds"
            
            # Verify service uses service principal mode
            assert service.auth_mode == "app", "Service should be in app (service principal) mode"
    
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
    
    @pytest.mark.asyncio
    async def test_client_creation_logs_auth_mode(self, mock_env):
        """Test that client creation logs the correct authentication mode."""
        with patch('server.services.unity_catalog_service.WorkspaceClient') as mock_client_class, \
             patch('server.services.unity_catalog_service.logger') as mock_logger:
            
            # Create mock client instance
            mock_client = Mock(spec=WorkspaceClient)
            mock_client_class.return_value = mock_client
            
            # Test OBO mode logging
            service_obo = UnityCatalogService(user_token="test-token")
            mock_logger.info.assert_called_with(
                "Unity Catalog service initialized with OBO user authorization"
            )
            
            # Reset mock
            mock_logger.reset_mock()
            
            # Test service principal mode logging
            service_sp = UnityCatalogService(user_token=None)
            mock_logger.info.assert_called_with(
                "Unity Catalog service initialized with service principal authorization"
            )
    
    @pytest.mark.asyncio
    async def test_service_requires_warehouse_id(self, monkeypatch):
        """Test that service raises error if DATABRICKS_WAREHOUSE_ID is not set."""
        monkeypatch.setenv('DATABRICKS_HOST', 'https://test.cloud.databricks.com')
        monkeypatch.setenv('DATABRICKS_CLIENT_ID', 'test-client-id')
        monkeypatch.setenv('DATABRICKS_CLIENT_SECRET', 'test-client-secret')
        # Do not set DATABRICKS_WAREHOUSE_ID
        
        with patch('server.services.unity_catalog_service.WorkspaceClient'):
            with pytest.raises(ValueError, match="DATABRICKS_WAREHOUSE_ID environment variable is required"):
                UnityCatalogService(user_token=None)
    
    @pytest.mark.asyncio
    async def test_timeout_configuration_applied(self, mock_env):
        """Test that 30-second timeout is configured for both OBO and service principal modes."""
        with patch('server.services.unity_catalog_service.WorkspaceClient') as mock_client_class:
            mock_client = Mock(spec=WorkspaceClient)
            mock_client_class.return_value = mock_client
            
            # Test OBO mode
            service_obo = UnityCatalogService(user_token="test-token")
            call_kwargs_obo = mock_client_class.call_args[1]
            config_obo = call_kwargs_obo.get('config')
            
            assert config_obo.timeout == 30, "OBO mode should have 30-second timeout"
            assert config_obo.retry_timeout == 30, "OBO mode should have 30-second retry timeout"
            
            # Reset mock
            mock_client_class.reset_mock()
            
            # Test service principal mode
            service_sp = UnityCatalogService(user_token=None)
            call_kwargs_sp = mock_client_class.call_args[1]
            config_sp = call_kwargs_sp.get('config')
            
            assert config_sp.timeout == 30, "Service principal mode should have 30-second timeout"
            assert config_sp.retry_timeout == 30, "Service principal mode should have 30-second retry timeout"


class TestUnityCatalogServiceQueries:
    """Test that Unity Catalog queries respect user permissions."""
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Set up environment variables for testing."""
        monkeypatch.setenv('DATABRICKS_HOST', 'https://test.cloud.databricks.com')
        monkeypatch.setenv('DATABRICKS_CLIENT_ID', 'test-client-id')
        monkeypatch.setenv('DATABRICKS_CLIENT_SECRET', 'test-client-secret')
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

