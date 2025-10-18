# Feature Specification: Comprehensive Integration Test Coverage

**Feature Branch**: `005-write-integration-test`  
**Created**: October 18, 2025  
**Status**: Draft  
**Input**: User description: "Write integration test to maximize the coverage."

## Clarifications

### Session 2025-10-18

- Q: How should external Databricks services (Unity Catalog APIs, Model Serving endpoints) be handled in integration tests? → A: Hybrid: mock external APIs for most tests, but have optional "live" tests that can run against real workspace if configured
- Q: How should test data be managed for integration tests? → A: Hybrid: shared read-only reference data plus per-test isolated data for write/update operations
- Q: Should individual slow tests have specific timeout thresholds? → A: No individual timeouts, only overall 5-minute suite limit
- Q: What concurrency levels should stress tests target to validate production readiness? → A: Light concurrency: 5-10 concurrent requests (validates basic thread safety)
- Q: How should "coverage" be measured for API endpoints? → A: Code coverage: 90% line/branch coverage in router and service files measured by pytest-cov

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Complete Lakebase API Coverage (Priority: P1)

Developers and QA engineers need comprehensive integration tests for all Lakebase (user preferences) API endpoints to ensure data isolation, error handling, and correct CRUD operations work end-to-end.

**Why this priority**: User preferences are a critical feature for personalization and data must be properly isolated per user. Missing test coverage for these endpoints represents a significant risk for data leakage and feature breakage.

**Independent Test**: Can be fully tested by executing CRUD operations on preferences endpoints with multiple users and verifying data isolation, error responses, and state management.

**Acceptance Scenarios** (will become automated tests following TDD):

1. **Given** no preferences exist for a user, **When** GET /api/lakebase/preferences is called, **Then** an empty list is returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_lakebase_full_flow.py

2. **Given** a user has saved preferences, **When** another user requests preferences, **Then** only their own preferences are returned (data isolation)
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_lakebase_full_flow.py

3. **Given** valid preference data, **When** POST /api/lakebase/preferences is called, **Then** preference is created with 201 status and can be retrieved
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_lakebase_full_flow.py

4. **Given** an existing preference, **When** POST is called again with same key, **Then** preference is updated (upsert behavior)
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_lakebase_full_flow.py

5. **Given** an existing preference, **When** DELETE /api/lakebase/preferences/{key} is called, **Then** preference is removed and GET returns empty
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_lakebase_full_flow.py

6. **Given** Lakebase is not configured, **When** any preferences endpoint is called, **Then** 503 error with LAKEBASE_NOT_CONFIGURED is returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_lakebase_full_flow.py

7. **Given** invalid preference key format, **When** saving preference, **Then** 400 error with validation details is returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_lakebase_full_flow.py

---

### User Story 2 - Complete Unity Catalog API Coverage (Priority: P1)

Developers need full integration test coverage for all Unity Catalog endpoints to ensure catalog browsing, table querying, and permission enforcement work correctly across the entire data access flow.

**Why this priority**: Unity Catalog is the primary data access layer. Incomplete test coverage means potential security vulnerabilities (unauthorized data access) and broken data browsing functionality.

**Independent Test**: Can be fully tested by executing catalog/schema/table listing operations and query operations with different user permissions, verifying results and error handling.

**Acceptance Scenarios** (will become automated tests following TDD):

1. **Given** a user with catalog access, **When** GET /api/unity-catalog/catalogs is called, **Then** accessible catalog names are returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_unity_catalog_full_flow.py

2. **Given** a catalog name, **When** GET /api/unity-catalog/schemas is called, **Then** schema names in that catalog are returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_unity_catalog_full_flow.py

3. **Given** catalog and schema names, **When** GET /api/unity-catalog/table-names is called, **Then** table names are returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_unity_catalog_full_flow.py

4. **Given** catalog/schema filters, **When** GET /api/unity-catalog/tables is called, **Then** filtered DataSource objects with metadata are returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_unity_catalog_full_flow.py

5. **Given** valid table coordinates, **When** GET /api/unity-catalog/query is called, **Then** table data with pagination is returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_unity_catalog_full_flow.py

