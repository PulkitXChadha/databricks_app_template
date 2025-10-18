# Data Model: Integration Test Fixtures and Test Data

**Feature**: 005-write-integration-test  
**Date**: October 18, 2025  
**Phase**: 1 - Design

## Overview

This document defines the data models for integration test fixtures, test data structures, and their relationships. Integration tests use a hybrid data approach: **session-scoped read-only reference data** (catalogs, users, endpoints) and **function-scoped isolated data** (preferences, logs) with automatic cleanup.

---

## 1. Test User Identities

### Model: TestUserIdentity

**Purpose**: Represents test user accounts for multi-user isolation testing.

**Attributes:**
- `user_id` (str): Email address used as user identifier (e.g., "test-user-a@example.com")
- `display_name` (str): Human-readable name (e.g., "Test User A")
- `token` (str): Databricks access token (mock or real from CLI)
- `active` (bool): Whether user account is active

**Scope**: Session-scoped (reused across tests)

**Fixture Implementation:**
```python
@pytest.fixture(scope="session")
def test_user_a():
    """Test User A identity (session-scoped)."""
    return {
        "user_id": "test-user-a@example.com",
        "display_name": "Test User A",
        "token": "mock-token-user-a",  # Or get_test_user_token("profile-a") for live
        "active": True
    }

@pytest.fixture(scope="session")
def test_user_b():
    """Test User B identity (session-scoped)."""
    return {
        "user_id": "test-user-b@example.com",
        "display_name": "Test User B",
        "token": "mock-token-user-b",
        "active": True
    }
```

**Usage Example:**
```python
def test_preference_isolation(client, test_user_a, test_user_b):
    """Test that User A cannot see User B's preferences."""
    with patch('server.routers.lakebase.get_current_user_id') as mock_user:
        mock_user.return_value = test_user_a["user_id"]
        # Create preference as User A
        # ...
```

---

## 2. Unity Catalog Reference Data

### Model: MockCatalogMetadata

**Purpose**: Provides read-only Unity Catalog structure (catalogs, schemas, tables) for testing data browsing and querying.

**Attributes:**
- `catalogs` (List[str]): Available catalog names
- `schemas` (Dict[str, List[str]]): Schemas per catalog
- `tables` (Dict[str, List[MockTableMetadata]]): Tables per schema
- `permissions` (Dict[str, Dict[str, str]]): User permissions per resource

**Scope**: Session-scoped (read-only, never modified)

**Fixture Implementation:**
```python
@pytest.fixture(scope="session")
def mock_catalog_metadata():
    """Mock Unity Catalog metadata (session-scoped, read-only)."""
    return {
        "catalogs": ["main", "samples"],
        "schemas": {
            "main": ["default", "sales"],
            "samples": ["tpch", "nyctaxi"]
        },
        "tables": {
            "main.default": [
                {
                    "catalog_name": "main",
                    "schema_name": "default",
                    "table_name": "customers",
                    "columns": [
                        {"name": "customer_id", "data_type": "bigint", "nullable": False},
                        {"name": "name", "data_type": "string", "nullable": True},
                        {"name": "email", "data_type": "string", "nullable": True}
                    ],
                    "owner": "admin",
                    "table_type": "MANAGED"
                },
                {
                    "catalog_name": "main",
                    "schema_name": "default",
                    "table_name": "orders",
                    "columns": [
                        {"name": "order_id", "data_type": "bigint", "nullable": False},
                        {"name": "customer_id", "data_type": "bigint", "nullable": False},
                        {"name": "amount", "data_type": "decimal(10,2)", "nullable": True}
                    ],
                    "owner": "admin",
                    "table_type": "MANAGED"
                }
            ],
            "samples.tpch": [
                {
                    "catalog_name": "samples",
                    "schema_name": "tpch",
                    "table_name": "nation",
                    "columns": [
                        {"name": "n_nationkey", "data_type": "bigint", "nullable": False},
                        {"name": "n_name", "data_type": "string", "nullable": True}
                    ],
                    "owner": "system",
                    "table_type": "EXTERNAL"
                }
            ]
        },
        "permissions": {
            "test-user-a@example.com": {
                "main.default.customers": "READ",
                "main.default.orders": "READ"
            },
            "test-user-b@example.com": {
                "samples.tpch.nation": "READ"
            }
        }
    }
```

