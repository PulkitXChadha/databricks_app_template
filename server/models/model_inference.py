"""Model Inference Pydantic models for Model Serving requests and responses.

Represents model inference requests and responses for Databricks Model Serving.
Source: User input (request) and Model Serving endpoint response.
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class InferenceStatus(str, Enum):
    """Model inference execution status."""
    SUCCESS = 'SUCCESS'
    ERROR = 'ERROR'
    TIMEOUT = 'TIMEOUT'


class ModelInferenceRequest(BaseModel):
    """Model inference request payload.
    
    Attributes:
        request_id: Unique identifier for this request
        endpoint_name: Target Model Serving endpoint name
        inputs: Input data for model (format depends on model schema)
        user_id: User making the request
        created_at: When request was created
        timeout_seconds: Request timeout (1-300 seconds, default 30)
    """
    
    request_id: str = Field(..., min_length=1, description='Unique request ID')
    endpoint_name: str = Field(..., min_length=1, description='Target endpoint name')
    inputs: dict = Field(..., min_length=1, description='Model input data')
    user_id: str = Field(..., description='User making request')
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description='Request creation timestamp'
    )
    timeout_seconds: int = Field(
        default=30,
        ge=1,
        le=300,
        description='Request timeout in seconds (1-300, default 30)'
    )
    
    @field_validator('timeout_seconds')
    @classmethod
    def validate_timeout_range(cls, v: int) -> int:
        """Ensure timeout is within acceptable range (1-300 seconds)."""
        if not 1 <= v <= 300:
            raise ValueError('timeout_seconds must be between 1 and 300 seconds')
        return v
    
    class Config:
        json_schema_extra = {
            'example': {
                'request_id': 'req_xyz789',
                'endpoint_name': 'sentiment-analysis',
                'inputs': {
                    'text': 'This product is amazing! Highly recommend.'
                },
                'user_id': 'user@example.com',
                'created_at': '2025-10-04T12:00:00Z',
                'timeout_seconds': 30
            }
        }


class ModelInferenceResponse(BaseModel):
    """Model inference response with predictions.
    
    Attributes:
        request_id: Matching request ID from ModelInferenceRequest
        endpoint_name: Endpoint that processed the request
        predictions: Model predictions/outputs (format depends on model)
        status: Inference execution status (SUCCESS, ERROR, TIMEOUT)
        execution_time_ms: Inference time in milliseconds
        error_message: Error message if status is ERROR (optional)
        completed_at: When response was received
    """
    
    request_id: str = Field(..., description='Matching request ID')
    endpoint_name: str = Field(..., description='Endpoint that processed request')
    predictions: dict = Field(default_factory=dict, description='Model predictions')
    status: InferenceStatus = Field(..., description='Inference status')
    execution_time_ms: int = Field(..., gt=0, description='Inference time (ms)')
    error_message: str | None = Field(
        default=None,
        description='Error message if status is ERROR'
    )
    completed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description='Response received timestamp'
    )
    
    @field_validator('error_message')
    @classmethod
    def validate_error_message_on_error(cls, v: str | None, info) -> str | None:
        """Ensure error_message is present when status is ERROR."""
        if 'status' in info.data and info.data['status'] == InferenceStatus.ERROR:
            if not v:
                raise ValueError('error_message required when status is ERROR')
        return v
    
    @field_validator('execution_time_ms')
    @classmethod
    def validate_execution_time_positive(cls, v: int) -> int:
        """Ensure execution_time_ms is positive."""
        if v <= 0:
            raise ValueError('execution_time_ms must be positive')
        return v
    
    class Config:
        json_schema_extra = {
            'example': {
                'request_id': 'req_xyz789',
                'endpoint_name': 'sentiment-analysis',
                'predictions': {
                    'sentiment': 'positive',
                    'confidence': 0.95,
                    'scores': {
                        'positive': 0.95,
                        'negative': 0.03,
                        'neutral': 0.02
                    }
                },
                'status': 'SUCCESS',
                'execution_time_ms': 1234,
                'error_message': None,
                'completed_at': '2025-10-04T12:00:00Z'
            }
        }
