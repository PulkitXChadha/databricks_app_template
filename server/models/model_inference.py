"""Model Inference Request/Response Pydantic Models.

Represents model inference requests and responses for Model Serving.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class InferenceStatus(str, Enum):
    """Model inference response status."""
    SUCCESS = 'SUCCESS'
    ERROR = 'ERROR'
    TIMEOUT = 'TIMEOUT'


class ModelInferenceRequest(BaseModel):
    """Request to invoke a model serving endpoint.

    Attributes:
        request_id: Unique request identifier
        endpoint_name: Target endpoint name
        inputs: Input data for model (format depends on model)
        user_id: User making the request
        created_at: When request was created
        timeout_seconds: Request timeout (1-300 seconds)
    """

    request_id: str = Field(..., min_length=1, description='Unique request identifier')
    endpoint_name: str = Field(..., min_length=1, description='Target endpoint name')
    inputs: dict[str, Any] = Field(..., description='Model input data')
    user_id: str = Field(..., description='User making request')
    created_at: datetime = Field(default_factory=datetime.utcnow, description='Request creation time')
    timeout_seconds: int = Field(default=30, ge=1, le=300, description='Request timeout')

    @field_validator('inputs')
    @classmethod
    def validate_inputs(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate inputs dictionary is not empty."""
        if not v:
            raise ValueError('inputs must contain at least one key-value pair')
        return v

    @field_validator('timeout_seconds')
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout is within allowed range (1-300 seconds)."""
        if v < 1 or v > 300:
            raise ValueError('timeout_seconds must be between 1 and 300 seconds')
        return v

    model_config = {
        'json_schema_extra': {
            'example': {
                'request_id': 'req-abc123',
                'endpoint_name': 'sentiment-analysis-prod',
                'inputs': {
                    'text': 'This product is amazing!'
                },
                'user_id': 'user@example.com',
                'created_at': '2025-10-05T12:00:00Z',
                'timeout_seconds': 30
            }
        }
    }


class ModelInferenceResponse(BaseModel):
    """Result of a model inference request.

    Attributes:
        request_id: Matching request ID
        endpoint_name: Endpoint that processed request
        predictions: Model predictions/outputs
        status: Response status
        execution_time_ms: Inference time in milliseconds
        error_message: Error message if status is ERROR
        completed_at: When response was received
    """

    request_id: str = Field(..., description='Matching request ID')
    endpoint_name: str = Field(..., description='Endpoint name')
    predictions: dict[str, Any] = Field(default={}, description='Model predictions')
    status: InferenceStatus = Field(..., description='Response status')
    execution_time_ms: int = Field(..., gt=0, description='Execution time in milliseconds')
    error_message: str | None = Field(default=None, description='Error message if failed')
    completed_at: datetime = Field(default_factory=datetime.utcnow, description='Completion timestamp')

    @field_validator('error_message')
    @classmethod
    def validate_error_message(cls, v: str | None, info) -> str | None:
        """Validate error_message is present when status is ERROR."""
        if 'status' in info.data:
            if info.data['status'] == InferenceStatus.ERROR and not v:
                raise ValueError('error_message required when status is ERROR')
            elif info.data['status'] == InferenceStatus.SUCCESS and v:
                raise ValueError('error_message should be None when status is SUCCESS')
        return v

    @field_validator('predictions')
    @classmethod
    def validate_predictions(cls, v: dict[str, Any], info) -> dict[str, Any]:
        """Validate predictions present when status is SUCCESS."""
        if 'status' in info.data and info.data['status'] == InferenceStatus.SUCCESS:
            if not v:
                raise ValueError('predictions required when status is SUCCESS')
        return v

    model_config = {
        'json_schema_extra': {
            'example': {
                'request_id': 'req-abc123',
                'endpoint_name': 'sentiment-analysis-prod',
                'predictions': {
                    'sentiment': 'positive',
                    'confidence': 0.95
                },
                'status': 'SUCCESS',
                'execution_time_ms': 150,
                'error_message': None,
                'completed_at': '2025-10-05T12:00:01Z'
            }
        }
    }