### Model: MockTableData

**Purpose**: Sample table data for query testing.

**Attributes:**
- `table_key` (str): Fully qualified table name (catalog.schema.table)
- `rows` (List[Dict]): Sample rows matching table schema
- `total_count` (int): Total row count (for pagination testing)

**Fixture Implementation:**
```python
@pytest.fixture(scope="session")
def mock_table_data():
    """Mock table data for query testing (session-scoped)."""
    return {
        "main.default.customers": {
            "rows": [
                {"customer_id": 1, "name": "Alice", "email": "alice@example.com"},
                {"customer_id": 2, "name": "Bob", "email": "bob@example.com"},
                {"customer_id": 3, "name": "Charlie", "email": "charlie@example.com"}
            ],
            "total_count": 3
        },
        "samples.tpch.nation": {
            "rows": [
                {"n_nationkey": 0, "n_name": "ALGERIA"},
                {"n_nationkey": 1, "n_name": "ARGENTINA"},
                {"n_nationkey": 2, "n_name": "BRAZIL"}
            ],
            "total_count": 3
        }
    }
```

---

## 3. Model Serving Reference Data

### Model: MockModelEndpoint

**Purpose**: Mock model serving endpoint configurations for inference testing.

**Attributes:**
- `name` (str): Endpoint name (e.g., "claude-sonnet-4")
- `endpoint_type` (str): Endpoint type ("FOUNDATION_MODEL_API" or "MODEL_SERVING")
- `state` (str): Endpoint state ("READY", "NOT_READY")
- `served_entities` (List[Dict]): Served models/entities configuration

**Scope**: Session-scoped (read-only)

**Fixture Implementation:**
```python
@pytest.fixture(scope="session")
def mock_model_endpoints():
    """Mock model serving endpoints (session-scoped)."""
    return [
        {
            "name": "claude-sonnet-4",
            "endpoint_type": "FOUNDATION_MODEL_API",
            "state": {"ready": "READY"},
            "served_entities": [
                {
                    "name": "claude-sonnet-4",
                    "entity_name": "claude-sonnet-4",
                    "entity_version": "latest"
                }
            ],
            "task": "llm/v1/chat",
            "creator": "Databricks"
        },
        {
            "name": "custom-classifier",
            "endpoint_type": "MODEL_SERVING",
            "state": {"ready": "READY"},
            "served_entities": [
                {
                    "name": "custom-classifier-v1",
                    "entity_name": "models:/custom-classifier/1",
                    "entity_version": "1"
                }
            ],
            "task": "custom",
            "creator": "test-user-a@example.com"
        }
    ]
```

### Model: MockDetectedSchema

**Purpose**: Mock detected input schemas for model endpoints.

**Attributes:**
- `endpoint_name` (str): Associated endpoint name
- `schema_type` (str): Schema type ("chat_format", "mlflow_schema", "unknown")
- `parameters` (List[Dict]): Input parameter definitions
- `example_json` (Dict): Example input payload

**Fixture Implementation:**
```python
@pytest.fixture(scope="session")
def mock_detected_schemas():
    """Mock detected model input schemas (session-scoped)."""
    return {
        "claude-sonnet-4": {
            "schema_type": "chat_format",
            "parameters": [
                {
                    "name": "messages",
                    "type": "array",
                    "required": True,
                    "description": "Array of chat messages"
                },
                {
                    "name": "max_tokens",
                    "type": "integer",
                    "required": False,
                    "description": "Maximum tokens to generate"
                }
            ],
            "example_json": {
                "messages": [
                    {"role": "user", "content": "Hello, world!"}
                ],
                "max_tokens": 1000
            }
        },
        "custom-classifier": {
            "schema_type": "mlflow_schema",
            "parameters": [
                {
                    "name": "text",
                    "type": "string",
                    "required": True
                }
            ],
            "example_json": {
                "inputs": [{"text": "Sample text for classification"}]
            }
        }
    }
```

