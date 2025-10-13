"""Contract tests for ModelServingService authentication patterns.

These tests validate that ModelServingService correctly implements dual authentication:
- Pattern A: Service Principal (when user_token is None)
- Pattern B: On-Behalf-Of-User (when user_token is provided)

Test Requirements (from contracts/service_layers.yaml):
- ModelServingService with user_token uses OBO
- ModelServingService without user_token uses service principal
- list_endpoints() respects user permissions
- Client creation uses correct auth_type
"""

import os
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import (
    ServingEndpoint,
    ServingEndpointDetailed,
    EndpointCoreConfigInput,
    ServedEntityInput,
    EndpointStateConfigUpdate,
    EndpointStateReady
)

from server.services.model_serving_service import ModelServingService

# Mark all tests in this module as contract tests
pytestmark = pytest.mark.contract


class TestModelServingServiceAuthentication:
    """Test ModelServingService authentication patterns."""
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Set up environment variables for testing."""
        monkeypatch.setenv('DATABRICKS_HOST', 'https://test.cloud.databricks.com')
        monkeypatch.setenv('DATABRICKS_CLIENT_ID', 'test-client-id')
        monkeypatch.setenv('DATABRICKS_CLIENT_SECRET', 'test-client-secret')
    
    @pytest.mark.asyncio
    async def test_with_user_token_uses_obo_auth(self, mock_env):
        """Test that ModelServingService with user_token creates client with auth_type='pat'."""
        user_token = "test-user-token-12345"
        
        with patch('server.services.model_serving_service.WorkspaceClient') as mock_client_class:
            # Create mock client instance
            mock_client = Mock(spec=WorkspaceClient)
            mock_client_class.return_value = mock_client
            
            # Initialize service with user token
            service = ModelServingService(user_token=user_token)
            
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
        """Test that ModelServingService without user_token uses service principal with auth_type='oauth-m2m'."""
        with patch('server.services.model_serving_service.WorkspaceClient') as mock_client_class:
            # Create mock client instance
            mock_client = Mock(spec=WorkspaceClient)
            mock_client_class.return_value = mock_client
            
            # Initialize service without user token (service principal mode)
            service = ModelServingService(user_token=None)
            
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
    async def test_list_endpoints_respects_user_permissions(self, mock_env):
        """Test that list_endpoints() returns different results for different users (permission enforcement)."""
        with patch('server.services.model_serving_service.WorkspaceClient') as mock_client_class:
            # Create mock client instances for two different users
            mock_client_user_a = Mock(spec=WorkspaceClient)
            mock_client_user_b = Mock(spec=WorkspaceClient)
            
            # Mock endpoint lists for two different users
            # User A has access to 2 endpoints
            endpoint_1 = Mock(spec=ServingEndpoint)
            endpoint_1.name = 'model-endpoint-1'
            endpoint_1.state = Mock()
            endpoint_1.state.config_update = EndpointStateConfigUpdate.NOT_UPDATING
            endpoint_1.config = Mock()
            endpoint_1.config.served_entities = []
            endpoint_1.config.served_models = [Mock(model_name='model1', model_version='1')]
            endpoint_1.creation_timestamp = int(datetime.now().timestamp() * 1000)
            
            endpoint_2 = Mock(spec=ServingEndpoint)
            endpoint_2.name = 'model-endpoint-2'
            endpoint_2.state = Mock()
            endpoint_2.state.config_update = EndpointStateConfigUpdate.NOT_UPDATING
            endpoint_2.config = Mock()
            endpoint_2.config.served_entities = []
            endpoint_2.config.served_models = [Mock(model_name='model2', model_version='1')]
            endpoint_2.creation_timestamp = int(datetime.now().timestamp() * 1000)
            
            mock_client_user_a.serving_endpoints.list.return_value = [endpoint_1, endpoint_2]
            
            # User B only has access to 1 endpoint
            mock_client_user_b.serving_endpoints.list.return_value = [endpoint_1]
            
            # Test User A
            mock_client_class.return_value = mock_client_user_a
            service_a = ModelServingService(user_token="user-a-token")
            endpoints_a = await service_a.list_endpoints()
            
            assert len(endpoints_a) == 2, "User A should see 2 endpoints"
            assert any(ep.endpoint_name == 'model-endpoint-1' for ep in endpoints_a), "User A should see endpoint 1"
            assert any(ep.endpoint_name == 'model-endpoint-2' for ep in endpoints_a), "User A should see endpoint 2"
            
            # Test User B
            mock_client_class.return_value = mock_client_user_b
            service_b = ModelServingService(user_token="user-b-token")
            endpoints_b = await service_b.list_endpoints()
            
            assert len(endpoints_b) == 1, "User B should see only 1 endpoint"
            assert endpoints_b[0].endpoint_name == 'model-endpoint-1', "User B should see endpoint 1"
            
            # Verify different users get different results
            assert len(endpoints_a) != len(endpoints_b), "Different users should see different endpoint lists"
    
    @pytest.mark.asyncio
    async def test_client_creation_logs_auth_mode(self, mock_env):
        """Test that client creation logs the correct authentication mode."""
        with patch('server.services.model_serving_service.WorkspaceClient') as mock_client_class, \
             patch('server.services.model_serving_service.logger') as mock_logger:
            
            # Create mock client instance
            mock_client = Mock(spec=WorkspaceClient)
            mock_client_class.return_value = mock_client
            
            # Test OBO mode logging
            service_obo = ModelServingService(user_token="test-token")
            mock_logger.info.assert_called_with(
                "Model Serving service initialized with OBO user authorization"
            )
            
            # Reset mock
            mock_logger.reset_mock()
            
            # Test service principal mode logging
            service_sp = ModelServingService(user_token=None)
            mock_logger.info.assert_called_with(
                "Model Serving service initialized with service principal authorization"
            )
    
    @pytest.mark.asyncio
    async def test_timeout_configuration_applied(self, mock_env):
        """Test that 30-second timeout is configured for both OBO and service principal modes."""
        with patch('server.services.model_serving_service.WorkspaceClient') as mock_client_class:
            mock_client = Mock(spec=WorkspaceClient)
            mock_client_class.return_value = mock_client
            
            # Test OBO mode
            service_obo = ModelServingService(user_token="test-token")
            call_kwargs_obo = mock_client_class.call_args[1]
            config_obo = call_kwargs_obo.get('config')
            
            assert config_obo.timeout == 30, "OBO mode should have 30-second timeout"
            assert config_obo.retry_timeout == 30, "OBO mode should have 30-second retry timeout"
            
            # Reset mock
            mock_client_class.reset_mock()
            
            # Test service principal mode
            service_sp = ModelServingService(user_token=None)
            call_kwargs_sp = mock_client_class.call_args[1]
            config_sp = call_kwargs_sp.get('config')
            
            assert config_sp.timeout == 30, "Service principal mode should have 30-second timeout"
            assert config_sp.retry_timeout == 30, "Service principal mode should have 30-second retry timeout"
    
    @pytest.mark.asyncio
    async def test_default_timeout_from_env(self, mock_env, monkeypatch):
        """Test that default timeout can be configured via environment variable."""
        monkeypatch.setenv('MODEL_SERVING_TIMEOUT', '45')
        
        with patch('server.services.model_serving_service.WorkspaceClient') as mock_client_class:
            mock_client = Mock(spec=WorkspaceClient)
            mock_client_class.return_value = mock_client
            
            service = ModelServingService(user_token=None)
            
            assert service.default_timeout == 45, "Default timeout should be read from MODEL_SERVING_TIMEOUT env var"


class TestModelServingServiceEndpointOperations:
    """Test that Model Serving operations respect user permissions."""
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Set up environment variables for testing."""
        monkeypatch.setenv('DATABRICKS_HOST', 'https://test.cloud.databricks.com')
        monkeypatch.setenv('DATABRICKS_CLIENT_ID', 'test-client-id')
        monkeypatch.setenv('DATABRICKS_CLIENT_SECRET', 'test-client-secret')
    
    @pytest.mark.asyncio
    async def test_get_endpoint_respects_permissions(self, mock_env):
        """Test that get_endpoint() only succeeds if user has permission."""
        with patch('server.services.model_serving_service.WorkspaceClient') as mock_client_class:
            mock_client = Mock(spec=WorkspaceClient)
            mock_client_class.return_value = mock_client
            
            # Mock successful endpoint retrieval
            mock_endpoint = Mock(spec=ServingEndpointDetailed)
            mock_endpoint.name = 'test-endpoint'
            mock_endpoint.id = 'endpoint-123'
            mock_endpoint.state = Mock()
            mock_endpoint.state.config_update = EndpointStateConfigUpdate.NOT_UPDATING
            mock_endpoint.config = Mock()
            mock_endpoint.config.served_entities = []
            mock_endpoint.config.served_models = [Mock(model_name='test-model', model_version='1')]
            mock_endpoint.creation_timestamp = int(datetime.now().timestamp() * 1000)
            
            mock_client.serving_endpoints.get.return_value = mock_endpoint
            
            service = ModelServingService(user_token="test-token")
            endpoint = await service.get_endpoint('test-endpoint')
            
            assert endpoint.endpoint_name == 'test-endpoint'
            assert endpoint.state.value == 'READY'
            
            # Verify get was called with correct endpoint name
            mock_client.serving_endpoints.get.assert_called_once_with('test-endpoint')
    
    @pytest.mark.asyncio
    async def test_invoke_model_uses_obo_token(self, mock_env):
        """Test that invoke_model() uses OBO token for authentication when provided."""
        with patch('server.services.model_serving_service.WorkspaceClient') as mock_client_class, \
             patch('server.services.model_serving_service.httpx.AsyncClient') as mock_http_client, \
             patch('server.services.model_serving_service.get_engine') as mock_get_engine:
            
            # Mock WorkspaceClient
            mock_client = Mock(spec=WorkspaceClient)
            mock_client_class.return_value = mock_client
            
            # Mock endpoint retrieval
            mock_endpoint = Mock()
            mock_endpoint.name = 'test-endpoint'
            mock_endpoint.state = Mock()
            mock_endpoint.state.config_update = EndpointStateConfigUpdate.NOT_UPDATING
            mock_endpoint.is_ready_for_inference = Mock(return_value=True)
            mock_endpoint.workload_url = 'https://test.cloud.databricks.com/serving-endpoints/test-endpoint/invocations'
            mock_client.serving_endpoints.get = AsyncMock(return_value=mock_endpoint)
            
            # Mock authentication headers
            mock_client.config.authenticate.return_value = {
                'Authorization': 'Bearer test-user-token-12345'
            }
            
            # Mock HTTP client response
            mock_http_instance = Mock()
            mock_http_response = Mock()
            mock_http_response.json.return_value = {'predictions': [0.9, 0.1]}
            mock_http_response.raise_for_status = Mock()
            mock_http_instance.post = AsyncMock(return_value=mock_http_response)
            mock_http_instance.__aenter__ = AsyncMock(return_value=mock_http_instance)
            mock_http_instance.__aexit__ = AsyncMock(return_value=None)
            mock_http_client.return_value = mock_http_instance
            
            # Mock database engine (inference logging)
            mock_get_engine.return_value = None  # Skip logging for this test
            
            # Create service with OBO token
            service = ModelServingService(user_token="test-user-token-12345")
            
            # Invoke model
            result = await service.invoke_model(
                endpoint_name='test-endpoint',
                inputs={'messages': [{'role': 'user', 'content': 'test'}]},
                user_id='user@example.com',
                timeout_seconds=30
            )
            
            # Verify HTTP client was called with OBO auth headers
            assert mock_http_instance.post.called, "HTTP POST should be called"
            call_kwargs = mock_http_instance.post.call_args[1]
            assert 'headers' in call_kwargs, "Headers should be provided"
            assert 'Authorization' in call_kwargs['headers'], "Authorization header should be present"
            assert call_kwargs['headers']['Authorization'] == 'Bearer test-user-token-12345', \
                "Authorization header should use OBO token"