6. **Given** valid table coordinates, **When** POST /api/unity-catalog/query is called with filters, **Then** filtered data is returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_unity_catalog_full_flow.py

7. **Given** user lacks permissions, **When** accessing restricted catalog, **Then** 403 error with CATALOG_PERMISSION_DENIED is returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_unity_catalog_full_flow.py

8. **Given** non-existent table, **When** querying table, **Then** 404 error with TABLE_NOT_FOUND is returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_unity_catalog_full_flow.py

9. **Given** invalid limit/offset parameters, **When** querying table, **Then** 400 error with validation details is returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_unity_catalog_full_flow.py

---

### User Story 3 - Complete Model Serving API Coverage (Priority: P1)

Developers need comprehensive integration tests for all Model Serving endpoints including endpoint discovery, schema detection, inference execution, and logging to ensure ML operations work end-to-end.

**Why this priority**: Model Serving is the core AI/ML functionality. Missing test coverage means potential model inference failures, schema detection issues, and logging gaps that could break the entire ML pipeline.

**Independent Test**: Can be fully tested by listing endpoints, detecting schemas, executing inference requests, and verifying logs are persisted correctly.

**Acceptance Scenarios** (will become automated tests following TDD):

1. **Given** model endpoints exist, **When** GET /api/model-serving/endpoints is called, **Then** list of endpoints with metadata is returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_model_serving_full_flow.py

2. **Given** an endpoint name, **When** GET /api/model-serving/endpoints/{name} is called, **Then** endpoint details are returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_model_serving_full_flow.py

3. **Given** a non-existent endpoint, **When** getting endpoint details, **Then** 404 error with ENDPOINT_NOT_FOUND is returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_model_serving_full_flow.py

4. **Given** an endpoint name, **When** GET /api/model-serving/endpoints/{name}/schema is called, **Then** detected schema with example JSON is returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_model_serving_full_flow.py

5. **Given** valid inference request, **When** POST /api/model-serving/invoke is called, **Then** predictions with SUCCESS status are returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_model_serving_full_flow.py

6. **Given** inference execution, **When** request completes, **Then** inference log is persisted to database with user_id
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_model_serving_full_flow.py

7. **Given** user has inference history, **When** GET /api/model-serving/logs is called, **Then** paginated logs for that user only are returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_model_serving_full_flow.py

8. **Given** inference timeout, **When** model takes too long, **Then** 503 error with MODEL_TIMEOUT is returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_model_serving_full_flow.py

9. **Given** invalid input format, **When** invoking model, **Then** 400 error with INVALID_INPUT is returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_model_serving_full_flow.py

10. **Given** Lakebase not configured, **When** GET /api/model-serving/logs is called, **Then** 503 error with LAKEBASE_NOT_CONFIGURED is returned
    - *Test Type*: Integration
    - *Test Location*: tests/integration/test_model_serving_full_flow.py

---

### User Story 4 - Cross-Service Integration Flows (Priority: P2)

Developers need integration tests that verify end-to-end workflows spanning multiple services (e.g., query data from Unity Catalog, use it for model inference, log results) to ensure the system works cohesively.

**Why this priority**: Individual service tests don't catch integration issues between services. Real-world usage involves multiple services working together, and gaps in cross-service testing can lead to workflow failures in production.

**Independent Test**: Can be tested by executing multi-step workflows like: authenticate → query catalog → detect model schema → invoke model → verify logs, ensuring data flows correctly across services.

**Acceptance Scenarios** (will become automated tests following TDD):

1. **Given** authenticated user, **When** browsing catalog then querying table then invoking model with data, **Then** entire workflow completes successfully
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_cross_service_workflows.py

2. **Given** user preferences saved, **When** using preferences to customize Unity Catalog queries, **Then** preferences affect query behavior correctly
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_cross_service_workflows.py

3. **Given** multiple concurrent users, **When** each executes full workflow (catalog → model inference), **Then** data isolation is maintained across all services
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_cross_service_workflows.py