---

## 4. User Preferences (Isolated Per-Test)

### Model: TestUserPreference

**Purpose**: User preference data created and cleaned up per test.

**Attributes:**
- `user_id` (str): User identifier (links to TestUserIdentity)
- `preference_key` (str): Preference key (e.g., "theme", "dashboard_layout")
- `preference_value` (Dict): Preference value (JSON object)
- `created_at` (datetime): Creation timestamp
- `updated_at` (datetime): Last update timestamp

**Scope**: Function-scoped (created per test, cleaned up automatically)

**Fixture Implementation:**
```python
@pytest.fixture(autouse=True)
def cleanup_test_preferences():
    """Clean up test preferences before and after each test (function-scoped)."""
    from server.lib.database import get_db_session
    from server.models.user_preference import UserPreference
    from sqlalchemy.orm import Session
    
    session: Session = next(get_db_session())
    test_user_ids = ["test-user-a@example.com", "test-user-b@example.com"]
    
    try:
        # Cleanup before test
        session.query(UserPreference).filter(
            UserPreference.user_id.in_(test_user_ids)
        ).delete(synchronize_session=False)
        session.commit()
        yield  # Run test
    finally:
        # Cleanup after test
        session.query(UserPreference).filter(
            UserPreference.user_id.in_(test_user_ids)
        ).delete(synchronize_session=False)
        session.commit()
        session.close()
```

**Test Data Factory:**
```python
def create_test_preference(user_id: str, key: str, value: Dict) -> Dict:
    """Factory function to create test preference data."""
    return {
        "preference_key": key,
        "preference_value": value,
        # user_id will be injected by service layer from auth context
    }

# Usage in tests
preference_data = create_test_preference(
    user_id="test-user-a@example.com",
    key="theme",
    value={"mode": "dark", "color": "blue"}
)
```

---

## 5. Model Inference Logs (Isolated Per-Test)

### Model: TestInferenceLog

**Purpose**: Model inference log data created and cleaned up per test.

**Attributes:**
- `id` (UUID): Log entry identifier
- `user_id` (str): User who made inference request
- `endpoint_name` (str): Model endpoint used
- `request_payload` (Dict): Input sent to model
- `response_payload` (Dict): Output from model
- `status` (str): Request status ("SUCCESS", "ERROR", "TIMEOUT")
- `duration_ms` (int): Request duration in milliseconds
- `created_at` (datetime): Request timestamp

**Scope**: Function-scoped (created per test, cleaned up automatically)

**Fixture Implementation:**
```python
@pytest.fixture(autouse=True)
def cleanup_inference_logs():
    """Clean up inference logs before and after each test (function-scoped)."""
    from server.lib.database import get_db_session
    from server.models.model_inference import ModelInferenceLog
    from sqlalchemy.orm import Session
    
    session: Session = next(get_db_session())
    test_user_ids = ["test-user-a@example.com", "test-user-b@example.com"]
    
    try:
        # Cleanup before test
        session.query(ModelInferenceLog).filter(
            ModelInferenceLog.user_id.in_(test_user_ids)
        ).delete(synchronize_session=False)
        session.commit()
        yield  # Run test
    finally:
        # Cleanup after test
        session.query(ModelInferenceLog).filter(
            ModelInferenceLog.user_id.in_(test_user_ids)
        ).delete(synchronize_session=False)
        session.commit()
        session.close()
```

---

