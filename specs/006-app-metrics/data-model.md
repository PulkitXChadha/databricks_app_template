# Data Model: App Usage and Performance Metrics

**Feature**: 006-app-metrics  
**Date**: 2025-10-18  
**Phase**: 1 (Data Model Design)

## Overview

This document defines the data entities, relationships, and lifecycle for the metrics collection system. All entities are persisted to Lakebase (Postgres in Databricks) and follow the hybrid retention model: 7 days raw data + 90 days aggregated data.

---

## Entity Diagram

```
┌─────────────────────┐
│  PerformanceMetric  │  (Raw, 7-day retention)
├─────────────────────┤
│ id: UUID (PK)       │
│ timestamp: DateTime │──┐
│ endpoint: String    │  │
│ method: String      │  │
│ status_code: Int    │  │  Aggregated daily at 2 AM
│ response_time_ms: Float│ │  (7-day-old records)
│ user_id: String?    │  │
│ error_type: String? │  │
└─────────────────────┘  │
                         │
┌─────────────────────┐  │
│    UsageEvent       │  │  (Raw, 7-day retention)
├─────────────────────┤  │
│ id: UUID (PK)       │  │
│ timestamp: DateTime │──┤
│ event_type: String  │  │
│ user_id: String     │  │
│ page_name: String?  │  │
│ element_id: String? │  │
│ success: Boolean?   │  │
│ metadata: JSON?     │  │
└─────────────────────┘  │
                         │
                         ▼
┌─────────────────────────┐
│   AggregatedMetric      │  (Computed, 90-day retention)
├─────────────────────────┤
│ id: UUID (PK)           │
│ time_bucket: DateTime   │  (hourly buckets)
│ metric_type: String     │  (performance/usage)
│ endpoint_path: String?  │  (for performance)
│ event_type: String?     │  (for usage)
│ aggregated_values: JSON │  (avg, min, max, count, p50, p95, p99)
│ sample_count: Int       │
└─────────────────────────┘
```

---

## Entity 1: PerformanceMetric

**Purpose**: Capture individual API request performance data for real-time debugging and detailed analysis.

### Fields

| Field | Type | Nullable | Indexed | Description | Validation |
|-------|------|----------|---------|-------------|------------|
| `id` | UUID | No | PK | Unique identifier (UUID v4) | Auto-generated |
| `timestamp` | DateTime(TZ) | No | Yes | Request timestamp (UTC) | Auto-set to `NOW()` |
| `endpoint` | String(500) | No | Yes | API endpoint path (e.g., `/api/v1/lakebase/sources`) | Max 500 chars |
| `method` | String(10) | No | No | HTTP method (GET, POST, PUT, DELETE, etc.) | Enum validation |
| `status_code` | Integer | No | No | HTTP response status code | 100-599 range |
| `response_time_ms` | Float | No | No | Request processing time in milliseconds | >= 0 |
| `user_id` | String(255) | Yes | Yes | Authenticated user ID (null for anonymous) | Optional |
| `error_type` | String(255) | Yes | No | Error category if status >= 400 (e.g., "ValidationError", "AuthError") | Optional |

### Indexes
- **Primary Key**: `id` (UUID)
- **Time-range queries**: `timestamp` (B-tree index)
- **Endpoint analysis**: `endpoint` (B-tree index)
- **User filtering**: `user_id` (B-tree index, nullable)

### Relationships
- **User**: Optional relationship to authenticated user (not enforced by FK; user_id is string identifier)
- **AggregatedMetric**: PerformanceMetrics older than 7 days are aggregated into AggregatedMetric records

### Lifecycle
1. **Creation**: Automatically created by FastAPI middleware on every API request (see `server/lib/metrics_middleware.py`)
2. **Retention**: Kept in raw form for 7 days for detailed debugging
3. **Aggregation**: After 7 days, daily job (2 AM) aggregates into hourly summaries
4. **Deletion**: Raw records deleted after aggregation (atomic transaction)

