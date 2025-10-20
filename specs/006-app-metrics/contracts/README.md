# API Contracts: Metrics System

**Feature**: 006-app-metrics  
**Date**: 2025-10-18

## Overview

This directory contains API contract specifications for the metrics collection and visualization system. Contracts define the expected request/response schemas, status codes, and error formats for all metrics endpoints.

## Contract Files

### metrics-api.yaml
OpenAPI 3.0 specification for metrics API endpoints:
- **GET /api/v1/metrics/performance**: Retrieve performance metrics
- **GET /api/v1/metrics/usage**: Retrieve usage metrics
- **GET /api/v1/metrics/usage/count**: Retrieve usage event count for authenticated user
- **GET /api/v1/metrics/time-series**: Retrieve time-series data for charts
- **POST /api/v1/metrics/usage-events**: Submit batch usage events

## Contract Testing Strategy

Following **Principle XII (Test Driven Development)**, contract tests MUST be written BEFORE endpoint implementation using the red-green-refactor methodology:

### Phase 1: RED (Write Failing Tests)
Before implementing any endpoints, create contract tests that validate:
1. **Request validation**: Endpoints reject invalid request parameters/bodies with 400 Bad Request
2. **Response schemas**: Successful responses match OpenAPI schema definitions
3. **Status codes**: Endpoints return correct HTTP status codes (200, 202, 400, 401, 403, 503)
4. **Error formats**: Error responses follow the ErrorResponse schema
5. **Authentication**: Endpoints enforce authentication requirements
6. **Authorization**: Admin-only endpoints return 403 for non-admin users

### Phase 2: GREEN (Implement Endpoints)
Implement minimal code to make contract tests pass:
1. Create FastAPI router with endpoint stubs
2. Add Pydantic models for request/response validation
3. Implement admin privilege checking dependency
4. Implement endpoint logic to return expected data structures
5. Add error handling with proper status codes

### Phase 3: REFACTOR (Improve Code Quality)
Once all contract tests pass, refactor for quality:
1. Extract common logic to service layer
2. Improve error messages and logging
3. Optimize query performance
4. Add documentation and comments

## Test Location

Contract tests are implemented in: `tests/contract/test_metrics_api.py`

The test file includes test classes/functions for each endpoint:
- `test_get_performance_metrics_*`: Tests for GET /metrics/performance
- `test_get_usage_metrics_*`: Tests for GET /metrics/usage
- `test_get_time_series_metrics_*`: Tests for GET /metrics/time-series
- `test_submit_usage_events_*`: Tests for POST /metrics/usage-events

## Endpoint Details

### GET /api/v1/metrics/performance

**Purpose**: Retrieve aggregated performance metrics for API requests

**Authentication**: Required (admin only)

**Rate Limiting**: None (admin-only access control provides sufficient protection)

**Query Parameters**:
- `time_range` (optional): "24h" | "7d" | "30d" | "90d" (default: "24h")
- `endpoint` (optional): Filter by specific endpoint path

**Success Response** (200):
```json
{
  "time_range": "24h",
  "start_time": "2025-10-17T00:00:00Z",
  "end_time": "2025-10-18T00:00:00Z",
  "metrics": {
    "avg_response_time_ms": 145.32,
    "total_requests": 15234,
    "error_rate": 0.0023,
    "p50_response_time_ms": 98.5,
    "p95_response_time_ms": 450.2,
    "p99_response_time_ms": 850.7
  },
  "endpoints": [
    {
      "endpoint": "/api/v1/lakebase/sources",
      "method": "GET",
      "avg_response_time_ms": 120.5,
      "request_count": 3456,
      "error_count": 2
    }
  ]
}
```

**Error Responses**:
- 401 Unauthorized: Missing/invalid token
- 403 Forbidden: User is not admin
- 503 Service Unavailable: Admin check failed

---

### GET /api/v1/metrics/usage

**Purpose**: Retrieve aggregated usage metrics for user interactions

**Authentication**: Required (admin only)

**Rate Limiting**: None (admin-only access control provides sufficient protection)

**Query Parameters**:
- `time_range` (optional): "24h" | "7d" | "30d" | "90d" (default: "24h")
- `event_type` (optional): Filter by specific event type

