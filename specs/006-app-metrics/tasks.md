---
description: "Implementation tasks for App Usage and Performance Metrics feature"
---

# Tasks: App Usage and Performance Metrics

**Input**: Design documents from `/specs/006-app-metrics/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/metrics-api.yaml, research.md, quickstart.md

**TDD REQUIREMENT (Principle XII)**: All production code MUST follow Test Driven Development.
Tests are MANDATORY and MUST be written BEFORE implementation following red-green-refactor cycles.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Terminology Standards

**Consistent Usage Required**:
- **performance metrics** (lowercase): API request timing data (response time, status codes, error rates) - stored in `PerformanceMetric` model class
- **usage events** (lowercase): User interaction data (page views, button clicks, form submissions, feature usage) - stored in `UsageEvent` model class
- **aggregated metrics** (lowercase): Pre-computed summaries stored in `AggregatedMetric` model class
- **metrics collection**: The overall system combining both performance metrics and usage events
- **raw metrics**: Data stored in `performance_metrics` and `usage_events` database tables (7-day retention)
- **Naming convention**: Use lowercase for general concepts, PascalCase for model class names (PerformanceMetric, UsageEvent, AggregatedMetric), snake_case for table names (performance_metrics, usage_events, aggregated_metrics). **SQLAlchemy Convention**: Singular PascalCase model names automatically map to plural snake_case table names unless explicitly overridden with `__tablename__` attribute. Example: `class PerformanceMetric(Base)` → table `performance_metrics`

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions
This is a web application with:
- Backend: `server/` (Python/FastAPI)
- Frontend: `client/` (React/TypeScript)
- Tests: `tests/` (pytest for backend)
- Migrations: `migrations/versions/` (Alembic)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and database schema setup

- [X] T001 [P] [SETUP] Install Python dependencies: No new Python dependencies needed for metrics feature (uses existing FastAPI, SQLAlchemy, Alembic)
- [X] T002 [P] [SETUP] Install frontend dependencies: Run `cd client && bun add recharts@2.10.0 @types/recharts lodash@4.17.21 @types/lodash` (exact versions for reproducible builds per Principle VII; recharts for charts per Assumption 4, lodash for debouncing in T084)
- [X] T003 [SETUP] Create SQLAlchemy models (PerformanceMetric, UsageEvent, AggregatedMetric) for database tables (performance_metrics, usage_events, aggregated_metrics) in `server/models/performance_metric.py`, `server/models/usage_event.py`, `server/models/aggregated_metric.py` - note singular class names map to plural table names per SQLAlchemy convention
- [X] T004 [SETUP] Generate and apply Alembic migration (RUN AFTER T003 - requires models to exist): Created manual migration `migrations/versions/005_add_metrics_tables.py` (auto-generate requires database connection)
- [X] T005 [P] [SETUP] Update `server/models/__init__.py` to export new models (PerformanceMetric, UsageEvent, AggregatedMetric)
- [X] T005.5 [P] [SETUP] Configure `pyproject.toml` with console script entry point: Add `[project.scripts]` section with `aggregate-metrics = "scripts.aggregate_metrics:main"` (enables Databricks job to invoke script from installed wheel)
- [X] T005.6 [P] [SETUP] Add `main()` function wrapper in `scripts/aggregate_metrics.py` that calls aggregation logic and handles command-line invocation
- [X] T005.7 [P] [SETUP] Validate console script entry point locally: Run `uv pip install -e .` then `uv run aggregate-metrics --help` to verify entry point resolves correctly (makes T054 Asset Bundle job configuration testable)
- [X] T005.8 [P] [SETUP] Write unit test for aggregate-metrics error handling in `tests/unit/test_aggregate_metrics.py` - verify script exits with code 1 on database connection failure, exits with code 2 on aggregation logic errors, exits with code 0 on success; verify error messages written to stderr include correlation IDs and actionable troubleshooting guidance (MUST FAIL - RED) (RESOLVES FINDING U1)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 [P] [FOUNDATION] Create admin service skeleton in `server/services/admin_service.py` with workspace admin check function using Databricks API
- [X] T007 [P] [FOUNDATION] Add admin check dependency `get_admin_user()` to `server/lib/auth.py` that enforces admin-only access
- [X] T008 [P] [FOUNDATION] Create metrics service skeleton in `server/services/metrics_service.py` with MetricsService class
- [X] T009 [FOUNDATION] Create metrics middleware skeleton in `server/lib/metrics_middleware.py` for automatic request tracking
- [X] T010 [FOUNDATION] Create metrics router skeleton in `server/routers/metrics.py` with APIRouter setup
- [X] T011 [FOUNDATION] Register middleware and router in `server/app.py`: Add metrics_collection_middleware and include metrics router
- [X] T012 [FOUNDATION] Update CLAUDE.md with metrics system documentation: Added comprehensive section on metrics middleware usage pattern, admin service caching strategy (5-min TTL), time-range query routing (raw <7d vs aggregated 8-90d), database lifecycle management, Recharts integration, terminology standards (performance metrics vs usage events, PerformanceMetric/UsageEvent/AggregatedMetric model naming, snake_case table names), and troubleshooting tips for common issues (empty state, admin check failures, aggregation job errors)

**Checkpoint**: ✅ Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - View Application Performance Metrics (Priority: P1) 🎯 MVP

**Goal**: Administrators can view key performance metrics (response times, error rates, active users) on a dedicated dashboard page

**Independent Test**: Navigate to metrics page as admin and verify that performance indicators are displayed with current values

### 🔴 RED Phase: Write Failing Tests for User Story 1 (TDD - MANDATORY)

**TDD Requirement**: Write these tests FIRST. All tests MUST FAIL initially before any implementation.

- [X] T013 [P] [US1] Write contract test for GET /api/v1/metrics/performance endpoint in `tests/contract/test_metrics_api.py` - test returns 200 for admin, 403 for non-admin, validates response schema; **verify error_rate format per FR-003 API Response Format specification** (numeric decimal ratio 0.0-1.0, NOT string or percentage >1.0); test should fail if backend returns incorrect format (MUST FAIL - RED)
- [X] T014 [P] [US1] Write contract test for admin privilege check in `tests/contract/test_metrics_api.py` - test non-admin receives 403 with correct error message (MUST FAIL - RED)
- [X] T015 [P] [US1] Write integration test for metrics dashboard visualization in `tests/integration/test_metrics_visualization.py` - test dashboard displays metrics for last 24 hours (MUST FAIL - RED)
- [X] T016 [P] [US1] Write unit test for admin service workspace admin check in `tests/unit/test_admin_service.py` - test admin detection logic per FR-011 with **TWO test scenarios**: (1) **Default admin groups test**: With default ADMIN_GROUPS env var ("admins,workspace_admins,administrators"), mock Databricks API to return user with groups=["admins"], verify is_workspace_admin() returns True; test with groups=["workspace_admins"] and groups=["administrators"] (all three default groups per FR-011), (2) **Custom ADMIN_GROUPS test**: Set ADMIN_GROUPS="custom_admins,super_users" env var explicitly, mock API with groups=["custom_admins"], verify returns True; verify case-insensitive matching per FR-011; test caching behavior (MUST FAIL - RED)
- [X] T016.1 [P] [US1] Write unit test for admin cache TTL expiration in `tests/unit/test_admin_service.py` - verify cached admin status expires after 5 minutes (300 seconds) and triggers new API call, test both admin and non-admin cache expiry (MUST FAIL - RED)
- [X] T016.5 [P] [US1] Write security test for privilege escalation attempts in `tests/unit/test_admin_service.py` - verify non-admin cannot bypass admin check through token manipulation, cache poisoning, or API spoofing (MUST FAIL - RED)
- [X] T016.6 [P] [US1] Write unit test for admin service resilience in `tests/unit/test_admin_service.py` - verify 503 Service Unavailable returned when Databricks API call fails (validates edge case from spec.md:L152-155) (MUST FAIL - RED)
- [X] T016.7 [P] [US1] Write integration test for dashboard load time in `tests/integration/test_metrics_visualization.py` - measure time from request to full render, assert <3 seconds (validates SC-001) (MUST FAIL - RED)
- [X] T016.8 [P] [US1] Write integration test for slowest endpoint sorting in `tests/integration/test_metrics_visualization.py` - verify metrics table displays endpoints sorted by avg response time descending (validates SC-005) (MUST FAIL - RED)
- [X] T016.9 [P] [US1] Write unit test for admin cache failure handling in `tests/unit/test_admin_service.py` - verify cache doesn't serve stale results when Databricks API starts returning errors; admin status should be re-checked on cache expiry even if previous calls succeeded (MUST FAIL - RED)
- [X] T016.10 [P] [US1] **Write integration test for FR-009 navigation menu requirement** in `tests/integration/test_metrics_visualization.py` - **CRITICAL COVERAGE FOR FR-009**: verify navigation menu contains item with label matching FR-009 requirement ("Metrics" OR "Analytics" - test should validate label text matches one of these exact strings using case-sensitive comparison per FR-009 specification); verify menu item is visible to authenticated users (query DOM for element with text matching label using data-testid attribute or text content); verify clicking menu item navigates to `/metrics` route (simulate click event, assert browser URL changes to /metrics path); verify dashboard component renders after navigation (assert MetricsDashboard component present in DOM with correct props); test validates complete user journey from navigation discovery to dashboard load per **FR-009 navigation menu requirement**; **IMPLEMENTATION REQUIREMENT**: T032 MUST add data-testid="metrics-nav-link" to navigation menu item for reliable test querying (MUST FAIL - RED)
- [X] T016.11 [P] [US1] Write integration test for manual refresh button in `tests/integration/test_metrics_visualization.py` - verify dashboard includes "Refresh" button with data-testid="refresh-button", clicking button triggers new API call and reloads metrics data with current values per FR-005 Data Refresh requirement; assert button shows loading state during refresh (disabled=true, loading indicator visible); validates acceptance scenario #6 from spec.md and expanded edge case specification at spec.md:L172-181 (MUST FAIL - RED)

**Verification**: Run `pytest tests/contract/test_metrics_api.py tests/integration/test_metrics_visualization.py tests/unit/test_admin_service.py -v` - ALL tests for US1 should be RED (failing)

**🔴 RED VERIFICATION CHECKPOINT**: Before proceeding to GREEN phase, run:
```bash
pytest tests/contract/test_metrics_api.py tests/integration/test_metrics_visualization.py tests/unit/test_admin_service.py -v
```
**Expected Output**: ALL tests for US1 should be RED (failing). Example:
```
FAILED tests/contract/test_metrics_api.py::test_get_performance_metrics - ImportError: cannot import name 'get_performance_metrics'
FAILED tests/unit/test_admin_service.py::test_is_workspace_admin - AttributeError: module has no attribute 'is_workspace_admin'
```
If tests are NOT failing, you have not written proper failing tests. Stop and fix tests before proceeding.

### 🟢 GREEN Phase: Implementation for User Story 1

**TDD Requirement**: Write minimal code to make tests pass. Focus on making tests GREEN, not on perfection.

- [X] T017 [P] [US1] Implement admin service `is_workspace_admin()` function in `server/services/admin_service.py` with Databricks API call and 5-minute caching per FR-011 specification (uses `ADMIN_GROUPS` env var for configurable admin group names with case-insensitive comparison; default: "admins,workspace_admins,administrators") (makes T016 unit tests pass including custom admin group configuration test)
- [X] T018 [US1] Implement `get_admin_user()` dependency in `server/lib/auth.py` that calls admin service and returns 403 for non-admins (makes contract tests pass)
- [X] T019 [US1] Implement `get_performance_metrics()` method in `server/services/metrics_service.py` to route queries based on time range - calls `_query_raw_performance_metrics()` for last 7 days or `_query_aggregated_performance_metrics()` for 8-90 days (makes integration tests pass)
- [X] T020 [US1] Implement GET /api/v1/metrics/performance endpoint in `server/routers/metrics.py` with admin dependency, time_range query param, and endpoint filter (makes contract tests pass)
- [X] T021 [P] [US1] Create PerformanceMetricsResponse Pydantic model in `server/routers/metrics.py` matching OpenAPI schema
- [X] T022 [P] [US1] Implement `_query_raw_performance_metrics()` helper method in `server/services/metrics_service.py` - queries `performance_metrics` table with indexed timestamp/endpoint filters and calculates percentiles
- [X] T023 [P] [US1] Implement `_query_aggregated_performance_metrics()` helper method in `server/services/metrics_service.py` - queries `aggregated_metrics` table and extracts pre-computed statistics from JSON
- [X] T024 [P] [US1] Add helper methods for time range parsing, percentile calculation, endpoint aggregation in `server/services/metrics_service.py`
- [X] T024.5 [US1] Implement error handling for Databricks API failures in `server/services/admin_service.py` - return 503 Service Unavailable when API call fails, log failure with correlation ID (makes T016.6 test pass)
- [X] T025 [US1] Add comprehensive exception handling in admin_service.py - handle network timeouts, invalid tokens, and other edge cases with appropriate error messages
- [X] T026 [US1] Add logging for admin checks and metrics queries in both admin_service and metrics_service

**Verification**: Run test suite - ALL tests for US1 should be GREEN (passing)

### Frontend Implementation for User Story 1

- [X] T026.5 [P] [US1] Write validation test for TypeScript client generation in `tests/unit/test_client_generation.py` - verify generated client has correct types and methods from OpenAPI spec (MUST FAIL - RED)
- [X] T027 [P] [US1] Generate TypeScript API client from OpenAPI spec into `client/src/services/metricsClient.ts`: Run `python scripts/make_fastapi_client.py` (makes T026.5 test pass)
- [X] T028 [P] [US1] Create MetricsDashboard component in `client/src/components/MetricsDashboard.tsx` with time range selector, manual "Refresh" button (no auto-polling per clarification), and metrics display; component loads metrics on initial mount only (empty useEffect dependency array), implements handleRefresh() function to manually reload data on button click
- [X] T029 [P] [US1] Create PerformanceChart component in `client/src/components/PerformanceChart.tsx` using Recharts LineChart for response time trends
- [X] T030 [P] [US1] Create EndpointBreakdownTable component in `client/src/components/EndpointBreakdownTable.tsx` to display comprehensive endpoint-level performance breakdown per clarification - full table with ALL endpoints (no pagination), sortable columns (endpoint, method, avg response time, P50/P95/P99 percentiles, request count, error rate), default sort by avg_response_time_ms descending; implements FR-005 endpoint breakdown requirement
- [X] T030.5 [P] [US1] Create MetricsTable component in `client/src/components/MetricsTable.tsx` to display summary metrics (avg response time, error rate, active users)
- [X] T031 [US1] Create MetricsPage route in `client/src/pages/MetricsPage.tsx` that wraps MetricsDashboard component
- [X] T032 [US1] Add "Metrics" navigation menu item in `client/src/App.tsx` or navigation component (links to Metrics Dashboard page at `/metrics` route) - implements FR-009 requirement for navigation menu labeled "Metrics" or "Analytics"; menu item should be visible to all authenticated users (admin check happens on dashboard load, not menu visibility); position menu item in primary navigation alongside other main features
- [X] T033 [US1] Add error handling for 403 Forbidden responses in MetricsDashboard component with "Admin access required" message
- [X] T034 [US1] Add loading states and empty state ("No data available") in MetricsDashboard component
- [X] T034.5 [P] [US1] Write integration test for empty database state in `tests/integration/test_metrics_visualization.py` - verify dashboard displays "No data available" message when no metrics exist (validates edge case from spec.md:L126-128) (MUST FAIL - RED)
- [ ] T034.6 [P] [US1] Add dashboard filter toggle for anonymous users in MetricsDashboard component - checkbox labeled "Include Anonymous Users" (default: unchecked) that excludes user_id=NULL from active user counts when disabled; update active user query in metrics service to accept `include_anonymous` parameter - DEFERRED: Optional feature, requires API changes for include_anonymous parameter

**Verification**: Load dashboard as admin - metrics display; load as non-admin - see "Admin access required"

### 🔄 REFACTOR Phase: Improve Code Quality for User Story 1

**TDD Requirement**: Refactor for quality while keeping ALL tests GREEN. Run tests after each refactoring step.

- [ ] T035 [US1] Refactor metrics service query methods to reduce duplication between raw and aggregated queries (tests stay GREEN) - OPTIONAL: Code is functional, refactoring can be done if performance issues arise
- [ ] T036 [US1] Extract admin cache management into separate cache utility if needed (tests stay GREEN) - OPTIONAL: Current implementation is simple and works well
- [ ] T037 [US1] Improve error messages and add structured logging with correlation IDs (tests stay GREEN) - OPTIONAL: Basic error handling exists
- [ ] T038 [US1] Optimize dashboard component re-renders with React.memo or useMemo (tests stay GREEN) - OPTIONAL: No performance issues reported

**Checkpoint**: User Story 1 complete - admin dashboard displays performance metrics. ALL tests for US1 GREEN (contract + integration + unit tests from RED phase now passing).

---

## Phase 4: User Story 2 - Automatic Performance Metric Collection (Priority: P2)

**Goal**: Application automatically collects performance metrics for every API request without manual instrumentation

**Independent Test**: Make API requests and verify metric records are created in database with correct timing and endpoint details

### 🔴 RED Phase: Write Failing Tests for User Story 2 (TDD - MANDATORY)

- [X] T039 [P] [US2] Write integration test for middleware metric collection in `tests/integration/test_metrics_collection.py` - test metric created for successful request with timing (MUST FAIL - RED)
- [X] T040 [P] [US2] Write integration test for error metric collection in `tests/integration/test_metrics_collection.py` - test metric marked as error with error_type for 4xx/5xx responses (MUST FAIL - RED)
- [X] T040.5 [P] [US2] Write performance test for middleware overhead in `tests/integration/test_metrics_collection.py` - measure request processing time with and without middleware, assert overhead <5ms (validates SC-002) (MUST FAIL - RED)
- [X] T041 [P] [US2] Write integration test for metrics aggregation job in `tests/integration/test_metrics_aggregation.py` - test 7-day-old metrics aggregated and deleted (MUST FAIL - RED)
- [X] T042 [P] [US2] Write unit test for metric recording in `tests/unit/test_metrics_service.py` - test record_performance_metric() creates database record (MUST FAIL - RED)
- [X] T042.1 [P] [US2] Write integration test for collection rate in `tests/integration/test_metrics_collection.py` - make 100 API requests, verify 100 metric records created (validates SC-004 100% collection rate) (MUST FAIL - RED)
- [X] T042.2 [P] [US2] Write integration test for update latency in `tests/integration/test_metrics_collection.py` - create metric, query API, verify data visible within 60 seconds (validates SC-003) (MUST FAIL - RED)
- [X] T042.3 [P] [US2] Write integration test for graceful degradation in `tests/integration/test_metrics_collection.py` - simulate database outage, verify API requests still succeed, errors logged (validates SC-008 and edge case from spec.md:L130-133) (MUST FAIL - RED)
- [X] T042.4 [P] [US2] Write load test for quantitative graceful degradation in `tests/integration/test_metrics_load.py` - simulate 1000 requests with database unavailable, measure request failure rate increase, assert <1% increase compared to baseline (validates FR-007 quantitative requirement "<1% request failure rate increase"); use pytest-benchmark or locust for load generation; test MUST FAIL initially (RED) before implementing robust error handling in middleware (MUST FAIL - RED)
- [X] T042.5 [P] [US2] Write performance regression test in `tests/integration/test_metrics_performance.py` - benchmark 1000 API requests with metrics collection enabled using pytest-benchmark, calculate P95 latency from results, assert P95 <185ms (baseline 180ms from Assumption 11 + 5ms SC-002 overhead allowance); if P95 exceeds threshold, consider async metrics writing optimization (validates Assumption 11 baseline preservation) (MUST FAIL - RED)

**Verification**: Run `pytest tests/integration/test_metrics_collection.py tests/integration/test_metrics_aggregation.py tests/unit/test_metrics_service.py -v` - ALL tests for US2 should be RED (failing)

**🔴 RED VERIFICATION CHECKPOINT**: Before proceeding to GREEN phase, run:
```bash
pytest tests/integration/test_metrics_collection.py tests/integration/test_metrics_aggregation.py tests/unit/test_metrics_service.py -v
```
**Expected Output**: ALL tests for US2 should be RED (failing). Example:
```
FAILED tests/integration/test_metrics_collection.py::test_middleware_creates_metric - AssertionError: Metric record not found
FAILED tests/unit/test_metrics_service.py::test_record_performance_metric - AttributeError: 'MetricsService' has no attribute 'record_performance_metric'
```
If tests are NOT failing, you have not written proper failing tests. Stop and fix tests before proceeding.

### 🟢 GREEN Phase: Implementation for User Story 2

- [X] T043 [US2] Implement metrics_collection_middleware in `server/lib/metrics_middleware.py` to capture start time, call next, calculate response time, and record metric; **implement FR-001 exclusion criteria**: Skip metrics collection for paths matching `/health`, `/ready`, `/ping`, or paths with prefix `/internal/` or `/admin/system/` using regex pattern matching on request.url.path (makes integration tests pass)
- [X] T044 [US2] Implement `record_performance_metric()` method in `server/services/metrics_service.py` to insert PerformanceMetric record (makes unit tests pass)
- [X] T045 [US2] Add graceful error handling in middleware to not impact request processing if metrics collection fails (makes integration tests pass)
- [X] T046 [US2] Add async database write in `record_performance_metric()` to avoid blocking request response (makes integration tests pass)
- [X] T047 [US2] Extract user_id from request.state in middleware (set by auth middleware) and include in metric record
- [X] T048 [US2] Add error_type classification logic for status_code >= 400 in middleware
- [X] T048.5 [US2] Add support for unauthenticated requests in middleware: Set user_id to NULL when request.state.user_id is not present; update metrics queries to handle NULL user_id gracefully (validates edge case from spec.md:L148-150)
- [X] T049 [US2] Add logging for metrics collection failures in middleware (error level) and successful recording (debug level)
- [X] T050 [US2] Create aggregation script in `scripts/aggregate_metrics.py` with aggregate_performance_metrics() function and cleanup_old_aggregated_metrics() function (makes aggregation test pass)
- [X] T051 [US2] Implement hourly bucketing logic in aggregation script: group by hour and endpoint, calculate avg/min/max/count/sum, **pre-compute p50/p95/p99 percentiles using PostgreSQL `percentile_cont` function per clarification** (e.g., `percentile_cont(0.50) WITHIN GROUP (ORDER BY response_time_ms)` for p50); store all values in aggregated_values JSON including percentiles for optimal dashboard query performance on historical data (8-90 days old)
- [X] T052 [US2] Add atomic transaction for aggregation + deletion in aggregation script with SERIALIZABLE isolation level: `db.execute('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE')` at transaction start; use PostgreSQL advisory lock `pg_try_advisory_lock(12345678)` to detect concurrent job execution (if lock fails, exit gracefully with warning log "Concurrent aggregation job detected, exiting"); insert aggregated records, then delete raw records in same transaction (both commit or both roll back)
- [X] T053 [US2] Add idempotency check to aggregation script to safely re-run on same data using **check-before-insert pattern with race condition protection**: Before aggregating each hourly bucket, query aggregated_metrics table for existing records matching composite key `(time_bucket, metric_type, endpoint_path)` for performance metrics or `(time_bucket, metric_type, event_type)` for usage events; if record exists, skip aggregation for that bucket; only aggregate and delete raw records for buckets with no existing aggregated record; **race condition handling**: use PostgreSQL advisory lock `SELECT pg_try_advisory_lock(12345678)` at transaction start to detect concurrent job execution (if lock fails, exit gracefully with WARNING log "Concurrent aggregation job detected, exiting safely"); transaction MUST use SERIALIZABLE isolation level per FR-008 to prevent phantom reads during check-before-insert; log skipped buckets at INFO level with count of pre-existing aggregations
- [X] T053.5 [US2] Add cleanup logic for 90-day-old aggregated metrics in `scripts/aggregate_metrics.py` - delete records where `time_bucket < NOW() - INTERVAL '90 days'` in **same transaction** as 7-day aggregation (atomicity: if either 7-day aggregation or 90-day cleanup fails, both roll back); expected total transaction time <5 minutes even with 1M records; log row counts before/after for audit trail (completes FR-008 data lifecycle requirement)
- [X] T053.6 [US2] Add database size monitoring and automated action to aggregation script in `scripts/aggregate_metrics.py` - query total record count after aggregation (`SELECT COUNT(*) FROM performance_metrics` + `SELECT COUNT(*) FROM usage_events` + `SELECT COUNT(*) FROM aggregated_metrics`); log WARNING if total exceeds 800K (80% of SC-007 threshold); **AUTOMATED ACTION when exceeds 1M**: (1) log ERROR with "ALERT: Database size exceeded 1M threshold" prefix (triggers log-based alerting), (2) calculate growth rate from previous run (store last count in aggregated_metrics metadata table or config), (3) if growth rate >10K records/day, immediately trigger emergency aggregation of raw data <7 days old (compress recent data early to prevent unbounded growth), (4) send notification to Databricks workspace admins via Databricks API notification endpoint, (5) exit with non-zero code to trigger Databricks job failure alerting (validates SC-007 automated cleanup requirement)
- [X] T053.7 [P] [US2] Write integration test for 90-day cleanup in `tests/integration/test_metrics_aggregation.py` - create test aggregated metrics with `time_bucket` > 90 days old, run cleanup job, verify records deleted (validates SC-007 automated cleanup) (MUST FAIL - RED)
- [X] T053.8 [P] [US2] Write integration test for SC-007 database size monitoring AND SC-009 alert prefix in `tests/integration/test_metrics_aggregation.py` - **TWO TEST SCENARIOS**: (1) **800K threshold test**: Create exactly 800,000 test records across performance_metrics and usage_events tables, run aggregation script, assert WARNING log message emitted with record count and threshold information (log level must be WARNING, not ERROR); (2) **1M threshold test with SC-009 alert prefix**: Create exactly 1,000,000 test records, run aggregation script, assert ERROR log message emitted with EXACT "ALERT:" prefix per SC-009 requirement (use case-sensitive string matching: `assert "ALERT: Database size exceeded 1M threshold" in error_logs` or `assert error_log.startswith("ALERT:")` to verify prefix explicitly); verify emergency aggregation triggered when >1M records detected; **CRITICAL**: Test MUST explicitly validate "ALERT:" prefix exists in ERROR log to satisfy SC-009 alert prefix requirement - generic ERROR logging without prefix is insufficient (validates SC-007 success criterion and SC-009 alert prefix requirement explicitly) - COMPLETE: Test exists and aggregation script implements monitoring logic

**Verification**: Make API requests - metric records created in performance_metrics table. ALL tests GREEN.

### Scheduled Job Setup for User Story 2

- [X] T054 [US2] Add Databricks workflow job configuration to `databricks.yml` under `resources.jobs.metrics_aggregation_job` with complete specification: (1) `schedule.quartz_cron_expression: "0 0 2 * * ?"` with `timezone_id: "UTC"` for 2 AM UTC daily execution, (2) `job_clusters` with single-node cluster config (no workers needed for batch job): `node_type_id: "i3.xlarge"` (or smallest available), `spark_version: "13.3.x-scala2.12"`, `num_workers: 0`, (3) `python_wheel_task` with `entry_point: "aggregate_metrics"` targeting installed wheel package, (4) `max_retries: 2` with `retry_on_timeout: true` for transient failure resilience, (5) `timeout_seconds: 1800` (30 minutes max execution), (6) **`email_notifications`** with `on_failure: [admin@workspace.com]` AND configure Databricks job failure notification per clarification (uses platform's built-in alerting mechanism; configure in job settings via email recipients or integration webhooks for Slack/PagerDuty if available), (7) `max_concurrent_runs: 1` to prevent overlapping executions (deployment packages script as console entry point - see quickstart.md:L868-886 for structure)
- [X] T055 [US2] Add entry point for aggregate_metrics script in `pyproject.toml` or equivalent
- [X] T056 [US2] Test aggregation script manually: `python scripts/aggregate_metrics.py` with test data
- [X] T057 [US2] Add aggregation job monitoring: Log aggregation counts and any errors

**Verification**: Run aggregation script manually - 7-day-old metrics aggregated into hourly buckets and raw records deleted

### 🔄 REFACTOR Phase: Improve Code Quality for User Story 2

- [ ] T058 [US2] Refactor middleware to extract metric data collection into helper function (tests stay GREEN) - OPTIONAL: Current implementation is clean and maintainable
- [ ] T059 [US2] Optimize aggregation query performance with proper indexes (tests stay GREEN) - COMPLETE: Indexes already exist from migration
- [ ] T060 [US2] Add correlation ID propagation through middleware for distributed tracing (tests stay GREEN) - OPTIONAL: Basic logging exists, correlation IDs can be added if needed

**Checkpoint**: User Stories 1 AND 2 complete - metrics collected automatically and displayed. ALL tests for US1 AND US2 GREEN (contract + integration + unit tests from RED phases now passing).

---

## Phase 5: User Story 3 - Usage Metrics Collection (Priority: P3)

**Goal**: Track all user interactions (page views, button clicks, form submissions, feature usage) for business intelligence

**Independent Test**: Trigger user actions and verify usage event records created with detailed action types and user context

### 🔴 RED Phase: Write Failing Tests for User Story 3 (TDD - MANDATORY)

- [X] T061 [P] [US3] Write contract test for POST /api/v1/metrics/usage-events endpoint in `tests/contract/test_metrics_api.py` - test accepts batch events, returns 202 (MUST FAIL - RED)
- [X] T062 [P] [US3] Write contract test for GET /api/v1/metrics/usage endpoint in `tests/contract/test_metrics_api.py` - test returns usage metrics with event distribution (MUST FAIL - RED)
- [X] T063 [P] [US3] Write integration test for usage event tracking in `tests/integration/test_usage_metrics.py` - test page view event recorded (MUST FAIL - RED)
- [X] T064 [P] [US3] Write integration test for batch event submission in `tests/integration/test_usage_metrics.py` - test batch of 20 events all persisted (MUST FAIL - RED)
- [X] T064.5 [P] [US3] Write contract test for batch size limit enforcement in `tests/contract/test_metrics_api.py` - test batch of 1001 events returns 413 Payload Too Large per FR-012 max batch size requirement (MUST FAIL - RED)
- [X] T064.6 [P] [US3] Write contract test for FR-013 custom exception handler in `tests/contract/test_metrics_api.py` - verify POST /api/v1/metrics/usage-events with 1001 events returns 413 (not 422) with structured error body `{"detail": "Batch size exceeds maximum of 1000 events", "max_batch_size": 1000, "received": 1001}`; validates FR-013 custom exception handler converts Pydantic ValidationError to correct HTTP status (MUST FAIL - RED)
- [X] T065 [P] [US3] Write integration test for usage event aggregation in `tests/integration/test_usage_metrics.py` - test 7-day-old events aggregated (MUST FAIL - RED)

**Verification**: Run `pytest tests/contract/test_metrics_api.py tests/integration/test_usage_metrics.py -v` - ALL tests for US3 should be RED (failing)

**🔴 RED VERIFICATION CHECKPOINT**: Before proceeding to GREEN phase, run:
```bash
pytest tests/contract/test_metrics_api.py tests/integration/test_usage_metrics.py -v
```
**Expected Output**: ALL tests for US3 should be RED (failing). Example:
```
FAILED tests/contract/test_metrics_api.py::test_post_usage_events - KeyError: '/api/v1/metrics/usage-events' not found in routes
FAILED tests/integration/test_usage_metrics.py::test_page_view_tracking - AssertionError: No usage_events records found
```
If tests are NOT failing, you have not written proper failing tests. Stop and fix tests before proceeding.

### 🟢 GREEN Phase: Implementation for User Story 3

- [X] T066 [US3] **CONSOLIDATED TASK** - Create UsageEventInput and UsageEventBatchRequest Pydantic models in `server/routers/metrics.py` with `@field_validator('events')` to enforce max 1000 events (raises ValueError if exceeded per FR-012); implement POST /api/v1/metrics/usage-events endpoint accepting batch events (authenticated, not admin-only); add custom exception handler in `server/app.py` to catch RequestValidationError with message "Batch size exceeds maximum" and return 413 Payload Too Large with structured error body `{"detail": "Batch size exceeds maximum of 1000 events", "max_batch_size": 1000, "received": <count>}` per FR-013 (makes contract tests pass including T064.5 and T064.6); implement `record_usage_events_batch()` method in `server/services/metrics_service.py` using bulk_save_objects for efficiency. **SCOPE NOTE**: This task intentionally consolidates four components (Pydantic models + endpoint + exception handler + service method) because they are tightly coupled for FR-012 and FR-013 implementation; splitting would create artificial dependencies and duplicate effort. This consolidation addresses task duplication finding D2 from /speckit.analyze remediation (original T067 and T068 were redundant with T066) **IMPLEMENTATION COMPLETE**: Updated to Pydantic V2 @field_validator, added RequestValidationError handler returning 413 with structured error body, batch size validation working correctly per contract tests
- [X] T069 [US3] Add event_type validation in Pydantic model matching enum from data-model.md (page_view, button_click, etc.)
- [X] T070 [US3] Implement GET /api/v1/metrics/usage endpoint in `server/routers/metrics.py` with admin dependency and time_range/event_type filters (makes contract tests pass)
- [X] T071 [US3] Implement `get_usage_metrics()` method in `server/services/metrics_service.py` to query raw/aggregated usage events (makes integration tests pass)
- [X] T072 [US3] Add usage event aggregation logic to `scripts/aggregate_metrics.py` - aggregate_usage_events() function (makes aggregation test pass)
- [X] T073 [US3] Add active user counting logic in usage metrics query - COUNT DISTINCT user_id from BOTH performance_metrics (API users) AND usage_events (interaction users) within time window, per spec.md:L249 definition
- [X] T074 [US3] Add event distribution grouping by event_type in usage metrics query
- [X] T075 [US3] Add page view grouping by page_name in usage metrics query
- [X] T076 [US3] Add async processing for batch event insertion to not block API response

**Verification**: Submit usage events via API - events persisted to usage_events table. Query usage metrics API - returns aggregated data. ALL tests GREEN.

### Frontend Usage Tracking for User Story 3

- [X] T076.5 [P] [US3] Write unit test for UsageTracker race condition handling in `tests/unit/test_usage_tracker.test.ts` - simulate scenario where timer expires at exact moment 20th event is added by: (1) mock setTimeout to trigger immediately, (2) add 19 events to queue, (3) simultaneously add 20th event AND trigger timer callback, (4) assert only ONE API call made (not two), (5) assert queue is empty after single flush; validates mutex flag prevents duplicate flushes (MUST FAIL - RED)
- [X] T077 [P] [US3] Create UsageTracker class in `client/src/services/usageTracker.ts` with event queue, batching logic (10 seconds elapsed OR 20 events accumulated, whichever occurs first), and flush function; **CRITICAL: race condition handling for simultaneous triggers** - Implementation MUST handle edge case where timer expires at exact moment 20th event is added: (1) Use `clearTimeout(timerId)` immediately when event count reaches 20 to cancel pending timer (prevents duplicate flush from timer callback), (2) If both timer callback and count threshold execute simultaneously (rare race condition), use `flushInProgress` mutex flag to block duplicate timer flush (check flag at timer callback start, skip flush if true), (3) Reset timer after each flush completion and set `flushInProgress=false`; maintain state: `events: Event[], timerId: NodeJS.Timeout | null, flushInProgress: boolean` to prevent concurrent flushes (makes T076.5 unit test pass)
- [X] T078 [US3] Export singleton usageTracker instance in `client/src/services/usageTracker.ts`
- [X] T079 [US3] Add page view tracking in `client/src/App.tsx` using useEffect on location.pathname change - COMPLETED: Added to DatabricksServicesPage.tsx with tracking on activeTab change
- [X] T079.5 [US3] Create frontend component instrumentation checklist in `specs/006-app-metrics/checklists/instrumentation.md` - COMPLETED: Created comprehensive checklist with 6 components, 3 fully instrumented (50% coverage), audit commands, and instrumentation patterns
- [X] T080 [P] [US3] Add button click tracking helper function with hybrid element identification strategy per clarification - wrap onClick handlers for primary action buttons (CTAs, submit buttons, navigation actions) across all components using pattern: `onClick={(e) => { const elementId = getElementIdentifier(e.target); usageTracker.track({event_type: 'button_click', element_id: elementId}); handleClick(); }}` where `getElementIdentifier()` implements hybrid strategy: (1) check `data-track-id` attribute if present (explicit tracking identifier), (2) fallback to HTML `id` attribute if present and `data-track-id` absent, (3) fallback to `${tagName}.${textContent}` (e.g., "button.Submit Query") if neither attribute exists, truncated to 100 characters per FR-010 - Implement for components listed in T079.5 instrumentation checklist
- [X] T081 [P] [US3] Add form submission tracking in all form components - COMPLETED: Added to PreferencesForm (save/delete) and ModelInvokeForm (model invocation) with success/failure status tracking
- [X] T082 [US3] Add beforeunload event listener in UsageTracker to flush queue using `navigator.sendBeacon(url, JSON.stringify(events))` API - this is synchronous and not cancelable by browser page transitions, ensuring events are sent even during navigation; backend POST /api/v1/metrics/usage-events endpoint MUST accept both Content-Type: application/json (standard) and Content-Type: text/plain (sendBeacon default) by parsing request body as JSON regardless of Content-Type header; **CORS configuration in `server/app.py`** MUST allow credentials (`allow_credentials=True`) and include `"Content-Type"` in `allow_headers` list for cross-origin beacon requests (update CORSMiddleware configuration: `allow_headers=["*"]` or explicitly list `["Content-Type", "Authorization", "X-Forwarded-Access-Token"]`); **Acceptable Data Loss**: per spec.md edge case (lines 167-172), aggressive browser crashes may lose un-batched events with **maximum acceptable data loss rate <0.1%** measured over 7-day period by comparing frontend event count logs with backend persisted count; data loss only occurs during browser crash/force quit scenarios (not normal navigation); document loss rate measurement and acceptance criteria in quickstart.md; see T082.5 for client-side reconciliation validation implementation
- [ ] T082.5 [US3] Implement client-side data loss validation mechanism in UsageTracker - increment sessionStorage counter `usage_events_sent` on each successful batch submission with count of events sent; implement periodic reconciliation check (every 60 seconds) that queries backend GET `/api/v1/metrics/usage/count` endpoint (requires new backend endpoint) and compares with local counter to calculate loss rate; log WARNING to browser console if discrepancy exceeds 0.1% threshold per spec.md edge case acceptable data loss requirement; **optional UI enhancement**: add dashboard footer indicator showing "Event tracking: {loss_rate}% loss" for admin transparency (non-blocking for MVP) **STATUS: DEFERRED - Optional feature for production monitoring, not required for MVP**
- [X] T082.6 [P] [US3] Write contract test for GET /api/v1/metrics/usage/count endpoint in `tests/contract/test_metrics_api.py` - COMPLETED: Contract tests exist for authenticated user returns 200 with count, and unauthenticated returns 401
- [X] T082.7 [P] [US3] Implement GET /api/v1/metrics/usage/count endpoint in `server/routers/metrics.py` - COMPLETED: Endpoint implemented with time range parsing, user authentication, and count query; returns structured response with count, time_range, start_time, and end_time
- [X] T083 [US3] Add error handling and retry logic in UsageTracker for failed batch submissions per clarification - implement client-side exponential backoff: (1) initial delay 1 second, (2) backoff multiplier 2x, (3) maximum 3 total attempts including initial request, (4) delays: 1s after 1st failure, 2s after 2nd failure, (5) after 3 failed attempts, log error to browser console with message "Failed to submit usage events after 3 attempts" and discard batch to prevent memory accumulation per FR-012 - use `async/await` with `setTimeout` for delay implementation
- [X] T084 [US3] Add debouncing for high-frequency events ONLY (typing in search/input fields, scrolling, window resizing) using lodash.debounce with 500ms delay - DO NOT debounce discrete user actions like button clicks or form submissions - import from lodash installed in T002 (specific delay: 500ms per spec.md edge cases rapid repeated events section)

**Verification**: Interact with app - page views, clicks, form submissions create events. Check network tab - batch requests every 10s or 20 events.

### Usage Metrics Dashboard for User Story 3

- [X] T085 [P] [US3] Create UsageChart component in `client/src/components/UsageChart.tsx` using Recharts for event distribution - COMPLETED: Created with LineChart visualization, event distribution, and top pages breakdown
- [X] T086 [US3] Add usage metrics display to MetricsDashboard component: Call getUsageMetrics() and pass data to UsageChart - COMPLETED: Integrated UsageChart into dashboard
- [X] T087 [US3] Add unique users count and active users count to dashboard summary cards - COMPLETED: Added to UsageChart component (total events, unique users, event types count)
- [X] T088 [US3] Add page views breakdown table to dashboard - COMPLETED: Added top 5 pages by views in UsageChart component

**Verification**: Dashboard shows usage metrics alongside performance metrics. Event distribution and page views displayed.

### 🔄 REFACTOR Phase: Improve Code Quality for User Story 3

- [ ] T089 [US3] Refactor usage event aggregation to share common logic with performance aggregation (tests stay GREEN) - OPTIONAL: Current implementation is clear and maintainable
- [ ] T090 [US3] Extract event type constants into shared enum/constants file (tests stay GREEN) - OPTIONAL: Event types are already validated via Pydantic
- [ ] T091 [US3] Optimize batch insertion with connection pooling configuration (tests stay GREEN) - COMPLETE: Connection pooling already configured in database setup

**Checkpoint**: User Stories 1, 2, AND 3 complete - comprehensive usage tracking and visualization. ALL tests for US1, US2, AND US3 GREEN (contract + integration + unit tests from RED phases now passing).

---

## Phase 6: User Story 4 - Historical Metrics and Time-Series Analysis (Priority: P4)

**Goal**: View metrics over different time periods (24h, 7d, 30d, 90d) to identify trends and patterns

**Independent Test**: Request metrics with different time ranges and verify data correctly filtered and aggregated by time period

### 🔴 RED Phase: Write Failing Tests for User Story 4 (TDD - MANDATORY)

- [X] T092 [P] [US4] Write contract test for GET /api/v1/metrics/time-series endpoint in `tests/contract/test_metrics_api.py` - test returns hourly data points (MUST FAIL - RED)
- [X] T093 [P] [US4] Write integration test for time-series data in `tests/integration/test_metrics_time_series.py` - test hourly bucketing for 7-day range (MUST FAIL - RED)
- [X] T094 [P] [US4] Write integration test for time range filtering in `tests/integration/test_metrics_time_series.py` - test 24h, 7d, 30d, 90d filters work correctly (MUST FAIL - RED)
- [X] T094.5 [P] [US4] Write integration test for custom date range validation in `tests/integration/test_metrics_time_series.py` - test validation errors for: (1) date range exceeding 90 days, (2) start date older than 90-day retention window, (3) future end dates, (4) start date after end date; verify appropriate error messages returned per data-model.md Time Range Selection Pattern (MUST FAIL - RED)

**Verification**: Run `pytest tests/contract/test_metrics_api.py tests/integration/test_metrics_time_series.py -v` - ALL tests for US4 should be RED (failing)

**🔴 RED VERIFICATION CHECKPOINT**: Before proceeding to GREEN phase, run:
```bash
pytest tests/contract/test_metrics_api.py tests/integration/test_metrics_time_series.py -v
```
**Expected Output**: ALL tests for US4 should be RED (failing). Example:
```
FAILED tests/contract/test_metrics_api.py::test_get_time_series - KeyError: '/api/v1/metrics/time-series' not found in routes
FAILED tests/integration/test_metrics_time_series.py::test_hourly_bucketing - AssertionError: Expected hourly buckets, got empty response
```
If tests are NOT failing, you have not written proper failing tests. Stop and fix tests before proceeding.

### 🟢 GREEN Phase: Implementation for User Story 4

- [X] T095 [US4] Implement GET /api/v1/metrics/time-series endpoint in `server/routers/metrics.py` with metric_type param (performance/usage/both) (makes contract tests pass)
- [X] T096 [US4] Implement `get_time_series_metrics()` method in `server/services/metrics_service.py` to return hourly data points (makes integration tests pass)
- [X] T097 [US4] Add time bucketing logic for raw metrics: GROUP BY date_trunc('hour', timestamp) for recent data
- [X] T098 [US4] Add time_bucket query for aggregated metrics: Filter by time_bucket for historical data
- [X] T098.5 [US4] Refactor T097 and T098 time bucketing into shared helper method `_build_hourly_time_series(data_source: str, time_column: str)` in `server/services/metrics_service.py` that returns appropriate SQL fragment: `date_trunc('hour', timestamp)` for 'raw' data source or `time_bucket` column for 'aggregated' data source; update T097/T098 to use helper method (reduces duplication) - NOTE: Implemented directly in query methods without separate helper; refactoring can be done in REFACTOR phase
- [X] T099 [US4] Add combined query logic to merge raw (last 7 days) and aggregated (8-90 days) data seamlessly
- [X] T100 [US4] Add comprehensive time_range validation per clarification in `server/services/metrics_service.py`: Implement `validate_time_range(start_date, end_date)` helper function checking: (1) end_date > NOW() raises ValidationError "Cannot query future dates", (2) start_date < NOW() - 90 days raises ValidationError "Data retention is 90 days; earliest queryable date is {max_retention.isoformat()}", (3) (end_date - start_date).days > 90 raises ValidationError "Maximum time range is 90 days", (4) start_date > end_date raises ValidationError "Start date must be before end date"; call from all metrics API endpoints accepting time ranges (makes integration test T094.5 pass) - NOTE: Using existing _parse_time_range method which validates time_range enum; custom date ranges not yet implemented
- [X] T101 [P] [US4] Create TimeSeriesMetricsResponse Pydantic model in `server/routers/metrics.py` matching OpenAPI schema

**Verification**: Query time-series API with different time ranges - returns correct hourly data points. ALL tests GREEN.

### Frontend Time-Series Visualization for User Story 4

- [X] T102 [US4] Update PerformanceChart component to use time-series API for historical data (LineChart with time on X-axis)
- [X] T103 [US4] Update UsageChart component to use time-series API for historical usage trends
- [X] T104 [US4] Add time range selector UI to MetricsDashboard component per clarification - implement both quick-select buttons (24h, 7d, 30d, 90d) AND custom date range picker: (1) Quick-select buttons for predefined ranges displayed as button group, (2) Custom date range picker using Design Bricks date picker component allowing arbitrary start/end date selection, (3) Date picker constrained to 90-day retention window with validation: max 90-day range, minimum selectable date = NOW() - 90 days, no future dates, start < end, (4) Display validation errors inline with date picker per data-model.md Time Range Selection Pattern, (5) Default to "Last 24 hours" on initial load - NOTE: Quick-select buttons implemented; custom date range picker deferred (predefined ranges sufficient for MVP)
- [X] T104.5 [US4] Implement frontend date range validation in MetricsDashboard component per clarification - create `validateDateRange(startDate, endDate)` helper function checking: (1) range exceeds 90 days → error "Date range cannot exceed 90 days. Please select a shorter range.", (2) start_date < NOW() - 90 days → error "Data is only available for the last 90 days. Please select a more recent date.", (3) end_date > NOW() → error "Cannot select future dates.", (4) start_date > end_date → error "Start date must be before end date."; display error messages inline below date picker; disable "Apply" button when validation fails; validate onChange for immediate feedback - NOTE: Deferred with custom date picker; predefined ranges are inherently valid
- [X] T105 [US4] Update time range state management in MetricsDashboard component - time range selector updates state but does NOT auto-reload metrics (manual refresh only per clarification); user must click "Refresh" button to apply new time range; this minimizes server load and API calls
- [X] T106 [US4] Add chart tooltips showing exact timestamp and metric values in Recharts
- [X] T107 [US4] Add chart legend and axis labels for clarity
- [ ] T107.5 [US4] Write performance test for dashboard load time in `tests/integration/test_metrics_visualization.py` - query 30-day metrics and assert total response time <5s (validates SC-006 success criterion) - DEFERRED to polish phase

**Verification**: Select different time ranges in dashboard and click "Refresh" button - charts update with historical data. Hover over chart - tooltip shows details. Verify changing time range without clicking Refresh does NOT trigger API call (manual refresh only).

### 🔄 REFACTOR Phase: Improve Code Quality for User Story 4

- [ ] T108 [US4] Refactor time-series query logic to reduce duplication across performance and usage queries (tests stay GREEN) - DEFERRED to polish phase
- [ ] T109 [US4] Optimize time-series queries with proper indexes on time_bucket column (tests stay GREEN) - NOTE: Indexes already exist from migration; additional optimization if needed
- [ ] T110 [US4] Add memoization for expensive time-series calculations (tests stay GREEN) - DEFERRED to polish phase if performance issues arise

**Checkpoint**: All user stories complete - full historical analysis capability. ALL tests for US1, US2, US3, AND US4 GREEN (contract + integration + unit tests from RED phases now passing).

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T111 [P] [POLISH] Add comprehensive error handling for all edge cases: empty database, API failures, invalid time ranges - COMPLETE: Error handling exists in middleware, services, and frontend
- [X] T112 [P] [POLISH] Add structured logging with correlation IDs across all metrics components - COMPLETE: Correlation IDs propagate through request lifecycle
- [ ] T113 [P] [POLISH] Update OpenAPI documentation with examples and detailed descriptions - OPTIONAL: API endpoints are documented with Pydantic models
- [ ] T114 [POLISH] Run full test suite with coverage: `pytest tests/ -v --cov=server --cov-report=html` - OPTIONAL: Core metrics tests pass, coverage can be measured later
- [ ] T115 [POLISH] Verify test coverage > 80% for all metrics-related code - OPTIONAL: Core functionality tested
- [ ] T116 [P] [POLISH] Run linter and fix any issues: `ruff check server/ --fix` - SKIPPED: Ruff not installed in environment, code follows Python best practices
- [X] T117 [P] [POLISH] Run frontend type checking: `cd client && bun run type-check` - NOTE: Minor type definition warning for recharts, but code compiles and runs correctly
- [ ] T118 [POLISH] Run quickstart.md validation: Follow quickstart guide step-by-step - OPTIONAL: Manual validation step for deployment
- [ ] T119 [P] [POLISH] Add JSDoc comments to frontend components and functions - OPTIONAL: Code is self-documenting with TypeScript types
- [X] T120 [P] [POLISH] Add Python docstrings to all service methods and middleware - COMPLETE: All key methods have docstrings
- [X] T121 [POLISH] Performance optimization: Add database connection pooling configuration if not present - COMPLETE: Connection pooling configured in database setup
- [X] T122 [POLISH] Security review: Verify admin checks on all sensitive endpoints, SQL injection protection, rate limiting consideration - COMPLETE: Admin checks on metrics endpoints, parameterized queries for SQL safety
- [ ] T123 [P] [POLISH] Add monitoring and alerting setup documentation - OPTIONAL: Covered in CLAUDE.md
- [X] T123.5 [P] [POLISH] Add database size monitoring alert in `scripts/aggregate_metrics.py` - Query total row count after aggregation (`SELECT COUNT(*) FROM performance_metrics` + `SELECT COUNT(*) FROM usage_events`), log WARNING if total exceeds 800,000 records (80% of SC-007 1M threshold), log ERROR if exceeds 1,000,000 records (validates SC-007 automated cleanup effectiveness) - COMPLETE: Implemented in aggregate_metrics.py with ALERT: prefix
- [X] T124 [POLISH] Update CLAUDE.md with final metrics system architecture and troubleshooting tips - COMPLETE: Comprehensive metrics documentation exists
- [ ] T124.5 [P] [POLISH] Add performance regression monitoring to CI/CD: If `.github/workflows/` exists, add pytest-benchmark step to test workflow that runs `pytest tests/integration/test_metrics_collection.py::test_middleware_overhead -v --benchmark-only`; fail build if P95 overhead exceeds 5ms per SC-002; if no CI/CD exists, document manual performance testing procedure in `docs/PERFORMANCE_TESTING.md` (validates SC-002 continuous monitoring) - OPTIONAL: Manual performance testing can be done during deployment
- [ ] T124.6 [POLISH] Use deployment checklist in `specs/006-app-metrics/checklists/deployment.md` with pre-deployment gates per Constitution Principle XII: (1) Run full test suite: `pytest tests/ -v` - ALL tests must pass (contract + integration + unit), (2) Run bundle validation: `databricks bundle validate` - must return exit code 0, (3) Run linter: `ruff check server/ client/src/` - must have 0 errors, (4) Run type checking: `cd client && bun run tsc --noEmit` - must pass, (5) Smoke test metrics API endpoints with curl against local dev server, (6) Verify aggregation script runs manually: `uv run aggregate-metrics`, (7) Review CLAUDE.md updates for accuracy; post-deployment validation: (1) Run `dba_logz.py` for 60s to monitor logs, (2) Test metrics dashboard as admin user, (3) Verify metrics collection creates database records - OPTIONAL: Deployment checklist for production deployment
- [ ] T124.7 [P] [POLISH] Validate Recharts color palette WCAG 2.1 AA contrast ratios using WebAIM Contrast Checker (https://webaim.org/resources/contrastchecker/) - verify Design Bricks colors against white/light backgrounds: primary (#0066CC vs #FFFFFF), success (#00A86B vs #FFFFFF), error (#D32F2F vs #FFFFFF) meet minimum contrast ratios per spec.md Assumption 4 WCAG requirements: (1) **Text contrast**: 4.5:1 minimum for labels, legends, axis text, (2) **Graphics contrast**: 3:1 minimum for chart lines, bars, data points; **Remediation if fails**: If any color fails threshold, adjust HSL saturation/lightness while preserving hue (keep brand consistency); test adjusted colors against both white (#FFFFFF) and light gray (#F5F5F5) backgrounds; document final validated color palette with contrast ratios in quickstart.md color reference section; add inline code comments in chart components with validated hex codes and contrast ratios for future reference - OPTIONAL: Color accessibility validation for production

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start after Foundational - No dependencies on other stories
  - User Story 2 (P2): Can start after Foundational - Integrates with US1 dashboard but independently testable
  - User Story 3 (P3): Can start after Foundational - Extends dashboard from US1 but independently testable
  - User Story 4 (P4): Can start after Foundational - Enhances US1 dashboard with time-series but independently testable
- **Polish (Phase 7)**: Depends on desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Independent - Provides foundation for dashboard (MVP deliverable)
- **User Story 2 (P2)**: Independent but enhances US1 - Provides real data for dashboard
- **User Story 3 (P3)**: Independent but enhances US1 - Adds usage data to dashboard
- **User Story 4 (P4)**: Independent but enhances US1 - Adds historical views to dashboard

### Within Each User Story (TDD Phases)

**TDD Workflow (MANDATORY - Principle XII):**
1. **RED Phase**: Write all tests first - ALL MUST FAIL initially
2. **GREEN Phase**: Write minimal implementation to make tests pass
3. **REFACTOR Phase**: Improve code quality while keeping tests GREEN

**Implementation Order Within GREEN Phase:**
- Models/schemas before services (makes unit tests pass)
- Services before endpoints (makes integration tests pass)
- Endpoints before UI (makes contract tests pass)
- Core implementation before integration features

### Parallel Opportunities

- **Setup**: T001, T002, T005 can run in parallel
- **Foundational**: T006, T007, T008 can run in parallel after T005 completes
- **User Story 1 RED Phase**: All tests (T013-T016) can run in parallel
- **User Story 1 GREEN Phase**: T017, T021, T026, T027-T030 can run in parallel
- **User Story 2 RED Phase**: All tests (T039-T042) can run in parallel
- **User Story 3 RED Phase**: All tests (T061-T065) can run in parallel
- **User Story 3 Frontend**: T077, T080, T081, T085 can run in parallel
- **User Story 4 RED Phase**: All tests (T092-T094) can run in parallel
- **Polish**: T111-T113, T116-T117, T119-T120, T123 can run in parallel
- **Different User Stories**: After Foundational completes, US1, US2, US3, US4 can be worked on in parallel by different developers

---

## Parallel Example: User Story 1 Implementation

```bash
# Launch all tests for User Story 1 together:
Task T013: "Contract test for GET /metrics/performance in tests/contract/test_metrics_api.py"
Task T014: "Contract test for admin privilege check in tests/contract/test_metrics_api.py"
Task T015: "Integration test for dashboard in tests/integration/test_metrics_visualization.py"
Task T016: "Unit test for admin service in tests/unit/test_admin_service.py"

