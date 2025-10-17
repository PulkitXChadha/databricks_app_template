# Quickstart: Automatic Model Input Schema Detection

**Feature**: 004-dynamic-endpoint-input-schema  
**Date**: October 17, 2025  
**Status**: Implementation Ready

## Overview

This quickstart guide demonstrates how to use the automatic model input schema detection feature for Databricks Model Serving endpoints. The feature automatically detects endpoint types (foundation models, MLflow models, or unknown) and generates appropriate input examples.

---

## User Flow

### 1. Select Endpoint → Schema Auto-Populates

**User Experience**:
1. User navigates to Model Inference page
2. User selects an endpoint from the dropdown (e.g., "databricks-claude-sonnet-4")
3. **Loading indicator** appears (JSON input box hidden during detection)
4. After ~250ms, **JSON input box appears** with pre-populated example
5. **Status badge** displays "Foundation Model" next to input box
6. User can edit JSON and invoke model immediately

**Visual Flow**:
```
[Select Endpoint Dropdown]
         ↓
    [🔄 Loading...]
         ↓
┌──────────────────────────────────┐
│ Input JSON  [Badge: Foundation]  │
│ ┌──────────────────────────────┐ │
│ │ {                            │ │
│ │   "messages": [              │ │
│ │     {                        │ │
│ │       "role": "user",        │ │
│ │       "content": "Hello!"    │ │
│ │     }                        │ │
│ │   ],                         │ │
│ │   "max_tokens": 150          │ │
│ │ }                            │ │
│ └──────────────────────────────┘ │
└──────────────────────────────────┘
         ↓
    [Invoke Model Button]
```

---

## API Usage Examples

### Example 1: Detect Schema for Foundation Model (Claude)

**Request**:
```http
GET /api/model-serving/endpoints/databricks-claude-sonnet-4/schema HTTP/1.1
Authorization: Bearer {user_token}
X-Correlation-ID: 550e8400-e29b-41d4-a716-446655440000
```

**Response** (200 OK, ~250ms):
```json
{
  "endpoint_name": "databricks-claude-sonnet-4",
  "detected_type": "FOUNDATION_MODEL",
  "status": "SUCCESS",
  "schema": null,
  "example_json": {
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
  },
  "error_message": null,
  "latency_ms": 245,
  "detected_at": "2025-10-17T10:30:00Z"
}
```

**Frontend Usage (TypeScript)**:
```typescript
import { ApiService } from '@/fastapi_client';

// In React component
const detectSchema = async (endpointName: string) => {
  try {
    const result = await ApiService.detectSchema(endpointName);
    
    if (result.status === 'SUCCESS') {
      // Populate JSON input box
      setInputJson(JSON.stringify(result.example_json, null, 2));
      
      // Display status badge
      setModelType(result.detected_type);  // "Foundation Model"
    }
  } catch (error) {
    console.error('Schema detection failed:', error);
  }
};
```

---

### Example 2: Detect Schema for MLflow Model

**Request**:
```http
GET /api/model-serving/endpoints/fraud-detection-model/schema HTTP/1.1
Authorization: Bearer {user_token}
```

**Response** (200 OK, ~1.8s):
```json
{
  "endpoint_name": "fraud-detection-model",
  "detected_type": "MLFLOW_MODEL",
  "status": "SUCCESS",
  "schema": {
    "type": "object",
    "properties": {
      "transaction_amount": {
        "type": "number"
      },
      "merchant_category": {
        "type": "string"
      },
      "user_account_age_days": {
        "type": "integer"
      }
    },
    "required": ["transaction_amount", "merchant_category"]
  },
  "example_json": {
    "transaction_amount": 3.14,
    "merchant_category": "example text",
    "user_account_age_days": 42
  },
  "error_message": null,
  "latency_ms": 1832,
  "detected_at": "2025-10-17T10:30:00Z"
}
```

