"""Pydantic models for schema detection results."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EndpointType(str, Enum):
    """Types of model serving endpoints."""
    FOUNDATION_MODEL = 'FOUNDATION_MODEL'
    MLFLOW_MODEL = 'MLFLOW_MODEL'
    UNKNOWN = 'UNKNOWN'


class DetectionStatus(str, Enum):
    """Status of schema detection attempt."""
    SUCCESS = 'SUCCESS'
    FAILURE = 'FAILURE'
    TIMEOUT = 'TIMEOUT'


class SchemaDetectionResult(BaseModel):
    """Result of automatic schema detection for a serving endpoint."""

    endpoint_name: str = Field(..., description='Name of the serving endpoint')
    detected_type: EndpointType = Field(..., description='Detected model type')
    status: DetectionStatus = Field(..., description='Detection result status')
    input_schema: dict[str, Any] | None = Field(default=None, description='JSON Schema definition', alias='schema')
    example_json: dict[str, Any] = Field(..., description='Generated example input JSON')
    error_message: str | None = Field(default=None, description='Error description if failed')
    latency_ms: int = Field(..., description='Schema detection latency in milliseconds', ge=0)
    detected_at: datetime = Field(default_factory=datetime.utcnow, description='Detection timestamp')

    model_config = {
        'populate_by_name': True,  # Allow both field name and alias
        'json_schema_extra': {
            'example': {
                'endpoint_name': 'databricks-claude-sonnet-4',
                'detected_type': 'FOUNDATION_MODEL',
                'status': 'SUCCESS',
                'schema': {'type': 'object', 'properties': {'messages': {'type': 'array'}}},
                'example_json': {
                    'messages': [
                        {'role': 'system', 'content': 'You are a helpful assistant.'},
                        {'role': 'user', 'content': 'Hello!'}
                    ],
                    'max_tokens': 150
                },
                'error_message': None,
                'latency_ms': 245,
                'detected_at': '2025-10-17T10:30:00Z'
            }
        }
    }

