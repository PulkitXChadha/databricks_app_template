# Tasks: Comprehensive Integration Test Coverage

**Feature**: 005-write-integration-test  
**Input**: Design documents from `/specs/005-write-integration-test/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/coverage-targets.yaml ✅

**TDD REQUIREMENT (Principle XII)**: This feature implements integration tests following Test Driven Development. Each test MUST be written to fail initially (RED), then implementation verified (GREEN), then refactored for quality (REFACTOR).

**IMPORTANT CONTEXT (C2 Clarification)**: The routers and services being tested (server/routers/*.py, server/services/*.py) were implemented in previous features (001-004). This feature adds comprehensive integration tests to validate existing code. Tests ARE the new implementation here. The GREEN phase verifies tests correctly validate the existing router/service implementations, not that we're writing routers after tests.

**Organization**: Tasks are grouped by user story to enable independent test implementation and coverage validation per story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Test Infrastructure)

**Purpose**: Initialize testing infrastructure and shared fixtures

- [ ] T001 Add pytest-cov to dev dependencies in pyproject.toml
- [ ] T002 Configure pytest coverage settings in pyproject.toml (source paths, omit patterns, report settings)
- [ ] T003 Update tests/conftest.py with session-scoped fixtures for TestUserIdentity (test-user-a, test-user-b)
- [ ] T004 Update tests/integration/conftest.py with session-scoped mock catalog metadata fixtures
- [ ] T005 [P] Add session-scoped mock model endpoint fixtures to tests/integration/conftest.py
- [ ] T006 [P] Add session-scoped mock detected schema fixtures to tests/integration/conftest.py
- [ ] T007 [P] Add session-scoped mock table data fixtures to tests/integration/conftest.py

---

## Phase 2: Foundational (Shared Test Utilities)

**Purpose**: Core test utilities and cleanup fixtures that ALL user stories depend on

**⚠️ CRITICAL**: No user story testing can begin until this phase is complete

- [ ] T008 Create cleanup fixture for user preferences in tests/integration/conftest.py (autouse, function-scoped)
- [ ] T009 [P] Create cleanup fixture for inference logs in tests/integration/conftest.py (autouse, function-scoped)
- [ ] T010 [P] Create cleanup fixture for schema detection events in tests/integration/conftest.py (autouse, function-scoped)
- [ ] T011 Create test data factory functions in tests/integration/conftest.py (create_test_preference, create_test_inference_log)
- [ ] T012 Add mock service patching utilities in tests/integration/conftest.py (mock_workspace_client, mock_lakebase_session)

**Checkpoint**: Foundation ready - user story test implementation can now begin in parallel

---

## Phase 3: User Story 1 - Complete Lakebase API Coverage (Priority: P1) 🎯 MVP

**Goal**: Comprehensive integration tests for all Lakebase (user preferences) API endpoints ensuring data isolation, error handling, and correct CRUD operations work end-to-end.

**Independent Test**: Execute CRUD operations on preferences endpoints with multiple users and verify data isolation, error responses, and state management.

**Success Criteria**: 
- 7 test scenarios implemented (scenarios 1-7 from spec.md)
- GET/POST/DELETE preferences endpoints covered
- User data isolation verified
- Error cases (503, 400) tested
- Coverage target: 90%+ for server/routers/lakebase.py and server/services/lakebase_service.py

### 🔴 RED Phase: Write Failing Tests for User Story 1 (TDD - MANDATORY)

**TDD Requirement**: Write these tests FIRST. All tests MUST FAIL initially before router/service implementation exists.

- [ ] T013 [US1] Create tests/integration/test_lakebase_full_flow.py with test class structure and imports
- [ ] T014 [US1] Write test: test_get_preferences_empty_when_no_data - Verify GET /api/lakebase/preferences returns empty list (MUST FAIL - RED)
- [ ] T015 [US1] Write test: test_preference_isolation_between_users - Verify User A cannot see User B's preferences (MUST FAIL - RED)
- [ ] T016 [US1] Write test: test_create_preference_with_valid_data - Verify POST /api/lakebase/preferences creates preference with 201 status (MUST FAIL - RED)
- [ ] T017 [US1] Write test: test_upsert_behavior_on_duplicate_key - Verify POST with same key updates preference (MUST FAIL - RED)
- [ ] T018 [US1] Write test: test_delete_preference_removes_data - Verify DELETE /api/lakebase/preferences/{key} removes preference (MUST FAIL - RED)
- [ ] T019 [US1] Write test: test_lakebase_not_configured_returns_503 - Verify 503 error with LAKEBASE_NOT_CONFIGURED when not configured (MUST FAIL - RED)
- [ ] T020 [US1] Write test: test_invalid_preference_key_returns_400 - Verify 400 error with validation details for invalid key format (MUST FAIL - RED)

**Verification**: Run `pytest tests/integration/test_lakebase_full_flow.py -v` - ALL 7 tests for US1 should be RED (failing with expected errors)

### 🟢 GREEN Phase: Verify Router/Service Implementation

**Note**: Router (server/routers/lakebase.py) and Service (server/services/lakebase_service.py) already exist. This phase verifies tests pass against existing implementation.

- [ ] T021 [US1] Run tests against server/routers/lakebase.py - Verify all endpoint tests pass (GREEN)
- [ ] T022 [US1] Run tests against server/services/lakebase_service.py - Verify all service logic tests pass (GREEN)
- [ ] T023 [US1] Generate coverage report for Lakebase router and service - Verify 90%+ coverage achieved

**Verification**: Run `pytest tests/integration/test_lakebase_full_flow.py --cov=server/routers/lakebase --cov=server/services/lakebase_service --cov-report=html` - ALL tests GREEN, coverage ≥90%

### 🔄 REFACTOR Phase: Improve Test Quality for User Story 1

**TDD Requirement**: Refactor tests for clarity and maintainability while keeping ALL tests GREEN.

**M6 Note**: Common refactor checklist applies to all user stories. See "Common Refactor Checklist" section below for standard improvements.

- [ ] T024 [US1] Extract common setup/teardown into class-level fixtures (tests stay GREEN)
- [ ] T025 [US1] Add docstrings with Given-When-Then format for all tests (tests stay GREEN)
- [ ] T026 [US1] Remove duplication in mock setup across tests (tests stay GREEN)
- [ ] T027 [US1] Add assertion messages for better failure diagnostics (tests stay GREEN)

**Checkpoint**: User Story 1 complete - Lakebase API fully tested with 90%+ coverage. ALL tests GREEN.

---

## Phase 4: User Story 2 - Complete Unity Catalog API Coverage (Priority: P1)

**Goal**: Full integration test coverage for all Unity Catalog endpoints ensuring catalog browsing, table querying, and permission enforcement work correctly across the entire data access flow.

**Independent Test**: Execute catalog/schema/table listing operations and query operations with different user permissions, verifying results and error handling.

**Success Criteria**: 
- 9 test scenarios implemented (scenarios 1-9 from spec.md)
- All Unity Catalog endpoints covered (catalogs, schemas, tables, query)
- Permission enforcement tested (403)
- Error cases (404, 400) tested
- Coverage target: 90%+ for server/routers/unity_catalog.py and server/services/unity_catalog_service.py

### 🔴 RED Phase: Write Failing Tests for User Story 2 (TDD - MANDATORY)

- [ ] T028 [US2] Create tests/integration/test_unity_catalog_full_flow.py with test class structure and imports
- [ ] T029 [US2] Write test: test_get_catalogs_returns_accessible_catalogs - Verify GET /api/unity-catalog/catalogs returns catalog names (MUST FAIL - RED)
- [ ] T030 [US2] Write test: test_get_schemas_for_catalog - Verify GET /api/unity-catalog/schemas returns schema names (MUST FAIL - RED)
- [ ] T031 [US2] Write test: test_get_table_names_for_schema - Verify GET /api/unity-catalog/table-names returns table names (MUST FAIL - RED)
- [ ] T032 [US2] Write test: test_get_tables_with_metadata - Verify GET /api/unity-catalog/tables returns DataSource objects with metadata (MUST FAIL - RED)
- [ ] T033 [US2] Write test: test_query_table_with_pagination - Verify GET /api/unity-catalog/query returns table data with pagination (MUST FAIL - RED)
- [ ] T034 [US2] Write test: test_query_table_with_filters - Verify POST /api/unity-catalog/query with filters returns filtered data (MUST FAIL - RED)
- [ ] T035 [US2] Write test: test_catalog_permission_denied_returns_403 - Verify 403 error with CATALOG_PERMISSION_DENIED when user lacks permissions (MUST FAIL - RED)
- [ ] T036 [US2] Write test: test_table_not_found_returns_404 - Verify 404 error with TABLE_NOT_FOUND for non-existent table (MUST FAIL - RED)
- [ ] T037 [US2] Write test: test_invalid_pagination_parameters_returns_400 - Verify 400 error with validation details for invalid limit/offset (MUST FAIL - RED)

**Verification**: Run `pytest tests/integration/test_unity_catalog_full_flow.py -v` - ALL 9 tests for US2 should be RED (failing)

### 🟢 GREEN Phase: Verify Router/Service Implementation

- [ ] T038 [US2] Run tests against server/routers/unity_catalog.py - Verify all endpoint tests pass (GREEN)
- [ ] T039 [US2] Run tests against server/services/unity_catalog_service.py - Verify all service logic tests pass (GREEN)
- [ ] T040 [US2] Generate coverage report for Unity Catalog router and service - Verify 90%+ coverage achieved

**Verification**: Run `pytest tests/integration/test_unity_catalog_full_flow.py --cov=server/routers/unity_catalog --cov=server/services/unity_catalog_service --cov-report=html` - ALL tests GREEN, coverage ≥90%

### 🔄 REFACTOR Phase: Improve Test Quality for User Story 2

- [ ] T041 [US2] Extract catalog metadata mocks into reusable fixtures (tests stay GREEN)
- [ ] T042 [US2] Add docstrings with Given-When-Then format for all tests (tests stay GREEN)
- [ ] T043 [US2] Standardize error assertion patterns across tests (tests stay GREEN)

**Checkpoint**: User Stories 1 AND 2 complete - Lakebase and Unity Catalog APIs fully tested. ALL tests GREEN.

---

## Phase 5: User Story 3 - Complete Model Serving API Coverage (Priority: P1)

**Goal**: Comprehensive integration tests for all Model Serving endpoints including endpoint discovery, schema detection, inference execution, and logging to ensure ML operations work end-to-end.

**Independent Test**: List endpoints, detect schemas, execute inference requests, and verify logs are persisted correctly.

**Success Criteria**: 
- 10 test scenarios implemented (scenarios 1-10 from spec.md)
- All Model Serving endpoints covered (list, get, schema, invoke, logs)
- Inference logging validated
- User data isolation in logs verified
- Error cases (404, 503, 400) tested
- Coverage target: 90%+ for server/routers/model_serving.py, server/services/model_serving_service.py, server/services/schema_detection_service.py

### 🔴 RED Phase: Write Failing Tests for User Story 3 (TDD - MANDATORY)

- [ ] T044 [US3] Create tests/integration/test_model_serving_full_flow.py with test class structure and imports
- [ ] T045 [US3] Write test: test_list_endpoints_returns_metadata - Verify GET /api/model-serving/endpoints returns list of endpoints (MUST FAIL - RED)
- [ ] T046 [US3] Write test: test_get_endpoint_details - Verify GET /api/model-serving/endpoints/{name} returns endpoint details (MUST FAIL - RED)
- [ ] T047 [US3] Write test: test_endpoint_not_found_returns_404 - Verify 404 error with ENDPOINT_NOT_FOUND for non-existent endpoint (MUST FAIL - RED)
- [ ] T048 [US3] Write test: test_detect_endpoint_schema - Verify GET /api/model-serving/endpoints/{name}/schema returns detected schema (MUST FAIL - RED)
- [ ] T049 [US3] Write test: test_invoke_model_returns_predictions - Verify POST /api/model-serving/invoke returns predictions with SUCCESS status (MUST FAIL - RED)
- [ ] T050 [US3] Write test: test_inference_log_persisted_to_database - Verify inference request logs persisted with user_id (MUST FAIL - RED)
- [ ] T051 [US3] Write test: test_get_inference_logs_with_user_isolation - Verify GET /api/model-serving/logs returns paginated logs for user only (MUST FAIL - RED)
- [ ] T052 [US3] Write test: test_model_timeout_returns_503 - Verify 503 error with MODEL_TIMEOUT when model takes too long (MUST FAIL - RED)
- [ ] T053 [US3] Write test: test_invalid_input_format_returns_400 - Verify 400 error with INVALID_INPUT for invalid payload (MUST FAIL - RED)
- [ ] T054 [US3] Write test: test_logs_without_lakebase_returns_503 - Verify 503 error with LAKEBASE_NOT_CONFIGURED when logs accessed without Lakebase (MUST FAIL - RED)

**Verification**: Run `pytest tests/integration/test_model_serving_full_flow.py -v` - ALL 10 tests for US3 should be RED (failing)

### 🟢 GREEN Phase: Verify Router/Service Implementation

- [ ] T055 [US3] Run tests against server/routers/model_serving.py - Verify all endpoint tests pass (GREEN)
- [ ] T056 [US3] Run tests against server/services/model_serving_service.py - Verify model serving logic tests pass (GREEN)
- [ ] T057 [US3] Run tests against server/services/schema_detection_service.py - Verify schema detection tests pass (GREEN)
- [ ] T058 [US3] Generate coverage report for Model Serving routers and services - Verify 90%+ coverage achieved

**Verification**: Run `pytest tests/integration/test_model_serving_full_flow.py --cov=server/routers/model_serving --cov=server/services/model_serving_service --cov=server/services/schema_detection_service --cov-report=html` - ALL tests GREEN, coverage ≥90%

### 🔄 REFACTOR Phase: Improve Test Quality for User Story 3

- [ ] T059 [US3] Extract model endpoint mocks into reusable fixtures (tests stay GREEN)
- [ ] T060 [US3] Add docstrings with Given-When-Then format for all tests (tests stay GREEN)
- [ ] T061 [US3] Standardize mock setup for WorkspaceClient across tests (tests stay GREEN)
- [ ] T062 [US3] Add helper functions for inference log validation (tests stay GREEN)

**Checkpoint**: User Stories 1, 2, AND 3 complete - All P1 APIs fully tested with 90%+ coverage. ALL tests GREEN.

---

## Phase 6: User Story 4 - Cross-Service Integration Flows (Priority: P2)

**Goal**: Integration tests that verify end-to-end workflows spanning multiple services (catalog → model inference → logging) to ensure the system works cohesively.

**Independent Test**: Execute multi-step workflows like authenticate → query catalog → detect model schema → invoke model → verify logs, ensuring data flows correctly across services.

**Success Criteria**: 
- 4 test scenarios implemented (scenarios 1-4 from spec.md)
- Multi-service workflows validated
- Cross-service data isolation verified
- End-to-end user journeys tested

### 🔴 RED Phase: Write Failing Tests for User Story 4 (TDD - MANDATORY)

- [ ] T063 [US4] Create tests/integration/test_cross_service_workflows.py with test class structure and imports
- [ ] T064 [US4] Write test: test_end_to_end_catalog_to_inference_workflow - Verify complete workflow from catalog query to model inference (MUST FAIL - RED)
- [ ] T065 [US4] Write test: test_preferences_customize_catalog_queries - Verify user preferences affect Unity Catalog query behavior (MUST FAIL - RED)
- [ ] T066 [US4] Write test: test_concurrent_users_maintain_isolation - Verify data isolation maintained across services for multiple users (MUST FAIL - RED)
- [ ] T067 [US4] Write test: test_inference_logs_persist_across_workflow - Verify inference history correctly persisted and retrievable (MUST FAIL - RED)

**Verification**: Run `pytest tests/integration/test_cross_service_workflows.py -v` - ALL 4 tests for US4 should be RED (failing)

### 🟢 GREEN Phase: Verify Cross-Service Integration

- [ ] T068 [US4] Run cross-service workflow tests - Verify all multi-service scenarios pass (GREEN)
- [ ] T069 [US4] Validate data flow integrity across service boundaries (GREEN)
- [ ] T070 [US4] Generate coverage report showing cross-service test coverage

**Verification**: Run `pytest tests/integration/test_cross_service_workflows.py -v` - ALL tests GREEN

### 🔄 REFACTOR Phase: Improve Test Quality for User Story 4

- [ ] T071 [US4] Extract common workflow setup into helper functions (tests stay GREEN)
- [ ] T072 [US4] Add docstrings with Given-When-Then format for all tests (tests stay GREEN)
- [ ] T073 [US4] Improve test readability by breaking complex workflows into steps (tests stay GREEN)

**Checkpoint**: User Story 4 complete - Cross-service workflows validated. ALL tests GREEN.

---

## Phase 7: User Story 5 - Error Recovery and Resilience Testing (Priority: P2)

**Goal**: Integration tests that verify error recovery mechanisms, graceful degradation, and retry logic work correctly when downstream services fail or are unavailable.

**Independent Test**: Simulate various failure scenarios (database unavailable, model timeout, permission errors) and verify appropriate error responses and recovery behavior.

**Success Criteria**: 
- 4 test scenarios implemented (scenarios 1-4 from spec.md)
- Failure scenarios validated
- Error recovery mechanisms tested
- Graceful degradation verified

### 🔴 RED Phase: Write Failing Tests for User Story 5 (TDD - MANDATORY)

- [ ] T074 [US5] Create tests/integration/test_error_recovery.py with test class structure and imports
- [ ] T075 [US5] Write test: test_database_unavailable_returns_503_with_retry - Verify 503 error with DATABASE_UNAVAILABLE and retry_after on DB failure (MUST FAIL - RED)
- [ ] T076 [US5] Write test: test_transient_model_service_failure_recovery - Verify subsequent request succeeds after transient error (MUST FAIL - RED)
- [ ] T077 [US5] Write test: test_permission_revoked_mid_session - Verify 403 error returned immediately when permissions change (MUST FAIL - RED)
- [ ] T078 [US5] Write test: test_corrupted_data_handled_gracefully - Verify system handles corrupted database data without crashing (MUST FAIL - RED)

**Verification**: Run `pytest tests/integration/test_error_recovery.py -v` - ALL 4 tests for US5 should be RED (failing)

### 🟢 GREEN Phase: Verify Error Recovery Implementation

- [ ] T079 [US5] Run error recovery tests - Verify all failure scenarios handled correctly (GREEN)
- [ ] T080 [US5] Validate error responses include appropriate status codes and messages (GREEN)
- [ ] T081 [US5] Generate coverage report for error handling paths

**Verification**: Run `pytest tests/integration/test_error_recovery.py -v` - ALL tests GREEN

### 🔄 REFACTOR Phase: Improve Test Quality for User Story 5

- [ ] T082 [US5] Extract failure simulation utilities into conftest.py (tests stay GREEN)
- [ ] T083 [US5] Add docstrings with Given-When-Then format for all tests (tests stay GREEN)
- [ ] T084 [US5] Standardize error response validation across tests (tests stay GREEN)

**Checkpoint**: User Story 5 complete - Error recovery validated. ALL tests GREEN.

---

## Phase 8: User Story 6 - Pagination and Large Dataset Handling (Priority: P3)

**Goal**: Integration tests that verify pagination works correctly across all endpoints that return lists, ensuring performance and data correctness with large datasets.

**Independent Test**: Create large datasets, then verify pagination parameters (limit, offset) work correctly and consistently across all list endpoints.

**Success Criteria**: 
- 4 test scenarios implemented (scenarios 1-4 from spec.md)
- Pagination validated for preferences, logs, and queries
- Large dataset handling tested
- Edge cases (offset edge cases) validated

### 🔴 RED Phase: Write Failing Tests for User Story 6 (TDD - MANDATORY)

- [ ] T085 [US6] Create tests/integration/test_pagination_comprehensive.py with test class structure and imports
- [ ] T086 [US6] Write test: test_paginate_200_preferences_without_gaps - Verify pagination through 200 preferences with limit=50 (MUST FAIL - RED)
- [ ] T087 [US6] Write test: test_paginate_500_inference_logs_consistent_order - Verify pagination with various limit/offset returns correct records (MUST FAIL - RED)
- [ ] T088 [US6] Write test: test_paginate_large_catalog_table_performance - Verify query performance remains acceptable with pagination (MUST FAIL - RED)
- [ ] T089 [US6] Write test: test_edge_case_pagination_parameters - Verify correct results with edge case pagination (offset=0 limit=1, offset=999 limit=1000) (MUST FAIL - RED)

**Verification**: Run `pytest tests/integration/test_pagination_comprehensive.py -v` - ALL 4 tests for US6 should be RED (failing)

### 🟢 GREEN Phase: Verify Pagination Implementation

- [ ] T090 [US6] Run pagination tests - Verify all pagination scenarios work correctly (GREEN)
- [ ] T091 [US6] Validate pagination performance meets requirements (under 5-minute suite limit) (GREEN)
- [ ] T092 [US6] Generate coverage report for pagination logic in routers/services

**Verification**: Run `pytest tests/integration/test_pagination_comprehensive.py -v` - ALL tests GREEN

### 🔄 REFACTOR Phase: Improve Test Quality for User Story 6

- [ ] T093 [US6] Extract large dataset creation into fixture/factory functions (tests stay GREEN)
- [ ] T094 [US6] Add docstrings with Given-When-Then format for all tests (tests stay GREEN)
- [ ] T095 [US6] Optimize test data cleanup for large datasets (tests stay GREEN)

**Checkpoint**: User Story 6 complete - Pagination validated. ALL tests GREEN.

---

## Phase 9: User Story 7 - Concurrent Request Handling (Priority: P3)

**Goal**: Integration tests that verify the system handles concurrent requests correctly, ensuring no race conditions, data corruption, or deadlocks occur under light load.

**Independent Test**: Execute multiple simultaneous requests to the same endpoints and verify data integrity, response correctness, and no system crashes.

**Concurrency Level (C3 Specification)**: All concurrency tests use **exactly 7 concurrent requests** (midpoint of 5-10 range specified in spec.md). This ensures reproducibility and consistent performance validation.

**Success Criteria**: 
- 4 test scenarios implemented (scenarios 1-4 from spec.md)
- Concurrent writes validated (no data loss)
- Concurrent reads validated (no interference)
- Basic thread safety verified with 7 concurrent requests

### 🔴 RED Phase: Write Failing Tests for User Story 7 (TDD - MANDATORY)

- [ ] T096 [US7] Create tests/integration/test_concurrency.py with test class structure and imports
- [ ] T097 [US7] Write test: test_concurrent_preference_saves_no_data_loss - Verify 7 concurrent users saving different preferences (MUST FAIL - RED)
- [ ] T098 [US7] Write test: test_concurrent_model_inference_all_complete - Verify 7 concurrent inference requests complete successfully (MUST FAIL - RED)
- [ ] T099 [US7] Write test: test_concurrent_read_write_same_preference_consistent - Verify 7 concurrent reads/writes to same key maintain consistency (MUST FAIL - RED)
- [ ] T100 [US7] Write test: test_concurrent_catalog_queries_no_interference - Verify 7 users querying same table return correct results (MUST FAIL - RED)

**Verification**: Run `pytest tests/integration/test_concurrency.py -v` - ALL 4 tests for US7 should be RED (failing)

### 🟢 GREEN Phase: Verify Concurrency Handling

- [ ] T101 [US7] Run concurrency tests - Verify all concurrent scenarios maintain data integrity (GREEN)
- [ ] T102 [US7] Validate no race conditions or deadlocks occur under load (GREEN)
- [ ] T103 [US7] Generate coverage report for concurrent request handling

**Verification**: Run `pytest tests/integration/test_concurrency.py -v` - ALL tests GREEN

### 🔄 REFACTOR Phase: Improve Test Quality for User Story 7

- [ ] T104 [US7] Extract concurrent request execution utilities into conftest.py (tests stay GREEN)
- [ ] T105 [US7] Add docstrings with Given-When-Then format for all tests (tests stay GREEN)
- [ ] T106 [US7] Improve concurrency test readability and assertions (tests stay GREEN)

**Checkpoint**: All user stories complete - All 7 user stories validated with 90%+ coverage. ALL tests GREEN.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements that affect multiple user stories and overall test suite quality

- [ ] T107 Run full integration test suite - Verify all tests pass and coverage meets 90% threshold
- [ ] T108 Generate comprehensive coverage report (terminal + HTML + XML) for all routers and services
- [ ] T109 [P] Validate test suite executes in under 300 seconds (5:00 max, fail at 301+) per SC-003 and M7 clarification
- [ ] T110 [P] Review HTML coverage report and identify any remaining coverage gaps
- [ ] T111 Add pytest markers (integration, slow) to test files for selective test execution
- [ ] T112 Update quickstart.md with actual test commands and examples (if needed)
- [ ] T113 [P] Add GitHub Actions workflow for CI/CD integration test execution (optional)
- [ ] T114 Update CLAUDE.md with integration testing patterns and pytest-cov usage (if needed)
- [ ] T115 Validate all error scenarios (400, 401, 403, 404, 503) are tested (SC-005 requirement)
- [ ] T116 Run final coverage validation: `pytest tests/integration/ --cov=server/routers --cov=server/services --cov-fail-under=90`

### Edge Case Coverage (C1 Remediation)

**Purpose**: Add tests for 8 edge cases defined in spec.md:272-281 that were missing from user story phases

- [ ] T117 [P] [Edge Cases] Write test: test_delete_nonexistent_preference_returns_404 - Verify 404 with appropriate message when deleting non-existent preference
- [ ] T118 [P] [Edge Cases] Write test: test_large_preference_value_rejected - Verify 10MB JSON preference value rejected with 400 and size limit message
- [ ] T119 [P] [Edge Cases] Write test: test_pagination_offset_exceeds_total_returns_empty - Verify empty list (not error) when offset > total record count
- [ ] T120 [P] [Edge Cases] Write test: test_timezone_consistency_utc_across_services - Verify all timestamp fields use UTC consistently across all APIs
- [ ] T121 [P] [Edge Cases] Write test: test_model_inference_input_size_limit - Verify inference input exceeding size limits returns 400 with validation message
- [ ] T122 [P] [Edge Cases] Write test: test_schema_detection_no_info_available - Verify schema detection returns "unknown" type with helpful message when no schema info
- [ ] T123 [P] [Edge Cases] Write test: test_concurrent_preference_update_last_write_wins - Verify last write wins and no data corruption with concurrent updates to same key
- [ ] T124 [P] [Edge Cases] Write test: test_special_characters_unicode_in_names - Verify proper handling of special chars/Unicode in table names, preference keys, endpoint names

### Live Mode Implementation (H1 Remediation - FR-016)

**Purpose**: Implement optional TEST_MODE=live for end-to-end validation against real Databricks workspace

- [ ] T125 [Live Mode] Implement TEST_MODE environment variable check in tests/integration/conftest.py
- [ ] T126 [Live Mode] Create conditional fixtures for live vs mock WorkspaceClient based on TEST_MODE
- [ ] T127 [Live Mode] Add pytest skipif markers for tests that require live workspace (e.g., @pytest.mark.skipif(os.getenv("TEST_MODE") != "live"))
- [ ] T128 [Live Mode] Document live mode usage, prerequisites, and configuration in quickstart.md (Databricks CLI setup, workspace access)

### Success Criteria Validation (H2-H5 Remediation)

**Purpose**: Add validation tasks for success criteria SC-002, SC-004, SC-006, SC-007

- [ ] T129 [SC-002] Validate all critical workflows have e2e tests - Create checklist: auth→catalog→inference→logging workflow tested
- [ ] T130 [SC-004] Setup CI/CD monitoring for zero test failures over 30 days (or document as post-implementation operational concern)
- [ ] T131 [SC-006] Validate developer experience - Conduct timed exercise: new developer adds test in <30 minutes using quickstart.md
- [ ] T132 [SC-007] Measure contract violation detection rate - Validate tests catch 95%+ of API contract violations (or mark as future metric)

### Optional Enhancements

- [ ] T133 [M8] [Optional] Implement post-deployment smoke tests for deployed app endpoint validation (per contracts/coverage-targets.yaml:204-206)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-9)**: All depend on Foundational phase completion
  - User Stories 1, 2, 3 (P1 priority) should be completed first
  - User Stories 4, 5 (P2 priority) should be completed next
  - User Stories 6, 7 (P3 priority) can be completed last
  - All user stories CAN proceed in parallel (if staffed) after Foundational phase
- **Polish (Phase 10)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1) - Lakebase**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1) - Unity Catalog**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (P1) - Model Serving**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 4 (P2) - Cross-Service**: Can start after Foundational - Integrates US1, US2, US3 but tests independently
- **User Story 5 (P2) - Error Recovery**: Can start after Foundational - Tests across all services
- **User Story 6 (P3) - Pagination**: Can start after Foundational - Tests across all services
- **User Story 7 (P3) - Concurrency**: Can start after Foundational - Tests across all services

### Within Each User Story (TDD Phases)

**TDD Workflow (MANDATORY - Principle XII):**
1. **RED Phase**: Write all tests first - ALL MUST FAIL initially
2. **GREEN Phase**: Verify tests pass against existing implementation (routers/services already exist)
3. **REFACTOR Phase**: Improve test code quality while keeping tests GREEN

**Note**: For this feature, tests ARE the implementation. The routers and services being tested already exist, so the GREEN phase verifies tests correctly validate existing code.

**Implementation Order Within Each Phase:**
- RED: Write all test functions for the user story
- GREEN: Run tests, verify they pass against existing implementation
- REFACTOR: Improve test quality (fixtures, docstrings, readability)
- Verify coverage meets 90% threshold before moving to next story

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T005, T006, T007)
- All Foundational cleanup fixtures marked [P] can run in parallel (T009, T010)
- Once Foundational phase completes, all user stories CAN start in parallel (if team capacity allows):
  - Developer A: User Story 1 (Lakebase tests)
  - Developer B: User Story 2 (Unity Catalog tests)
  - Developer C: User Story 3 (Model Serving tests)
  - etc.
- Within Polish phase, tasks marked [P] can run in parallel (T109, T110, T113)

---

## Parallel Example: After Foundational Phase Complete

```bash
# All P1 user stories can start in parallel:

