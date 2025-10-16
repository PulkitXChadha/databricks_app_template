"""Model Serving API Router

FastAPI endpoints for Model Serving inference.
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import Any

from server.services.model_serving_service import ModelServingService
from server.models.model_endpoint import ModelEndpointResponse
from server.models.model_inference import ModelInferenceResponse
from server.lib.structured_logger import StructuredLogger
from server.lib.auth import get_current_user_id, get_user_token

router = APIRouter()
logger = StructuredLogger(__name__)


# Request/Response models
class InvokeModelRequest(BaseModel):
    """Request body for model inference."""
    endpoint_name: str = Field(..., description="Target endpoint name")
    inputs: dict[str, Any] = Field(..., description="Model input data")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Request timeout")


@router.get("/endpoints", response_model=list[ModelEndpointResponse])
async def list_endpoints(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    user_token: str = Depends(get_user_token)
):
    """List available Model Serving endpoints.
    
    Returns:
        List of endpoint metadata
        
    Raises:
        401: Authentication required (EC-003)
        503: Service unavailable
    """
    logger.info(
        "Listing model serving endpoints",
        user_id=user_id
    )
    
    try:
        service = ModelServingService(user_token=user_token)
        endpoints = await service.list_endpoints()
        
        logger.info(
            f"Retrieved {len(endpoints)} model serving endpoints",
            user_id=user_id,
            endpoint_count=len(endpoints)
        )
        
        return endpoints
        
    except Exception as e:
        logger.error(
            f"Error listing model serving endpoints: {str(e)}",
            exc_info=True,
            user_id=user_id
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "SERVICE_UNAVAILABLE",
                "message": "Model Serving service temporarily unavailable.",
                "technical_details": {"error_type": type(e).__name__},
                "retry_after": 10
            }
        )


@router.get("/endpoints/{endpoint_name}")
async def get_endpoint(
    endpoint_name: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    user_token: str = Depends(get_user_token)
):
    """Get specific Model Serving endpoint details.
    
    Args:
        endpoint_name: Name of the endpoint
        
    Returns:
        ModelEndpoint with metadata
        
    Raises:
        401: Authentication required
        404: Endpoint not found
        503: Service unavailable
    """
    logger.info(
        "Getting model serving endpoint",
        user_id=user_id,
        endpoint=endpoint_name
    )
    
    try:
        service = ModelServingService(user_token=user_token)
        endpoint = await service.get_endpoint(endpoint_name=endpoint_name)
        
        logger.info(
            f"Retrieved endpoint details",
            user_id=user_id,
            endpoint=endpoint_name
        )
        
        return endpoint
        
    except Exception as e:
        error_str = str(e).lower()
        
        # Check if endpoint not found
        if "not found" in error_str or "does not exist" in error_str:
            logger.warning(
                f"Endpoint not found: {endpoint_name}",
                user_id=user_id
            )
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "ENDPOINT_NOT_FOUND",
                    "message": f"Model serving endpoint '{endpoint_name}' not found."
                }
            )
        
        logger.error(
            f"Error getting model serving endpoint: {str(e)}",
            exc_info=True,
            user_id=user_id,
            endpoint=endpoint_name
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "SERVICE_UNAVAILABLE",
                "message": "Model Serving service temporarily unavailable.",
                "technical_details": {"error_type": type(e).__name__},
                "retry_after": 10
            }
        )


@router.post("/invoke", response_model=ModelInferenceResponse)
async def invoke_model(
    http_request: Request,
    request: InvokeModelRequest,
    user_id: str = Depends(get_current_user_id),
    user_token: str = Depends(get_user_token)
):
    """Invoke model for inference.
    
    Request Body:
        endpoint_name: Target endpoint name
        inputs: Model input data (format depends on model)
        timeout_seconds: Request timeout (1-300 seconds, default: 30)
        
    Returns:
        ModelInferenceResponse with predictions or error
        
    Raises:
        400: Invalid input data
        503: Model unavailable (EC-001)
    """
    logger.info(
        "Invoking model",
        user_id=user_id,
        endpoint=request.endpoint_name,
        timeout=request.timeout_seconds
    )
    
    try:
        service = ModelServingService(user_token=user_token)
        response = await service.invoke_model(
            endpoint_name=request.endpoint_name,
            inputs=request.inputs,
            user_id=user_id,
            timeout_seconds=request.timeout_seconds
        )
        
        logger.info(
            f"Model invocation completed with status: {response.status}",
            user_id=user_id,
            endpoint=request.endpoint_name,
            status=response.status,
            execution_time_ms=response.execution_time_ms
        )
        
        # If response has error status, return 503 with error details
        if response.status == "ERROR":
            raise HTTPException(
                status_code=503,
                detail={
                    "error_code": "MODEL_UNAVAILABLE",
                    "message": "Model service temporarily unavailable. Please try again in a few moments.",
                    "technical_details": {
                        "endpoint": request.endpoint_name,
                        "error": response.error_message
                    },
                    "retry_after": 30
                }
            )
        
        # If timeout, return 503 with timeout message
        if response.status == "TIMEOUT":
            raise HTTPException(
                status_code=503,
                detail={
                    "error_code": "MODEL_TIMEOUT",
                    "message": f"Model inference timeout after {request.timeout_seconds} seconds.",
                    "technical_details": {
                        "endpoint": request.endpoint_name,
                        "timeout": request.timeout_seconds
                    },
                    "retry_after": 30
                }
            )
        
        return response
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    
    except ValueError as e:
        logger.warning(
            f"Invalid inference request: {str(e)}",
            user_id=user_id,
            endpoint=request.endpoint_name
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_INPUT",
                "message": str(e)
            }
        )
    
    except Exception as e:
        logger.error(
            f"Error invoking model: {str(e)}",
            exc_info=True,
            user_id=user_id,
            endpoint=request.endpoint_name
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "MODEL_UNAVAILABLE",
                "message": "Model service temporarily unavailable. Please try again in a few moments.",
                "technical_details": {
                    "endpoint": request.endpoint_name,
                    "error": str(e)
                },
                "retry_after": 30
            }
        )


class InferenceLogResponse(BaseModel):
    """Response model for inference log."""
    id: int
    request_id: str
    endpoint_name: str
    user_id: str
    inputs: dict[str, Any]
    predictions: dict[str, Any] | None
    status: str
    execution_time_ms: int | None
    error_message: str | None
    created_at: str | None
    completed_at: str | None


class InferenceLogsListResponse(BaseModel):
    """Response model for list of inference logs."""
    logs: list[InferenceLogResponse]
    total_count: int
    limit: int
    offset: int


@router.get("/logs", response_model=InferenceLogsListResponse)
async def get_inference_logs(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id)
):
    """Get inference logs for the current user.
    
    Query Parameters:
        limit: Maximum number of logs to return (default: 50)
        offset: Offset for pagination (default: 0)
        
    Returns:
        InferenceLogsListResponse with logs and pagination info
        
    Raises:
        401: Authentication required
        503: Service unavailable
    """
    logger.info(
        "Retrieving inference logs",
        user_id=user_id,
        limit=limit,
        offset=offset
    )
    
    try:
        service = ModelServingService()
        logs, total_count = await service.get_user_inference_logs(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        logger.info(
            f"Retrieved {len(logs)} inference logs (total: {total_count})",
            user_id=user_id,
            count=len(logs),
            total_count=total_count
        )
        
        return InferenceLogsListResponse(
            logs=[InferenceLogResponse(**log) for log in logs],
            total_count=total_count,
            limit=limit,
            offset=offset
        )
        
    except ValueError as e:
        # Lakebase not configured
        if "Lakebase is not configured" in str(e):
            logger.warning(
                f"Lakebase not configured: {str(e)}",
                user_id=user_id
            )
            raise HTTPException(
                status_code=503,
                detail={
                    "error_code": "LAKEBASE_NOT_CONFIGURED",
                    "message": "Inference logs are not available. Lakebase database is not configured for this deployment.",
                    "technical_details": {
                        "error_type": "ConfigurationError",
                        "suggestion": "Configure Lakebase resource in databricks.yml or set PGHOST and LAKEBASE_DATABASE environment variables."
                    },
                    "retry_after": None
                }
            )
        # Other ValueError
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_REQUEST",
                "message": str(e)
            }
        )
    
    except Exception as e:
        logger.error(
            f"Error retrieving inference logs: {str(e)}",
            exc_info=True,
            user_id=user_id
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "SERVICE_UNAVAILABLE",
                "message": "Failed to retrieve inference logs.",
                "technical_details": {"error_type": type(e).__name__},
                "retry_after": 10
            }
        )