**Usage Notes**:
- MLflow models query Model Registry (slower than foundation models)
- Schema includes field types and required/optional indicators
- Generated example uses realistic sample values per type

---

### Example 3: Schema Detection Timeout (Fallback)

**Request**:
```http
GET /api/model-serving/endpoints/slow-model-endpoint/schema HTTP/1.1
Authorization: Bearer {user_token}
```

**Response** (200 OK, ~5s):
```json
{
  "endpoint_name": "slow-model-endpoint",
  "detected_type": "UNKNOWN",
  "status": "TIMEOUT",
  "schema": null,
  "example_json": {
    "input": "value",
    "_comment": "Schema detection unavailable. Consult model documentation for correct input format."
  },
  "error_message": "Schema retrieval timed out after 5 seconds",
  "latency_ms": 5003,
  "detected_at": "2025-10-17T10:30:00Z"
}
```

**Frontend Handling**:
```typescript
if (result.status === 'TIMEOUT' || result.status === 'FAILURE') {
  // Show warning alert
  showWarning({
    severity: 'warning',
    message: result.error_message || 'Schema detection unavailable',
    actionText: 'Consult Documentation'
  });
  
  // Still populate with fallback template (user can edit)
  setInputJson(JSON.stringify(result.example_json, null, 2));
  setModelType('Unknown');
}
```

---

## Browser Session Caching

### Cache Storage Example

**After first detection**, schema is cached in `sessionStorage`:

```typescript
// Automatically cached by useSchemaCache hook
sessionStorage.setItem(
  'schema_databricks-claude-sonnet-4',
  JSON.stringify({
    endpoint_name: 'databricks-claude-sonnet-4',
    detected_type: 'FOUNDATION_MODEL',
    status: 'SUCCESS',
    schema: null,
    example_json: { messages: [...], max_tokens: 150 },
    error_message: null,
    latency_ms: 245,
    detected_at: '2025-10-17T10:30:00Z'
  })
);
```

**Subsequent selections** (same endpoint):
```typescript
// useSchemaCache hook checks cache first
const cached = sessionStorage.getItem('schema_databricks-claude-sonnet-4');

if (cached) {
  // Instant population (0ms, no API call)
  setInputJson(JSON.parse(cached).example_json);
  setModelType(JSON.parse(cached).detected_type);
}
```

**Cache Lifecycle**:
- ✅ Persists until browser tab/window closes
- ✅ Per-tab isolation (different tabs have independent caches)
- ✅ Automatic cleanup on tab close (no manual invalidation needed)
- ❌ Does NOT persist across page reloads (re-detects on reload)

---

## Backend Service Usage

### SchemaDetectionService Integration

**Service Initialization**:
```python
from server.services.schema_detection_service import SchemaDetectionService

# Initialize with OBO user token
service = SchemaDetectionService(user_token=request.user_token)
```

**Detect Schema**:
```python
async def detect_schema_endpoint(endpoint_name: str, user_id: str):
    """FastAPI endpoint handler."""
    service = SchemaDetectionService(user_token=user_token)
    
    try:
        result = await service.detect_schema(
            endpoint_name=endpoint_name,
            user_token=user_token,
            user_id=user_id
        )
        
        # Automatically logs to Lakebase
        return result
    
    except Exception as e:
        logger.error(f"Schema detection failed: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=str(e))
```

**Service Methods**:
```python
class SchemaDetectionService:
    async def detect_schema(
        self, 
        endpoint_name: str,
        user_token: str,
        user_id: str
    ) -> SchemaDetectionResult:
        """
        Main detection workflow:
        1. Get endpoint metadata from Serving Endpoints API
        2. Detect endpoint type (foundation, mlflow, unknown)
        3. For foundation: return chat format immediately
        4. For mlflow: query Model Registry with 5s timeout
        5. Generate example JSON from schema
        6. Log event to Lakebase
        7. Return SchemaDetectionResult
        """
        pass
    
    def detect_endpoint_type(self, endpoint: ModelEndpoint) -> EndpointType:
        """Heuristic-based endpoint type detection."""
        pass
    
    async def retrieve_mlflow_schema(
        self, 
        model_name: str, 
        version: str
    ) -> dict | None:
        """Query Unity Catalog Model Registry."""
        pass
    
    def generate_example_json(self, schema: dict) -> dict:
        """Generate realistic example from JSON Schema."""
        pass
    
    async def log_detection_event(self, event: SchemaDetectionEvent):
        """Persist event to Lakebase for observability."""
        pass
```

