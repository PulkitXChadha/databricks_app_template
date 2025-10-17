# Data Model: Automatic Model Input Schema Detection

**Feature**: 004-dynamic-endpoint-input-schema  
**Date**: October 17, 2025  
**Status**: Complete

## Overview

This document defines the data entities, database schema, API models, and validation rules for automatic model input schema detection. All entities follow the project's type safety requirements (Python Pydantic models, TypeScript interfaces) and align with constitutional principles.

---

## 1. Core Entities

### 1.1 SchemaDetectionResult

Represents the outcome of automatic schema detection for a serving endpoint.

**Purpose**: API response model containing detected schema, example JSON, status, and metadata

**Fields**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `endpoint_name` | `str` | Yes | Name of the serving endpoint | Non-empty string |
| `detected_type` | `EndpointType` | Yes | Detected model type | Enum: "FOUNDATION_MODEL", "MLFLOW_MODEL", "UNKNOWN" |
| `status` | `DetectionStatus` | Yes | Detection result status | Enum: "SUCCESS", "FAILURE", "TIMEOUT" |
| `schema` | `dict \| None` | No | JSON Schema definition (if available) | Valid JSON object or null |
| `example_json` | `dict` | Yes | Generated example input JSON | Valid JSON object |
| `error_message` | `str \| None` | No | Error description (if status != SUCCESS) | Optional string |
| `latency_ms` | `int` | Yes | Schema detection latency in milliseconds | Positive integer |
| `detected_at` | `datetime` | Yes | Timestamp of detection | ISO 8601 UTC timestamp |

**State Transitions**:
- Initial state: N/A (created per request, not persisted in application state)
- No state transitions (immutable response object)

**Relationships**:
- None (ephemeral response object, not persisted in database except via logs)

**Python Model** (`server/models/schema_detection_result.py`):
```python
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Any

class EndpointType(str, Enum):
    FOUNDATION_MODEL = "FOUNDATION_MODEL"
    MLFLOW_MODEL = "MLFLOW_MODEL"
    UNKNOWN = "UNKNOWN"

class DetectionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    TIMEOUT = "TIMEOUT"

class SchemaDetectionResult(BaseModel):
    endpoint_name: str = Field(..., description="Name of the serving endpoint")
    detected_type: EndpointType = Field(..., description="Detected model type")
    status: DetectionStatus = Field(..., description="Detection result status")
    schema: dict[str, Any] | None = Field(default=None, description="JSON Schema definition")
    example_json: dict[str, Any] = Field(..., description="Generated example input JSON")
    error_message: str | None = Field(default=None, description="Error description if failed")
    latency_ms: int = Field(..., description="Schema detection latency in milliseconds", ge=0)
    detected_at: datetime = Field(default_factory=datetime.utcnow, description="Detection timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "endpoint_name": "databricks-claude-sonnet-4",
                "detected_type": "FOUNDATION_MODEL",
                "status": "SUCCESS",
                "schema": {"type": "object", "properties": {"messages": {"type": "array"}}},
                "example_json": {
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Hello!"}
                    ],
                    "max_tokens": 150
                },
                "error_message": None,
                "latency_ms": 245,
                "detected_at": "2025-10-17T10:30:00Z"
            }
        }
```

**TypeScript Interface** (auto-generated from OpenAPI spec):
```typescript
// client/src/fastapi_client/models/SchemaDetectionResult.ts
export enum EndpointType {
  FOUNDATION_MODEL = "FOUNDATION_MODEL",
  MLFLOW_MODEL = "MLFLOW_MODEL",
  UNKNOWN = "UNKNOWN"
}

export enum DetectionStatus {
  SUCCESS = "SUCCESS",
  FAILURE = "FAILURE",
  TIMEOUT = "TIMEOUT"
}

export interface SchemaDetectionResult {
  endpoint_name: string;
  detected_type: EndpointType;
  status: DetectionStatus;
  schema: Record<string, any> | null;
  example_json: Record<string, any>;
  error_message: string | null;
  latency_ms: number;
  detected_at: string;  // ISO 8601 string
}
```

---

### 1.2 SchemaDetectionEvent

Represents a logged schema detection event in Lakebase for observability and debugging.

**Purpose**: Persistent audit log of all schema detection attempts with correlation IDs for tracing

