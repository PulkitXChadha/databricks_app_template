"""Schema Detection Service.

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

from server.lib.database import get_db_session
from server.lib.distributed_tracing import get_correlation_id
from server.lib.structured_logger import StructuredLogger
from server.models.model_endpoint import ModelEndpoint
from server.models.schema_detection_event import SchemaDetectionEvent
from server.models.schema_detection_result import (
    DetectionStatus,
    EndpointType,
    SchemaDetectionResult,
)

logger = StructuredLogger(__name__)

# Foundation model chat format constants (T006)
FOUNDATION_MODEL_CHAT_SCHEMA = {
    'type': 'object',
    'properties': {
        'messages': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'role': {'type': 'string'},
                    'content': {'type': 'string'}
                }
            }
        },
        'max_tokens': {'type': 'integer'},
        'temperature': {'type': 'number'}
    },
    'required': ['messages']
}

FOUNDATION_MODEL_CHAT_EXAMPLE = {
    'messages': [
        {
            'role': 'system',
            'content': 'You are a helpful assistant.'
        },
        {
            'role': 'user',
            'content': 'Hello, how can you help me?'
        }
    ],
    'max_tokens': 150,
    'temperature': 0.7
}

# Generic fallback template constant (T007)
GENERIC_FALLBACK_TEMPLATE = {
    'input': 'value',
    '_comment': 'Schema detection unavailable. Consult model documentation for correct input format.'
}


class SchemaDetectionService:
    """Service for automatic model input schema detection."""

    def __init__(self, user_token: str):
        """Initialize schema detection service with user token.

        Args:
            user_token: User's OAuth token for OBO authentication
        """
        self.user_token = user_token
        self.client = WorkspaceClient(token=user_token, auth_type='pat')

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
                    'Foundation model schema detection complete',
                    endpoint_name=endpoint_name,
                    detected_type='FOUNDATION_MODEL',
                    status='SUCCESS',
                    latency_ms=latency_ms,
                    user_id=user_id
                )

                # Log to Lakebase
                await self._log_event(
                    correlation_id=correlation_id,
                    endpoint_name=endpoint_name,
                    detected_type='FOUNDATION_MODEL',
                    status='SUCCESS',
                    latency_ms=latency_ms,
                    error_details=None,
                    user_id=user_id
                )

                return result

            # Step 4: MLflow model path (T023)
            elif endpoint_type == EndpointType.MLFLOW_MODEL:
                # Extract model name and version from endpoint config
                if not endpoint.config or 'served_models' not in endpoint.config:
                    raise ValueError('MLflow endpoint missing served_models configuration')

                served_model = endpoint.config['served_models'][0]
                model_name = served_model.get('model_name')
                model_version = served_model.get('model_version')

                if not model_name or not model_version:
                    raise ValueError('MLflow endpoint missing model_name or model_version')

                # Query Model Registry with timeout
                try:
                    mlflow_schema = await asyncio.wait_for(
                        self.retrieve_mlflow_schema(model_name, model_version),
                        timeout=5.0
                    )

                    if mlflow_schema:
                        # Generate example JSON from schema (T024 - schema parsing is in retrieve_mlflow_schema)
                        example_json = self.generate_example_json(mlflow_schema)
                        latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

                        result = SchemaDetectionResult(
                            endpoint_name=endpoint_name,
                            detected_type=EndpointType.MLFLOW_MODEL,
                            status=DetectionStatus.SUCCESS,
                            input_schema=mlflow_schema if isinstance(mlflow_schema, dict) else None,
                            example_json=example_json,
                            error_message=None,
                            latency_ms=latency_ms,
                            detected_at=datetime.utcnow()
                        )

                        # Log structured event (T025)
                        logger.info(
                            'MLflow model schema detection complete',
                            endpoint_name=endpoint_name,
                            detected_type='MLFLOW_MODEL',
                            status='SUCCESS',
                            latency_ms=latency_ms,
                            user_id=user_id,
                            model_name=model_name,
                            model_version=model_version
                        )

                        # Log to Lakebase
                        await self._log_event(
                            correlation_id=correlation_id,
                            endpoint_name=endpoint_name,
                            detected_type='MLFLOW_MODEL',
                            status='SUCCESS',
                            latency_ms=latency_ms,
                            error_details=None,
                            user_id=user_id
                        )

                        return result
                    else:
                        # Schema not available, will fallback in Phase 5
                        raise ValueError('Schema not available in Model Registry')

                except asyncio.TimeoutError:
                    # Timeout fallback will be implemented in Phase 5
                    raise

            # Step 5: Unknown endpoint type fallback (T029)
            else:
                # Unknown type, use generic fallback template
                latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

                result = SchemaDetectionResult(
                    endpoint_name=endpoint_name,
                    detected_type=EndpointType.UNKNOWN,
                    status=DetectionStatus.FAILURE,
                    input_schema=None,
                    example_json=GENERIC_FALLBACK_TEMPLATE,
                    error_message='Unable to detect endpoint type. Please consult model documentation.',
                    latency_ms=latency_ms,
                    detected_at=datetime.utcnow()
                )

                # Log structured event (T030)
                logger.warning(
                    'Unknown endpoint type - using fallback template',
                    endpoint_name=endpoint_name,
                    detected_type='UNKNOWN',
                    status='FAILURE',
                    latency_ms=latency_ms,
                    user_id=user_id
                )

                # Log to Lakebase
                await self._log_event(
                    correlation_id=correlation_id,
                    endpoint_name=endpoint_name,
                    detected_type='UNKNOWN',
                    status='FAILURE',
                    latency_ms=latency_ms,
                    error_details='Unable to detect endpoint type',
                    user_id=user_id
                )

                return result

        except asyncio.TimeoutError:
            # Timeout fallback (T028)
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            result = SchemaDetectionResult(
                endpoint_name=endpoint_name,
                detected_type=EndpointType.UNKNOWN,
                status=DetectionStatus.TIMEOUT,
                input_schema=None,
                example_json=GENERIC_FALLBACK_TEMPLATE,
                error_message='Schema retrieval timed out after 5 seconds',
                latency_ms=latency_ms,
                detected_at=datetime.utcnow()
            )

            # Log structured event (T030)
            logger.warning(
                'Schema detection timeout',
                endpoint_name=endpoint_name,
                detected_type='UNKNOWN',
                status='TIMEOUT',
                latency_ms=latency_ms,
                user_id=user_id
            )

            # Log to Lakebase
            await self._log_event(
                correlation_id=correlation_id,
                endpoint_name=endpoint_name,
                detected_type='UNKNOWN',
                status='TIMEOUT',
                latency_ms=latency_ms,
                error_details='Schema retrieval timed out after 5 seconds',
                user_id=user_id
            )

            return result

        except Exception as e:
            # Error fallback (T029)
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            error_msg = str(e)

            # Check for 403 permission errors
            if '403' in error_msg or 'permission' in error_msg.lower() or 'forbidden' in error_msg.lower():
                error_message = f"Permission Denied: {error_msg}. You may not have access to this endpoint's schema."
                status_msg = 'PERMISSION_DENIED'
            else:
                error_message = f'Schema detection failed: {error_msg}'
                status_msg = 'FAILURE'

            result = SchemaDetectionResult(
                endpoint_name=endpoint_name,
                detected_type=EndpointType.UNKNOWN,
                status=DetectionStatus.FAILURE,
                input_schema=None,
                example_json=GENERIC_FALLBACK_TEMPLATE,
                error_message=error_message,
                latency_ms=latency_ms,
                detected_at=datetime.utcnow()
            )

            # Log structured event with stack trace (T030)
            logger.error(
                f'Schema detection failed: {error_msg}',
                exc_info=True,
                endpoint_name=endpoint_name,
                detected_type='UNKNOWN',
                status=status_msg,
                latency_ms=latency_ms,
                user_id=user_id,
                error_type=type(e).__name__
            )

            # Log to Lakebase
            await self._log_event(
                correlation_id=correlation_id,
                endpoint_name=endpoint_name,
                detected_type='UNKNOWN',
                status='FAILURE',
                latency_ms=latency_ms,
                error_details=error_message,
                user_id=user_id
            )

            return result

    def detect_endpoint_type(self, endpoint: ModelEndpoint) -> EndpointType:
        """Detect endpoint type from metadata. (T011).

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
        if 'served_models' in endpoint.config and endpoint.config['served_models']:
            served_model = endpoint.config['served_models'][0]
            # MLflow models have model_name pointing to Unity Catalog
            if isinstance(served_model, dict) and 'model_name' in served_model and served_model['model_name']:
                # Check if it has model_version (MLflow registered models)
                if 'model_version' in served_model and served_model['model_version']:
                    return EndpointType.MLFLOW_MODEL

        # Check for foundation models (have served_entities)
        if 'served_entities' in endpoint.config and endpoint.config['served_entities']:
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
        """Retrieve MLflow model input schema from Model Registry. (T020).

        Queries Unity Catalog Model Registry using Databricks SDK with
        OBO authentication and 5s timeout. Includes exponential backoff
        retry logic for 429 rate limit errors.

        Args:
            model_name: Fully-qualified model name (e.g., "main.default.model")
            version: Model version string

        Returns:
            JSON Schema dict or None if unavailable
        """
        # Retry configuration for 429 rate limit errors (exponential backoff)
        max_retries = 3
        retry_delays = [2, 4, 8]  # seconds

        for attempt in range(max_retries + 1):
            try:
                # Query Model Registry with 5s timeout
                model_version = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.model_registry.get_model_version,
                        full_name=model_name,
                        version=version
                    ),
                    timeout=5.0
                )

                # Check if model version has signature with input schema
                if not hasattr(model_version, 'signature') or not model_version.signature:
                    logger.warning(
                        'MLflow model has no signature',
                        model_name=model_name,
                        version=version
                    )
                    return None

                # Parse signature JSON (MLflow ModelSignature format)
                # The signature field contains input/output schema as JSON
                if hasattr(model_version.signature, 'inputs') and model_version.signature.inputs:
                    # Parse inputs field (may be JSON string or dict)
                    inputs = model_version.signature.inputs
                    if isinstance(inputs, str):
                        inputs_schema = json.loads(inputs)
                    else:
                        inputs_schema = inputs

                    logger.info(
                        'MLflow schema retrieved successfully',
                        model_name=model_name,
                        version=version,
                        schema_fields=len(inputs_schema) if isinstance(inputs_schema, list) else 0
                    )

                    return inputs_schema

                return None

            except asyncio.TimeoutError:
                logger.warning(
                    'MLflow schema retrieval timeout',
                    model_name=model_name,
                    version=version,
                    attempt=attempt + 1
                )
                raise  # Don't retry on timeout

            except Exception as e:
                error_msg = str(e)

                # Check for 429 rate limit error
                if '429' in error_msg or 'rate limit' in error_msg.lower():
                    if attempt < max_retries:
                        delay = retry_delays[attempt]
                        logger.warning(
                            'Rate limit encountered, retrying',
                            model_name=model_name,
                            version=version,
                            attempt=attempt + 1,
                            retry_delay_seconds=delay
                        )
                        await asyncio.sleep(delay)
                        continue  # Retry
                    else:
                        logger.error(
                            'Rate limit retry exhausted',
                            model_name=model_name,
                            version=version,
                            attempts=max_retries + 1
                        )
                        raise

                # For other errors, log and return None
                logger.warning(
                    f'Failed to retrieve MLflow schema: {error_msg}',
                    model_name=model_name,
                    version=version,
                    error_type=type(e).__name__
                )
                return None

    def generate_example_json(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate example JSON from schema definition. (T021).

        Creates realistic sample values based on JSON Schema types:
        - strings → "example text"
        - integers → 42
        - floats → 3.14
        - booleans → true
        - arrays → sample items (up to 3 for primitives, 1 for objects)

        Args:
            schema: JSON Schema definition or MLflow schema format (list of field definitions)

        Returns:
            Example input JSON with realistic sample values
        """
        example = {}

        # Handle MLflow schema format (list of field definitions)
        # Example: [{"name": "field1", "type": "double"}, {"name": "field2", "type": "string"}]
        if isinstance(schema, list):
            for field_def in schema:
                if isinstance(field_def, dict) and 'name' in field_def:
                    field_name = field_def['name']
                    field_type = field_def.get('type', 'string')

                    # Map MLflow types to sample values
                    if field_type in ['double', 'float']:
                        example[field_name] = 3.14
                    elif field_type in ['integer', 'long', 'int']:
                        example[field_name] = 42
                    elif field_type in ['string', 'str']:
                        example[field_name] = 'example text'
                    elif field_type in ['boolean', 'bool']:
                        example[field_name] = True
                    elif field_type == 'array':
                        # Generate sample array (3 items for primitives)
                        example[field_name] = [1.0, 2.0, 3.0]
                    else:
                        example[field_name] = None

            return example

        # Handle JSON Schema format (dict with "properties")
        # Example: {"type": "object", "properties": {"field1": {"type": "number"}}}
        if not isinstance(schema, dict):
            return {'input': 'value'}

        properties = schema.get('properties', {})

        for field_name, field_spec in properties.items():
            if not isinstance(field_spec, dict):
                example[field_name] = None
                continue

            field_type = field_spec.get('type')

            if field_type == 'string':
                example[field_name] = 'example text'
            elif field_type == 'integer':
                example[field_name] = 42
            elif field_type == 'number':
                example[field_name] = 3.14
            elif field_type == 'boolean':
                example[field_name] = True
            elif field_type == 'array':
                # Generate array with sample items based on items type
                items_spec = field_spec.get('items', {})
                if isinstance(items_spec, dict):
                    items_type = items_spec.get('type', 'string')

                    if items_type == 'string':
                        example[field_name] = ['example']
                    elif items_type in ['integer', 'number']:
                        # Generate 3 items for primitive arrays
                        example[field_name] = [1.0, 2.0, 3.0]
                    elif items_type == 'object':
                        # Generate 1 nested structure for object arrays (keep readable)
                        nested_example = self.generate_example_json(items_spec)
                        example[field_name] = [nested_example] if nested_example else []
                    else:
                        example[field_name] = []
                else:
                    example[field_name] = []
            elif field_type == 'object':
                # Nested object - recurse
                nested_example = self.generate_example_json(field_spec)
                example[field_name] = nested_example if nested_example else {}
            else:
                example[field_name] = None

        return example

    async def log_detection_event(
        self,
        event: SchemaDetectionEvent
    ) -> None:
        """Log schema detection event to Lakebase. (T008).

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
                    'Schema detection event logged',
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
                f'Failed to log schema detection event: {str(e)}',
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