# Terminal 1: User Story 1 - Lakebase tests
cd tests/integration/
# Create test_lakebase_full_flow.py with 7 test scenarios

# Terminal 2: User Story 2 - Unity Catalog tests
cd tests/integration/
# Create test_unity_catalog_full_flow.py with 9 test scenarios

# Terminal 3: User Story 3 - Model Serving tests
cd tests/integration/
# Create test_model_serving_full_flow.py with 10 test scenarios
```

---

## Implementation Strategy

### MVP First (User Stories 1, 2, 3 - All P1)

1. Complete Phase 1: Setup (pytest-cov, fixtures)
2. Complete Phase 2: Foundational (cleanup fixtures, test utilities) - **CRITICAL - blocks all stories**
3. Complete Phase 3: User Story 1 (Lakebase tests)
4. Complete Phase 4: User Story 2 (Unity Catalog tests)
5. Complete Phase 5: User Story 3 (Model Serving tests)
6. **VALIDATE MVP**: Run coverage validation - ALL P1 APIs should have 90%+ coverage
7. Generate coverage reports and review gaps

### Incremental Delivery

1. Complete Setup + Foundational → Test infrastructure ready
2. Add User Story 1 → Validate independently → 90%+ coverage on Lakebase
3. Add User Story 2 → Validate independently → 90%+ coverage on Unity Catalog
4. Add User Story 3 → Validate independently → 90%+ coverage on Model Serving
5. **MVP CHECKPOINT** - All P1 APIs covered
6. Add User Story 4 → Validate cross-service workflows
7. Add User Story 5 → Validate error recovery
8. Add User Story 6 → Validate pagination
9. Add User Story 7 → Validate concurrency
10. Complete Polish phase → Full test suite with 90%+ overall coverage

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (Phases 1-2)
2. Once Foundational is done:
   - Developer A: User Story 1 (Lakebase - 7 tests)
   - Developer B: User Story 2 (Unity Catalog - 9 tests)
   - Developer C: User Story 3 (Model Serving - 10 tests)
3. After P1 stories complete:
   - Developer A: User Story 4 (Cross-service - 4 tests)
   - Developer B: User Story 5 (Error recovery - 4 tests)
   - Developer C: User Story 6 (Pagination - 4 tests) + User Story 7 (Concurrency - 4 tests)
4. Team completes Polish phase together

---

## Coverage Validation Commands

### Run All Integration Tests with Coverage

```bash
# Full coverage report (terminal + HTML + XML)
pytest tests/integration/ \
  --cov=server/routers \
  --cov=server/services \
  --cov-report=term \
  --cov-report=html \
  --cov-report=xml

