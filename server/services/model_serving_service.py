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
from sqlalchemy import text

from server.models.model_endpoint import ModelEndpoint, ModelEndpointResponse, EndpointState
from server.models.model_inference import (
    ModelInferenceRequest,
    ModelInferenceResponse,
    InferenceStatus
)
from server.lib.structured_logger import StructuredLogger
from server.lib.database import get_engine

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
    
    async def list_endpoints(self) -> list[ModelEndpointResponse]:
        """List available Model Serving endpoints.
        
        Returns:
            List of endpoint metadata as ModelEndpointResponse objects
            
        Raises:
            DatabricksError: If API call fails
        """
        try:
            endpoints = []
            
            # List all serving endpoints
            endpoint_list = self.client.serving_endpoints.list()
            
            for ep in endpoint_list:
                try:
                    # Extract served model/entity config (supports both old and new formats)
                    served_model = None
                    served_entity = None
                    model_name = "unknown"
                    model_version = None
                    
                    if ep.config:
                        # New format: served_entities (for foundation models)
                        if hasattr(ep.config, 'served_entities') and ep.config.served_entities:
                            served_entity = ep.config.served_entities[0]
                            model_name = served_entity.entity_name if hasattr(served_entity, 'entity_name') else served_entity.name
                            model_version = str(served_entity.entity_version) if hasattr(served_entity, 'entity_version') else None
                        # Old format: served_models (for custom/MLflow models)
                        elif hasattr(ep.config, 'served_models') and ep.config.served_models:
                            served_model = ep.config.served_models[0]
                            model_name = served_model.model_name if served_model else "unknown"
                            model_version = str(served_model.model_version) if served_model and served_model.model_version else None
                    
                    # Map state
                    state_str = ep.state.config_update.value if ep.state and ep.state.config_update else "UNKNOWN"
                    state_mapping = {
                        "NOT_UPDATING": "READY",
                        "UPDATE_PENDING": "UPDATING",
                        "CREATING": "CREATING",
                        "UPDATE_FAILED": "FAILED",
                    }
                    state = state_mapping.get(state_str, "UPDATING")
                    
                    # Convert timestamp if present (Unix timestamp in milliseconds)
                    creation_timestamp = None
                    if hasattr(ep, 'creation_timestamp') and ep.creation_timestamp:
                        try:
                            # Convert from milliseconds to datetime, then to ISO string
                            dt = datetime.fromtimestamp(ep.creation_timestamp / 1000)
                            creation_timestamp = dt.isoformat() + 'Z'
                        except (ValueError, TypeError):
                            creation_timestamp = None
                    
                    endpoint_response = ModelEndpointResponse(
                        endpoint_name=ep.name,
                        endpoint_id=None,  # Not typically available in list response
                        model_name=model_name,
                        model_version=model_version,
                        state=state,
                        creation_timestamp=creation_timestamp
                    )
                    
                    endpoints.append(endpoint_response)
                    
                except Exception as e:
                    # Log error but continue processing other endpoints
                    logger.warning(
                        f"Error processing endpoint {ep.name if hasattr(ep, 'name') else 'unknown'}: {str(e)}",
                        endpoint=ep.name if hasattr(ep, 'name') else None
                    )
                    continue
            
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
            
            # Extract served model/entity info (supports both formats)
            served_model = None
            served_entity = None
            model_name = "unknown"
            model_version = "unknown"
            config_dict = {}
            
            if ep.config:
                # New format: served_entities (foundation models)
                if hasattr(ep.config, 'served_entities') and ep.config.served_entities:
                    served_entity = ep.config.served_entities[0]
                    model_name = served_entity.entity_name if hasattr(served_entity, 'entity_name') else served_entity.name
                    model_version = str(served_entity.entity_version) if hasattr(served_entity, 'entity_version') else "unknown"
                    config_dict = {"served_entities": [served_entity.as_dict()] if hasattr(served_entity, 'as_dict') else []}
                # Old format: served_models (custom/MLflow models)
                elif hasattr(ep.config, 'served_models') and ep.config.served_models:
                    served_model = ep.config.served_models[0]
                    model_name = served_model.model_name if served_model else "unknown"
                    model_version = str(served_model.model_version) if served_model and served_model.model_version else "unknown"
                    config_dict = {"served_models": [served_model.as_dict()] if served_model and hasattr(served_model, 'as_dict') else []}
            
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
            workspace_url = os.getenv('DATABRICKS_HOST', 'https://example.cloud.databricks.com').rstrip('/')
            workload_url = f"{workspace_url}/serving-endpoints/{endpoint_name}/invocations"
            
            endpoint = ModelEndpoint(
                endpoint_name=ep.name,
                endpoint_id=ep.id if hasattr(ep, 'id') else ep.name,
                model_name=model_name,
                model_version=model_version,
                state=state,
                workload_url=workload_url,
                creation_timestamp=datetime.fromtimestamp(ep.creation_timestamp / 1000) if hasattr(ep, 'creation_timestamp') else datetime.utcnow(),
                last_updated_timestamp=datetime.utcnow(),
                config=config_dict
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
        
        start_time = datetime.utcnow()
        
        try:
            # Check endpoint is ready
            endpoint = await self.get_endpoint(endpoint_name)
            if not endpoint.is_ready_for_inference():
                raise ValueError(f"Endpoint {endpoint_name} is not ready (state: {endpoint.state})")
            
            # Determine if this is a chat/foundation model or traditional ML model
            # Chat models have 'messages' key in inputs, traditional models typically have other structures
            is_chat_model = 'messages' in inputs
            
            # Make request with retry logic
            predictions = await self._invoke_with_retry(
                endpoint.workload_url,
                inputs,
                timeout,
                max_retries=3,
                is_chat_model=is_chat_model
            )
            
            end_time = datetime.utcnow()
            execution_time_ms = max(1, int((end_time - start_time).total_seconds() * 1000))
            
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
            
            # Log inference to Lakebase model_inference_logs table
            await self._log_inference(request, response)
            
            return response
            
        except httpx.TimeoutException as e:
            logger.error(
                f"Inference timeout after {timeout}s",
                exc_info=True,
                request_id=request.request_id,
                endpoint=endpoint_name,
                user_id=user_id
            )
            
            response = ModelInferenceResponse(
                request_id=request.request_id,
                endpoint_name=endpoint_name,
                predictions={},
                status=InferenceStatus.TIMEOUT,
                execution_time_ms=timeout * 1000,
                error_message=f"Request timeout after {timeout} seconds",
                completed_at=datetime.utcnow()
            )
            
            # Log inference to Lakebase
            await self._log_inference(request, response)
            
            return response
            
        except (httpx.HTTPError, DatabricksError, ValueError) as e:
            end_time = datetime.utcnow()
            execution_time_ms = max(1, int((end_time - start_time).total_seconds() * 1000))
            
            # Enhance error message for 400 Bad Request errors
            error_message = str(e)
            if "400" in error_message and "Bad Request" in error_message:
                error_message = (
                    f"{error_message}\n\n"
                    "This usually means the request format doesn't match what the model expects. "
                    "Please check:\n"
                    "1. For foundation models (Claude, GPT, etc.), use: "
                    '{"messages": [{"role": "user", "content": "..."}], "max_tokens": 150}\n'
                    "2. For traditional ML models, use: "
                    '{"inputs": [[feature1, feature2, ...]]}\n'
                    "3. For custom models with dataframe input, use: "
                    '{"dataframe_split": {"columns": [...], "data": [[...]]}}'
                )
            
            logger.error(
                f"Inference error: {error_message}",
                exc_info=True,
                request_id=request.request_id,
                endpoint=endpoint_name,
                user_id=user_id
            )
            
            response = ModelInferenceResponse(
                request_id=request.request_id,
                endpoint_name=endpoint_name,
                predictions={},
                status=InferenceStatus.ERROR,
                execution_time_ms=execution_time_ms,
                error_message=error_message,
                completed_at=end_time
            )
            
            # Log inference to Lakebase
            await self._log_inference(request, response)
            
            return response
    
    async def _invoke_with_retry(
        self,
        url: str,
        inputs: dict[str, Any],
        timeout: int,
        max_retries: int = 3,
        is_chat_model: bool = False
    ) -> dict[str, Any]:
        """Invoke endpoint with exponential backoff retry.
        
        Args:
            url: Endpoint URL
            inputs: Model inputs
            timeout: Request timeout
            max_retries: Maximum retry attempts
            is_chat_model: Whether this is a chat/foundation model (affects request format)
            
        Returns:
            Predictions dictionary
            
        Raises:
            httpx.HTTPError: If all retries fail
        """
        # Get authentication headers from WorkspaceClient
        # authenticate() returns a dict with Authorization header (works with PAT and OAuth)
        auth_headers = self.client.config.authenticate()
        if not auth_headers or 'Authorization' not in auth_headers:
            raise ValueError("Failed to authenticate with Databricks. Please check your credentials.")
        
        headers = {
            **auth_headers,  # Unpack authentication headers (includes Authorization)
            'Content-Type': 'application/json'
        }
        
        # Prepare request body based on model type
        # For foundation models (chat models), send inputs directly without wrapping
        # For traditional ML models, the inputs might already be wrapped correctly
        request_body = inputs
        
        retry_count = 0
        last_exception = None
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            while retry_count < max_retries:
                try:
                    logger.debug(
                        f"Invoking model endpoint (attempt {retry_count + 1}/{max_retries})",
                        url=url,
                        is_chat_model=is_chat_model,
                        request_body_keys=list(request_body.keys())
                    )
                    
                    response = await client.post(
                        url,
                        json=request_body,
                        headers=headers
                    )
                    response.raise_for_status()
                    
                    return response.json()
                    
                except (httpx.HTTPError, httpx.TimeoutException) as e:
                    retry_count += 1
                    last_exception = e
                    
                    # Log detailed error information for 4xx errors
                    if isinstance(e, httpx.HTTPStatusError):
                        try:
                            error_body = e.response.text
                            logger.error(
                                f"HTTP {e.response.status_code} error from model endpoint",
                                url=url,
                                status_code=e.response.status_code,
                                error_body=error_body,
                                request_body_keys=list(request_body.keys()),
                                is_chat_model=is_chat_model
                            )
                            
                            # For 400 errors, provide helpful guidance
                            if e.response.status_code == 400:
                                logger.error(
                                    "Bad Request - Request format may not match model expectations. "
                                    "Check the endpoint's input schema or model documentation.",
                                    endpoint_url=url
                                )
                        except Exception:
                            pass
                    
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
    
    async def _log_inference(
        self,
        request: ModelInferenceRequest,
        response: ModelInferenceResponse
    ) -> None:
        """Log inference request and response to Lakebase.
        
        Args:
            request: Model inference request
            response: Model inference response
        """
        try:
            engine = get_engine()
            
            # Serialize inputs and predictions as JSON
            import json
            inputs_json = json.dumps(request.inputs)
            predictions_json = json.dumps(response.predictions) if response.predictions else None
            
            # Insert log record
            with engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO model_inference_logs (
                            request_id, endpoint_name, user_id, inputs, predictions,
                            status, execution_time_ms, error_message, created_at, completed_at
                        ) VALUES (
                            :request_id, :endpoint_name, :user_id, :inputs::jsonb, :predictions::jsonb,
                            :status, :execution_time_ms, :error_message, :created_at, :completed_at
                        )
                    """),
                    {
                        "request_id": request.request_id,
                        "endpoint_name": request.endpoint_name,
                        "user_id": request.user_id,
                        "inputs": inputs_json,
                        "predictions": predictions_json,
                        "status": response.status.value,
                        "execution_time_ms": response.execution_time_ms,
                        "error_message": response.error_message,
                        "created_at": request.created_at,
                        "completed_at": response.completed_at
                    }
                )
                conn.commit()
            
            logger.debug(
                f"Logged inference to database",
                request_id=request.request_id,
                user_id=request.user_id
            )
            
        except Exception as e:
            # Log error but don't fail the inference request
            logger.error(
                f"Failed to log inference to database: {str(e)}",
                exc_info=True,
                request_id=request.request_id
            )
    
    async def get_user_inference_logs(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[list[dict[str, Any]], int]:
        """Get inference logs for a specific user.
        
        Args:
            user_id: User ID to filter logs
            limit: Maximum number of logs to return
            offset: Offset for pagination
            
        Returns:
            Tuple of (logs list, total count)
        """
        try:
            engine = get_engine()
            
            with engine.connect() as conn:
                # Get total count
                count_result = conn.execute(
                    text("""
                        SELECT COUNT(*) as total
                        FROM model_inference_logs
                        WHERE user_id = :user_id
                    """),
                    {"user_id": user_id}
                )
                total_count = count_result.fetchone()[0]
                
                # Get logs
                result = conn.execute(
                    text("""
                        SELECT 
                            id, request_id, endpoint_name, user_id,
                            inputs, predictions, status, execution_time_ms,
                            error_message, created_at, completed_at
                        FROM model_inference_logs
                        WHERE user_id = :user_id
                        ORDER BY created_at DESC
                        LIMIT :limit OFFSET :offset
                    """),
                    {"user_id": user_id, "limit": limit, "offset": offset}
                )
                
                logs = []
                for row in result:
                    logs.append({
                        "id": row[0],
                        "request_id": row[1],
                        "endpoint_name": row[2],
                        "user_id": row[3],
                        "inputs": row[4],
                        "predictions": row[5],
                        "status": row[6],
                        "execution_time_ms": row[7],
                        "error_message": row[8],
                        "created_at": row[9].isoformat() if row[9] else None,
                        "completed_at": row[10].isoformat() if row[10] else None
                    })
                
                return logs, total_count
                
        except Exception as e:
            logger.error(
                f"Failed to retrieve inference logs: {str(e)}",
                exc_info=True,
                user_id=user_id
            )
            raise