---

## Observability & Debugging

### Structured Logging

**Log Output** (JSON format):
```json
{
  "timestamp": "2025-10-17T10:30:00Z",
  "level": "INFO",
  "message": "Schema detection complete",
  "module": "schema_detection_service",
  "function": "detect_schema",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user@company.com",
  "endpoint_name": "databricks-claude-sonnet-4",
  "detected_type": "FOUNDATION_MODEL",
  "status": "SUCCESS",
  "latency_ms": 245
}
```

**Query Logs in Lakebase**:
```sql
-- Get detection history for user
SELECT * FROM schema_detection_events
WHERE user_id = 'user@company.com'
ORDER BY created_at DESC
LIMIT 100;

-- Calculate failure rate by endpoint
SELECT 
    endpoint_name,
    COUNT(*) as total_detections,
    SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
    AVG(latency_ms) as avg_latency_ms
FROM schema_detection_events
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY endpoint_name;

-- Trace request by correlation ID
SELECT * FROM schema_detection_events
WHERE correlation_id = '550e8400-e29b-41d4-a716-446655440000';
```

---

## Testing Scenarios

### Contract Test: Foundation Model Schema Detection

```python
# tests/contract/test_schema_detection_contract.py
import pytest
from fastapi.testclient import TestClient

def test_detect_foundation_model_schema(client: TestClient):
    """Contract test: Detect schema for Claude foundation model."""
    response = client.get(
        '/api/model-serving/endpoints/databricks-claude-sonnet-4/schema',
        headers={'Authorization': f'Bearer {user_token}'}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Contract assertions
    assert data['detected_type'] == 'FOUNDATION_MODEL'
    assert data['status'] == 'SUCCESS'
    assert 'messages' in data['example_json']
    assert data['latency_ms'] < 1000  # Foundation models should be fast
    assert data['schema'] is None  # Foundation models don't have explicit schema
```

### Integration Test: MLflow Model Schema Retrieval

```python
@pytest.mark.integration
async def test_mlflow_schema_retrieval_from_model_registry():
    """Integration test: Query Model Registry for MLflow schema."""
    service = SchemaDetectionService(user_token=test_user_token)
    
    schema = await service.retrieve_mlflow_schema(
        model_name='main.default.fraud_detection_model',
        version='1'
    )
    
    assert schema is not None
    assert 'properties' in schema
    assert 'transaction_amount' in schema['properties']
```

### E2E Test: User Flow with Playwright

```typescript
// tests/e2e/test_schema_detection_ui.spec.ts
import { test, expect } from '@playwright/test';

test('user selects endpoint and sees auto-populated schema', async ({ page }) => {
  await page.goto('/databricks-services');
  
  // Select endpoint
  await page.getByLabel('Select Endpoint').click();
  await page.getByText('databricks-claude-sonnet-4').click();
  
  // Wait for schema detection (loading indicator)
  await expect(page.getByTestId('schema-loading')).toBeVisible();
  
  // Verify JSON input populated
  const jsonInput = page.getByTestId('json-input-box');
  await expect(jsonInput).toBeVisible();
  
  const inputValue = await jsonInput.inputValue();
  const parsedJson = JSON.parse(inputValue);
  
  expect(parsedJson).toHaveProperty('messages');
  expect(parsedJson.messages[0]).toHaveProperty('role');
  
  // Verify status badge
  await expect(page.getByText('Foundation Model')).toBeVisible();
});
```

