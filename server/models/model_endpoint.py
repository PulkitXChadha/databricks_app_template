"""ModelEndpoint Pydantic model for Databricks Model Serving endpoints.

Represents a Databricks Model Serving endpoint that can be invoked for inference.
Source: Databricks Model Serving API.
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class EndpointState(str, Enum):
    """Model Serving endpoint state."""
    CREATING = 'CREATING'
    READY = 'READY'
    UPDATING = 'UPDATING'
    FAILED = 'FAILED'


class ModelEndpoint(BaseModel):
    """Model Serving endpoint metadata.
    
    Attributes:
        endpoint_name: Unique endpoint name within workspace
        endpoint_id: Databricks endpoint ID
        model_name: Fully qualified model name from Unity Catalog Model Registry
        model_version: Model version being served
        state: Endpoint state (must be READY for inference)
        workload_url: URL to invoke the endpoint
        creation_timestamp: When endpoint was created
        last_updated_timestamp: When endpoint was last modified
        config: Endpoint configuration (served models, traffic routing)
    """
    
    endpoint_name: str = Field(..., min_length=1, description='Unique endpoint name')
    endpoint_id: str = Field(..., min_length=1, description='Databricks endpoint ID')
    model_name: str = Field(
        ...,
        min_length=1,
        description='Model name from Unity Catalog Model Registry'
    )
    model_version: str = Field(..., min_length=1, description='Model version')
    state: EndpointState = Field(..., description='Endpoint state')
    workload_url: str = Field(
        ...,
        pattern=r'^https://.*',
        description='Endpoint invocation URL'
    )
    creation_timestamp: datetime = Field(
        ...,
        description='Endpoint creation time'
    )
    last_updated_timestamp: datetime = Field(
        ...,
        description='Last modification time'
    )
    config: dict = Field(default_factory=dict, description='Endpoint configuration')
    
    @field_validator('state')
    @classmethod
    def validate_ready_state_for_inference(cls, v: EndpointState) -> EndpointState:
        """Validate endpoint is in READY state for inference operations.
        
        Note: This validator is strict for safety. In production, you may want
        to allow checking state separately before inference.
        """
        if v != EndpointState.READY:
            raise ValueError(
                f'Endpoint must be READY for inference (current state: {v})'
            )
        return v
    
    class Config:
        json_schema_extra = {
            'example': {
                'endpoint_name': 'sentiment-analysis',
                'endpoint_id': 'ep_abc123',
                'model_name': 'main.ml_models.sentiment_classifier',
                'model_version': '3',
                'state': 'READY',
                'workload_url': 'https://workspace.cloud.databricks.com/serving-endpoints/sentiment-analysis/invocations',
                'creation_timestamp': '2025-10-01T08:00:00Z',
                'last_updated_timestamp': '2025-10-04T10:00:00Z',
                'config': {
                    'served_models': [
                        {
                            'model_name': 'main.ml_models.sentiment_classifier',
                            'model_version': '3',
                            'workload_size': 'Small'
                        }
                    ]
                }
            }
        }