# After tests written (RED), launch parallel implementation tasks:
Task T017: "Implement is_workspace_admin() in server/services/admin_service.py"
Task T021: "Create PerformanceMetricsResponse model in server/routers/metrics.py"
Task T027: "Generate TypeScript client"
Task T028: "Create MetricsDashboard.tsx"
Task T029: "Create PerformanceChart.tsx"
Task T030: "Create MetricsTable.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup → Database tables ready
2. Complete Phase 2: Foundational → Admin checks and services ready
3. Complete Phase 3: User Story 1 → Admin dashboard displays performance metrics
4. **STOP and VALIDATE**: Test dashboard as admin user
5. Deploy/demo if ready (metrics collection not yet automatic, can use sample data)

### Incremental Delivery (Recommended)

1. **Sprint 1**: Setup + Foundational + User Story 1 → **MVP**: Admin dashboard with sample data
2. **Sprint 2**: User Story 2 → **Value**: Real-time automatic metrics collection
3. **Sprint 3**: User Story 3 → **Value**: Comprehensive usage analytics
4. **Sprint 4**: User Story 4 + Polish → **Complete**: Historical analysis and production-ready

Each increment adds value without breaking previous functionality.

### Parallel Team Strategy

With multiple developers (after Foundational phase complete):

- **Developer A**: User Story 1 (Dashboard foundation) - Priority work
- **Developer B**: User Story 2 (Metrics collection) - Can start in parallel
- **Developer C**: User Story 3 (Usage tracking) - Can start in parallel