### Business Rules
- **FR-001**: Every HTTP API request MUST create exactly one PerformanceMetric record
- **FR-007**: Metric collection failures MUST NOT impact application functionality (graceful degradation)
- **Anonymity**: Unauthenticated requests recorded with `user_id = NULL`
- **Error classification**: Status codes >= 400 MUST populate `error_type` field

---

## Entity 2: UsageEvent

**Purpose**: Track all user interactions (page views, clicks, form submissions, feature usage) for product analytics and user behavior understanding.

### Fields

| Field | Type | Nullable | Indexed | Description | Validation |
|-------|------|----------|---------|-------------|------------|
| `id` | UUID | No | PK | Unique identifier (UUID v4) | Auto-generated |
| `timestamp` | DateTime(TZ) | No | Yes | Event occurrence timestamp (UTC) | Auto-set to `NOW()` |
| `event_type` | String(100) | No | Yes | Event category (page_view, button_click, form_submit, query_executed, model_invoked, etc.) | Enum validation |
| `user_id` | String(255) | No | Yes | Authenticated user ID | Required |
| `page_name` | String(255) | Yes | No | Page/route name where event occurred (e.g., "/metrics", "/lakebase/sources") | Optional |
| `element_id` | String(255) | Yes | No | UI element identifier for interaction events (e.g., "submit-query-btn") | Optional |
| `success` | Boolean | Yes | No | Whether the action completed successfully (null for non-action events) | Optional |
| `metadata` | JSON | Yes | No | Flexible context data (e.g., query text, model name, filter values) | Valid JSON |

### Indexes
- **Primary Key**: `id` (UUID)
- **Time-range queries**: `timestamp` (B-tree index)
- **Event analysis**: `event_type` (B-tree index)
- **User behavior tracking**: `user_id` (B-tree index)

### Relationships
- **User**: Associated with authenticated user (required; anonymous events not tracked for usage)
- **AggregatedMetric**: UsageEvents older than 7 days are aggregated into AggregatedMetric records

### Lifecycle
1. **Creation**: Created by frontend tracker (batched submissions) or backend API calls
2. **Batching**: Frontend accumulates events (10s or 20 events) before submitting batch to `/api/v1/metrics/usage-events` endpoint
3. **Retry Logic**: Failed batch submissions retry with client-side exponential backoff (initial delay 1s, backoff multiplier 2x, max 3 attempts total; delays: 1s after 1st failure, 2s after 2nd failure); after 3 failed attempts, batch is discarded with console error logging to prevent memory accumulation
4. **Retention**: Kept in raw form for 7 days for detailed user journey analysis
5. **Aggregation**: After 7 days, daily job (2 AM) aggregates into hourly summaries by event type
6. **Deletion**: Raw records deleted after aggregation (atomic transaction)

### Business Rules
- **FR-010**: System MUST track all user interactions (page views, clicks, form submissions, feature usage)
- **FR-012**: Backend MUST accept batch submissions of usage events (array of events)
- **Debouncing**: Rapid repeated events (e.g., typing) SHOULD be debounced on frontend before submission
- **Authentication required**: All usage events require authenticated user (user_id cannot be null)

### Event Types (Enum)
- `page_view`: User navigated to a page
- `button_click`: User clicked a button or link
- `form_submit`: User submitted a form
- `query_executed`: User executed a SQL query
- `model_invoked`: User invoked a model endpoint
- `preference_changed`: User updated preferences
- `data_source_selected`: User selected a data source
- `schema_detected`: Schema detection triggered
- `file_uploaded`: User uploaded a file
- `export_triggered`: User exported data

---

## Entity 3: AggregatedMetric

**Purpose**: Store pre-computed hourly summaries of performance and usage metrics for efficient historical queries (8-90 days ago).

### Fields