## 6. Schema Detection Events (Isolated Per-Test)

### Model: TestSchemaDetectionEvent

**Purpose**: Schema detection event data for tracking schema detection operations.

**Attributes:**
- `id` (UUID): Event identifier
- `user_id` (str): User who triggered detection
- `endpoint_name` (str): Endpoint for which schema was detected
- `detection_strategy` (str): Strategy used ("chat_format", "mlflow", "fallback")
- `success` (bool): Whether detection succeeded
- `created_at` (datetime): Detection timestamp

**Scope**: Function-scoped (created per test, cleaned up automatically)

**Fixture Implementation:**
```python
@pytest.fixture(autouse=True)
def cleanup_schema_events():
    """Clean up schema detection events before and after each test (function-scoped)."""
    from server.lib.database import get_db_session
    from server.models.schema_detection_event import SchemaDetectionEvent
    from sqlalchemy.orm import Session
    
    session: Session = next(get_db_session())
    test_user_ids = ["test-user-a@example.com", "test-user-b@example.com"]
    
    try:
        # Cleanup before test
        session.query(SchemaDetectionEvent).filter(
            SchemaDetectionEvent.user_id.in_(test_user_ids)
        ).delete(synchronize_session=False)
        session.commit()
        yield  # Run test
    finally:
        # Cleanup after test
        session.query(SchemaDetectionEvent).filter(
            SchemaDetectionEvent.user_id.in_(test_user_ids)
        ).delete(synchronize_session=False)
        session.commit()
        session.close()
```

---

## 7. Test Data Relationships

### Entity Relationship Diagram

```
┌─────────────────────┐
│ TestUserIdentity    │
│ (session-scoped)    │
├─────────────────────┤
│ user_id (PK)        │
│ display_name        │
│ token               │
│ active              │
└──────────┬──────────┘
           │
           │ 1:N
           │
           ├────────────────────────────────────┐
           │                                    │
           │                                    │
    ┌──────▼──────────────┐          ┌─────────▼──────────────┐
    │ TestUserPreference  │          │ TestInferenceLog       │
    │ (function-scoped)   │          │ (function-scoped)      │
    ├─────────────────────┤          ├────────────────────────┤
    │ user_id (FK)        │          │ id (PK)                │
    │ preference_key      │          │ user_id (FK)           │
    │ preference_value    │          │ endpoint_name (FK)     │
    │ created_at          │          │ request_payload        │
    │ updated_at          │          │ response_payload       │
    └─────────────────────┘          │ status                 │
                                     │ duration_ms            │
                                     └────────┬───────────────┘
                                              │
                                              │ N:1
                                              │
                                     ┌────────▼───────────────┐
                                     │ MockModelEndpoint      │
                                     │ (session-scoped)       │
                                     ├────────────────────────┤
                                     │ name (PK)              │
                                     │ endpoint_type          │
                                     │ state                  │
                                     │ served_entities        │
                                     └────────────────────────┘

┌────────────────────────┐
│ MockCatalogMetadata    │
│ (session-scoped)       │
├────────────────────────┤
│ catalogs               │
│ schemas                │
│ tables                 │
│ permissions            │
└────────────────────────┘
```

### Relationship Rules

1. **TestUserIdentity → TestUserPreference**: One-to-Many (user can have many preferences)
2. **TestUserIdentity → TestInferenceLog**: One-to-Many (user can have many inference logs)
3. **MockModelEndpoint → TestInferenceLog**: One-to-Many (endpoint can have many inference logs)
4. **MockCatalogMetadata**: Standalone (no foreign keys, read-only reference data)

---

## 8. Fixture Loading Strategy

### Phase 1: Session Initialization (Once per test session)

1. Load `TestUserIdentity` fixtures (test-user-a, test-user-b)
2. Load `MockCatalogMetadata` (catalogs, schemas, tables, permissions)
3. Load `MockModelEndpoints` (claude-sonnet-4, custom-classifier)
4. Load `MockDetectedSchemas` (schema definitions for endpoints)
5. Load `MockTableData` (sample rows for query testing)

