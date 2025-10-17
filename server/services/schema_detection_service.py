"""Schema Detection Service

Provides automatic schema detection for Databricks Model Serving endpoints.
Detects endpoint types (foundation models, MLflow models) and generates
appropriate input examples.
"""

import asyncio
import json
from datetime import datetime
from typing import Any

from databricks.sdk import WorkspaceClient
from sqlalchemy.orm import Session

from server.models.schema_detection_result import (
    SchemaDetectionResult,
    EndpointType,
    DetectionStatus
)
from server.models.schema_detection_event import SchemaDetectionEvent
from server.models.model_endpoint import ModelEndpoint
from server.lib.structured_logger import StructuredLogger
from server.lib.distributed_tracing import get_correlation_id
from server.lib.database import get_db_session

logger = StructuredLogger(__name__)

# Foundation model chat format constants (T006)
FOUNDATION_MODEL_CHAT_SCHEMA = {
    "type": "object",
    "properties": {
        "messages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "role": {"type": "string"},
                    "content": {"type": "string"}
                }
            }
        },
        "max_tokens": {"type": "integer"},
        "temperature": {"type": "number"}
    },
    "required": ["messages"]
}

FOUNDATION_MODEL_CHAT_EXAMPLE = {
    "messages": [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": "Hello, how can you help me?"
        }
    ],
    "max_tokens": 150,
    "temperature": 0.7
}

# Generic fallback template constant (T007)
GENERIC_FALLBACK_TEMPLATE = {
    "input": "value",
    "_comment": "Schema detection unavailable. Consult model documentation for correct input format."
}


