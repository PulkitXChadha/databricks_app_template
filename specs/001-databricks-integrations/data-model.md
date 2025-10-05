# Data Model: Databricks Service Integrations

**Feature**: `001-databricks-integrations`  
**Date**: Saturday, October 4, 2025  
**Status**: Complete

## Overview

This document defines the data entities, relationships, and validation rules for the Databricks service integrations feature. Entities map to both Unity Catalog tables (lakehouse data) and Lakebase tables (transactional data).

---

## Entity Definitions

### 1. User Session

**Purpose**: Represents an authenticated user's interaction session with the application.

**Source**: Derived from Databricks SDK authentication

**Fields**:
- `user_id` (string, required): Unique user identifier from Databricks workspace
- `user_name` (string, required): Display name of the user
- `email` (string, required): Primary email address
- `active` (boolean, required): Whether user account is active
- `session_token` (string, required): Authentication token for the session
- `workspace_url` (string, required): Databricks workspace URL
- `created_at` (timestamp, required): When session was created
- `expires_at` (timestamp, required): When session token expires

**Validation Rules**:
- `user_id` must not be empty
- `email` must be valid email format
- `expires_at` must be after `created_at`
- `session_token` must be validated with Databricks SDK

**State Transitions**:
```
New → Authenticated → Active → Expired
                    ↓
                 Invalidated
```

**Python Model**:
```python
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class UserSession(BaseModel):
    user_id: str = Field(..., min_length=1)
    user_name: str = Field(..., min_length=1)
    email: EmailStr
    active: bool = True
    session_token: str = Field(..., min_length=10)
    workspace_url: str = Field(..., pattern=r"^https://.*\.databricks\.com$")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
```

---

### 2. Data Source

**Purpose**: Represents a Unity Catalog table that the application can query.

**Source**: Unity Catalog managed tables

**Fields**:
- `catalog_name` (string, required): Unity Catalog name (e.g., "main")
- `schema_name` (string, required): Schema name within catalog (e.g., "samples")
- `table_name` (string, required): Table name (e.g., "demo_data")
- `full_name` (string, computed): Fully qualified name `catalog.schema.table`
- `columns` (array, required): List of column definitions
  - `name` (string): Column name
  - `data_type` (string): Column data type
  - `nullable` (boolean): Whether column allows NULL
- `row_count` (integer, optional): Approximate number of rows
- `size_bytes` (integer, optional): Approximate table size in bytes
- `owner` (string, required): Table owner user/group
- `access_level` (enum, required): User's access level (READ, WRITE, NONE)
- `last_refreshed` (timestamp, required): When metadata was last fetched

**Validation Rules**:
- `catalog_name`, `schema_name`, `table_name` must be valid SQL identifiers (alphanumeric + underscore)
- `full_name` must equal `{catalog_name}.{schema_name}.{table_name}`
- `columns` array must have at least one column
- `access_level` must be checked before any operation

**Relationships**:
- One `DataSource` → Many `QueryResult` (one table can be queried multiple times)
- One `UserSession` → Many `DataSource` (user can access multiple tables based on permissions)

**Python Model**:
```python
from enum import Enum
from pydantic import BaseModel, Field, validator
from datetime import datetime

class AccessLevel(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    NONE = "NONE"

class ColumnDefinition(BaseModel):
    name: str
    data_type: str
    nullable: bool = True

class DataSource(BaseModel):
    catalog_name: str = Field(..., pattern=r"^[a-zA-Z0-9_]+$")
    schema_name: str = Field(..., pattern=r"^[a-zA-Z0-9_]+$")
    table_name: str = Field(..., pattern=r"^[a-zA-Z0-9_]+$")
    columns: list[ColumnDefinition] = Field(..., min_items=1)
    row_count: int | None = None
    size_bytes: int | None = None
    owner: str
    access_level: AccessLevel = AccessLevel.NONE
    last_refreshed: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def full_name(self) -> str:
        return f"{self.catalog_name}.{self.schema_name}.{self.table_name}"
    
    @validator('access_level')
    def validate_access(cls, v):
        if v == AccessLevel.NONE:
            raise ValueError("User has no access to this table")
        return v
```

---

### 3. Query Result

**Purpose**: Represents the result of a Unity Catalog query execution.

**Source**: Generated from SQL Warehouse query execution

**Fields**:
- `query_id` (string, required): Unique identifier for this query
- `data_source` (DataSource, required): The table that was queried
- `sql_statement` (string, required): The SQL query that was executed
- `rows` (array, required): Query result rows (array of dictionaries)
- `row_count` (integer, required): Number of rows returned
- `execution_time_ms` (integer, required): Query execution time in milliseconds
- `user_id` (string, required): User who executed the query
- `executed_at` (timestamp, required): When query was executed
- `status` (enum, required): Query status (PENDING, RUNNING, SUCCEEDED, FAILED)
- `error_message` (string, optional): Error message if query failed

