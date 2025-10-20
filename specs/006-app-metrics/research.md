# Research: App Usage and Performance Metrics

**Feature**: 006-app-metrics  
**Date**: 2025-10-18  
**Phase**: 0 (Research & Design Decisions)

## Overview

This document captures research findings and design decisions for implementing comprehensive metrics collection, persistence, and visualization in the Databricks app template.

---

## 1. Performance Metrics Collection Strategy

### Decision
Use FastAPI middleware for automatic performance metric collection on all API requests.

### Rationale
- **Zero-touch instrumentation**: Middleware automatically captures all requests without modifying individual endpoint code
- **Consistent data**: Every request captured with identical metadata structure
- **Low overhead**: Middleware adds <1ms overhead per request (timestamp capture)
- **Built-in FastAPI support**: Middleware pattern is idiomatic and well-documented in FastAPI
- **Correlation ID propagation**: Middleware can extract/generate correlation IDs for distributed tracing

### Alternatives Considered
1. **Manual instrumentation per endpoint**
   - Rejected: High maintenance burden, easy to miss endpoints, inconsistent implementation
   - Would require touching every router function
   
2. **Decorator-based approach**
   - Rejected: Still requires manual application to each endpoint
   - Middleware provides same functionality with less code
   
3. **External APM tools (Datadog, New Relic)**
   - Rejected: Adds external dependency, cost, and complexity
   - Requirements specify using Lakebase for persistence
   - Custom solution provides full control and integration

### Implementation Notes
- Middleware will use `request.state` to share timing data between pre/post processing
- Performance metrics written to database asynchronously to avoid blocking request processing
- Error handling ensures metrics collection failure doesn't impact application functionality

---

## 2. Database Schema Design

### Decision
Use three separate tables: `performance_metrics` (raw), `usage_events` (raw), and `aggregated_metrics` (computed).

### Rationale
- **Separation of concerns**: Performance and usage data have different structures and query patterns
- **Optimized queries**: Separate tables allow targeted indexes for each metric type
- **Flexible retention**: Different retention policies can be applied per table if needed
- **Clear data lifecycle**: Raw vs aggregated separation makes lifecycle management explicit
- **Query performance**: Dashboard can query raw tables for recent data (7 days) and aggregated for historical (8-90 days)

### Alternatives Considered
1. **Single metrics table with type discriminator**
   - Rejected: Would require JSONB column for flexible schema, slower queries
   - Index bloat from supporting multiple query patterns
   
2. **Separate tables for raw and aggregated performance/usage (4 tables)**
   - Rejected: Over-engineering for current requirements
   - Aggregated metrics can include both performance and usage in same table
   - Current approach can evolve to 4 tables if needed
   
3. **Time-series database (InfluxDB, TimescaleDB)**
   - Rejected: Adds external dependency, requires separate deployment
   - Lakebase (Postgres) is sufficient for application-scale metrics
   - Constitution mandates Lakebase for persistent data

### Schema Details
```sql
-- Raw performance metrics (7-day retention)
performance_metrics: id (UUID), timestamp, endpoint, method, status_code, response_time_ms, user_id, error_type

-- Raw usage events (7-day retention)  
usage_events: id (UUID), timestamp, event_type, user_id, page_name, element_id, success, metadata (JSONB)

-- Aggregated metrics (90-day retention)
aggregated_metrics: id (UUID), time_bucket (hourly), metric_type, endpoint_path, event_type, aggregated_values (JSONB), sample_count
```

---

## 3. Data Aggregation & Retention Strategy

### Decision
Daily scheduled job (2 AM) to aggregate 7-day-old raw metrics into hourly summaries and delete raw data.

### Rationale
- **Storage efficiency**: Raw metrics grow unbounded without aggregation; 7-day window balances debugging needs with storage costs
- **Query performance**: Aggregated hourly data reduces query complexity for historical time-series
- **Off-peak execution**: 2 AM scheduling minimizes impact on production workload
- **Simple implementation**: Daily batch job using standard Python script (no complex streaming required)
- **Deterministic lifecycle**: Clear 7-day boundary makes debugging and data investigation straightforward

### Alternatives Considered
1. **Real-time aggregation with streaming (Kafka, Flink)**
   - Rejected: Over-engineered for application-scale metrics
   - Adds significant infrastructure complexity
   - 7-day raw retention is sufficient for debugging
   
2. **Continuous aggregation (trigger-based)**
   - Rejected: Higher database load, more complex error handling
   - Daily batch is simpler and sufficient for 60-second latency requirement
   
3. **Longer raw retention (30 days)**
   - Rejected: Unnecessary storage cost for diminishing debugging value
   - 7 days captures weekly patterns and provides sufficient debugging window
   
4. **Shorter raw retention (24 hours)**
   - Rejected: Too aggressive for debugging production issues
   - User story requires 7-day historical queries with high granularity