**Success Response** (200):
```json
{
  "time_range": "24h",
  "start_time": "2025-10-17T00:00:00Z",
  "end_time": "2025-10-18T00:00:00Z",
  "metrics": {
    "total_events": 45678,
    "unique_users": 123,
    "active_users_current_hour": 12
  },
  "event_distribution": {
    "page_view": 15234,
    "button_click": 23456,
    "query_executed": 3456
  },
  "page_views": {
    "/metrics": 234,
    "/lakebase/sources": 5678
  }
}
```

**Error Responses**:
- 401 Unauthorized: Missing/invalid token
- 403 Forbidden: User is not admin
- 503 Service Unavailable: Admin check failed

---

### GET /api/v1/metrics/time-series

**Purpose**: Retrieve time-series metrics data for chart visualization

**Authentication**: Required (admin only)

**Rate Limiting**: None (admin-only access control provides sufficient protection)

**Query Parameters**:
- `time_range` (optional): "24h" | "7d" | "30d" | "90d" (default: "24h")
- `metric_type` (required): "performance" | "usage" | "both"

**Success Response** (200):
```json
{
  "time_range": "24h",
  "interval": "hourly",
  "data_points": [
    {
      "timestamp": "2025-10-18T00:00:00Z",
      "avg_response_time_ms": 145.3,
      "total_requests": 634,
      "error_rate": 0.0031,
      "total_events": 1890,
      "unique_users": 23
    }
  ]
}
```

**Error Responses**:
- 401 Unauthorized: Missing/invalid token
- 403 Forbidden: User is not admin

---

### GET /api/v1/metrics/usage/count

**Purpose**: Retrieve usage event count for authenticated user to support client-side data loss validation

**Authentication**: Required (any authenticated user, not admin-only)

**Rate Limiting**: None (authentication provides sufficient protection)

**Query Parameters**:
- `time_range` (optional): "24h" | "7d" | "30d" | "90d" (default: "24h")

**Success Response** (200):
```json
{
  "count": 1523,
  "time_range": "24h",
  "start_time": "2025-10-19T12:00:00Z",
  "end_time": "2025-10-20T12:00:00Z"
}
```

**Error Responses**:
- 401 Unauthorized: Missing/invalid token

**Use Case**: Frontend UsageTracker uses this endpoint to reconcile sent event count with backend persisted count to calculate data loss rate (acceptable threshold: <0.1% per spec.md edge cases).

---

### POST /api/v1/metrics/usage-events

**Purpose**: Submit batch usage events from frontend

**Authentication**: Required (any authenticated user, not admin-only)

**Rate Limiting**: None (frontend batching and authentication provide sufficient protection)

**Content-Type Support**: Accepts BOTH `Content-Type: application/json` (standard API calls) AND `Content-Type: text/plain` (navigator.sendBeacon default for page unload events); endpoint parses request body as JSON regardless of Content-Type header for compatibility with browser sendBeacon constraints during page transitions

**Request Body**:
```json
{
  "events": [
    {
      "event_type": "page_view",
      "page_name": "/metrics",
      "timestamp": "2025-10-18T12:34:56Z"
    },
    {
      "event_type": "button_click",
      "page_name": "/lakebase/sources",
      "element_id": "add-source-btn",
      "success": true,
      "timestamp": "2025-10-18T12:35:02Z"
    }
  ]
}
```

**Success Response** (202 Accepted):
```json
{
  "message": "Events accepted",
  "events_received": 2,
  "status": "processing"
}
```

**Error Responses**:
- 400 Bad Request: Invalid event data
- 401 Unauthorized: Missing/invalid token
- 413 Payload Too Large: Batch exceeds 1000 events (see FR-013 for custom exception handler)

---

## Contract Validation

### Pre-Implementation Validation
Before writing code, validate contract tests fail correctly:
```bash
# Run contract tests (should fail with 404 Not Found)
pytest tests/contract/test_metrics_api.py -v

# Expected output: All tests FAIL (RED phase)
# test_get_performance_metrics_returns_200 ... FAILED (404 Not Found)
# test_get_usage_metrics_returns_200 ... FAILED (404 Not Found)
```

### Post-Implementation Validation
After implementing endpoints, verify contract tests pass:
```bash
# Run contract tests (should pass)
pytest tests/contract/test_metrics_api.py -v

# Expected output: All tests PASS (GREEN phase)
# test_get_performance_metrics_returns_200 ... PASSED
# test_get_usage_metrics_returns_200 ... PASSED
```