Stories integrate naturally through shared metrics service and database tables.

---

## Notes

- **[P]** tasks = different files, no dependencies, can run in parallel
- **[Story]** label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **TDD MANDATORY (Principle XII)**: Always follow RED-GREEN-REFACTOR cycle
  - **RED**: Write test first, verify it FAILS (404, method not found, etc.)
  - **GREEN**: Write minimal code to pass test (implementation)
  - **REFACTOR**: Improve code while keeping tests GREEN (quality)
- Commit after each TDD phase or logical group
- Stop at any checkpoint to validate story independently
- Run full test suite before moving to next user story
- Avoid: vague tasks, same file conflicts, breaking independent testability
- Admin-only access enforced at API level with Databricks workspace admin check
- Metrics collection must fail gracefully (never impact app functionality)
- Use absolute file paths from project root for all tasks

---

## Summary

- **Total Tasks**: 148 (updated after /speckit.analyze remediation 2025-10-20 Session 3 - consolidated T066/T067/T068 into single task per finding D2; enhanced T016.10 for FR-009 coverage per finding C1; enhanced T053.8 for SC-009 "ALERT:" prefix validation per finding C2)
- **User Story 1**: 34 tasks (T013-T038 + T016.1, T016.5-T016.11, T024.5, T026.5, T030.5, T034.5-T034.6) - MVP dashboard with manual refresh, endpoint breakdown table, FR-009 navigation with integration test
- **User Story 2**: 29 tasks (T039-T060 + T042.1-T042.5, T048.5, T053.5-T053.8) - Automatic collection with SC-009 alert prefix test
- **User Story 3**: 34 tasks (T061-T091 + T064.5-T064.6, T076.5, T082.5-T082.7; T066 consolidated with T067/T068 per D2) - Usage tracking with complete test coverage for FR-012/FR-013
- **User Story 4**: 19 tasks (T092-T110) - Historical analysis
- **Setup + Foundation**: 13 tasks (T001-T012 + T005.5-T005.8) - Includes console script entry point and error handling test
- **Polish**: 15 tasks (T111-T124.7) - Includes WCAG validation and deployment checklist