4. **Given** model inference logs, **When** querying logs after multiple inference calls, **Then** all inference history is correctly persisted and retrievable
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_cross_service_workflows.py

---

### User Story 5 - Error Recovery and Resilience Testing (Priority: P2)

Developers need integration tests that verify error recovery mechanisms, graceful degradation, and retry logic work correctly when downstream services fail or are unavailable.

**Why this priority**: Production systems face transient failures. Without proper error recovery testing, users will experience poor error messages, lost data, or complete system failures instead of graceful degradation.

**Independent Test**: Can be tested by simulating various failure scenarios (database unavailable, model timeout, permission errors) and verifying appropriate error responses and recovery behavior.

**Acceptance Scenarios** (will become automated tests following TDD):

1. **Given** database connection failure, **When** any database-dependent endpoint is called, **Then** 503 error with DATABASE_UNAVAILABLE and retry_after is returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_error_recovery.py

2. **Given** intermittent model service failure, **When** retrying inference request, **Then** subsequent request succeeds after transient error
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_error_recovery.py

3. **Given** permission revoked mid-session, **When** accessing previously accessible resource, **Then** 403 error is returned immediately
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_error_recovery.py

4. **Given** corrupted data in database, **When** retrieving preferences, **Then** system handles gracefully without crashing
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_error_recovery.py

---

### User Story 6 - Pagination and Large Dataset Handling (Priority: P3)

Developers need integration tests that verify pagination works correctly across all endpoints that return lists, ensuring performance and data correctness with large datasets.

**Why this priority**: Pagination bugs can cause data loss, incorrect ordering, duplicate records, or performance issues. While less critical than core functionality, pagination failures significantly degrade user experience.

**Independent Test**: Can be tested by creating large datasets, then verifying pagination parameters (limit, offset) work correctly and consistently across all list endpoints.

**Acceptance Scenarios** (will become automated tests following TDD):

1. **Given** 200 preferences for a user, **When** paginating through preferences with limit=50, **Then** all 200 records are retrieved without duplicates or gaps
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_pagination_comprehensive.py

2. **Given** 500 inference logs, **When** paginating with various limit/offset combinations, **Then** correct records are returned in consistent order
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_pagination_comprehensive.py

3. **Given** large Unity Catalog table, **When** querying with pagination, **Then** query performance remains acceptable and data is correct
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_pagination_comprehensive.py

4. **Given** edge case pagination parameters (offset=0, limit=1; offset=999, limit=1000), **When** querying, **Then** correct results are returned
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_pagination_comprehensive.py

---

### User Story 7 - Concurrent Request Handling (Priority: P3)

Developers need integration tests that verify the system handles concurrent requests correctly, ensuring no race conditions, data corruption, or deadlocks occur under load.

**Why this priority**: Concurrent access is inevitable in production. Race conditions and deadlocks are difficult to debug and can cause intermittent failures that are hard to reproduce. These tests focus on basic thread safety validation with light concurrency (5-10 concurrent requests).

**Independent Test**: Can be tested by executing multiple simultaneous requests to the same endpoints and verifying data integrity, response correctness, and no system crashes.

**Acceptance Scenarios** (will become automated tests following TDD):

1. **Given** 5-10 concurrent users, **When** each saves different preferences simultaneously, **Then** all preferences are correctly persisted without data loss
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_concurrency.py

2. **Given** 5-10 concurrent model inference requests, **When** all execute simultaneously, **Then** all complete successfully with correct predictions and logs
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_concurrency.py

3. **Given** 5-10 concurrent reads and writes to same preference key, **When** executed simultaneously, **Then** final state is consistent and no data corruption occurs
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_concurrency.py

4. **Given** 5-10 users querying same Unity Catalog table, **When** queries execute concurrently, **Then** all return correct results without interference
   - *Test Type*: Integration
   - *Test Location*: tests/integration/test_concurrency.py

---

### Edge Cases