**Validation Rules**:
- `sql_statement` must be SELECT only (no INSERT/UPDATE/DELETE for safety)
- `row_count` must equal `len(rows)`
- `execution_time_ms` must be positive
- If `status` is FAILED, `error_message` must be present

**Python Model**:
```python
from enum import Enum

class QueryStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"

class QueryResult(BaseModel):
    query_id: str = Field(..., min_length=1)
    data_source: DataSource
    sql_statement: str = Field(..., min_length=1)
    rows: list[dict] = []
    row_count: int = Field(..., ge=0)
    execution_time_ms: int = Field(..., gt=0)
    user_id: str
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    status: QueryStatus = QueryStatus.PENDING
    error_message: str | None = None
    
    @validator('sql_statement')
    def validate_select_only(cls, v):
        if not v.strip().upper().startswith('SELECT'):
            raise ValueError("Only SELECT queries allowed")
        return v
    
    @validator('row_count')
    def validate_row_count(cls, v, values):
        if 'rows' in values and len(values['rows']) != v:
            raise ValueError("row_count must equal len(rows)")
        return v
```

---

### 4. User Preference

**Purpose**: Represents user-specific application state and preferences stored in Lakebase.

**Source**: Lakebase `user_preferences` table

**Fields**:
- `id` (integer, primary key): Auto-incremented ID
- `user_id` (string, required, indexed): User identifier (matches `UserSession.user_id`)
- `preference_key` (string, required): Preference category (e.g., "dashboard_layout", "favorite_tables")
- `preference_value` (json, required): Preference data as JSON
- `created_at` (timestamp, required): When preference was created
- `updated_at` (timestamp, required): When preference was last updated

**Database Schema** (Lakebase/Postgres):
```sql
CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    preference_key VARCHAR(100) NOT NULL,
    preference_value JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, preference_key)
);

CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
```

**Validation Rules**:
- `user_id` must match authenticated user (data isolation)
- `preference_key` must be one of allowed keys: `dashboard_layout`, `favorite_tables`, `theme`
- `preference_value` must be valid JSON
- `updated_at` must be >= `created_at`

**Python Model**:
```python
from sqlalchemy import Column, Integer, String, JSON, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class UserPreference(Base):
    __tablename__ = 'user_preferences'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    preference_key = Column(String(100), nullable=False)
    preference_value = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        {'schema': 'public'}
    )
```

---

### 5. Model Endpoint

**Purpose**: Represents a Databricks Model Serving endpoint that can be invoked for inference.

**Source**: Databricks Model Serving API

**Fields**:
- `endpoint_name` (string, required): Unique endpoint name
- `endpoint_id` (string, required): Databricks endpoint ID
- `model_name` (string, required): Model name from Unity Catalog Model Registry
- `model_version` (string, required): Model version being served
- `state` (enum, required): Endpoint state (CREATING, READY, UPDATING, FAILED)
- `workload_url` (string, required): URL to invoke the endpoint
- `creation_timestamp` (timestamp, required): When endpoint was created
- `last_updated_timestamp` (timestamp, required): When endpoint was last modified
- `config` (json, required): Endpoint configuration (served models, traffic routing)

**Validation Rules**:
- `endpoint_name` must be unique within workspace
- `state` must be READY before invocation
- `workload_url` must be valid HTTPS URL
- `model_version` must exist in Unity Catalog Model Registry

**Relationships**:
- One `Model` → One `ModelEndpoint` (one-to-one active deployment)
- One `ModelEndpoint` → Many `ModelInference` (one endpoint can be invoked many times)

**Python Model**:
```python
class EndpointState(str, Enum):
    CREATING = "CREATING"
    READY = "READY"
    UPDATING = "UPDATING"
    FAILED = "FAILED"

class ModelEndpoint(BaseModel):
    endpoint_name: str = Field(..., min_length=1)
    endpoint_id: str = Field(..., min_length=1)
    model_name: str = Field(..., min_length=1)
    model_version: str = Field(..., min_length=1)
    state: EndpointState
    workload_url: str = Field(..., pattern=r"^https://.*")
    creation_timestamp: datetime
    last_updated_timestamp: datetime
    config: dict = {}
    
    @validator('state')
    def validate_ready_state(cls, v):
        if v != EndpointState.READY:
            raise ValueError("Endpoint must be READY for inference")
        return v
```

---

### 6. Model Inference Request

**Purpose**: Represents a request to invoke a model serving endpoint for predictions.

**Source**: User input to application

**Fields**:
- `request_id` (string, required): Unique request identifier
- `endpoint_name` (string, required): Target endpoint name
- `inputs` (json, required): Input data for model (format depends on model)
- `user_id` (string, required): User making the request
- `created_at` (timestamp, required): When request was created
- `timeout_seconds` (integer, required): Request timeout (default: 30)

