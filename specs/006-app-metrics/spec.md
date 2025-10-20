# Feature Specification: App Usage and Performance Metrics

**Feature Branch**: `006-app-metrics`  
**Created**: October 18, 2025  
**Status**: Draft  
**Input**: User description: "Help me implement the collection of app usage and performance metrics. use lakebase tables to persiste the data. Visualize the data as a page within the app itself."

## Clarifications

### Session 2025-10-18

- **Q**: Should raw individual metric records be stored permanently, or should they be aggregated and the raw data discarded?  
  **A**: Hybrid approach - Keep raw metrics for 7 days, then aggregate hourly and delete raw data; dashboard queries use appropriate table

- **Q**: How should the system determine if a user has administrator privileges?  
  **A**: Databricks workspace admin - Check if user has workspace admin privileges via Databricks API

- **Q**: Which specific user actions should trigger usage metric collection?  
  **A**: All interactions - Track every user action including button clicks, form submissions, navigation, and feature usage

- **Q**: How frequently should the aggregation job run to process 7-day-old raw metrics?  
  **A**: Daily at off-peak - Run once per day at 2 AM UTC to aggregate all 7-day-old metrics in a batch (reduces system load)

- **Q**: Should each metric/event record have a unique identifier, and are there any uniqueness constraints?  
  **A**: UUIDs for global uniqueness - Use UUID primary keys for distributed scalability and global uniqueness

### Session 2025-10-19