class SchemaDetectionService:
    """Service for automatic model input schema detection."""
    
    def __init__(self, user_token: str):
        """Initialize schema detection service with user token.
        
        Args:
            user_token: User's OAuth token for OBO authentication
        """
        self.user_token = user_token
        self.client = WorkspaceClient(token=user_token, auth_type="pat")
    
    async def detect_schema(
        self,
        endpoint_name: str,
        user_id: str
    ) -> SchemaDetectionResult:
        """Detect input schema for a serving endpoint.
        
        Main detection workflow:
        1. Get endpoint metadata from Serving Endpoints API
        2. Detect endpoint type (foundation, mlflow, unknown)
        3. For foundation: return chat format immediately
        4. For mlflow: query Model Registry with 5s timeout
        5. Generate example JSON from schema
        6. Log event to Lakebase
        7. Return SchemaDetectionResult
        
        Args:
            endpoint_name: Name of the serving endpoint
            user_id: Databricks user ID for logging
        
        Returns:
            SchemaDetectionResult with detected schema and example
        
        Raises:
            ValueError: Invalid endpoint name
            DatabricksError: API errors (propagated to caller)
        """
        start_time = datetime.utcnow()
        correlation_id = get_correlation_id()
        
        try:
            # Step 1: Get endpoint metadata
            from server.services.model_serving_service import ModelServingService
            serving_service = ModelServingService(user_token=self.user_token)
            endpoint = await serving_service.get_endpoint(endpoint_name)
            
            # Step 2: Detect endpoint type (T011)
            endpoint_type = self.detect_endpoint_type(endpoint)
            
            # Step 3: Foundation model fast path (T012)
            if endpoint_type == EndpointType.FOUNDATION_MODEL:
                latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                result = SchemaDetectionResult(
                    endpoint_name=endpoint_name,
                    detected_type=EndpointType.FOUNDATION_MODEL,
                    status=DetectionStatus.SUCCESS,
                    input_schema=FOUNDATION_MODEL_CHAT_SCHEMA,
                    example_json=FOUNDATION_MODEL_CHAT_EXAMPLE,
                    error_message=None,
                    latency_ms=latency_ms,
                    detected_at=datetime.utcnow()
                )
                
                # Log structured event (T013)
                logger.info(
                    "Foundation model schema detection complete",
                    endpoint_name=endpoint_name,
                    detected_type="FOUNDATION_MODEL",
                    status="SUCCESS",
                    latency_ms=latency_ms,
                    user_id=user_id
                )
                
                # Log to Lakebase
                await self._log_event(
                    correlation_id=correlation_id,
                    endpoint_name=endpoint_name,
                    detected_type="FOUNDATION_MODEL",
                    status="SUCCESS",
                    latency_ms=latency_ms,
                    error_details=None,
                    user_id=user_id
                )
                
                return result
            
            # MLflow and unknown types will be implemented in Phase 4 and 5
            raise NotImplementedError(
                f"Schema detection for {endpoint_type.value} endpoints will be implemented in Phase 4"
            )
            
        except Exception as e:
            # Error handling will be fully implemented in Phase 5
            logger.error(
                f"Schema detection failed: {str(e)}",
                exc_info=True,
                endpoint_name=endpoint_name,
                user_id=user_id
            )
            raise
    
    def detect_endpoint_type(self, endpoint: ModelEndpoint) -> EndpointType:
        """Detect endpoint type from metadata. (T011)
        
        Uses heuristic-based detection:
        - MLflow models have model_name and model_version in config.served_models
        - Foundation models have served_entities or specific naming patterns
        - Unknown for everything else
        
        Args:
            endpoint: Model endpoint metadata
        
        Returns:
            EndpointType enum value
        """
        # Check if endpoint has config
        if not endpoint.config:
            return EndpointType.UNKNOWN
        
        # Check for MLflow models (have served_models with model_name and version)
        if "served_models" in endpoint.config and endpoint.config["served_models"]:
            served_model = endpoint.config["served_models"][0]
            # MLflow models have model_name pointing to Unity Catalog
            if isinstance(served_model, dict) and "model_name" in served_model and served_model["model_name"]:
                model_name = served_model["model_name"]
                # Check if it has model_version (MLflow registered models)
                if "model_version" in served_model and served_model["model_version"]:
                    return EndpointType.MLFLOW_MODEL
        
        # Check for foundation models (have served_entities)
        if "served_entities" in endpoint.config and endpoint.config["served_entities"]:
            return EndpointType.FOUNDATION_MODEL
        
        # Heuristic: Check endpoint name for foundation model keywords
        endpoint_name_lower = endpoint.endpoint_name.lower()
        foundation_keywords = ['claude', 'gpt', 'llama', 'mistral', 'chat', 'foundation']
        
        if any(keyword in endpoint_name_lower for keyword in foundation_keywords):
            return EndpointType.FOUNDATION_MODEL
        
        return EndpointType.UNKNOWN
    
    async def retrieve_mlflow_schema(
        self,
        model_name: str,
        version: str
    ) -> dict | None:
        """Retrieve MLflow model input schema from Model Registry.
        
        Queries Unity Catalog Model Registry using Databricks SDK with
        OBO authentication and 5s timeout.
        
        Args:
            model_name: Fully-qualified model name (e.g., "main.default.model")
            version: Model version string
        
        Returns:
            JSON Schema dict or None if unavailable
        """
        # Implementation will be added in Phase 4 (User Story 2)
        raise NotImplementedError("retrieve_mlflow_schema will be implemented in Phase 4")
    
    def generate_example_json(self, schema: dict) -> dict:
        """Generate example JSON from schema definition.
        
        Creates realistic sample values based on JSON Schema types:
        - strings → "example text"
        - integers → 42
        - floats → 3.14
        - booleans → true
        - arrays → sample items
        
        Args:
            schema: JSON Schema definition
        
        Returns:
            Example input JSON with realistic sample values
        """
        # Implementation will be added in Phase 4 (User Story 2)
        raise NotImplementedError("generate_example_json will be implemented in Phase 4")
    
    async def log_detection_event(
        self,
        event: SchemaDetectionEvent
    ) -> None:
        """Log schema detection event to Lakebase. (T008)
        
        Persists detection events for observability and debugging.
        All queries filtered by user_id for multi-user data isolation.
        
        Args:
            event: SchemaDetectionEvent to persist
        """
        try:
            # Get database session
            session_gen = get_db_session()
            session: Session = next(session_gen)
            
            try:
                # Insert event
                session.add(event)
                session.commit()
                
                logger.info(
                    "Schema detection event logged",
                    correlation_id=event.correlation_id,
                    endpoint_name=event.endpoint_name,
                    detected_type=event.detected_type,
                    status=event.status,
                    user_id=event.user_id
                )
            finally:
                session.close()
                
        except Exception as e:
            logger.error(
                f"Failed to log schema detection event: {str(e)}",
                exc_info=True,
                endpoint_name=event.endpoint_name,
                user_id=event.user_id
            )
            # Don't raise - logging failure shouldn't break detection
    
    async def _log_event(
        self,
        correlation_id: str,
        endpoint_name: str,
        detected_type: str,
        status: str,
        latency_ms: int,
        error_details: str | None,
        user_id: str
    ) -> None:
        """Helper to create and log detection event.
        
        Args:
            correlation_id: Request correlation ID
            endpoint_name: Endpoint name
            detected_type: Detected endpoint type
            status: Detection status
            latency_ms: Detection latency
            error_details: Error message if failed
            user_id: User ID
        """
        event = SchemaDetectionEvent(
            correlation_id=correlation_id,
            endpoint_name=endpoint_name,
            detected_type=detected_type,
            status=status,
            latency_ms=latency_ms,
            error_details=error_details,
            user_id=user_id,
            created_at=datetime.utcnow()
        )
        
        await self.log_detection_event(event)