### Implementation Approach
- Scheduled job runs as Databricks workflow (defined in databricks.yml)
- Job queries `performance_metrics WHERE timestamp < NOW() - INTERVAL '7 days'`
- Aggregates into hourly buckets with AVG, MIN, MAX, COUNT, P50, P95, P99 percentiles
- Inserts aggregated data into `aggregated_metrics` table
- Deletes processed raw records in same transaction (atomicity)
- Job failures logged and retried (idempotent design)

---

## 4. Admin Privilege Verification

### Decision
Use Databricks Workspace API to check if user has workspace admin role, with 5-minute caching.

### Rationale
- **Authoritative source**: Databricks Workspace API is the single source of truth for user roles
- **Security**: No client-side trust; server validates admin status on every request
- **OBO alignment**: Uses existing On-Behalf-Of-User token to query API as the authenticated user
- **Caching**: 5-minute TTL reduces API calls while maintaining reasonable security (edge case from spec)
- **Fail-secure**: API failures return 503 Service Unavailable (deny access)

### Alternatives Considered
1. **Hardcoded admin user list**
   - Rejected: Brittle, requires code changes to update admins
   - Doesn't scale, prone to staleness
   
2. **Custom admin role in Lakebase**
   - Rejected: Duplicates Databricks workspace role management
   - Requires manual synchronization
   - Constitution mandates using platform-native authentication
   
3. **No caching (API call per request)**
   - Rejected: Excessive API load for frequently accessed dashboard
   - 5-minute cache balances freshness with performance (spec requirement)

### Implementation Notes
- Admin check implemented as FastAPI dependency: `get_admin_user()`
- Dependency calls `admin_service.is_workspace_admin(user_token)`
- Cache key: `f"admin_check:{user_id}"` stored in-memory (simple dict with expiry)
- Cache invalidation: TTL-based (5 minutes)
- Error handling: Log API failures and return 503 with clear error message

---

## 5. Frontend Visualization Library

### Decision
Use Recharts for dashboard charts (line charts, bar charts, pie charts).

### Rationale
- **React-native**: Built specifically for React with hooks and component patterns
- **TypeScript support**: Full TypeScript definitions for type safety
- **Design Bricks compatibility**: Recharts styling can match Databricks design system
- **Lightweight**: ~100KB gzipped, no heavy dependencies
- **Declarative API**: JSX-based chart definition aligns with React philosophy
- **Time-series focus**: Excellent support for time-based data visualization

### Alternatives Considered
1. **Chart.js**
   - Rejected: Imperative canvas-based API less idiomatic in React
   - Requires react-chartjs-2 wrapper adding indirection
   - Slightly larger bundle size
   
2. **Victory**
   - Rejected: Similar to Recharts but less active maintenance
   - More complex API for simple use cases
   
3. **D3.js**
   - Rejected: Extremely powerful but overkill for dashboard charts
   - Steep learning curve, verbose code for standard charts
   - Large bundle size (~300KB)
   
4. **Design Bricks native charts**
   - Investigated: Design Bricks may not include charting components
   - Will verify during implementation; if available, will prefer Design Bricks
   - Recharts chosen as fallback with styling to match Design Bricks

### Implementation Notes
- Install: `bun add recharts`
- Components: `<LineChart>`, `<BarChart>`, `<PieChart>` for different metric types
- Time-series: Use `<LineChart>` with `<XAxis dataKey="timestamp">` for historical trends
- Styling: Custom theme colors to match Databricks design system

---

## 6. Usage Event Tracking Strategy

### Decision
Frontend batches usage events (10 seconds or 20 events) and submits to backend batch endpoint asynchronously.

### Rationale
- **Reduced API overhead**: Batching reduces HTTP requests from potentially hundreds to 6 per minute
- **Non-blocking UX**: Async submission ensures user interactions aren't slowed by metric tracking
- **Debouncing support**: Frontend can deduplicate rapid repeated events (e.g., typing in input field)
- **Backend efficiency**: Single batch insert is faster than many individual inserts
- **Network resilience**: Batching with retry logic handles transient network failures gracefully

### Alternatives Considered
1. **Real-time event submission (per interaction)**
   - Rejected: Excessive API overhead (100+ requests per minute per user)
   - Network latency could impact perceived performance
   
2. **Longer batching window (60 seconds)**
   - Rejected: Too aggressive; user navigation away from page would lose events
   - 10 seconds balances API efficiency with data freshness
   
3. **LocalStorage queue with periodic sync**
   - Rejected: Over-engineered for current requirements
   - Adds complexity for edge cases (user closes browser)
   - 10-second batching is sufficient for 60-second latency requirement

### Implementation Details
```typescript
// Frontend usage tracker
class UsageTracker {
  private eventQueue: UsageEvent[] = [];
  private batchSize = 20;
  private batchInterval = 10000; // 10 seconds
  
  track(event: UsageEvent) {
    this.eventQueue.push(event);
    if (this.eventQueue.length >= this.batchSize) {
      this.flush();
    }
  }
  
  flush() {
    if (this.eventQueue.length === 0) return;
    const batch = this.eventQueue.splice(0);
    metricsClient.submitUsageEvents(batch); // Async, non-blocking
  }
}
```