| Field | Type | Nullable | Indexed | Description | Validation |
|-------|------|----------|---------|-------------|------------|
| `id` | UUID | No | PK | Unique identifier (UUID v4) | Auto-generated |
| `time_bucket` | DateTime(TZ) | No | Yes | Hourly time bucket (e.g., "2025-10-18 14:00:00 UTC") | Hour-aligned timestamp |
| `metric_type` | String(50) | No | Yes | Metric category: "performance" or "usage" | Enum: performance, usage |
| `endpoint_path` | String(500) | Yes | Yes | API endpoint (for performance metrics only, null for usage) | Optional |
| `event_type` | String(100) | Yes | Yes | Event type (for usage metrics only, null for performance) | Optional |
| `aggregated_values` | JSON | No | No | Statistical aggregates (structure varies by metric_type) | Valid JSON |
| `sample_count` | Integer | No | No | Number of raw records aggregated into this bucket | >= 0 |

### Indexes
- **Primary Key**: `id` (UUID)
- **Time-range queries**: `time_bucket` (B-tree index)
- **Metric filtering**: `metric_type` (B-tree index)
- **Endpoint analysis**: `endpoint_path` (B-tree index, nullable)
- **Event analysis**: `event_type` (B-tree index, nullable)

### Aggregated Values Structure

**For Performance Metrics** (`metric_type = "performance"`):
```json
{
  "avg_response_time_ms": 123.45,
  "min_response_time_ms": 10.2,
  "max_response_time_ms": 850.7,
  "p50_response_time_ms": 95.3,
  "p95_response_time_ms": 450.2,
  "p99_response_time_ms": 720.5,
  "total_requests": 1523,
  "error_count": 12,
  "error_rate": 0.0079,  // Decimal ratio (not percentage), UI converts to 0.79% for display
  "status_code_distribution": {
    "200": 1480,
    "400": 8,
    "404": 3,
    "500": 1
  }
}
```

**Note**: Percentile values (p50, p95, p99) are pre-computed during the daily aggregation job using PostgreSQL `percentile_cont` function for optimal dashboard query performance. For recent data (<7 days old), percentiles are calculated on-demand from raw metrics; for historical data (8-90 days old), pre-computed percentiles are retrieved from this JSON structure.

**For Usage Metrics** (`metric_type = "usage"`):
```json
{
  "total_events": 5432,
  "unique_users": 45,
  "event_count_by_page": {
    "/metrics": 234,
    "/lakebase/sources": 567,
    "/model-inference": 432
  },
  "success_count": 5320,
  "failure_count": 112,
  "success_rate": 0.9794
}
```

### Relationships
- **Source data**: Computed from PerformanceMetric and UsageEvent records older than 7 days
- **Time-series continuity**: Each hourly bucket aggregates all raw records with `timestamp` in that hour

### Lifecycle
1. **Creation**: Generated by daily aggregation job (2 AM UTC) for all 7-day-old raw metrics; percentiles (p50, p95, p99) pre-computed using PostgreSQL `percentile_cont` function during aggregation
2. **Immutable**: Once created, aggregated records are never updated (append-only)
3. **Retention**: Kept for 90 days total (including the 7 days covered by raw data)
4. **Deletion**: Records with `time_bucket < NOW() - INTERVAL '90 days'` deleted by cleanup job
5. **Alerting**: Failed aggregations logged at ERROR level with detailed error context and trigger Databricks job failure notification (configured in job settings via email recipients or integration webhooks)

### Business Rules
- **FR-008**: Aggregation job MUST run daily at 2 AM UTC to process 7-day-old raw metrics
- **Atomicity**: Aggregation and raw data deletion MUST occur in same transaction
- **Idempotency**: Aggregation job MUST be idempotent (safe to re-run on same data) via check-before-insert pattern: Before aggregating each hourly bucket, query `aggregated_metrics` table for existing records matching `(time_bucket, metric_type, endpoint_path/event_type)` composite key; if record exists, skip aggregation for that bucket; only aggregate and delete raw records for buckets with no existing aggregated record. This allows safe retry after partial failures without duplicate aggregation or premature raw data deletion.
- **Dashboard routing**: Queries for time ranges > 7 days ago MUST use AggregatedMetric table with pre-computed percentile values; queries for <7 days use raw tables with on-demand percentile calculation
- **Percentile Strategy**: Pre-compute percentiles during aggregation for faster dashboard queries (8-90 day historical data); calculate on-demand for recent data (<7 days)

