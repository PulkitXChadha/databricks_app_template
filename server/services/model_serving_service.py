"""Model Serving Service

Service for invoking Databricks Model Serving endpoints for inference.
"""

import os
import asyncio
from datetime import datetime
from typing import Any

import httpx
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import DatabricksError

from server.models.model_endpoint import ModelEndpoint, EndpointState
from server.models.model_inference import (
    ModelInferenceRequest,
    ModelInferenceResponse,
    InferenceStatus
)
from server.lib.structured_logger import StructuredLogger

logger = StructuredLogger(__name__)


class ModelServingService:
    """Service for Model Serving inference.
    
    Provides methods to:
    - List available serving endpoints
    - Invoke model endpoints for predictions
    - Log inference requests to Lakebase
    """
    
    def __init__(self):
        """Initialize Model Serving service."""
        self.client = WorkspaceClient()
        self.default_timeout = int(os.getenv('MODEL_SERVING_TIMEOUT', '30'))
    
    async def list_endpoints(self) -> list[dict[str, Any]]:
        """List available Model Serving endpoints.
        
        Returns:
            List of endpoint metadata dictionaries
            
        Raises:
            DatabricksError: If API call fails
        """
        try:
            endpoints = []
            
            # List all serving endpoints
            endpoint_list = self.client.serving_endpoints.list()
            
            for ep in endpoint_list:
                # Extract first served model config
                served_model = ep.config.served_models[0] if ep.config and ep.config.served_models else None
                
                endpoint_data = {
                    "endpoint_name": ep.name,
                    "endpoint_id": ep.id if hasattr(ep, 'id') else ep.name,
                    "model_name": served_model.model_name if served_model else "unknown",
                    "model_version": served_model.model_version if served_model else "unknown",
                    "state": ep.state.config_update.value if ep.state and ep.state.config_update else "UNKNOWN",
                    "creation_timestamp": ep.creation_timestamp if hasattr(ep, 'creation_timestamp') else None
                }
                
                endpoints.append(endpoint_data)
            
            logger.info(f"Listed {len(endpoints)} serving endpoints")
            
            return endpoints
            
        except DatabricksError as e:
            logger.error(
                f"Error listing model serving endpoints: {str(e)}",
                exc_info=True
            )
            raise
    
    async def get_endpoint(self, endpoint_name: str) -> ModelEndpoint:
        """Get endpoint metadata.
        
        Args:
            endpoint_name: Endpoint name
            
        Returns:
            ModelEndpoint with metadata
            
        Raises:
            DatabricksError: If endpoint not found
        """
        try:
            ep = self.client.serving_endpoints.get(endpoint_name)
            
            # Extract served model info
            served_model = ep.config.served_models[0] if ep.config and ep.config.served_models else None
            
            # Map state
            state_mapping = {
                "NOT_UPDATING": EndpointState.READY,
                "UPDATE_PENDING": EndpointState.UPDATING,
                "CREATING": EndpointState.CREATING,
                "UPDATE_FAILED": EndpointState.FAILED,
            }
            
            state_str = ep.state.config_update.value if ep.state and ep.state.config_update else "UNKNOWN"
            state = state_mapping.get(state_str, EndpointState.UPDATING)
            
            # Build workload URL (endpoint invocation URL)
            workspace_url = os.getenv('DATABRICKS_HOST', 'https://example.cloud.databricks.com')
            workload_url = f"{workspace_url}/serving-endpoints/{endpoint_name}/invocations"
            
            endpoint = ModelEndpoint(
                endpoint_name=ep.name,
                endpoint_id=ep.id if hasattr(ep, 'id') else ep.name,
                model_name=served_model.model_name if served_model else "unknown",
                model_version=served_model.model_version if served_model else "unknown",
                state=state,
                workload_url=workload_url,
                creation_timestamp=datetime.fromtimestamp(ep.creation_timestamp / 1000) if hasattr(ep, 'creation_timestamp') else datetime.utcnow(),
                last_updated_timestamp=datetime.utcnow(),
                config={"served_models": [served_model.as_dict()] if served_model and hasattr(served_model, 'as_dict') else []}
            )
            
            return endpoint
            
        except DatabricksError as e:
            logger.error(
                f"Error getting endpoint {endpoint_name}: {str(e)}",
                exc_info=True,
                endpoint=endpoint_name
            )
            raise
    
    async def invoke_model(
        self,
        endpoint_name: str,
        inputs: dict[str, Any],
        user_id: str,
        timeout_seconds: int | None = None
    ) -> ModelInferenceResponse:
        """Invoke model serving endpoint for predictions.
        
        Args:
            endpoint_name: Target endpoint name
            inputs: Model input data
            user_id: User making the request
            timeout_seconds: Request timeout (default: 30s)
            
        Returns:
            ModelInferenceResponse with predictions or error
            
        Raises:
            ValueError: If endpoint not ready
            httpx.TimeoutException: If request times out (EC-001)
            httpx.HTTPError: If HTTP request fails (EC-001)
        """
        timeout = timeout_seconds or self.default_timeout
        
        # Create inference request
        request = ModelInferenceRequest(
            request_id=f"req-{datetime.utcnow().timestamp()}",
            endpoint_name=endpoint_name,
            inputs=inputs,
            user_id=user_id,
            timeout_seconds=timeout
        )
        
        try:
            # Check endpoint is ready
            endpoint = await self.get_endpoint(endpoint_name)
            if not endpoint.is_ready_for_inference():
                raise ValueError(f"Endpoint {endpoint_name} is not ready (state: {endpoint.state})")
            
            # Make HTTP request with retry logic
            start_time = datetime.utcnow()
            
            predictions = await self._invoke_with_retry(
                endpoint.workload_url,
                inputs,
                timeout,
                max_retries=3
            )
            
            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Create success response
            response = ModelInferenceResponse(
                request_id=request.request_id,
                endpoint_name=endpoint_name,
                predictions=predictions,
                status=InferenceStatus.SUCCESS,
                execution_time_ms=execution_time_ms,
                error_message=None,
                completed_at=end_time
            )
            
            logger.info(
                f"Inference succeeded in {execution_time_ms}ms",
                request_id=request.request_id,
                endpoint=endpoint_name,
                user_id=user_id,
                execution_time_ms=execution_time_ms
            )
            
            # TODO: Log inference to Lakebase model_inference_logs table (future task)
            
            return response
            
        except httpx.TimeoutException as e:
            logger.error(
                f"Inference timeout after {timeout}s",
                exc_info=True,
                request_id=request.request_id,
                endpoint=endpoint_name,
                user_id=user_id
            )
            
            return ModelInferenceResponse(
                request_id=request.request_id,
                endpoint_name=endpoint_name,
                predictions={},
                status=InferenceStatus.TIMEOUT,
                execution_time_ms=timeout * 1000,
                error_message=f"Request timeout after {timeout} seconds",
                completed_at=datetime.utcnow()
            )
            
        except (httpx.HTTPError, DatabricksError, ValueError) as e:
            logger.error(
                f"Inference error: {str(e)}",
                exc_info=True,
                request_id=request.request_id,
                endpoint=endpoint_name,
                user_id=user_id
            )
            
            return ModelInferenceResponse(
                request_id=request.request_id,
                endpoint_name=endpoint_name,
                predictions={},
                status=InferenceStatus.ERROR,
                execution_time_ms=0,
                error_message=str(e),
                completed_at=datetime.utcnow()
            )
    
    async def _invoke_with_retry(
        self,
        url: str,
        inputs: dict[str, Any],
        timeout: int,
        max_retries: int = 3
    ) -> dict[str, Any]:
        """Invoke endpoint with exponential backoff retry.
        
        Args:
            url: Endpoint URL
            inputs: Model inputs
            timeout: Request timeout
            max_retries: Maximum retry attempts
            
        Returns:
            Predictions dictionary
            
        Raises:
            httpx.HTTPError: If all retries fail
        """
        token = os.getenv('DATABRICKS_TOKEN')
        if not token:
            raise ValueError("DATABRICKS_TOKEN environment variable is required")
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        retry_count = 0
        last_exception = None
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            while retry_count < max_retries:
                try:
                    response = await client.post(
                        url,
                        json={"inputs": inputs},
                        headers=headers
                    )
                    response.raise_for_status()
                    
                    return response.json()
                    
                except (httpx.HTTPError, httpx.TimeoutException) as e:
                    retry_count += 1
                    last_exception = e
                    
                    # Only retry on server errors (5xx) or timeouts
                    if isinstance(e, httpx.HTTPStatusError) and 400 <= e.response.status_code < 500:
                        # Client error - don't retry
                        raise
                    
                    if retry_count < max_retries:
                        # Exponential backoff: 1s, 2s, 4s
                        wait_time = 2 ** (retry_count - 1)
                        logger.warning(
                            f"Retry {retry_count}/{max_retries} after {wait_time}s",
                            url=url
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        # Max retries reached
                        raise last_exception