# View HTML report
open htmlcov/index.html  # macOS
```

### Run Specific User Story Tests with Coverage

```bash
# User Story 1 - Lakebase
pytest tests/integration/test_lakebase_full_flow.py \
  --cov=server/routers/lakebase \
  --cov=server/services/lakebase_service \
  --cov-report=term

# User Story 2 - Unity Catalog
pytest tests/integration/test_unity_catalog_full_flow.py \
  --cov=server/routers/unity_catalog \
  --cov=server/services/unity_catalog_service \
  --cov-report=term

# User Story 3 - Model Serving
pytest tests/integration/test_model_serving_full_flow.py \
  --cov=server/routers/model_serving \
  --cov=server/services/model_serving_service \
  --cov=server/services/schema_detection_service \
  --cov-report=term
```

### CI/CD Validation (with failure threshold)

```bash
# Fail if coverage < 90% (SC-001 requirement)
pytest tests/integration/ \
  --cov=server/routers \
  --cov=server/services \
  --cov-report=xml \
  --cov-fail-under=90
```

---

## Common Refactor Checklist (M6 Reference)

**Purpose**: Standard refactoring improvements that apply to ALL user story REFACTOR phases to avoid task duplication.

**Use this checklist for tasks T024-T027, T041-T043, T059-T062, T071-T073, T082-T084, T093-T095, T104-T106:**

1. **Extract Common Patterns**
   - Move repeated setup/teardown logic into class-level or module-level fixtures
   - Create helper functions for common assertion patterns
   - Consolidate mock setup into reusable fixtures

2. **Documentation**
   - Add docstrings to all test functions using Given-When-Then format
   - Document complex test scenarios with inline comments
   - Add module-level docstrings explaining test file purpose

3. **Improve Readability**
   - Use descriptive variable names (avoid generic `data`, `result`, `response`)
   - Break complex test logic into smaller helper functions
   - Add assertion messages for better failure diagnostics

4. **Remove Duplication**
   - Identify repeated mock configurations and extract to fixtures
   - Consolidate similar test scenarios using parametrization
   - Share test data factories across test files

5. **Verify Quality**
   - Run tests after each refactoring step to ensure GREEN
   - Check coverage remains at 90%+ after refactoring
   - Validate test execution time hasn't increased significantly

**Reminder**: All refactoring MUST keep tests GREEN. Run `pytest <test_file> -v` after each change.

---

## Notes

- **[P] tasks** = different files, no dependencies, can run in parallel
- **[Story] label** maps task to specific user story for traceability (US1, US2, US3, etc.)
- **Tests ARE the implementation** for this feature - write comprehensive integration tests
- **TDD MANDATORY** (Principle XII): Always follow RED-GREEN-REFACTOR cycle
  - RED: Write test first, verify it FAILS (no implementation yet OR incorrect implementation)
  - GREEN: Verify test passes against existing router/service implementation
  - REFACTOR: Improve test code quality while keeping tests GREEN
- **Coverage target**: 90% minimum for server/routers/ and server/services/ (SC-001)
- **Performance target**: Full test suite under 5 minutes (SC-003)
- **Each user story is independently completable and testable**
- Commit after each TDD phase (RED, GREEN, REFACTOR) or logical group
- Stop at any checkpoint to validate coverage independently
- Run coverage reports frequently to identify gaps
- Focus on critical paths and edge cases (don't aim for 100% coverage)

---

## Summary

**Total Tasks**: 133 tasks across 10 phases (updated after /speckit.analyze remediation)

**Task Breakdown by Phase**:
- Phase 1 (Setup): 7 tasks
- Phase 2 (Foundational): 5 tasks
- Phase 3 (US1 - Lakebase): 15 tasks (7 test scenarios)
- Phase 4 (US2 - Unity Catalog): 16 tasks (9 test scenarios)
- Phase 5 (US3 - Model Serving): 19 tasks (10 test scenarios)
- Phase 6 (US4 - Cross-Service): 11 tasks (4 test scenarios)
- Phase 7 (US5 - Error Recovery): 11 tasks (4 test scenarios)
- Phase 8 (US6 - Pagination): 11 tasks (4 test scenarios)
- Phase 9 (US7 - Concurrency): 11 tasks (4 test scenarios)
- Phase 10 (Polish): 27 tasks (includes edge cases, live mode, success criteria validation)

**Test Scenarios by User Story**:
- User Story 1: 7 scenarios (Lakebase API)
- User Story 2: 9 scenarios (Unity Catalog API)
- User Story 3: 10 scenarios (Model Serving API)
- User Story 4: 4 scenarios (Cross-Service workflows)
- User Story 5: 4 scenarios (Error Recovery)
- User Story 6: 4 scenarios (Pagination)
- User Story 7: 4 scenarios (Concurrency)
- **Total: 42 integration test scenarios**

**Parallel Opportunities**:
- Phase 1: 3 fixture creation tasks can run in parallel (T005-T007)
- Phase 2: 2 cleanup fixture tasks can run in parallel (T009-T010)
- Phases 3-9: All user stories can run in parallel after Foundational phase complete
- Within each user story RED phase: All test writing tasks can proceed together
- Phase 10: Multiple validation tasks can run in parallel (T109-T110, T113, T117-T128 edge cases and live mode)

**MVP Scope** (Suggested):
- Phases 1, 2: Setup + Foundational (MUST complete) - 12 tasks
- Phases 3, 4, 5: User Stories 1, 2, 3 (All P1 - core API coverage) - 50 tasks
- Phase 10 (Core validation only): T107-T116 - 10 tasks
- **Estimated 72 tasks for MVP** (covers all P1 user stories with 90%+ coverage, excludes edge cases/live mode)

**Success Criteria Validation**:
- SC-001: 90% line/branch coverage in routers/services (validated in Phase 10, Task T108)
- SC-003: Test suite under 5 minutes (validated in Phase 10, Task T109)
- SC-005: All error scenarios tested (validated in Phase 10, Task T115)
- SC-007: Integration tests catch API contract violations (validated by contract test structure)
- SC-008: Test documentation complete (quickstart.md already exists)