---

## Error Scenarios

### Scenario 1: Endpoint Not Found

**Request**: GET `/api/model-serving/endpoints/invalid-endpoint/schema`

**Response** (404):
```json
{
  "error_code": "ENDPOINT_NOT_FOUND",
  "message": "Model serving endpoint 'invalid-endpoint' not found."
}
```

**Frontend Handling**: Show error alert, disable Invoke button

---

### Scenario 2: Model Registry Unavailable

**Request**: GET `/api/model-serving/endpoints/mlflow-model/schema`

**Response** (503):
```json
{
  "error_code": "SERVICE_UNAVAILABLE",
  "message": "Model Registry service temporarily unavailable.",
  "technical_details": {
    "error_type": "ConnectionError"
  },
  "retry_after": 10
}
```

**Frontend Handling**: Show retry message, suggest manual input

---

### Scenario 3: Malformed Schema (Fallback)

**Internal Detection**: Schema JSON parsing fails

**Response** (200 OK, degraded):
```json
{
  "endpoint_name": "problematic-model",
  "detected_type": "UNKNOWN",
  "status": "FAILURE",
  "schema": null,
  "example_json": {
    "input": "value",
    "_comment": "Schema detection unavailable. Consult model documentation."
  },
  "error_message": "Malformed schema definition in Model Registry",
  "latency_ms": 1543,
  "detected_at": "2025-10-17T10:30:00Z"
}
```

**Frontend Handling**: Show warning, allow manual editing

---

## Performance Characteristics

| Model Type | Latency Target | Typical Latency | Timeout |
|------------|----------------|-----------------|---------|
| Foundation Model | < 500ms | ~250ms | N/A (instant) |
| MLflow Model (cached) | < 100ms | ~50ms | N/A (cache hit) |
| MLflow Model (uncached) | < 3s | ~1.8s | 5s |
| Unknown/Fallback | < 100ms | ~50ms | N/A (immediate fallback) |

**Success Criteria**:
- 95%+ foundation model detections complete in < 500ms (SC-001)
- 90%+ MLflow model detections complete in < 3s (SC-002)
- 100% graceful fallback handling (SC-006)

---

## Next Steps

1. **Implement Backend**: Follow `data-model.md` and contracts for service layer
2. **Generate TypeScript Client**: Run `python scripts/make_fastapi_client.py` after backend implementation
3. **Implement Frontend**: Integrate with `DatabricksServicesPage.tsx` using Design Bricks components
4. **Create Tests**: Implement contract, integration, and E2E tests per examples above
5. **Deploy**: Validate with `databricks bundle validate` before deployment

---

## Support & Troubleshooting

**Common Issues**:

| Issue | Cause | Solution |
|-------|-------|----------|
| Schema not detected | Model Registry permissions | Verify user has `SELECT` permission on model |
| Timeout errors | Slow Model Registry response | Check Model Registry API health, increase timeout if needed |
| Cache not working | sessionStorage disabled | Verify browser allows sessionStorage, check Privacy settings |
| Wrong endpoint type detected | Ambiguous endpoint name | Manually adjust detection logic heuristics |

**Debugging Commands**:
```bash
# Check Lakebase logs
python dba_logz.py | grep schema_detection

# Query detection events
psql -h $LAKEBASE_HOST -U $LAKEBASE_USER -d $LAKEBASE_DB \
  -c "SELECT * FROM schema_detection_events ORDER BY created_at DESC LIMIT 10;"

# Test Model Registry connectivity
python -c "
from databricks.sdk import WorkspaceClient
client = WorkspaceClient(token='$USER_TOKEN')
mv = client.model_registry.get_model_version(
    full_name='main.default.test_model',
    version='1'
)
print(mv)
"
```

---

**Feature Complete** ✅ Ready for implementation in Phase 2