---

## Data Lifecycle Summary

```
┌─────────────────────────────────────────────────────────────┐
│                     Metrics Lifecycle                        │
└─────────────────────────────────────────────────────────────┘

T=0                T=7 days            T=90 days
 │                     │                    │
 │  Raw Metrics        │  Aggregation Job   │  Cleanup Job
 │  Created            │  (2 AM Daily)      │  (2 AM Daily)
 │                     │                    │
 ▼                     ▼                    ▼
[PerformanceMetric] ──> [Deleted] ──────────────────────────
[UsageEvent]        ──>                                     
                        │                    │
                        ▼                    ▼
                   [AggregatedMetric] ──> [Deleted]
                   (Hourly Summaries)
                   Kept for 90 days total
```

**Dashboard Query Strategy**:
- **Last 7 days (0-7 days ago)**: Query raw `PerformanceMetric` and `UsageEvent` tables ONLY (high granularity)
- **8-90 days ago**: Query `AggregatedMetric` table ONLY (hourly summaries)
- **Time-series charts**: Combine raw + aggregated data for seamless visualization across time ranges

**Boundary Handling (7-8 day cutoff)**:
- **No hybrid queries**: Never mix raw and aggregated data for the same time bucket
- **Query routing logic**:
  ```python
  if time_range_end <= NOW() - INTERVAL '7 days':
      # All data is > 7 days old → Use aggregated table ONLY
      query_table = "aggregated_metrics"
  elif time_range_start >= NOW() - INTERVAL '7 days':
      # All data is ≤ 7 days old → Use raw tables ONLY
      query_table = "performance_metrics" or "usage_events"
  else:
      # Time range spans boundary → Split into two queries:
      #   1. Raw data for last 7 days
      #   2. Aggregated data for 8+ days ago
      #   Merge results in application layer
      query_tables = ["raw", "aggregated"]
  ```
- **Aggregation job timing**: At 2 AM, metrics with `timestamp < NOW() - INTERVAL '7 days'` are aggregated
- **Grace period**: During aggregation job execution (2:00-2:15 AM), queries for 7-day boundary may show temporary gaps (acceptable)

---

## Database Schema (SQLAlchemy Models)

### PerformanceMetric Model
```python
from sqlalchemy import Column, String, Integer, Float, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

class PerformanceMetric(Base):
    __tablename__ = 'performance_metrics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    endpoint = Column(String(500), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Float, nullable=False)
    user_id = Column(String(255), nullable=True, index=True)
    error_type = Column(String(255), nullable=True)
    
    __table_args__ = (
        Index('ix_performance_metrics_timestamp', 'timestamp'),
        Index('ix_performance_metrics_endpoint', 'endpoint'),
        Index('ix_performance_metrics_user_id', 'user_id'),
    )
```

### UsageEvent Model
```python
from sqlalchemy import Column, String, Boolean, DateTime, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

class UsageEvent(Base):
    __tablename__ = 'usage_events'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    page_name = Column(String(255), nullable=True)
    element_id = Column(String(255), nullable=True)
    success = Column(Boolean, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    __table_args__ = (
        Index('ix_usage_events_timestamp', 'timestamp'),
        Index('ix_usage_events_event_type', 'event_type'),
        Index('ix_usage_events_user_id', 'user_id'),
    )
```

### AggregatedMetric Model
```python
from sqlalchemy import Column, String, Integer, DateTime, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid

class AggregatedMetric(Base):
    __tablename__ = 'aggregated_metrics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    time_bucket = Column(DateTime(timezone=True), nullable=False, index=True)
    metric_type = Column(String(50), nullable=False, index=True)
    endpoint_path = Column(String(500), nullable=True, index=True)
    event_type = Column(String(100), nullable=True, index=True)
    aggregated_values = Column(JSON, nullable=False)
    sample_count = Column(Integer, nullable=False)
    
    __table_args__ = (
        Index('ix_aggregated_metrics_time_bucket', 'time_bucket'),
        Index('ix_aggregated_metrics_metric_type', 'metric_type'),
        Index('ix_aggregated_metrics_endpoint_path', 'endpoint_path'),
        Index('ix_aggregated_metrics_event_type', 'event_type'),
    )
```