**Performance**: All session-scoped fixtures load once, amortizing cost across all tests.

### Phase 2: Per-Test Setup (Before each test)

1. Clean up isolated data (preferences, inference logs, schema events)
2. Create test-specific mock users (if needed for test)
3. Patch external services (WorkspaceClient, model serving APIs)

**Performance**: Only isolated data cleanup occurs per test, not full fixture reload.

### Phase 3: Per-Test Teardown (After each test)

1. Delete test preferences by user_id filter
2. Delete test inference logs by user_id filter
3. Delete test schema events by user_id filter
4. Close database sessions

**Performance**: Targeted deletes by user_id are fast (indexed), no full table drops.

---

## 9. Data Validation Rules

### TestUserIdentity Validation

- `user_id` MUST be valid email format
- `user_id` MUST be unique across test users
- `token` MUST be non-empty string
- `display_name` MUST be non-empty string

### MockCatalogMetadata Validation

- `catalogs` MUST NOT be empty
- Each catalog in `schemas` MUST exist in `catalogs` list
- Table names MUST follow `catalog.schema.table` format
- Column data types MUST be valid SQL types

### TestUserPreference Validation

- `user_id` MUST match TestUserIdentity.user_id
- `preference_key` MUST be non-empty string
- `preference_value` MUST be valid JSON object
- Duplicate (user_id, preference_key) results in update (upsert behavior)

### TestInferenceLog Validation

- `user_id` MUST match TestUserIdentity.user_id
- `endpoint_name` MUST match MockModelEndpoint.name
- `status` MUST be one of: "SUCCESS", "ERROR", "TIMEOUT"
- `duration_ms` MUST be non-negative integer
- `request_payload` and `response_payload` MUST be valid JSON

---

## 10. Test Data Size Guidelines

### Session-Scoped Data (Small, Reusable)

- **Test Users**: 2-3 users maximum (test-user-a, test-user-b, test-admin)
- **Mock Catalogs**: 2-3 catalogs (main, samples)
- **Mock Schemas**: 2-4 schemas per catalog
- **Mock Tables**: 2-5 tables per schema
- **Mock Endpoints**: 2-4 model endpoints

**Rationale**: Small reference data sets keep tests fast, easy to understand, and maintain.

### Function-Scoped Data (Variable, Cleaned Up)

- **Preferences per test**: 1-10 preferences (test-specific)
- **Inference logs per test**: 1-20 logs (test-specific)
- **Schema events per test**: 1-5 events (test-specific)

**Rationale**: Each test creates only data it needs, avoiding unnecessary setup overhead.

### Concurrency Testing Data (C3 Specification)

- **Concurrent request level**: Exactly 7 concurrent requests (midpoint of 5-10 range specified in spec.md)
- **Rationale**: Provides reproducible concurrency testing without excessive load (validates basic thread safety)
- **Usage**: All User Story 7 (concurrency) tests use 7 concurrent operations (preferences, inference, queries)

### Pagination Testing Data

- **Large datasets**: 100-500 records (created only for pagination tests)
- **Cleanup**: Automatically deleted after pagination test completes
- **Performance**: Use database bulk insert for speed

---

## Summary

This data model defines all test fixtures and data structures needed for comprehensive integration testing. Key design principles:

1. **Session-scoped read-only data**: Catalogs, users, endpoints (loaded once, never modified)
2. **Function-scoped isolated data**: Preferences, logs, events (created per test, cleaned up automatically)
3. **User-scoped cleanup**: Delete by user_id filter (fast, targeted, safe)
4. **Realistic data**: Mock data matches production data structures
5. **Small reference sets**: Minimal data for speed, maximum coverage for quality

**Next**: Define coverage contracts and quickstart guide (Phase 1 continuation).