- Q: What alerting approach should be implemented for aggregation job failures? → A: Databricks job failure notification (uses platform's built-in alerting)
- Q: Should percentile values (P50/P95/P99) be pre-computed during hourly aggregation or calculated on-demand? → A: Pre-compute during aggregation (faster queries, more storage, aggregation takes longer)
- Q: What retry strategy should be implemented for failed batch event submissions? → A: Client-side retry with exponential backoff (3 attempts max, complex client logic)
- Q: What strategy should be used to identify UI elements for click tracking? → A: Hybrid: data-track-id preferred, fallback to id then tag+text
- Q: Should custom date range selection be supported beyond predefined options (24h, 7d, 30d, 90d)? → A: Yes - full custom date picker (flexible but more complex UI)

### Session 2025-10-20

- Q: Should rate limiting be implemented for the metrics API endpoints to prevent abuse or resource exhaustion? → A: No rate limiting (admin-only access is sufficient protection)
- Q: What transaction isolation level should be used for writing raw performance metrics and usage events to the database? → A: No explicit isolation (rely on database defaults)
- Q: Should the metrics dashboard display endpoint-level breakdown (showing performance for each API route individually)? → A: Yes - Full table with all endpoints (comprehensive but potentially overwhelming UI)
- Q: Should the dashboard automatically refresh metrics data, or require manual refresh? → A: Manual refresh only (user-controlled, least server load)
- Q: How should the system handle database connection pool exhaustion when writing metrics under extreme load? → A: Block and wait for available connection (ensures all metrics saved but may slow requests)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Application Performance Metrics (Priority: P1)

As an application administrator, I want to view key performance metrics on a dedicated dashboard page so that I can monitor application health and identify performance issues.

**Why this priority**: This is the core MVP feature that delivers immediate value by making metrics visible to administrators. Without this, collected metrics cannot be accessed or acted upon.

**Independent Test**: Can be fully tested by navigating to the metrics page and verifying that key performance indicators (response times, error rates, active users) are displayed with current values. Delivers immediate visibility into app health.

**Acceptance Scenarios** (will become automated tests following TDD):

1. **Given** I am an authenticated administrator, **When** I navigate to the metrics dashboard page, **Then** I see a page titled "Application Metrics" with performance charts
   - *Test Type*: Contract
   - *Test Location*: tests/contract/test_metrics_api.py

2. **Given** I am viewing the metrics dashboard, **When** the page loads, **Then** I see average response time, total requests, error rate, and active users metrics for the last 24 hours
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_metrics_visualization.py

3. **Given** metrics data exists in the database, **When** I request metrics via the API, **Then** I receive aggregated metrics data in the correct format
   - *Test Type*: Contract
   - *Test Location*: tests/contract/test_metrics_api.py

4. **Given** I am a non-administrator user, **When** I attempt to access the metrics dashboard or API, **Then** I receive a 403 Forbidden response with an "Access Denied" message
   - *Test Type*: Contract
   - *Test Location*: tests/contract/test_metrics_api.py

5. **Given** I am viewing the metrics dashboard, **When** the page loads, **Then** I see a comprehensive table displaying performance metrics for all API endpoints with columns for endpoint path, average response time, P50/P95/P99 percentiles, request count, and error rate, sortable by any column
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_metrics_visualization.py

6. **Given** I am viewing the metrics dashboard with existing data, **When** I click the "Refresh" button, **Then** the dashboard reloads all metrics data from the API with current values
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_metrics_visualization.py

---

### User Story 2 - Automatic Performance Metric Collection (Priority: P2)

As a developer, I want the application to automatically collect performance metrics for every API request so that I can identify slow endpoints and performance bottlenecks without manual instrumentation.

**Why this priority**: This enables the automatic performance metric collection that powers the P1 dashboard. While critical for long-term value, the system can function without it initially using sample/test data.

**Independent Test**: Can be tested by making API requests and verifying that metric records are created in the database with correct timing information and endpoint details.

**Acceptance Scenarios** (will become automated tests following TDD):

1. **Given** the application is running, **When** any API endpoint receives a request, **Then** a performance metric record is automatically created with request timestamp, endpoint, method, response time, and status code
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_metrics_collection.py

2. **Given** an API request completes successfully, **When** the response is sent, **Then** the metric record contains the actual response time in milliseconds
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_metrics_collection.py

3. **Given** an API request results in an error, **When** the error response is sent, **Then** the metric record is marked as an error with the error type
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_metrics_collection.py

4. **Given** raw metrics exist that are older than 7 days, **When** the scheduled aggregation job runs, **Then** metrics are processed per FR-008 data lifecycle policy (aggregated into hourly summaries, raw records deleted, aggregated data queryable)
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_metrics_aggregation.py
   - *Note*: FR-008 specifies complete lifecycle requirements (7-day retention, 2 AM UTC schedule, 90-day aggregated retention)

---

### User Story 3 - Usage Metrics Collection (Priority: P3)

As a product manager, I want to track all user interactions (page views, button clicks, form submissions, feature usage) so that I can understand user behavior patterns and prioritize development efforts on high-value features.

**Why this priority**: Provides comprehensive business intelligence but is not essential for application health monitoring. Can be added after performance monitoring is stable.

**Independent Test**: Can be tested by triggering various user actions (page views, button clicks, form submissions, feature usage) and verifying that usage event records are created with detailed action types and user context.

**Acceptance Scenarios** (will become automated tests following TDD):

1. **Given** a user views a page, **When** the page loads, **Then** a usage metric record is created with page name, user ID, and timestamp
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_usage_metrics.py

2. **Given** a user performs a key action (e.g., runs a query, invokes a model), **When** the action completes, **Then** a usage metric record captures the action type and success status
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_usage_metrics.py

3. **Given** multiple users are active, **When** requesting active user count, **Then** the API returns the number of unique users active in the specified time window
   - *Test Type*: Contract
   - *Test Location*: tests/contract/test_metrics_api.py

4. **Given** a user clicks buttons or interacts with UI elements, **When** the frontend batches usage events, **Then** all interaction events are submitted to the backend in bulk and persisted with element identifiers and context
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_usage_metrics.py

---

### User Story 4 - Historical Metrics and Time-Series Analysis (Priority: P4)

As an administrator, I want to view metrics over different time periods (24 hours, 7 days, 30 days, 90 days, or custom date range) so that I can identify trends and patterns in application usage and performance.

**Why this priority**: Enhances the P1 dashboard with time-series capabilities, but basic real-time monitoring delivers value first.

**Independent Test**: Can be tested by requesting metrics with different time range parameters (predefined and custom date ranges) and verifying that data is correctly filtered and aggregated by time period.

**Acceptance Scenarios** (will become automated tests following TDD):

1. **Given** I am viewing the metrics dashboard, **When** I select a predefined time range (24h, 7d, 30d, 90d), **Then** all metrics update to show data for the selected period
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_metrics_time_series.py

2. **Given** I am viewing the metrics dashboard, **When** I select a custom date range using the date picker (e.g., April 1-15), **Then** all metrics update to show data for the custom period with proper validation (max 90 days, not beyond retention)
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_metrics_time_series.py

3. **Given** historical metrics exist, **When** I request time-series data, **Then** I receive metrics grouped by hourly intervals showing trends over time
   - *Test Type*: Contract
   - *Test Location*: tests/contract/test_metrics_api.py

4. **Given** I attempt to select a custom date range exceeding 90 days or dates older than the retention window, **When** I submit the selection, **Then** I receive a validation error message indicating the constraint
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_metrics_time_series.py

---

### Edge Cases

- What happens when the metrics database table is empty (new installation)?
  - Dashboard should display "No data available" message with helpful guidance
  - API should return empty arrays with 200 status, not errors

- How does the dashboard "Refresh" button work?
  - **User Action**: User clicks "Refresh" button to manually reload metrics data from API
  - **Behavior**: Button triggers new API calls to fetch current metrics using the currently selected time range filter (preserves user's time range selection - does not reset to default)
  - **API Calls**: Refresh triggers parallel requests to all active metrics endpoints (GET /api/v1/metrics/performance, GET /api/v1/metrics/usage, GET /api/v1/metrics/time-series) with current time range parameters
  - **Loading State**: While refreshing, button displays loading indicator (spinner icon) and is disabled to prevent duplicate/concurrent requests; button text changes to "Refreshing..." for accessibility
  - **Success**: Dashboard re-renders all metrics visualizations (charts, tables, summary cards) with updated values from API response; button returns to normal state ("Refresh") and is re-enabled
  - **Failure**: If any API call fails, display error toast notification "Failed to refresh metrics. Please try again." with error details; button returns to normal state and is re-enabled to allow retry
  - **Error Handling**: Individual endpoint failures display specific error messages (e.g., "Failed to load performance metrics" vs "Failed to load usage metrics"); partial success is acceptable (show available data + error message for failed endpoints)
  - **Caching**: Frontend does NOT cache metrics data between refreshes; each refresh fetches fresh data from backend
  - **No Auto-Refresh**: Dashboard NEVER automatically polls for updates (no setInterval, no WebSocket); all data refreshes are user-initiated per FR-005 manual refresh requirement

- What happens when metrics collection fails (database unavailable)?
  - See FR-007 for complete graceful failure requirements (continue processing with <1% failure rate increase, ERROR-level logging, 30s retry interval)
  - Metrics collection errors logged with correlation IDs for debugging
  - Background retry uses exponential backoff (30s, 1m, 2m, 5m max) to reconnect

- How does the system handle high-volume metric data?
  - **Volume Definition**: See Assumption 12 for high-volume thresholds and scale testing requirements
  - Data lifecycle managed per FR-008: 7-day raw retention with daily aggregation, 90-day aggregated retention
  - Dashboard query routing per FR-006 (raw <7d, aggregated 8-90d, hourly GROUP BY for consistency)
  - All queries use indexed columns (timestamp, endpoint, user_id) for performance
  - Off-peak scheduling (2 AM UTC) minimizes impact on production workload
  - Query performance and error rate calculation details specified in FR-003 (comprehensive specification including query timeout handling, loading states, and high-volume optimization strategies)

- What happens when API requests timeout during metrics collection?
  - **Timeout Definition**: Requests that do not complete before the configured timeout threshold of 30 seconds (FastAPI default; configurable via TIMEOUT_SECONDS environment variable)
  - **Metrics Recording**: Timeout requests are counted as errors in performance metrics with `status_code = 504` (Gateway Timeout) and `error_type = "Timeout"`
  - **Dashboard Impact**: Timeouts contribute to error rate calculation and P99 response time measurements
  - **Implementation**: Middleware records 504 status when request processing exceeds timeout threshold

- What happens when a non-administrator tries to access the metrics page?
  - Non-admin users should be blocked entirely with an appropriate error message (e.g., "Access Denied: Administrator privileges required")
  - The metrics dashboard is an administrative tool only
  - The API should return 403 Forbidden status for non-admin requests

- How are metrics handled for unauthenticated requests?
  - Metrics should still be collected with user_id marked as "anonymous" or null
  - These should be included in aggregate counts but excluded from user-specific metrics

- What happens if the Databricks Workspace API call to check admin status fails?
  - System should fail secure: deny access with 503 Service Unavailable
  - Log the API failure for monitoring
  - Cache admin status checks for 5 minutes to reduce API calls and improve resilience

- How does the system handle high-volume usage event tracking (all user interactions)?
  - Frontend batches events and sends them in bulk (e.g., every 10 seconds or 20 events)
  - Backend accepts batch event submissions to reduce API overhead
  - Events are written to database asynchronously to avoid blocking user interactions
  - Same 7-day raw retention prevents unbounded growth
  - Rapid repeated events (e.g., typing in input field) should be debounced on frontend
  - **Failed batch submissions**: Client-side retry with exponential backoff - initial delay 1s, backoff multiplier 2x, maximum 3 total attempts (including initial request); retry delays: 1s after 1st failure, 2s after 2nd failure; after 3 failed attempts, log error to browser console and discard batch to prevent memory accumulation. Complete specification including memory management and edge cases in data-model.md "UsageEvent Lifecycle" section (step 3: "Retry Logic" lines 127-132)

- What happens if the database connection pool is exhausted during metric writes?
  - System blocks and waits for available connection per FR-002 (prioritizes data completeness)
  - May increase request latency under extreme load scenarios
  - See data-model.md "Write Performance" section for complete connection pool configuration and sizing recommendations
  - If connection acquisition timeout exceeded, treated as database unavailability per FR-007 with retry logic

- What happens when an administrator's privileges are revoked while they have an active session?
  - Admin privilege changes have up to 5-minute propagation delay due to caching (per FR-011 5-minute TTL)
  - User retains admin access to metrics dashboard for up to 300 seconds after privilege revocation
  - Acceptable trade-off for reduced Databricks API load and improved resilience
  - Cache automatically expires on TTL; next API request triggers fresh admin check
  - **Admin Group Configuration**: See data-model.md "Admin Check Pattern" section L490-512 for ADMIN_GROUPS environment variable specification (default admin group names, case-insensitive matching, configuration details)
  - **Future enhancement** (not required for MVP): Manual cache invalidation endpoint for immediate revocation in security-critical scenarios

- How does the aggregation script (console entry point) handle errors and failures?
  - **Exit Codes**: Script MUST exit with appropriate codes for Databricks job monitoring: (1) Exit code 0 on successful completion, (2) Exit code 1 on database connection failures, (3) Exit code 2 on aggregation logic errors (e.g., invalid data, computation failures)
  - **Error Messages**: All error messages MUST be written to stderr with correlation IDs for troubleshooting; include actionable guidance (e.g., "Check database connectivity", "Review aggregation logs for correlation_id=XXX")
  - **Logging**: Errors logged at ERROR level with full context (timestamp, error type, stack trace, affected time buckets, record counts)
  - **Job Monitoring**: Exit codes enable Databricks job failure notifications per FR-008; non-zero exits trigger admin alerts
  - **Implementation**: `scripts/aggregate_metrics.py` includes `main()` function wrapper that catches exceptions and translates to appropriate exit codes

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST automatically collect **backend performance metrics** for all user-facing HTTP API requests (excluding internal health checks, scheduled job endpoints, and service-to-service calls) with attributes defined in the Performance Metric entity (see Key Entities section) via FastAPI middleware instrumentation. **Exclusion Criteria**: Exclude endpoints matching these patterns using regex matching on `request.url.path` (Python implementation: `re.match()` for prefix patterns): (1) `/health`, `/ready`, `/ping` (health check endpoints), (2) Any endpoint with path prefix `/internal/` or `/admin/system/` (internal administrative endpoints), (3) Background job callback endpoints (if any exist, document in middleware implementation). Note: FR-001 covers **backend API request timing** via middleware; FR-010 covers **frontend user interaction tracking** via client-side instrumentation - these are complementary data collection mechanisms for comprehensive observability
  
- **FR-002**: System MUST persist all collected metrics to Lakebase tables using the existing database connection patterns and service principal authentication. **Transaction Isolation**: Raw metric and event writes use database default transaction isolation (PostgreSQL default: READ COMMITTED); aggregation job uses SERIALIZABLE isolation per FR-008. **Connection Pool Handling**: Under extreme load, metric writes block and wait for available database connections (ensures data completeness at the cost of potential request slowdown); connection acquisition timeout set to 30 seconds (configurable via POOL_TIMEOUT environment variable; default: 30); if timeout exceeded (connection unavailable after 30s wait), treat as database unavailability per FR-007 graceful degradation (log error, skip metric write, continue request processing)
  
- **FR-003**: System MUST provide an API endpoint that returns aggregated performance metrics including average response time, P50/P95/P99 percentiles, total request count, error rate as decimal ratio, and active user count for a specified time range. **API Response Format**: Error rate MUST be returned as numeric decimal ratio in JSON response (example: `{"error_rate": 0.0079, "avg_response_time_ms": 45.2, "p50": 42, "p95": 180, "p99": 350, "total_requests": 10000, "active_users": 25}` where 0.0079 represents 0.79% error rate). Frontend MUST display as percentage string with % symbol: "0.79%". Backend NEVER returns percentage strings or pre-formatted values. **Error Rate Calculation**: For all scenarios, calculate as `COUNT(*) FILTER (WHERE status_code >= 400)` divided by total requests using database aggregate for O(n) single-pass performance; **Query Performance Thresholds**: Two distinct thresholds control UX and reliability: (1) **UX Loading State Threshold: 2 seconds** - If query execution time exceeds 2 seconds (measured via query timing logs), display "Calculating..." loading state with spinner in dashboard to provide user feedback during long-running queries, (2) **Hard Query Timeout: 10 seconds** - Query MUST abort after 10 seconds maximum execution time with fallback to "Data temporarily unavailable" error message to prevent indefinite hanging and resource exhaustion; backend implements 10s timeout at database query level (SQLAlchemy `execution_options(timeout=10)`), frontend sets matching 10s timeout on API fetch call; **High-Volume Optimization**: For datasets >100K requests, leverage indexed timestamp and status_code columns for efficient filtering without full table scans. *Percentile Calculation*: For recent data (<7 days old), use PostgreSQL `percentile_cont` function for real-time calculation; for historical data (8-90 days old), retrieve pre-computed percentile values from aggregated_metrics table (computed during daily aggregation job per FR-008); this hybrid approach optimizes dashboard query performance while maintaining accuracy. **Rate Limiting**: No rate limiting is implemented for metrics API endpoints; admin-only access control (FR-011) provides sufficient protection against abuse
  
- **FR-004**: System MUST provide an API endpoint that returns usage metrics including page views, feature usage counts, and unique user counts for a specified time range. **Rate Limiting**: No rate limiting is implemented; admin-only access control (FR-011) provides sufficient protection against abuse
  
- **FR-005**: System MUST display a Metrics Dashboard page within the application that visualizes performance and usage metrics using charts and tables (navigation menu item labeled "Metrics"). **Endpoint-Level Breakdown**: Dashboard MUST include a comprehensive table displaying performance metrics for all API endpoints individually (endpoint path, average response time, P50/P95/P99 percentiles, request count, error rate), sortable by any column, with no pagination limit (displays all tracked endpoints). **Data Refresh**: Dashboard uses manual refresh only (no automatic polling); MUST include a "Refresh" button to reload metrics data on demand, minimizing server load and API calls
  
- **FR-006**: System MUST support time range filtering for metrics with both quick-select predefined options (last 24 hours, 7 days, 30 days, 90 days) and custom date range picker allowing arbitrary start/end date selection within the 90-day retention window; all time ranges use hourly aggregation for time-series visualization. **Query Routing**: Queries for data <7 days old use raw metrics tables with `GROUP BY date_trunc('hour', timestamp)`; queries for data 8-90 days old use aggregated_metrics table filtering by `time_bucket` column (TIMESTAMP type storing hour-truncated timestamp values). **Custom Range Validation**: Date picker MUST enforce validation rules (see data-model.md "Time Range Selection Pattern" section L623-675 for complete frontend/backend validation specification: max 90-day range, no dates older than retention, no future dates, start before end with detailed error messages). See FR-008 for complete data lifecycle and aggregation process
  
- **FR-007**: System MUST handle metrics collection failures gracefully without impacting application functionality or user experience, defined as: (1) Continue processing user API requests with <1% request failure rate increase during database outage (measured via load test: 1000 baseline requests with metrics DB available vs 1000 requests with metrics DB unavailable; failure rate delta must be <0.01), (2) Log metrics collection errors at ERROR level with correlation ID, (3) Retry database connection every 30 seconds with exponential backoff (max 5 minutes), (4) Never throw exceptions from metrics middleware that would propagate to user-facing responses
  
- **FR-008**: System MUST automatically manage metrics data lifecycle via a scheduled job that runs daily at 2 AM UTC (timezone MUST be UTC exclusively with no DST adjustments; quartz cron expression: "0 0 2 * * ?" in UTC timezone; Databricks job configuration specifies timezone: "UTC"): raw metrics where `timestamp` column is older than 7 days from current date (`timestamp < NOW() - INTERVAL '7 days'`) are aggregated into hourly summaries (computing avg, min, max, count, sum, P50/P95/P99 percentiles using PostgreSQL `percentile_cont` function) and deleted; aggregated metrics where `time_bucket` column is older than 90 days from current date (`time_bucket < NOW() - INTERVAL '90 days'`) are permanently deleted; aggregation job MUST be idempotent and safely retryable using check-before-insert pattern (query for existing aggregated records matching `(time_bucket, metric_type, endpoint_path/event_type)` composite key before aggregating each hourly bucket; skip aggregation if record exists; only aggregate and delete raw records for buckets with no existing aggregated record) with SERIALIZABLE transaction isolation level to prevent race conditions from concurrent executions (rare clock skew or manual trigger scenarios); failed aggregations MUST be logged at ERROR level with detailed error context and use Databricks job failure notification (configured in job settings via email recipients or integration webhooks) to alert administrators; failures must not block subsequent runs
  
- **FR-009**: Users MUST be able to access the metrics dashboard via a navigation menu item labeled "Metrics" or "Analytics"
  
- **FR-010**: System MUST collect usage event metrics for all user interactions including page navigation, button clicks, form submissions, query execution, model invocation, and all feature usage, capturing action type, user ID, timestamp, and relevant context metadata; for click events, element identification uses hybrid strategy with precedence: (1) `data-track-id` custom attribute if present (explicit tracking identifier), (2) HTML `id` attribute if present and `data-track-id` absent, (3) fallback to `{tagName}.{textContent}` (e.g., "button.Submit Query") if neither attribute exists, truncated to 100 characters to prevent excessive data from long text elements

- **FR-011**: System MUST restrict access to the metrics dashboard and metrics API endpoints to users with Databricks workspace administrator privileges only (verified via Databricks Workspace API using `WorkspaceClient.current_user.me()` to retrieve user details, then checking if `groups` array contains an entry with `display` field matching admin group names - see data-model.md "Admin Check Pattern" section L453-533 for complete specification including ADMIN_GROUPS environment variable configuration, case-insensitive matching, caching strategy with 5-minute TTL, and error handling); returning 403 Forbidden status for non-administrator users

- **FR-012**: System MUST provide an API endpoint for batch submission of usage events to efficiently handle high-volume comprehensive tracking, accepting arrays of events (maximum batch size: 1000 events per request, enforced via Pydantic validator; requests exceeding limit return 413 Payload Too Large) and processing them asynchronously; frontend SHOULD batch events with trigger conditions of either 10 seconds elapsed OR 20 events accumulated (whichever occurs first, timer resets after each flush) to optimize network efficiency; frontend MUST flush all remaining batched events on page unload/navigation (via `beforeunload` event using `navigator.sendBeacon()` API for reliable delivery during page transitions); **Content-Type Support**: POST /api/v1/metrics/usage-events endpoint MUST accept BOTH Content-Type: application/json (standard API calls) AND Content-Type: text/plain (navigator.sendBeacon default), parsing request body as JSON regardless of Content-Type header for compatibility with browser sendBeacon constraints; CORS configuration in server/app.py MUST allow credentials and include "Content-Type" in allow_headers list; frontend MUST implement client-side retry logic with exponential backoff for failed batch submissions (see data-model.md "UsageEvent Lifecycle" section L127-132 for complete retry specification: 3 attempts max, 1s/2s delays, discard after final failure)

- **FR-013**: System MUST provide custom FastAPI exception handler to convert Pydantic ValidationError for batch size limit (>1000 events) into HTTP 413 Payload Too Large response with structured error body `{"detail": "Batch size exceeds maximum of 1000 events", "max_batch_size": 1000, "received": <count>}`; standard Pydantic validation returns 422 Unprocessable Entity which is semantically incorrect for size limits

- **FR-014**: System MUST provide an API endpoint for retrieving usage event count per user (GET /api/v1/metrics/usage/count) accepting authenticated user (not admin-only), query parameter `time_range` (default: "24h"), returning JSON response `{"count": <integer>}` from SQL query `SELECT COUNT(*) FROM usage_events WHERE user_id = :user_id AND timestamp > :start_time`; endpoint supports client-side data loss validation mechanism by enabling frontend to compare sent event count with backend persisted count (see data-model.md "UsageEvent Lifecycle" section for reconciliation logic)

### Key Entities *(include if feature involves data)*

- **Performance Metric**: Represents a single API request's performance metrics
  - Identity: UUID primary key for global uniqueness and distributed scalability
  - Key attributes: id (UUID), timestamp, endpoint path, HTTP method, response time (milliseconds), status code, user ID (optional), error type (if applicable)
  - Relationships: Associated with a specific user (optional) and timestamp for time-series aggregation
  - Indexes: timestamp (for time-range queries), endpoint path (for per-endpoint analysis), user_id (for user filtering)

- **Usage Event**: Represents any user interaction with the application (comprehensive tracking)
  - Identity: UUID primary key for global uniqueness and distributed scalability
  - Key attributes: id (UUID), timestamp, event type (page_view, button_click, form_submit, query_executed, model_invoked, preference_changed, etc.), user ID, page/feature name, element identifier (for clicks - captured using hybrid strategy per FR-010: data-track-id > id > tagName.textContent; max 100 chars), success status, metadata (flexible JSON for context like query text, model name, etc.)
  - Relationships: Associated with a specific user and timestamp; follows same 7-day raw / 90-day aggregated lifecycle as Performance Metrics
  - Indexes: timestamp (for time-range queries), event_type (for event category analysis), user_id (for user behavior tracking)
  - Lifecycle: Same hybrid storage model as Performance Metrics (7 days raw, then hourly aggregation)

- **Aggregated Metric**: Pre-computed hourly summary statistics for dashboard queries beyond 7-day window
  - Identity: UUID primary key for global uniqueness and distributed scalability
  - Key attributes: id (UUID), time_bucket (hourly timestamp), metric_type (performance/usage), aggregated_values (JSON containing avg, min, max, count, sum, p50, p95, p99 for performance metrics; avg, count, sum for usage metrics), sample_count, endpoint_path (for performance metrics), event_type (for usage metrics)
  - Relationships: Computed from raw Performance Metrics and Usage Events older than 7 days via scheduled aggregation job; replaces raw data after aggregation
  - Indexes: time_bucket (for time-range queries), metric_type (for query filtering), endpoint_path/event_type (for specific metric lookups)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Administrators can view current application performance metrics (response time, error rate, request volume) within 3 seconds of loading the metrics dashboard

- **SC-002**: Performance metric collection adds less than 5 milliseconds of overhead to each API request processing time

- **SC-003**: The metrics dashboard displays data for at least the last 24 hours with updates visible within 60 seconds of metric database insertion (measured from `INSERT` completion to API query returning new data)

- **SC-004**: System successfully collects and persists 100% of API request metrics during normal operation (excluding database outage scenarios)

- **SC-005**: Administrators can view a comprehensive table of all API endpoints with performance metrics (response times, percentiles, request counts, error rates) and sort by any column to identify slowest endpoints, highest error rates, or most frequently called routes

- **SC-006**: The metrics page loads and displays visualizations for up to 30 days of historical data in under 5 seconds

- **SC-007**: Metrics database tables remain under 1 million records through automated cleanup of data older than the retention period

- **SC-008**: Application continues normal operation when metrics database is unavailable, logging collection failures without impacting user requests

- **SC-009**: Automated monitoring alerts trigger at 800K records (WARNING log level) and 1M records (ERROR log level with "ALERT:" prefix) to ensure proactive database size governance and prevent unbounded growth

- **SC-010**: All Recharts visualizations MUST meet WCAG 2.1 AA contrast requirements with validated contrast ratios: (1) Text contrast >= 4.5:1 for labels, legends, axis text against background colors, (2) Graphics contrast >= 3:1 for chart lines, bars, data points against background colors; validation performed using WebAIM Contrast Checker (https://webaim.org/resources/contrastchecker/) against white (#FFFFFF) and light gray (#F5F5F5) backgrounds; if Design Bricks colors fail validation, adjust HSL saturation/lightness while preserving hue for brand consistency; document validated color palette with measured contrast ratios in quickstart.md

## Assumptions

1. **Access Control**: Metrics dashboard will be accessible only to users with Databricks workspace administrator privileges. Admin status is verified by querying the Databricks Workspace API to check user permissions. Non-workspace-admins receive 403 Forbidden.

2. **Retention Period**: Raw metrics are retained for 7 days to enable detailed debugging. Aggregated hourly metrics are retained for 90 days total. This hybrid approach balances storage costs with analysis needs.

3. **Collection Scope**: Performance metrics will be collected for all HTTP API endpoints. Internal service-to-service calls and background jobs are excluded from initial scope.

4. **Visualization Technology**: Dashboard will use Recharts 2.10.0 charting library (exact version for reproducible builds per Constitution Principle VII; version locked in client/package.json; version updates require regression testing of all chart components to verify API compatibility and visual consistency). Specific chart types: LineChart for time-series performance metrics (response time over time), BarChart for event distribution (usage events by type), ResponsiveContainer for responsive sizing, Tooltip for data point details, Legend for series identification. Color palette follows Design Bricks theming (primary: #0066CC, success: #00A86B, error: #D32F2F) **with WCAG 2.1 AA contrast requirements (4.5:1 minimum for text, 3:1 for graphics/charts)**. **Accessibility**: All charts MUST include `aria-label` attributes on ResponsiveContainer for screen reader support (e.g., "Performance metrics time series chart"); tooltip content MUST be keyboard accessible; data tables provided alongside charts for non-visual access. **Theme Support - Explicit Decision**: Charts use Design Bricks light theme colors only; **dark mode support explicitly deferred to post-MVP** (rationale: light theme only reduces MVP complexity and development time; dark mode requires Recharts theme customization via `theme` prop based on user preference state + theme context provider implementation + dynamic color palette switching for all chart components + additional WCAG contrast validation against dark backgrounds; estimated 3-5 additional development days for comprehensive dark mode support; MVP prioritizes core metrics collection and visualization functionality over theme variants). Recharts is acceptable per Constitution Principle I as Design Bricks does not provide charting components.

5. **Real-time Updates**: Dashboard displays current metrics data on page load and manual refresh (via "Refresh" button). No automatic polling or WebSocket-based real-time updates. Metrics data reflects database state at the time of query with up to 60-second collection latency (SC-003).

6. **Data Aggregation**: Dashboard queries use raw metrics for the past 7 days (high granularity) and pre-computed hourly aggregates for 8-90 days ago (query performance). Aggregation runs daily at 2 AM as a scheduled background job to minimize production impact.

7. **Error Definition**: An "error" is defined as any HTTP response with status code >= 400 for performance metrics calculation.

8. **Active User Definition**: An "active user" is defined as any user who made at least one request or performed one action within the specified time window. Active user count INCLUDES administrators (admins are users); count is filtered by user_id presence (non-null), not by role/group membership. Authenticated and unauthenticated users are counted separately (see edge case for unauthenticated handling).

9. **Database Schema**: Metrics tables will be created in the same Lakebase database as existing user_preferences table, using the 'public' schema. All tables use UUID primary keys for global uniqueness and distributed scalability.

10. **UUID Generation**: UUIDs are generated using standard UUID v4 (random) for all metric and event records, ensuring global uniqueness without coordination.

11. **Performance Baseline**: Current application measured baseline: P50 API latency = 45ms, P95 API latency = 180ms, P99 API latency = 350ms (measured via Databricks monitoring for 7-day period ending 2025-10-18 using raw percentile calculation over 100,000+ request samples). Metrics collection overhead must remain <5ms (P95) per SC-002, keeping post-implementation P95 latency <185ms. **Performance Test Approval Process**: Automated performance regression tests (see tasks.md T042.5) run via pytest-benchmark measuring P95 middleware overhead across 1000 API request samples; if P95 overhead exceeds 5ms threshold (test assertion fails), PR MUST NOT be approved until either: (1) async/background metrics collection is implemented to reduce overhead below threshold, OR (2) architectural trade-off is explicitly documented in PR description with approval from tech lead justifying increased latency (requires demonstrating that async implementation would add unacceptable complexity without proportional benefit); performance test failure is blocking gate, cannot be bypassed without explicit approval and documentation. **Connection Pool Sizing**: SQLAlchemy connection pool configured with min=5 (warm standby for immediate availability), max=20 (supports expected peak concurrency of 100 concurrent users × ~20% making simultaneous API requests = 20 concurrent connections); pool_pre_ping=True ensures stale connections are recycled; pool_recycle=3600 (1 hour) prevents connection timeout issues with Lakebase OAuth tokens. Sizing based on Assumption 12 high-volume threshold (10K requests/hour = ~3 requests/second average, 20 requests/second peak with 1s request duration). See data-model.md "Write Performance" section L433-439 for complete pool configuration.

12. **High-Volume Handling**: High-volume threshold defined as >10,000 API requests/hour OR >50,000 usage events/hour (based on expected production load: 100 concurrent users × 100 requests/user/hour + 500 UI interactions/user/hour). Scale testing validates system handles 2x expected volume (20K requests/hour, 100K events/hour) without degradation. Data lifecycle and query optimization strategies in FR-006, FR-008, and edge cases ensure system remains performant under high load.