**Fields**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `id` | `int` | Yes | Primary key (auto-increment) | Positive integer |
| `correlation_id` | `str` | Yes | Request correlation ID (from X-Correlation-ID header or generated UUID) | UUID v4 format |
| `endpoint_name` | `str` | Yes | Name of the serving endpoint | Non-empty string |
| `detected_type` | `str` | Yes | Detected model type | Enum: "FOUNDATION_MODEL", "MLFLOW_MODEL", "UNKNOWN" |
| `status` | `str` | Yes | Detection result status | Enum: "SUCCESS", "FAILURE", "TIMEOUT" |
| `latency_ms` | `int` | Yes | Schema detection latency in milliseconds | Positive integer |
| `error_details` | `str \| None` | No | Error message or stack trace (if status != SUCCESS) | Optional text |
| `user_id` | `str` | Yes | Databricks user ID who triggered detection | Non-empty string |
| `created_at` | `datetime` | Yes | Event creation timestamp | UTC timestamp |

**Database Table** (`schema_detection_events`):

```sql
CREATE TABLE schema_detection_events (
    id SERIAL PRIMARY KEY,
    correlation_id VARCHAR(36) NOT NULL,
    endpoint_name VARCHAR(255) NOT NULL,
    detected_type VARCHAR(50) NOT NULL CHECK (detected_type IN ('FOUNDATION_MODEL', 'MLFLOW_MODEL', 'UNKNOWN')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('SUCCESS', 'FAILURE', 'TIMEOUT')),
    latency_ms INTEGER NOT NULL CHECK (latency_ms >= 0),
    error_details TEXT,
    user_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for query performance
    INDEX idx_correlation_id (correlation_id),
    INDEX idx_user_id (user_id),
    INDEX idx_endpoint_name (endpoint_name),
    INDEX idx_created_at (created_at DESC)
);
```

**SQLAlchemy Model** (`server/models/schema_detection_event.py`):

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class SchemaDetectionEvent(Base):
    __tablename__ = 'schema_detection_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    correlation_id = Column(String(36), nullable=False, index=True)
    endpoint_name = Column(String(255), nullable=False, index=True)
    detected_type = Column(
        String(50), 
        nullable=False,
        CheckConstraint("detected_type IN ('FOUNDATION_MODEL', 'MLFLOW_MODEL', 'UNKNOWN')")
    )
    status = Column(
        String(20),
        nullable=False,
        CheckConstraint("status IN ('SUCCESS', 'FAILURE', 'TIMEOUT')")
    )
    latency_ms = Column(Integer, nullable=False, CheckConstraint("latency_ms >= 0"))
    error_details = Column(Text, nullable=True)
    user_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<SchemaDetectionEvent(id={self.id}, endpoint={self.endpoint_name}, status={self.status})>"