**Validation Rules**:
- `endpoint_name` must reference an existing endpoint
- `inputs` must match model's expected input schema
- `timeout_seconds` must be between 1 and 300 (5 minutes max)

**Python Model**:
```python
class ModelInferenceRequest(BaseModel):
    request_id: str = Field(..., min_length=1)
    endpoint_name: str = Field(..., min_length=1)
    inputs: dict = Field(..., min_items=1)
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
```

---

### 7. Model Inference Response

**Purpose**: Represents the result of a model inference request.

**Source**: Model Serving endpoint response

**Fields**:
- `request_id` (string, required): Matching request ID
- `endpoint_name` (string, required): Endpoint that processed request
- `predictions` (json, required): Model predictions/outputs
- `status` (enum, required): Response status (SUCCESS, ERROR, TIMEOUT)
- `execution_time_ms` (integer, required): Inference time in milliseconds
- `error_message` (string, optional): Error message if status is ERROR
- `completed_at` (timestamp, required): When response was received

**Validation Rules**:
- `request_id` must match an existing request
- If `status` is ERROR, `error_message` must be present
- `execution_time_ms` must be positive

**Database Storage** (Lakebase):
```sql
CREATE TABLE model_inference_logs (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(100) NOT NULL,
    endpoint_name VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    inputs JSONB NOT NULL,
    predictions JSONB,
    status VARCHAR(50) NOT NULL,
    execution_time_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_inference_user_id ON model_inference_logs(user_id);
CREATE INDEX idx_inference_endpoint ON model_inference_logs(endpoint_name);
```

**Python Model**:
```python
class InferenceStatus(str, Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"

class ModelInferenceResponse(BaseModel):
    request_id: str
    endpoint_name: str
    predictions: dict = {}
    status: InferenceStatus
    execution_time_ms: int = Field(..., gt=0)
    error_message: str | None = None
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('error_message')
    def validate_error_message(cls, v, values):
        if values.get('status') == InferenceStatus.ERROR and not v:
            raise ValueError("error_message required when status is ERROR")
        return v
```

---

## Entity Relationships

```
UserSession (1) ──< queries >── (*) QueryResult
    │
    └──< has permissions for >──(*) DataSource
    │
    └──< stores preferences >──(*) UserPreference (Lakebase)
    │
    └──< invokes >──(*) ModelInferenceRequest
                          │
                          └──< produces >──(1) ModelInferenceResponse

ModelEndpoint (1) ──< serves >── (*) ModelInferenceRequest
    │
    └──< references >── Model (Unity Catalog Model Registry)

DataSource (Unity Catalog Table)
    └──< queried by >── SQL Warehouse
```

---

## Data Storage Summary

| Entity | Storage Location | Primary Key | Indexes |
|--------|------------------|-------------|---------|
| `UserSession` | In-memory (ephemeral) | `user_id` | - |
| `DataSource` | Unity Catalog (metadata) | `full_name` | - |
| `QueryResult` | In-memory (not persisted) | `query_id` | - |
| `UserPreference` | Lakebase | `id` | `user_id` |
| `ModelEndpoint` | Databricks Model Serving | `endpoint_name` | - |
| `ModelInferenceRequest` | In-memory | `request_id` | - |
| `ModelInferenceResponse` | Lakebase (logs) | `id` | `user_id`, `endpoint_name` |

---

## State Transition Diagrams

### Query Lifecycle
```
PENDING → RUNNING → SUCCEEDED
                 ↓
               FAILED
```

### Model Endpoint State
```
CREATING → READY → UPDATING → READY
           │         │
           ↓         ↓
         FAILED ← FAILED
```

### Inference Request Lifecycle
```
CREATED → SUBMITTED → PROCESSING → SUCCESS
                                 ↓
                               ERROR
                                 ↓
                              TIMEOUT
```

---

## Validation & Constraints

### Cross-Entity Rules
1. **User Access**: `UserSession.user_id` must match `UserPreference.user_id` (Lakebase isolation)
2. **Endpoint Availability**: `ModelEndpoint.state` must be READY before accepting `ModelInferenceRequest`
3. **Data Access**: `DataSource.access_level` must be READ or WRITE before allowing queries
4. **Query Safety**: All queries must be read-only (SELECT) to prevent data modification

### Performance Constraints
1. **Query Results**: Limit to 1000 rows maximum in `QueryResult.rows`
2. **Inference Timeout**: Maximum 300 seconds for `ModelInferenceRequest.timeout_seconds`
3. **Preference Size**: `UserPreference.preference_value` limited to 100KB JSON
4. **Connection Pooling**: Lakebase connection pool max 10 connections

---

**Status**: ✅ Data model complete, ready for contract generation.