---

## Validation Rules

### PerformanceMetric Validation
- `id`: Must be valid UUID v4
- `timestamp`: Must be in UTC timezone
- `endpoint`: Max 500 characters, non-empty
- `method`: Must be valid HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
- `status_code`: Must be in range 100-599
- `response_time_ms`: Must be >= 0
- `user_id`: Optional, max 255 characters
- `error_type`: Optional, max 255 characters, required if `status_code >= 400`

### UsageEvent Validation
- `id`: Must be valid UUID v4
- `timestamp`: Must be in UTC timezone
- `event_type`: Must be valid event type from enum (see Event Types section)
- `user_id`: Required, max 255 characters
- `page_name`: Optional, max 255 characters
- `element_id`: Optional, max 255 characters; captured using hybrid strategy: (1) `data-track-id` custom attribute if present (explicit tracking identifier), (2) HTML `id` attribute if present and `data-track-id` absent, (3) fallback to `{tagName}.{textContent}` (e.g., "button.Submit Query") if neither attribute exists, truncated to 100 characters
- `success`: Optional boolean
- `metadata`: Must be valid JSON object if present

### AggregatedMetric Validation
- `id`: Must be valid UUID v4
- `time_bucket`: Must be hour-aligned timestamp (minutes/seconds = 00)
- `metric_type`: Must be "performance" or "usage"
- `endpoint_path`: Required if `metric_type = "performance"`, null otherwise
- `event_type`: Required if `metric_type = "usage"`, null otherwise
- `aggregated_values`: Must be valid JSON object matching structure for metric_type
- `sample_count`: Must be >= 0

---

## Migration Strategy

All three tables created in single Alembic migration: `migrations/versions/xxx_add_metrics_tables.py`

**Migration includes**:
1. Create `performance_metrics` table with indexes
2. Create `usage_events` table with indexes
3. Create `aggregated_metrics` table with indexes
4. Down migration drops all three tables

**Migration execution**:
```bash
# Generate migration
uv run alembic revision --autogenerate -m "Add metrics tables"

# Review generated migration
cat migrations/versions/xxx_add_metrics_tables.py

# Apply migration
uv run alembic upgrade head
```

---

## Performance Considerations

### Query Optimization
- **Time-range filtering**: All queries use indexed `timestamp` column for efficient time-range scans
- **Endpoint analysis**: `endpoint` index enables fast filtering by API path
- **User filtering**: `user_id` index supports per-user queries
- **Aggregation routing**: Dashboard automatically routes queries to raw vs aggregated tables based on time range

### Write Performance
- **Async writes**: Metrics written asynchronously to avoid blocking request processing
- **Batch inserts**: Usage events submitted in batches (10s/20 events) to reduce insert overhead
- **Connection pooling**: SQLAlchemy connection pool (min=5, max=20) handles concurrent writes
- **Connection Pool Exhaustion**: Under extreme load, metric writes block and wait for available connections (ensures data completeness at cost of potential request slowdown); if connection acquisition timeout exceeded, treat as database unavailability per FR-007
- **Transaction Isolation**: Raw metric/event writes use database default isolation (PostgreSQL READ COMMITTED); aggregation job uses SERIALIZABLE isolation to prevent race conditions

### Storage Management
- **7-day retention**: Limits raw table growth to ~7 days * daily_request_volume rows
- **90-day retention**: Aggregated hourly summaries drastically reduce storage (hourly vs per-request)
- **Example calculation**: 10K requests/day = 70K raw rows (7 days) + 2,160 aggregated rows (90 days * 24 hours)

---

## Summary

The data model implements a hybrid retention strategy balancing detailed debugging (7-day raw) with long-term trend analysis (90-day aggregated). All entities use UUID primary keys for distributed scalability, proper indexing for query performance, and flexible JSON columns for extensibility. The design follows constitutional requirements (Lakebase persistence, type safety, multi-user isolation) and supports all functional requirements from the feature specification.