```

**Alembic Migration** (`migrations/versions/004_create_schema_detection_events.py`):

```python
"""Create schema_detection_events table

Revision ID: 004_schema_detection_events
Revises: 003_add_user_id_columns
Create Date: 2025-10-17 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '004_schema_detection_events'
down_revision = '003_add_user_id_columns'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'schema_detection_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('correlation_id', sa.String(length=36), nullable=False),
        sa.Column('endpoint_name', sa.String(length=255), nullable=False),
        sa.Column('detected_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("detected_type IN ('FOUNDATION_MODEL', 'MLFLOW_MODEL', 'UNKNOWN')"),
        sa.CheckConstraint("status IN ('SUCCESS', 'FAILURE', 'TIMEOUT')"),
        sa.CheckConstraint("latency_ms >= 0")
    )
    
    # Create indexes for query performance
    op.create_index('idx_correlation_id', 'schema_detection_events', ['correlation_id'])
    op.create_index('idx_user_id', 'schema_detection_events', ['user_id'])
    op.create_index('idx_endpoint_name', 'schema_detection_events', ['endpoint_name'])
    op.create_index('idx_created_at', 'schema_detection_events', ['created_at'], postgresql_ops={'created_at': 'DESC'})

def downgrade():
    op.drop_index('idx_created_at', table_name='schema_detection_events')
    op.drop_index('idx_endpoint_name', table_name='schema_detection_events')
    op.drop_index('idx_user_id', table_name='schema_detection_events')
    op.drop_index('idx_correlation_id', table_name='schema_detection_events')
    op.drop_table('schema_detection_events')
```

---

### 1.3 ModelEndpointSchema (Conceptual Entity)

Represents the input schema definition for a serving endpoint (not persisted, derived from Model Registry).

**Purpose**: Intermediate data structure for schema information retrieved from Model Registry or generated for foundation models

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `endpoint_name` | `str` | Yes | Name of the serving endpoint |
| `model_type` | `EndpointType` | Yes | Foundation, MLflow, or Unknown |
| `input_schema` | `dict` | No | JSON Schema definition (MLflow models only) |
| `input_example` | `dict` | Yes | Generated example input JSON |
| `required_fields` | `list[str]` | No | List of required field names (for MLflow models) |
| `optional_fields` | `list[str]` | No | List of optional field names (for MLflow models) |

**Note**: This entity is NOT persisted in database. It's a runtime data structure used during schema generation. Frontend receives `SchemaDetectionResult` which includes the relevant schema information.

---

## 2. API Request/Response Models

### 2.1 DetectSchemaRequest

Request to detect schema for a specific endpoint.

**HTTP Method**: `GET`  
**Endpoint**: `/api/model-serving/endpoints/{endpoint_name}/schema`  
**Authentication**: Required (OBO user token)

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `endpoint_name` | `str` | Yes | Name of the serving endpoint |

**Response**: `SchemaDetectionResult` (see Section 1.1)

**Errors**:
- `401 Unauthorized`: Missing or invalid authentication token
- `404 Not Found`: Endpoint does not exist
- `503 Service Unavailable`: Model Registry API unavailable

---

### 2.2 Enhanced ModelEndpointResponse

Extends existing `ModelEndpointResponse` to include schema detection hint.

**Purpose**: Optionally include schema availability hint when listing endpoints

**Added Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `has_schema_support` | `bool` | Yes | Whether endpoint supports automatic schema detection |

**Note**: This is a non-breaking enhancement. Existing `ModelEndpointResponse` model already has most fields. We add one optional boolean to indicate schema support.

**Python Model Enhancement** (`server/models/model_endpoint.py`):
```python
# Add field to existing ModelEndpointResponse
class ModelEndpointResponse(BaseModel):
    # ... existing fields ...
    has_schema_support: bool = Field(
        default=False,
        description="Whether endpoint supports automatic schema detection"
    )
```

---

## 3. Validation Rules

### 3.1 Endpoint Name Validation

- **Rule**: Endpoint name must match pattern `^[a-zA-Z0-9_-]+$`
- **Rationale**: Databricks endpoint naming constraints
- **Enforcement**: FastAPI path parameter validation

### 3.2 Schema JSON Validation

- **Rule**: Schema must be valid JSON Schema Draft 7 format (if present)
- **Rationale**: Ensures schema is parseable and follows standard
- **Enforcement**: JSON schema validator in schema generation service

### 3.3 Example JSON Validation

- **Rule**: Generated example JSON must parse as valid JSON
- **Rationale**: Frontend JSON editor expects valid JSON
- **Enforcement**: `json.dumps()` / `json.loads()` round-trip test

### 3.4 Correlation ID Validation

- **Rule**: Correlation ID must be UUID v4 format if client-provided
- **Rationale**: Consistent tracing format
- **Enforcement**: Middleware validation with fallback to server-generated UUID

### 3.5 User ID Validation

- **Rule**: User ID must be non-empty string extracted from Databricks auth context
- **Rationale**: Multi-user data isolation (Constitution Principle IX)
- **Enforcement**: FastAPI dependency injection with auth validation

---

## 4. Browser Storage Schema (sessionStorage)

### 4.1 Schema Cache Entry

**Key**: `schema_{endpoint_name}`  
**Value**: JSON-serialized `SchemaDetectionResult`

**Example**:
```json
{
  "endpoint_name": "databricks-claude-sonnet-4",
  "detected_type": "FOUNDATION_MODEL",
  "status": "SUCCESS",
  "schema": null,
  "example_json": {
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 150
  },
  "error_message": null,
  "latency_ms": 123,
  "detected_at": "2025-10-17T10:30:00Z"
}
```

**Lifecycle**:
- **Created**: After first successful schema detection for an endpoint
- **Read**: When user selects previously-detected endpoint
- **Updated**: Never (immutable per session)
- **Deleted**: On browser tab close (automatic sessionStorage cleanup)

---

## 5. Service Layer Contracts

### 5.1 SchemaDetectionService

**Purpose**: Core business logic for schema detection

**Methods**:

```python
class SchemaDetectionService:
    async def detect_schema(
        self, 
        endpoint_name: str, 
        user_token: str, 
        user_id: str
    ) -> SchemaDetectionResult:
        """
        Detect input schema for a serving endpoint.
        
        Args:
            endpoint_name: Name of the serving endpoint
            user_token: User's OAuth token for OBO authentication
            user_id: Databricks user ID for logging
        
        Returns:
            SchemaDetectionResult with detected schema and example
        
        Raises:
            ValueError: Invalid endpoint name
            DatabricksError: API errors (propagated to caller)
        """
        pass
    
    async def log_detection_event(
        self, 
        event: SchemaDetectionEvent
    ) -> None:
        """
        Log schema detection event to Lakebase.
        
        Args:
            event: SchemaDetectionEvent to persist
        """
        pass
    
    def detect_endpoint_type(
        self, 
        endpoint: ModelEndpoint
    ) -> EndpointType:
        """
        Detect endpoint type from metadata.
        
        Args:
            endpoint: Model endpoint metadata
        
        Returns:
            EndpointType enum value
        """
        pass
    
    async def retrieve_mlflow_schema(
        self, 
        model_name: str, 
        version: str
    ) -> dict | None:
        """
        Retrieve MLflow model input schema from Model Registry.
        
        Args:
            model_name: Fully-qualified model name (e.g., "main.default.model")
            version: Model version string
        
        Returns:
            JSON Schema dict or None if unavailable
        """
        pass
    
    def generate_example_json(
        self, 
        schema: dict
    ) -> dict:
        """
        Generate example JSON from schema definition.
        
        Args:
            schema: JSON Schema definition
        
        Returns:
            Example input JSON with realistic sample values
        """
        pass
```

---

## 6. Database Queries

### 6.1 Query Detection Events by User

```sql
-- Get all schema detection events for a user
SELECT * FROM schema_detection_events
WHERE user_id = :user_id
ORDER BY created_at DESC
LIMIT 100;
```

### 6.2 Query Detection Events by Correlation ID

```sql
-- Get all events for a specific request (correlation ID tracing)
SELECT * FROM schema_detection_events
WHERE correlation_id = :correlation_id
ORDER BY created_at ASC;
```

### 6.3 Query Detection Failure Rate

```sql
-- Calculate failure rate for observability
SELECT 
    endpoint_name,
    COUNT(*) as total_detections,
    SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
    SUM(CASE WHEN status = 'FAILURE' THEN 1 ELSE 0 END) as failures,
    SUM(CASE WHEN status = 'TIMEOUT' THEN 1 ELSE 0 END) as timeouts,
    AVG(latency_ms) as avg_latency_ms
FROM schema_detection_events
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY endpoint_name
ORDER BY total_detections DESC;
```

---

## 7. Multi-User Data Isolation

**Requirement**: All Lakebase queries MUST filter by `user_id` (Constitution Principle IX)

**Implementation**:

```python
# CORRECT: Filter by user_id
async def get_user_detection_history(user_id: str) -> list[SchemaDetectionEvent]:
    async with get_db_session() as session:
        result = await session.execute(
            select(SchemaDetectionEvent)
            .where(SchemaDetectionEvent.user_id == user_id)
            .order_by(SchemaDetectionEvent.created_at.desc())
            .limit(100)
        )
        return result.scalars().all()

# INCORRECT: No user_id filter (security violation)
async def get_all_detection_events() -> list[SchemaDetectionEvent]:
    # ❌ BAD: Exposes all users' data
    async with get_db_session() as session:
        result = await session.execute(
            select(SchemaDetectionEvent)
            .order_by(SchemaDetectionEvent.created_at.desc())
        )
        return result.scalars().all()
```

**Testing**: Multi-user isolation MUST be tested with multiple user accounts (see Phase 2 testing requirements).

---

## 8. Summary

**New Database Tables**: 1 (`schema_detection_events`)  
**New API Models**: 2 (`SchemaDetectionResult`, `SchemaDetectionEvent`)  
**Enhanced Existing Models**: 1 (`ModelEndpointResponse` + `has_schema_support` field)  
**Browser Storage Entries**: 1 per endpoint (sessionStorage)  
**Service Layer**: 1 new service (`SchemaDetectionService`)

**Type Safety**: ✅ All entities have Pydantic models (Python) and TypeScript interfaces (auto-generated)  
**Validation**: ✅ Comprehensive validation rules defined  
**Multi-User Isolation**: ✅ All queries filtered by user_id  
**Observability**: ✅ All events logged to Lakebase with correlation IDs