### Continuous Validation
Contract tests run as part of CI/CD pipeline:
```bash
# Full test suite (deployment gate)
pytest tests/contract/ -v --cov

# Contract tests MUST pass before deployment
# Constitution Principle III (Asset Bundle Deployment)
```

## Schema Validation

All request/response schemas validated using Pydantic models:

### Request Validation
- FastAPI automatically validates request parameters and bodies against Pydantic models
- Invalid requests return 422 Unprocessable Entity with detailed error messages

### Response Validation
- Contract tests validate response schemas match OpenAPI definitions
- Use `pydantic.BaseModel` for all response types
- Auto-generate TypeScript client from OpenAPI spec (Constitution Principle VI)

## Error Handling Standards

All error responses follow the `ErrorResponse` schema:

```json
{
  "error": "Error Type",
  "message": "Human-readable error message",
  "status_code": 403,
  "details": {
    "additional": "context"
  }
}
```

**Error Types**:
- `Unauthorized`: Missing or invalid authentication token (401)
- `Forbidden`: User lacks required permissions (403)
- `Bad Request`: Invalid request parameters or body (400)
- `Service Unavailable`: External service failure (503)
- `Internal Server Error`: Unexpected server error (500)

## Admin Privilege Checking

Admin-only endpoints use the `get_admin_user()` FastAPI dependency:

```python
from server.lib.auth import get_admin_user

@router.get("/metrics/performance")
async def get_performance_metrics(
    admin_user = Depends(get_admin_user),  # Enforces admin check
    time_range: str = "24h"
):
    # admin_user populated only if workspace admin
    # Non-admins receive 403 Forbidden
    ...
```

**Admin Check Logic**:
1. Extract user token from request (X-Forwarded-Access-Token header)
2. Call Databricks Workspace API to check if user has admin role
3. Cache result for 5 minutes (per-user cache key)
4. Return 503 if API call fails (fail-secure)
5. Return 403 if user is not admin

## Testing Checklist

### Contract Tests (RED Phase - Before Implementation)
- [ ] Test GET /metrics/performance returns 404 (not implemented)
- [ ] Test GET /metrics/usage returns 404 (not implemented)
- [ ] Test GET /metrics/time-series returns 404 (not implemented)
- [ ] Test POST /metrics/usage-events returns 404 (not implemented)

### Contract Tests (GREEN Phase - After Implementation)
- [ ] Test GET /metrics/performance returns 200 with valid schema
- [ ] Test GET /metrics/performance returns 403 for non-admin
- [ ] Test GET /metrics/performance accepts time_range parameter
- [ ] Test GET /metrics/performance accepts endpoint filter
- [ ] Test GET /metrics/usage returns 200 with valid schema
- [ ] Test GET /metrics/usage returns 403 for non-admin
- [ ] Test GET /metrics/usage accepts time_range parameter
- [ ] Test GET /metrics/usage accepts event_type filter
- [ ] Test GET /metrics/time-series returns 200 with valid schema
- [ ] Test GET /metrics/time-series requires metric_type parameter
- [ ] Test POST /metrics/usage-events returns 202 for valid batch
- [ ] Test POST /metrics/usage-events returns 400 for invalid events
- [ ] Test POST /metrics/usage-events does NOT require admin
- [ ] Test all endpoints return 401 for unauthenticated requests

### Schema Validation Tests
- [ ] Validate PerformanceMetricsResponse schema matches OpenAPI
- [ ] Validate UsageMetricsResponse schema matches OpenAPI
- [ ] Validate TimeSeriesMetricsResponse schema matches OpenAPI
- [ ] Validate UsageEventBatchRequest schema matches OpenAPI
- [ ] Validate ErrorResponse schema matches OpenAPI

### Error Handling Tests
- [ ] Test 401 response format matches ErrorResponse schema
- [ ] Test 403 response format matches ErrorResponse schema
- [ ] Test 400 response format matches ErrorResponse schema
- [ ] Test 503 response format matches ErrorResponse schema

---

## References

- **Feature Spec**: [../spec.md](../spec.md)
- **Data Model**: [../data-model.md](../data-model.md)
- **Research**: [../research.md](../research.md)
- **Constitution**: [/.specify/memory/constitution.md](/.specify/memory/constitution.md)
  - Principle IV: Type Safety Throughout (contract testing)
  - Principle XII: Test Driven Development (TDD methodology)