---

## Admin Check Pattern

**Purpose**: Document the Databricks Workspace API integration pattern for verifying administrator privileges.

### Implementation Details

**API Call**: `WorkspaceClient.current_user.me()`

**Response Structure**:
```python
{
  "id": "1234567890",
  "userName": "user@example.com",
  "displayName": "User Name",
  "active": true,
  "emails": [...],
  "groups": [
    {
      "display": "users",
      "value": "group-id-1",
      "$ref": "Groups/group-id-1"
    },
    {
      "display": "admins",  # ← Admin indicator
      "value": "group-id-2",
      "$ref": "Groups/group-id-2"
    }
  ]
}
```

### Admin Detection Logic

**Field Name**: Use `"display"` field from groups array (NOT `"displayName"` which doesn't exist in groups)

**String Matching**: Case-insensitive comparison using `.lower()` for robustness

**Known Admin Group Names**: 
- `"admins"` (standard Databricks workspace admin group)
- `"workspace_admins"` (alternative naming in some deployments)
- `"administrators"` (legacy naming convention)

```python
def is_workspace_admin(user_info: dict) -> bool:
    """
    Check if user has workspace admin privileges.
    
    Args:
        user_info: Response from WorkspaceClient.current_user.me()
    
    Returns:
        True if user is admin, False otherwise
        
    Implementation:
        - Case-insensitive match on group "display" field
        - Checks multiple possible admin group names
        - Returns False if groups array is missing or empty
    """
    ADMIN_GROUP_NAMES = {"admins", "workspace_admins", "administrators"}
    
    groups = user_info.get("groups", [])
    return any(
        group.get("display", "").lower() in ADMIN_GROUP_NAMES
        for group in groups
    )
```

**Edge Cases**:
- Missing `groups` field → Returns False (safe default)
- Empty `groups` array → Returns False
- Group with missing `display` field → Skipped (`.get("display", "")` returns empty string)
- Case variations ("Admins", "ADMINS") → Handled by `.lower()` normalization

### Caching Strategy

- **Cache Key**: `f"admin_check:{user_id}"`
- **Cache TTL**: 300 seconds (5 minutes)
- **Cache Backend**: In-memory dictionary with timestamp-based TTL check (structure: `{user_id: {"is_admin": bool, "expires_at": datetime}}`); no LRU/LFU eviction needed (single cache entry per user, low cardinality)
- **Cache Invalidation**: Automatic expiry after TTL via timestamp comparison (`datetime.utcnow() > cache[user_id]["expires_at"]`)
- **Fallback**: On cache miss or expiry, call Databricks API and cache result with new expiry timestamp
- **Concurrency**: No locking required (cache reads are idempotent; worst case = redundant API call)

### Error Handling

| Scenario | Response | Rationale |
|----------|----------|-----------|
| API call succeeds, user is admin | Allow access (200) | Normal flow |
| API call succeeds, user not admin | 403 Forbidden | Security requirement |
| API call fails (network, timeout, 5xx) | 503 Service Unavailable | Fail secure |
| Invalid token / 401 from API | 401 Unauthorized | Authentication issue |
| Cache hit within TTL | Use cached result | Performance optimization |

### Testing Considerations

- **Unit tests**: Mock `WorkspaceClient.current_user.me()` response
- **Integration tests**: Use test workspace with known admin/non-admin users
- **Cache tests**: Verify TTL expiration triggers new API call
- **Security tests**: Verify non-admin cannot bypass check via token manipulation

---

## Active User Count Pattern

**Purpose**: Define the canonical method for calculating active user counts to prevent double-counting users who appear in both performance metrics (API requests) and usage events (UI interactions).

### Definition

**Active User**: A unique user (`user_id`) who performed at least one action OR made at least one API request within the specified time window.

### SQL Query Pattern

```sql
-- Active User Count (prevents double-counting across tables)
SELECT COUNT(DISTINCT user_id) AS active_users
FROM (
    -- Users from API requests (performance metrics)
    SELECT user_id 
    FROM performance_metrics
    WHERE timestamp >= :start_time
      AND timestamp <= :end_time
      AND user_id IS NOT NULL  -- Exclude anonymous requests
    
    UNION
    
    -- Users from UI interactions (usage events)
    SELECT user_id
    FROM usage_events
    WHERE timestamp >= :start_time
      AND timestamp <= :end_time
) AS all_users;
```

### Implementation Details

**Time Range Handling**:
- **Last 7 days**: Query both raw tables (`performance_metrics`, `usage_events`)
- **8-90 days ago**: Query aggregated metrics and extract `unique_users` from `aggregated_values` JSON (pre-computed during aggregation)
- **Spanning boundary**: Split query and merge unique user sets in application layer

**Anonymous User Handling**:
- **Default behavior**: Exclude `user_id = NULL` from active user counts
- **Optional inclusion**: Dashboard provides toggle to include anonymous users in counts
- **Anonymous count query**: Separate query for `COUNT(*) WHERE user_id IS NULL`

**Aggregation Job**:
When aggregating into `AggregatedMetric`, store unique user count in JSON:
```python
aggregated_values = {
    "unique_users": len(set(performance_user_ids) | set(usage_user_ids)),
    # ... other metrics
}
```

### Dashboard Display

**Metrics Card**:
```
Active Users (Last 24h)
━━━━━━━━━━━━━━━━━━━━━
    156 users
    
    [ ] Include Anonymous
```

**Filter Behavior**:
- Unchecked (default): Shows authenticated users only (`user_id IS NOT NULL`)
- Checked: Shows total activity including anonymous (`user_id IS NULL OR user_id IS NOT NULL`)

---

## Time Range Selection Pattern

**Purpose**: Document the UI pattern for time range filtering with predefined options and custom date range picker.

### UI Components

**Quick Select Buttons** (predefined options):
- Last 24 hours
- Last 7 days
- Last 30 days
- Last 90 days

**Custom Date Range Picker**:
- Full date picker widget allowing arbitrary start/end date selection
- Constrained to 90-day retention window
- Maximum range: 90 days between start and end date
- Minimum selectable date: NOW() - 90 days (data retention limit)

### Validation Rules

**Frontend Validation** (Design Bricks date picker component):
1. **Maximum Range**: If `(end_date - start_date) > 90 days`, display error: "Date range cannot exceed 90 days. Please select a shorter range."
2. **Historical Limit**: If `start_date < NOW() - 90 days`, display error: "Data is only available for the last 90 days. Please select a more recent date."
3. **Future Dates**: If `end_date > NOW()`, display error: "Cannot select future dates."
4. **Start After End**: If `start_date > end_date`, display error: "Start date must be before end date."

**Backend Validation** (API endpoint):
```python
def validate_time_range(start_date: datetime, end_date: datetime) -> None:
    now = datetime.utcnow()
    max_retention = now - timedelta(days=90)
    
    if end_date > now:
        raise ValidationError("Cannot query future dates")
    if start_date < max_retention:
        raise ValidationError("Data retention is 90 days; earliest queryable date is " + max_retention.isoformat())
    if (end_date - start_date).days > 90:
        raise ValidationError("Maximum time range is 90 days")
    if start_date > end_date:
        raise ValidationError("Start date must be before end date")
```

### Dashboard UX Flow

1. **Initial Load**: Default to "Last 24 hours" quick-select option
2. **Quick Select**: Click predefined button → Update all charts instantly
3. **Custom Range**: 
   - Click date picker icon → Open date picker modal
   - Select start date → Validate against constraints
   - Select end date → Validate against constraints
   - Click "Apply" → Update all charts with custom range
4. **Error Handling**: Display validation errors inline with date picker, prevent submission until valid

### Testing Validation

**Test Scenario**: User performs both API request AND UI interaction
- Insert 1 performance_metric record with `user_id = "test-user"`
- Insert 1 usage_event record with `user_id = "test-user"`
- Query active_users → Expected result: `1` (not 2)