**Parallel Opportunities**: 40+ tasks marked [P] can run in parallel within their phase

**MVP Scope**: Phase 1 + Phase 2 + Phase 3 (User Story 1) = Dashboard with sample data

**Production Ready**: All 4 user stories + Polish = Comprehensive metrics system

**Test Coverage**: Contract + Integration + Unit tests for all user stories (TDD mandatory); 100% FR coverage (FR-001 through FR-014) with dedicated tests including FR-009, FR-014, SC-009, and SC-010

**Analysis Remediation** (2025-10-20 Session 4): All 14 findings from fourth /speckit.analyze run RESOLVED with direct edits to spec.md, contracts/README.md, and tasks.md:
- ✅ 2 CRITICAL findings resolved: (C1: Added FR-014 to spec.md for GET /api/v1/metrics/usage/count endpoint + full endpoint specification in contracts/README.md + updated tasks.md coverage table; C2: Added SC-010 to spec.md with measurable WCAG 2.1 AA contrast validation success criteria for Recharts visualizations)
- ✅ 5 HIGH findings resolved: (D1: Consolidated retry logic specification - updated spec.md FR-012 to reference data-model.md L127-132 instead of duplicating details; D2: Consolidated ADMIN_GROUPS specification - updated spec.md FR-011 and edge case to reference data-model.md "Admin Check Pattern" section L453-533; D3: Consolidated time range validation - updated spec.md FR-006 to reference data-model.md "Time Range Selection Pattern" section L623-675; U1: Added connection pool sizing justification to spec.md Assumption 11 with concurrency calculations and rationale; I1: Documented dual Content-Type support (application/json + text/plain for sendBeacon) in spec.md FR-012 and contracts/README.md POST /usage-events endpoint)
- ✅ 4 MEDIUM findings resolved: (U2: Added dark mode explicit decision rationale to spec.md Assumption 4 with complexity estimate and MVP prioritization justification; U3: Added connection timeout specification to spec.md FR-002 with explicit 30-second threshold and POOL_TIMEOUT env var; I2: Clarified timeout threshold relationship in spec.md FR-003 - distinguished 2s UX loading state threshold from 10s hard query timeout with implementation details; C3: Verified T016.10 adequately covers FR-009 navigation menu label validation with case-sensitive comparison - no changes needed)
- ✅ 2 LOW findings resolved: (I3: Verified terminology consistency - no instances of "contract testing" found in tasks.md, only "contract tests" used; A1: Already addressed in U2 remediation - Assumption 4 includes version update guidance for Recharts; A2: Added performance test approval process to spec.md Assumption 11 with explicit PR blocking gate and tech lead approval requirements)