- What happens when a user deletes a preference that doesn't exist? (Should return 404 with appropriate message)
- How does the system handle extremely large preference values (e.g., 10MB JSON)? (Should validate and reject with appropriate limits)
- What happens when pagination offset exceeds total record count? (Should return empty list, not error)
- How are timezone differences handled in timestamp fields across all services? (Should use UTC consistently)
- What happens when model inference input exceeds size limits? (Should return 400 with clear validation message)
- How does schema detection handle endpoints with no schema information available? (Should return "unknown" type with helpful message)
- What happens when concurrent users try to update the same preference key simultaneously? (Last write wins, no data corruption)
- How are special characters and Unicode in table names, preference keys, and endpoint names handled? (Should support properly encoded values)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide integration tests for all Lakebase API endpoints (GET/POST/DELETE preferences) covering success and error cases
- **FR-002**: System MUST provide integration tests for all Unity Catalog API endpoints (catalogs, schemas, tables, queries) covering success and error cases
- **FR-003**: System MUST provide integration tests for all Model Serving API endpoints (list, get, schema, invoke, logs) covering success and error cases
- **FR-004**: System MUST provide integration tests for cross-service workflows that span multiple API endpoints and services
- **FR-005**: System MUST provide integration tests that verify data isolation between users across all services
- **FR-006**: System MUST provide integration tests that verify error handling and recovery for all failure scenarios
- **FR-007**: System MUST provide integration tests that verify pagination works correctly for all list endpoints
- **FR-008**: System MUST provide integration tests that verify concurrent request handling (5-10 concurrent requests) without data corruption to validate basic thread safety
- **FR-009**: System MUST provide integration tests that verify all HTTP status codes and error response formats are correct
- **FR-010**: System MUST provide integration tests that verify authentication and authorization work correctly for all endpoints
- **FR-011**: System MUST provide integration tests that verify logging and observability for all operations
- **FR-012**: System MUST use pytest fixtures to reduce test duplication and improve maintainability
- **FR-013**: System MUST organize tests in logical files matching service boundaries (lakebase, unity_catalog, model_serving, user)
- **FR-014**: System MUST include test documentation explaining test coverage and how to run tests
- **FR-017**: Integration tests MUST use shared read-only reference data fixtures for catalog metadata, user identities, and endpoint configurations
- **FR-018**: Integration tests MUST create isolated per-test data for all write and update operations (preferences, inference logs) with automatic cleanup
- **FR-015**: Integration tests MUST use mocked external Databricks APIs by default to run without external dependencies in CI/CD
- **FR-016**: System MUST provide optional "live" integration tests that can run against a configured test Databricks workspace for end-to-end validation
- **FR-019**: System MUST use pytest-cov to measure and report line/branch coverage for router and service files, targeting 90% coverage minimum

### Key Entities *(include if feature involves data)*

- **Integration Test Suite**: Collection of test files organized by service/feature area with consistent structure
- **Test Fixtures**: Reusable test setup including mock users, database sessions, and service clients; divided into session-scoped (read-only reference data) and function-scoped (isolated per-test data)
- **Test Data**: Read-only reference data (catalog metadata, user identities, endpoint configs) shared across tests plus isolated per-test data (preferences, logs) with automatic cleanup
- **Mock Services**: Simulated external dependencies (Databricks APIs, model endpoints) for isolated testing; supports both mocked responses (default) and optional live workspace connections
- **Test Results**: Coverage metrics, test execution logs, and failure reports

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Integration test coverage reaches at least 90% line/branch coverage in router and service files (server/routers/, server/services/) as measured by pytest-cov
- **SC-002**: All critical user workflows (authentication → data access → model inference → logging) have end-to-end integration tests
- **SC-003**: Integration test suite executes completely in under 5 minutes in CI/CD pipeline (no individual test timeouts, only suite-level limit)
- **SC-004**: Zero integration test failures on main branch over 30-day period after implementation
- **SC-005**: All error scenarios (400, 401, 403, 404, 503 responses) have corresponding integration tests
- **SC-006**: Developers can add new integration tests following established patterns in under 30 minutes
- **SC-007**: Integration tests catch at least 95% of API contract violations before code review
- **SC-008**: Test documentation clearly explains coverage gaps and prioritization for future tests
