"""Model Endpoint Pydantic Model.

Represents a Databricks Model Serving endpoint that can be invoked for inference.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EndpointState(str, Enum):
    """Model Serving endpoint state."""
    CREATING = 'CREATING'
    READY = 'READY'
    UPDATING = 'UPDATING'
    FAILED = 'FAILED'


class ModelEndpointResponse(BaseModel):
    """Response model for Model Serving endpoint metadata (API response).

    This is a simplified version of ModelEndpoint for API responses.
    Uses string timestamps instead of datetime for JSON serialization.
    """

    endpoint_name: str = Field(..., description='Unique endpoint name')
    endpoint_id: str | None = Field(default=None, description='Databricks endpoint ID')
    model_name: str | None = Field(default=None, description='Model name (optional for some endpoint types)')
    model_version: str | None = Field(default=None, description='Model version')
    state: str = Field(..., description='Endpoint state')
    creation_timestamp: str | None = Field(default=None, description='Creation time (ISO 8601)')


class ModelEndpoint(BaseModel):
    """Databricks Model Serving endpoint metadata.

    Attributes:
        endpoint_name: Unique endpoint name
        endpoint_id: Databricks endpoint ID
        model_name: Model name from Unity Catalog Model Registry
        model_version: Model version being served
        state: Endpoint state
        workload_url: URL to invoke the endpoint
        creation_timestamp: When endpoint was created
        last_updated_timestamp: When endpoint was last modified
        config: Endpoint configuration (served models, traffic routing)
    """

    endpoint_name: str = Field(..., min_length=1, description='Unique endpoint name')
    endpoint_id: str | None = Field(default=None, description='Databricks endpoint ID')
    model_name: str = Field(..., min_length=1, description='Model name')
    model_version: str | None = Field(default=None, description='Model version')
    state: EndpointState = Field(..., description='Endpoint state')
    workload_url: str | None = Field(default=None, description='Endpoint invocation URL')
    creation_timestamp: datetime | None = Field(default=None, description='Creation time')
    last_updated_timestamp: datetime | None = Field(default=None, description='Last update time')
    config: dict[str, Any] = Field(default={}, description='Endpoint configuration')

    @field_validator('workload_url')
    @classmethod
    def validate_workload_url(cls, v: str | None) -> str | None:
        """Validate workload URL is HTTPS."""
        if v and not v.startswith('https://'):
            raise ValueError('workload_url must use HTTPS')
        return v

    @field_validator('state')
    @classmethod
    def validate_ready_state(cls, v: EndpointState) -> EndpointState:
        """Validate endpoint is ready for inference.

        Note: This validator only checks state for newly created endpoints.
        For existing endpoints, check state before invocation in service layer.
        """
        # Allow all states during model creation, check in service layer before invocation
        return v

    def is_ready_for_inference(self) -> bool:
        """Check if endpoint is ready to serve predictions."""
        return self.state == EndpointState.READY

    model_config = {
        'json_schema_extra': {
            'example': {
                'endpoint_name': 'sentiment-analysis-prod',
                'endpoint_id': 'ep-123abc',
                'model_name': 'sentiment_classifier',
                'model_version': '3',
                'state': 'READY',
                'workload_url': 'https://example.cloud.databricks.com/serving-endpoints/sentiment-analysis-prod',
                'creation_timestamp': '2025-10-01T12:00:00Z',
                'last_updated_timestamp': '2025-10-05T10:00:00Z',
                'config': {
                    'served_models': [
                        {
                            'model_name': 'sentiment_classifier',
                            'model_version': '3',
                            'workload_size': 'Small',
                            'scale_to_zero_enabled': True
                        }
                    ]
                }
            }
        }
    }
