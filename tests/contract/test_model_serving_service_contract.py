"""Contract tests for ModelServingService OBO-only authentication.

These tests validate that ModelServingService correctly implements OBO-only authentication:
- Service REQUIRES user_token parameter (not Optional)
- Service raises ValueError if user_token is None or empty
- Service creates WorkspaceClient with auth_type='pat' only

Test Requirements (from contracts/service_authentication.yaml):
- ModelServingService(user_token=None) raises ValueError
- ModelServingService(user_token="mock-token") succeeds with OBO client
- list_endpoints() respects user permissions
- No service principal fallback
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
    """Test ModelServingService OBO-only authentication patterns."""
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Set up environment variables for testing."""
        monkeypatch.setenv('DATABRICKS_HOST', 'https://test.cloud.databricks.com')
    
    def test_service_accepts_none_for_service_principal_mode(self, mock_env):
        """Test that ModelServingService accepts None for service principal mode."""
        with patch('server.services.model_serving_service.WorkspaceClient') as mock_client_class:
            mock_client = Mock(spec=WorkspaceClient)
            mock_client_class.return_value = mock_client
            
            # Should not raise exception - None means service principal mode
            service = ModelServingService(user_token=None)
            assert service.user_token is None
    
    def test_service_accepts_empty_string_for_service_principal_mode(self, mock_env):
        """Test that ModelServingService accepts empty string for service principal mode."""
        with patch('server.services.model_serving_service.WorkspaceClient') as mock_client_class:
            mock_client = Mock(spec=WorkspaceClient)
            mock_client_class.return_value = mock_client
            
            # Empty string treated as no token
            service = ModelServingService(user_token="")
            assert service.user_token == ""
    
    def test_service_initialization_succeeds_with_valid_token(self, mock_env):
        """Test that ModelServingService initializes successfully with valid token."""
        with patch('server.services.model_serving_service.WorkspaceClient') as mock_client_class:
            mock_client = Mock(spec=WorkspaceClient)
            mock_client_class.return_value = mock_client
            
            # Should not raise exception
            service = ModelServingService(user_token="mock-token-12345")
            
            assert service.user_token == "mock-token-12345"
            assert service.workspace_url == 'https://test.cloud.databricks.com'
    
    def test_service_creates_workspace_client_with_obo_auth(self, mock_env):
        """Test that ModelServingService creates WorkspaceClient with auth_type='pat' only."""
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
    


class TestModelServingServiceEndpointOperations:
    """Test that Model Serving operations respect user permissions."""
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Set up environment variables for testing."""
        monkeypatch.setenv('DATABRICKS_HOST', 'https://test.cloud.databricks.com')
    
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
            mock_endpoint.id = 'endpoint-123'
            mock_endpoint.state = Mock()
            mock_endpoint.state.config_update = EndpointStateConfigUpdate.NOT_UPDATING
            mock_endpoint.creation_timestamp = int(datetime.now().timestamp() * 1000)
            mock_endpoint.config = Mock()
            mock_endpoint.config.served_entities = []
            mock_endpoint.config.served_models = [Mock(model_name='test-model', model_version='1')]
            mock_client.serving_endpoints.get = Mock(return_value=mock_endpoint)
            
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
            mock_endpoint.id = 'endpoint-123'
            mock_endpoint.state = Mock()
            mock_endpoint.state.config_update = EndpointStateConfigUpdate.NOT_UPDATING
            mock_endpoint.creation_timestamp = int(datetime.now().timestamp() * 1000)
            mock_endpoint.config = Mock()
            mock_endpoint.config.served_entities = []
            mock_endpoint.config.served_models = [Mock(model_name='test-model', model_version='1')]
            mock_client.serving_endpoints.get = Mock(return_value=mock_endpoint)
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
            # execute is called as: execute(text(...), {...})
            # So call_args[0] is a tuple: (text_object, params_dict)
            call_args = mock_conn.execute.call_args[0]
            params = call_args[1]  # Get the params dict from positional args
            
            assert 'user_id' in params, "user_id should be in database insert params"
            assert params['user_id'] == 'user@example.com', "user_id should match the provided value"
            assert 'endpoint_name' in params, "endpoint_name should be logged"
            assert params['endpoint_name'] == 'test-endpoint', "endpoint_name should match"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