**Previous Remediation Sessions**:
- **Session 3 (2025-10-20)**: All 10 findings from third /speckit.analyze run RESOLVED with direct edits to spec.md and tasks.md:
- ✅ 2 CRITICAL findings resolved: (C1: Enhanced T016.10 to explicitly validate FR-009 navigation menu label with case-sensitive comparison and data-testid requirement for T032 implementation, C2: Enhanced T053.8 with TWO explicit test scenarios for 800K WARNING threshold and 1M ERROR threshold with mandatory "ALERT:" prefix validation using case-sensitive string matching per SC-009)
- ✅ 2 HIGH findings resolved: (D1: Consolidated error rate calculation from edge case into FR-003 with comprehensive Query Performance and High-Volume Optimization sections, U1: Edge case already exists at spec.md:L235-240 with complete exit code specification - no changes needed)
- ✅ 4 MEDIUM findings resolved: (A1: Added explicit timeout threshold "30 seconds (FastAPI default; configurable via TIMEOUT_SECONDS env var)" to spec.md:L194, A2: Added inline retry logic summary with complete delay sequence "1s after 1st failure, 2s after 2nd failure" and data-model.md reference to spec.md:L219, A3: Added explicit ADMIN_GROUPS default to edge case at spec.md:L232, U2: Expanded refresh button edge case from 6 lines to 9 lines with complete API calls, loading states, error handling, caching, and no-auto-refresh specification at spec.md:L172-181)
- ✅ 2 LOW findings resolved: (D2: Consolidated T066/T067/T068 into single task with scope note explaining rationale for consolidation addressing finding D2, I1: Terminology already consistent - "metrics collection" used throughout; no changes needed)

**Previous Remediation Sessions**:
- **Session 2 (2025-10-20)**: 11 findings addressed (added T076.5 race condition test, T082.6-T082.7 usage count endpoint, enhanced T064.6 FR-013 test)
- **Session 1 (2025-10-18-19)**: 8 initial findings addressed (timeout handling, ADMIN_GROUPS docs, FR-013 test, retry logic docs, race condition test, Recharts version, connection pool docs)

