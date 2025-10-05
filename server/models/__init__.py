"""Pydantic and SQLAlchemy models for Databricks service integrations.

This module exports all entity models used throughout the application:
- UserSession: Authenticated user session (Pydantic)
- DataSource: Unity Catalog table metadata (Pydantic)
- QueryResult: Query execution result (Pydantic)
- UserPreference: User preferences in Lakebase (SQLAlchemy)
- ModelEndpoint: Model Serving endpoint metadata (Pydantic)
- ModelInferenceRequest: Model inference request (Pydantic)
- ModelInferenceResponse: Model inference response (Pydantic)
"""

from server.models.user_session import UserSession
from server.models.data_source import DataSource, AccessLevel, ColumnDefinition
from server.models.query_result import QueryResult, QueryStatus
from server.models.user_preference import UserPreference, Base as LakebaseBase
from server.models.model_endpoint import ModelEndpoint, EndpointState
from server.models.model_inference import (
    ModelInferenceRequest,
    ModelInferenceResponse,
    InferenceStatus
)

__all__ = [
    # User Session
    'UserSession',
    
    # Unity Catalog (Data Source)
    'DataSource',
    'AccessLevel',
    'ColumnDefinition',
    'QueryResult',
    'QueryStatus',
    
    # Lakebase (User Preferences)
    'UserPreference',
    'LakebaseBase',
    
    # Model Serving
    'ModelEndpoint',
    'EndpointState',
    'ModelInferenceRequest',
    'ModelInferenceResponse',
    'InferenceStatus',
]