class TestModelServingServiceInferenceLogging:
    """Test that inference requests are logged with user_id."""
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Set up environment variables for testing."""
        monkeypatch.setenv('DATABRICKS_HOST', 'https://test.cloud.databricks.com')
        monkeypatch.setenv('DATABRICKS_CLIENT_ID', 'test-client-id')
        monkeypatch.setenv('DATABRICKS_CLIENT_SECRET', 'test-client-secret')
    
    @pytest.mark.asyncio
    async def test_inference_logged_with_user_id(self, mock_env):
        """Test that all inference requests are logged to Lakebase with user_id."""
        with patch('server.services.model_serving_service.WorkspaceClient') as mock_client_class, \
             patch('server.services.model_serving_service.httpx.AsyncClient') as mock_http_client, \
             patch('server.services.model_serving_service.get_engine') as mock_get_engine, \
             patch('server.services.model_serving_service.is_lakebase_configured') as mock_is_configured:
            
            # Mock Lakebase is configured
            mock_is_configured.return_value = True
            
            # Mock database engine
            mock_engine = Mock()
            mock_conn = Mock()
            mock_conn.execute = Mock()
            mock_conn.commit = Mock()
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=None)
            mock_engine.connect.return_value = mock_conn
            mock_get_engine.return_value = mock_engine
            
            # Mock WorkspaceClient and HTTP client (similar to previous test)
            mock_client = Mock(spec=WorkspaceClient)
            mock_client_class.return_value = mock_client
            
            mock_endpoint = Mock()
            mock_endpoint.name = 'test-endpoint'
            mock_endpoint.state = Mock()
            mock_endpoint.state.config_update = EndpointStateConfigUpdate.NOT_UPDATING
            mock_endpoint.is_ready_for_inference = Mock(return_value=True)
            mock_endpoint.workload_url = 'https://test.cloud.databricks.com/serving-endpoints/test-endpoint/invocations'
            mock_client.serving_endpoints.get = AsyncMock(return_value=mock_endpoint)
            mock_client.config.authenticate.return_value = {'Authorization': 'Bearer test-token'}
            
            mock_http_instance = Mock()
            mock_http_response = Mock()
            mock_http_response.json.return_value = {'predictions': [0.9, 0.1]}
            mock_http_response.raise_for_status = Mock()
            mock_http_instance.post = AsyncMock(return_value=mock_http_response)
            mock_http_instance.__aenter__ = AsyncMock(return_value=mock_http_instance)
            mock_http_instance.__aexit__ = AsyncMock(return_value=None)
            mock_http_client.return_value = mock_http_instance
            
            # Create service and invoke model
            service = ModelServingService(user_token="test-token")
            await service.invoke_model(
                endpoint_name='test-endpoint',
                inputs={'messages': [{'role': 'user', 'content': 'test'}]},
                user_id='user@example.com',
                timeout_seconds=30
            )
            
            # Verify database insert was called with user_id
            assert mock_conn.execute.called, "Database insert should be called"
            call_args = mock_conn.execute.call_args[0]
            params = mock_conn.execute.call_args[1]
            
            assert 'user_id' in params, "user_id should be in database insert params"
            assert params['user_id'] == 'user@example.com', "user_id should match the provided value"
            assert 'endpoint_name' in params, "endpoint_name should be logged"
            assert params['endpoint_name'] == 'test-endpoint', "endpoint_name should match"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