- Debouncing: Use lodash.debounce for input field events (e.g., search box typing)
- Page unload: Flush queue on `beforeunload` event (best-effort)
- Error handling: Failed batch submissions logged but don't retry (avoid memory leaks)

---

## 7. Database Migration Strategy

### Decision
Use Alembic migration to add metrics tables with proper indexes and constraints.

### Rationale
- **Version control**: Alembic tracks schema changes in git with the codebase
- **Reproducibility**: Same migration runs identically in dev, staging, prod
- **Rollback support**: Down migrations enable safe rollback if issues arise
- **Existing pattern**: Project already uses Alembic (migrations/ directory exists)
- **Constitution compliance**: Follows database best practices from constitution

### Migration Content
```python
# versions/xxx_add_metrics_tables.py
def upgrade():
    # Create performance_metrics table
    op.create_table('performance_metrics',
        sa.Column('id', sa.UUID, primary_key=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('endpoint', sa.String, nullable=False, index=True),
        sa.Column('method', sa.String, nullable=False),
        sa.Column('status_code', sa.Integer, nullable=False),
        sa.Column('response_time_ms', sa.Float, nullable=False),
        sa.Column('user_id', sa.String, nullable=True, index=True),
        sa.Column('error_type', sa.String, nullable=True)
    )
    
    # Create usage_events table
    op.create_table('usage_events',
        sa.Column('id', sa.UUID, primary_key=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('event_type', sa.String, nullable=False, index=True),
        sa.Column('user_id', sa.String, nullable=False, index=True),
        sa.Column('page_name', sa.String, nullable=True),
        sa.Column('element_id', sa.String, nullable=True),
        sa.Column('success', sa.Boolean, nullable=True),
        sa.Column('metadata', sa.JSON, nullable=True)
    )
    
    # Create aggregated_metrics table
    op.create_table('aggregated_metrics',
        sa.Column('id', sa.UUID, primary_key=True),
        sa.Column('time_bucket', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('metric_type', sa.String, nullable=False, index=True),
        sa.Column('endpoint_path', sa.String, nullable=True, index=True),
        sa.Column('event_type', sa.String, nullable=True, index=True),
        sa.Column('aggregated_values', sa.JSON, nullable=False),
        sa.Column('sample_count', sa.Integer, nullable=False)
    )
    
def downgrade():
    op.drop_table('aggregated_metrics')
    op.drop_table('usage_events')
    op.drop_table('performance_metrics')
```

---

## 8. Test-Driven Development Approach

### Decision
Follow strict TDD red-green-refactor cycles for all production code: contract tests → integration tests → implementation.

### Rationale
- **Constitution mandate**: Principle XII requires TDD for all production code
- **Contract-first design**: Writing contract tests from OpenAPI specs catches API design issues early
- **Regression prevention**: Comprehensive test coverage from day one prevents future breaks
- **Living documentation**: Tests document expected behavior and serve as usage examples
- **Confidence for refactoring**: Full test coverage enables safe refactoring later

### Test Implementation Order
1. **RED Phase: Write failing contract tests**
   - `test_metrics_api.py`: Test all API endpoints return 404 (not implemented yet)
   - Validate request/response schemas, status codes, error formats
   
2. **RED Phase: Write failing integration tests**
   - `test_metrics_collection.py`: Test middleware doesn't collect metrics yet
   - `test_usage_metrics.py`: Test usage tracking endpoints return 404
   - `test_metrics_aggregation.py`: Test aggregation logic doesn't exist
   
3. **GREEN Phase: Implement minimal code to pass tests**
   - Create models, services, routers, middleware
   - Each test failure guides next implementation step
   
4. **REFACTOR Phase: Improve code quality while keeping tests green**
   - Extract helper functions, improve naming, optimize queries
   - Tests remain green throughout refactoring

### Test Coverage Requirements
- Contract tests: 100% of API endpoints (GET /metrics, POST /usage-events, etc.)
- Integration tests: All middleware collection, service methods, aggregation job
- Unit tests: Admin check logic, time-range filtering, aggregation calculations
- All tests MUST fail initially before implementation (verify RED phase)

---

## Summary

All research decisions documented above provide clear implementation guidance for Phase 1 (design) and Phase 2 (tasks). Key technologies selected:
- **Performance collection**: FastAPI middleware
- **Database**: Lakebase (3 tables: raw performance, raw usage, aggregated)
- **Aggregation**: Daily scheduled job (2 AM) via Databricks workflow
- **Admin check**: Databricks Workspace API with 5-minute caching
- **Visualization**: Recharts (React charting library)
- **Usage tracking**: Frontend batching (10s/20 events)
- **Migration**: Alembic for schema versioning
- **Testing**: Strict TDD with contract tests first

All decisions align with constitutional requirements and project best practices documented in `.specify/memory/constitution.md`.

