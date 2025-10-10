# Tasks: Fix API Authentication and Implement OBO Authentication

**Input**: Design documents from `/specs/002-fix-api-authentication/`  
**Prerequisites**: plan.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅  
**Feature Branch**: `002-fix-api-authentication`  
**Target**: Fix "more than one authorization method configured" error and implement On-Behalf-Of (OBO) authentication

---

## Execution Summary

This feature fixes authentication failures in deployed Databricks Apps by implementing:
1. **Dual Authentication**: OBO for user operations, service principal for Lakebase
2. **User Identity Tracking**: Add user_id to database tables for data isolation
3. **Exponential Backoff Retry**: Handle transient authentication failures
4. **Observability**: Structured logging and metrics for auth operations

**Tech Stack**: Python 3.11+, FastAPI 0.104+, Databricks SDK 0.59.0, SQLAlchemy 2.0+, React 18.3, TypeScript 5.2+

---

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- All file paths are absolute from repository root: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/`

---

## Phase 3.1: Setup & Preparation

- [ ] **T001** Verify Databricks SDK version is pinned to 0.59.0 in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/requirements.txt`
  - Requirement: FR-024, NFR-013
  - Action: Confirm `databricks-sdk==0.59.0` (exact version, not range like >=0.59.0 or ~=0.59.0)
  - Validation: Grep for exact string "databricks-sdk==0.59.0" in requirements.txt
  - Historical Context: Minimum SDK 0.33.0 introduced auth_type parameter (not a validation criterion - we use 0.59.0)

- [ ] **T002** Create database migration file `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/migrations/versions/003_add_user_id_to_tables.py`
  - Add user_id column to user_preferences table (VARCHAR(255), NOT NULL, indexed)
  - Add user_id column to model_inference_logs table (VARCHAR(255), NOT NULL, indexed)
  - Create unique index on user_preferences(user_id, key)
  - Create index on model_inference_logs(user_id)
  - Include upgrade() and downgrade() functions
  - Requirement: FR-010, FR-013

- [ ] **T003** Run database migration to add user_id columns
  - Command: `cd /Users/pulkit.chadha/Documents/Projects/databricks-app-template && uv run alembic upgrade head`
  - Verify: Check that user_id columns and indexes exist in both tables
  - Requirement: FR-010

---

## Phase 3.2: Contract Tests (TDD - Must Fail Before Implementation)

**Important**: These tests MUST be modified first and MUST fail initially. This is Test-Driven Development (TDD).

- [ ] **T004** [P] Modify User API contract tests in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/tests/contract/test_user_contract.py`
  - Update test_get_current_user() to require X-Forwarded-Access-Token header
  - Update test_get_workspace_info() to require X-Forwarded-Access-Token header
  - Add assertion: response.auth_method == "obo"
  - Add negative test: verify 401 when header missing (local dev should fallback)
  - Contract: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/specs/002-fix-api-authentication/contracts/user_api.yaml`
  - Expected: Tests FAIL (implementation not done yet)

- [ ] **T005** [P] Modify Model Serving API contract tests in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/tests/contract/test_model_serving_contract.py`
  - Update test_list_endpoints() to require X-Forwarded-Access-Token header
  - Update test_get_endpoint() to require X-Forwarded-Access-Token header
  - Add assertion: verify SDK uses auth_type="pat"
  - Contract: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/specs/002-fix-api-authentication/contracts/model_serving_api.yaml`
  - Expected: Tests FAIL (implementation not done yet)

- [ ] **T006** [P] Modify Unity Catalog API contract tests in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/tests/contract/test_unity_catalog_contract.py`
  - Update test_list_catalogs() to require X-Forwarded-Access-Token header
  - Update test_list_schemas() to require X-Forwarded-Access-Token header
  - Update test_list_tables() to require X-Forwarded-Access-Token header
  - Add multi-user permission test: verify different users see different catalogs
  - Contract: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/specs/002-fix-api-authentication/contracts/unity_catalog_api.yaml`
  - Expected: Tests FAIL (implementation not done yet)

- [ ] **T007** Run all contract tests to verify they FAIL
  - Command: `cd /Users/pulkit.chadha/Documents/Projects/databricks-app-template && uv run pytest tests/contract/ -v`
  - Expected: All modified tests FAIL (no implementation yet)
  - Success: Failing tests confirm contract requirements
  - Requirement: TDD methodology

---

## Phase 3.3: Authentication Utilities (Core Foundation)

- [ ] **T008** [P] Implement get_user_token() FastAPI dependency in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/lib/auth.py`
  - Extract token from X-Forwarded-Access-Token header
  - Return Optional[str] (None if header absent)
  - Add structured logging: log token presence (not token value)
  - Type hints: `async def get_user_token(request: Request) -> str | None:`
  - Requirement: FR-001, FR-017

- [ ] **T009** [P] Implement get_user_identity() function in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/lib/auth.py`
  - Accept user_token parameter
  - Create WorkspaceClient with token and auth_type="pat"
  - Call client.current_user.me() to extract user identity
  - Return dict with user_id, email, username, display_name
  - Handle errors: invalid token, network issues
  - Type hints: `async def get_user_identity(user_token: str) -> dict:`
  - Requirement: FR-002, FR-003

- [ ] **T010** [P] Implement retry_with_backoff() decorator in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/lib/auth.py`
  - Exponential backoff: 100ms, 200ms, 400ms (3 attempts)
  - Total timeout: 5 seconds maximum
  - Detect HTTP 429 (rate limit) and fail immediately without retry
  - Log retry attempts with correlation_id
  - Type hints: `async def retry_with_backoff(func: Callable, max_attempts: int = 3, base_delay: float = 0.1, max_timeout: float = 5.0):`
  - Requirement: FR-018, FR-019, NFR-006

- [ ] **T011** [P] Implement create_obo_client() factory in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/lib/auth.py`
  - Accept user_token parameter
  - Create WorkspaceClient with explicit auth_type="pat"
  - Return configured WorkspaceClient instance
  - Add logging: auth_method="obo", token_present=True
  - Type hints: `def create_obo_client(user_token: str) -> WorkspaceClient:`
  - Requirement: FR-003

- [ ] **T012** [P] Implement create_service_principal_client() factory in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/lib/auth.py`
  - Read DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET from environment
  - Create WorkspaceClient with explicit auth_type="oauth-m2m"
  - Return configured WorkspaceClient instance
  - Add logging: auth_method="service_principal"
  - Never log client_secret (NFR-004)
  - Type hints: `def create_service_principal_client() -> WorkspaceClient:`
  - Requirement: FR-004, FR-011

- [ ] **T013** [P] Create unit tests for auth utilities in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/tests/unit/test_auth.py`
  - Test get_user_token(): header present, absent, malformed
  - Test get_user_identity(): valid token, invalid token, network error
  - Test retry_with_backoff(): success on retry, timeout, rate limit
  - Test SDK client factories: correct auth_type configuration
  - Mock WorkspaceClient to avoid real API calls
  - Requirement: Testing strategy

---

## Phase 3.4: Service Layer Modifications

- [ ] **T014** [P] Modify UserService in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/services/user_service.py`
  - Add user_token parameter to __init__()
  - Use create_obo_client(user_token) for all operations
  - Update get_current_user() to use OBO client
  - Apply retry_with_backoff() to API calls
  - Add structured logging with user_id
  - Type hints: `def __init__(self, user_token: str):`
  - Requirement: FR-005, FR-006

- [ ] **T015** [P] Modify UnityCatalogService in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/services/unity_catalog_service.py`
  - Add user_token parameter to __init__()
  - Use create_obo_client(user_token) for all operations
  - Update list_catalogs(), list_schemas(), list_tables() to use OBO client
  - Apply retry_with_backoff() to API calls
  - Add structured logging with user_id
  - Type hints: `def __init__(self, user_token: str):`
  - Requirement: FR-007, FR-008

- [ ] **T016** [P] Modify ModelServingService in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/services/model_serving_service.py`
  - Add user_token parameter to __init__()
  - Use create_obo_client(user_token) for all operations
  - Update list_endpoints(), get_endpoint() to use OBO client
  - Apply retry_with_backoff() to API calls
  - Add structured logging with user_id
  - Type hints: `def __init__(self, user_token: str):`
  - Requirement: FR-009

- [ ] **T017** Verify LakebaseService uses service principal only in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/services/lakebase_service.py`
  - **Acceptance Criteria**:
    1. ✅ LakebaseService class has NO user_token parameter in __init__()
    2. ✅ Database connection creation uses create_service_principal_client() with auth_type="oauth-m2m"
    3. ✅ All user-scoped methods (get_preferences, set_preference, get_inference_logs) accept user_id parameter
    4. ✅ FR-014 validation implemented: user_id presence check before executing queries (raise ValueError if missing)
    5. ✅ FR-013 compliance: All SELECT queries include WHERE user_id = ? clause (review SQL generation)
    6. ✅ All INSERT queries include user_id in column list and values
    7. ✅ Type hints present: Methods typed as `async def get_preferences(self, user_id: str) -> list[UserPreference]:`
  - Requirement: FR-011, FR-013, FR-014

---

## Phase 3.5: Database Model Updates

- [ ] **T018** [P] Update UserPreference model in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/models/user_preference.py`
  - Add user_id field: Column(String(255), nullable=False, index=True)
  - Add unique constraint: Index("ix_user_preferences_user_id_key", "user_id", "key", unique=True)
  - Update __repr__() to include user_id
  - Requirement: Data model

- [ ] **T019** [P] Update ModelInferenceLog model in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/models/model_inference.py`
  - Add user_id field: Column(String(255), nullable=False, index=True)
  - Add index: Index("ix_model_inference_logs_user_id", "user_id")
  - Update __repr__() to include user_id
  - Requirement: Data model

- [ ] **T020** Verify UserSession model has user_id in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/models/user_session.py`
  - Confirm user_id field exists with proper index
  - No changes needed if field already exists
  - Requirement: Data model

---

## Phase 3.6: Router Modifications (Endpoint Implementation)

**Note**: These modify same files, so NOT parallel

- [ ] **T021** Update /api/user/me endpoint in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/routers/user.py`
  - Add get_user_token dependency: `user_token: str | None = Depends(get_user_token)`
  - Pass user_token to UserService
  - Handle fallback: if user_token is None, use service principal (FR-016)
  - Add structured logging: auth_method, token_present, user_id
  - Update response to include auth_method field
  - Requirement: FR-001, FR-002, FR-016, FR-021

- [ ] **T022** Update /api/user/me/workspace endpoint in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/routers/user.py`
  - Add get_user_token dependency
  - Pass user_token to UserService
  - Handle fallback to service principal
  - Add structured logging
  - Requirement: FR-001, FR-002

- [ ] **T023** Configure upstream service timeouts for transparent loading state
  - Set timeout parameter to 30 seconds minimum for all Databricks API calls (NFR-010)
  - Apply to Unity Catalog service methods (list_catalogs, list_schemas, list_tables)
  - Apply to Model Serving service methods (list_endpoints, get_endpoint)
  - Implement transparent loading state behavior: maintain loading indicator until service recovers or timeout reached (FR-023)
  - Location: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/services/unity_catalog_service.py`, `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/services/model_serving_service.py`
  - Requirement: FR-023, NFR-010

- [ ] **T024** Update /api/model-serving/endpoints endpoint in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/routers/model_serving.py`
  - Add get_user_token dependency
  - Pass user_token to ModelServingService
  - Add pagination parameters: limit, offset
  - Add structured logging with user_id
  - Requirement: FR-009

- [ ] **T025** Update /api/model-serving/endpoints/{endpoint_name} endpoint in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/routers/model_serving.py`
  - Add get_user_token dependency
  - Pass user_token to ModelServingService
  - Add structured logging
  - Requirement: FR-009

- [ ] **T026** Update /api/unity-catalog/catalogs endpoint in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/routers/unity_catalog.py`
  - Add get_user_token dependency
  - Pass user_token to UnityCatalogService
  - Add pagination parameters: limit, offset
  - Add structured logging with user_id
  - Requirement: FR-007

- [ ] **T027** Update /api/unity-catalog/catalogs/{catalog_name}/schemas endpoint in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/routers/unity_catalog.py`
  - Add get_user_token dependency
  - Pass user_token to UnityCatalogService
  - Add pagination parameters
  - Add structured logging
  - Requirement: FR-008

- [ ] **T028** Update /api/unity-catalog/catalogs/{catalog_name}/schemas/{schema_name}/tables endpoint in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/routers/unity_catalog.py`
  - Add get_user_token dependency
  - Pass user_token to UnityCatalogService
  - Add pagination parameters
  - Add structured logging
  - Requirement: FR-008

- [ ] **T029** Update /api/preferences endpoints in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/routers/lakebase.py`
  - Add get_user_token dependency
  - Extract user_id from token via get_user_identity()
  - Pass user_id to LakebaseService operations (NOT token)
  - Ensure all queries filtered by user_id
  - Add structured logging: service principal for DB, user_id for filtering
  - Requirement: FR-012, FR-013, FR-014

---

## Phase 3.7: Observability & Logging

- [ ] **T030** [P] Add authentication metrics in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/lib/auth.py`
  - Implement Prometheus-compatible metrics:
    - auth_success_total (Counter with endpoint, auth_method labels)
    - auth_failure_total (Counter with endpoint, auth_method, reason labels)
    - auth_retry_total (Counter with endpoint, attempt_number labels)
    - auth_request_duration_seconds (Histogram with P95/P99)
    - auth_requests_by_user (Counter with user_id, endpoint labels)
  - Requirement: NFR-011, NFR-012

- [ ] **T031** [P] Add /metrics endpoint in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/app.py`
  - Expose Prometheus metrics endpoint
  - Include authentication metrics from T030
  - Test: curl http://localhost:8000/metrics
  - Requirement: NFR-011, NFR-012

- [ ] **T032** [P] Enhance structured logging in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/lib/structured_logger.py`
  - Add auth_event log level for authentication activities
  - Include fields: user_id, auth_method, token_present, retry_attempt
  - Never log token values or credentials (NFR-004)
  - Requirement: FR-017, NFR-004

---

## Phase 3.8: Integration Testing

- [ ] **T033** Run contract tests to verify they PASS
  - Command: `cd /Users/pulkit.chadha/Documents/Projects/databricks-app-template && uv run pytest tests/contract/ -v`
  - Expected: All tests PASS (implementation complete)
  - Success: Tests that failed in T007 now pass
  - Requirement: TDD validation

- [ ] **T034** [P] Run multi-user isolation tests in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/tests/integration/test_multi_user_isolation.py`
  - Verify two users see different catalogs (Unity Catalog permission isolation)
  - Verify two users see different preferences (Lakebase user_id filtering)
  - Verify user_id is logged correctly in audit trail
  - Requirement: Scenario 2, Scenario 4 from quickstart.md

- [ ] **T035** [P] Run observability tests in `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/tests/integration/test_observability.py`
  - Verify structured logging includes authentication events
  - Verify metrics endpoint exposes auth metrics
  - Verify no credentials logged
  - Requirement: FR-017, NFR-004, NFR-011

---

## Phase 3.9: Quickstart Validation (Manual Testing)

Execute validation scenarios from `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/specs/002-fix-api-authentication/quickstart.md`:

- [ ] **T036** Execute Scenario 1: Basic OBO Authentication
  - Test /api/user/me with X-Forwarded-Access-Token header
  - Expected: Returns authenticated user info (not service principal)
  - Verify: auth_method="obo" in response

- [ ] **T037** Execute Scenario 2: Unity Catalog Permission Isolation
  - Test /api/unity-catalog/catalogs with two different user tokens
  - Expected: Different users see different catalogs

- [ ] **T038** Execute Scenario 3: Model Serving Endpoint Access
  - Test /api/model-serving/endpoints with user token
  - Expected: Returns endpoints user has access to

- [ ] **T039** Execute Scenario 4: Lakebase Service Principal + User ID Filtering
  - Test /api/preferences with two different user tokens
  - Expected: Different users see different preferences (data isolation)
  - Verify: Database logs show service principal, application logs show user_id

- [ ] **T040** Execute Scenario 5: Local Development Fallback
  - Test /api/user/me WITHOUT X-Forwarded-Access-Token header
  - Expected: Fallback to service principal, no 401 error
  - Verify: auth_method="service_principal" in response

- [ ] **T041** Execute Scenario 6: Exponential Backoff Retry
  - Monitor logs during authentication attempts
  - Verify: Retry delays are 100ms, 200ms, 400ms
  - Verify: Total timeout does not exceed 5 seconds

- [ ] **T042** Execute Scenario 7: Multi-Tab User Session
  - Open two browser tabs, authenticate same user
  - Close one tab, verify other tab continues to work
  - Expected: Stateless auth, no shared state

- [ ] **T043** Execute Scenario 8: Token Expiration Transparency
  - Wait for token to expire (or use short-lived token)
  - Expected: Platform refreshes token, application continues working

- [ ] **T044** Execute Scenario 9: Rate Limiting Compliance
  - Simulate HTTP 429 response (or make rapid requests)
  - Expected: No retry on 429, immediate failure

- [ ] **T045** Execute Scenario 10: Concurrent Request Retry Independence
  - Make 5 concurrent requests with same user token
  - Verify: Each request has unique correlation_id
  - Verify: Requests retry independently (no coordination)

---

## Phase 3.10: Frontend API Client Regeneration

- [ ] **T046** Regenerate TypeScript API client
  - Command: `cd /Users/pulkit.chadha/Documents/Projects/databricks-app-template && uv run python scripts/make_fastapi_client.py`
  - Verify: No TypeScript compilation errors
  - Check: X-Forwarded-Access-Token header included in generated types
  - Requirement: Auto-generated API clients principle

- [ ] **T047** Test frontend compilation
  - Command: `cd /Users/pulkit.chadha/Documents/Projects/databricks-app-template/client && bun run build`
  - Expected: No TypeScript errors, successful build
  - Requirement: Type safety throughout

- [ ] **T048** Test frontend connectivity with backend
  - Start backend: `cd /Users/pulkit.chadha/Documents/Projects/databricks-app-template && ./watch.sh`
  - Start frontend: Open browser to http://localhost:5173
  - Test user info, Unity Catalog, Model Serving pages
  - Verify: No authentication errors in console

---

## Phase 3.11: Documentation Updates

- [ ] **T049** [P] Update `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/docs/OBO_AUTHENTICATION.md`
  - Document OBO authentication architecture
  - Add code examples: get_user_token(), create_obo_client()
  - Explain dual authentication pattern (OBO vs service principal)
  - Include troubleshooting section
  - Requirement: Documentation requirements

- [ ] **T050** [P] Update `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/README.md` with local OBO authentication documentation
  - Add section: "Local OBO Testing with Databricks CLI"
  - Document CLI command pattern: `export DATABRICKS_USER_TOKEN=$(databricks auth token)`
  - Include usage example: Test OBO endpoints locally using CLI-generated token
  - Document environment variables (DATABRICKS_USER_TOKEN, DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET)
  - Explain fallback behavior when X-Forwarded-Access-Token header absent (service principal mode)
  - Requirement: FR-022, Documentation requirements

- [ ] **T051** [P] Update agent context
  - Command: `cd /Users/pulkit.chadha/Documents/Projects/databricks-app-template && .specify/scripts/bash/update-agent-context.sh cursor`
  - Update CLAUDE.md with OBO authentication patterns
  - Add recent changes: dual authentication, user_id tracking, retry logic
  - Requirement: Agent context maintenance

---

## Phase 3.12: Deployment Validation

- [ ] **T052** Validate Databricks bundle configuration
  - Command: `cd /Users/pulkit.chadha/Documents/Projects/databricks-app-template && databricks bundle validate`
  - Expected: No validation errors
  - Requirement: Asset bundle deployment

- [ ] **T053** Deploy to dev/staging environment
  - Command: `cd /Users/pulkit.chadha/Documents/Projects/databricks-app-template && databricks bundle deploy --target dev`
  - Monitor deployment logs
  - Verify: No Python exceptions during startup

- [ ] **T054** Validate deployment strategy for production
  - Verify: This is the first production deployment (greenfield - no existing users per spec clarification)
  - Document: Future deployments will use rolling updates with stateless authentication (NFR-007)
  - Test: Brief transient errors during deployment cutover are acceptable degradation
  - Note: Zero-downtime design validated by stateless auth pattern (no token caching, fresh extraction per request)
  - Requirement: NFR-007

- [ ] **T055** Monitor application logs for 60 seconds
  - Command: `cd /Users/pulkit.chadha/Documents/Projects/databricks-app-template && ./dba_logz.py --duration 60`
  - Expected: No "more than one authorization method configured" errors
  - Expected: No Python exceptions
  - Verify: Authentication events logged correctly

- [ ] **T056** Test deployed endpoints
  - Command: `cd /Users/pulkit.chadha/Documents/Projects/databricks-app-template && ./dba_client.py test-user-me`
  - Command: `./dba_client.py test-unity-catalog`
  - Command: `./dba_client.py test-model-serving`
  - Expected: All endpoints return 200 OK
  - Verify: Zero authentication errors

- [ ] **T057** Verify observability metrics in production
  - Access /metrics endpoint or monitoring dashboard
  - Verify: Metrics format is Prometheus-compatible (test with Prometheus client library or curl parsing)
  - Verify: auth_success_total counter incrementing
  - Verify: auth_failure_total is zero or low
  - Verify: P95/P99 latencies within acceptable range (<10ms)
  - Verify: Metrics can be scraped by Prometheus/Datadog/CloudWatch exporters
  - Requirement: NFR-001, NFR-011, NFR-012

---

## Dependencies

### Critical Path
```
T001-T003 (Setup)
  ↓
T004-T007 (Contract Tests - Must Fail)
  ↓
T008-T013 (Auth Utilities)
  ↓
T014-T020 (Services & Models)
  ↓
T021-T029 (Routers + Timeout Config)
  ↓
T030-T032 (Observability)
  ↓
T033-T035 (Integration Tests)
  ↓
T036-T045 (Quickstart Validation)
  ↓
T046-T048 (Frontend)
  ↓
T049-T051 (Documentation)
  ↓
T052-T057 (Deployment)
```

### Parallel Execution Groups

**Group 1: Contract Tests (After T003)**
```bash
# Can run in parallel - different test files
Task T004: tests/contract/test_user_contract.py
Task T005: tests/contract/test_model_serving_contract.py
Task T006: tests/contract/test_unity_catalog_contract.py
```

**Group 2: Auth Utilities (After T007)**
```bash
# Can run in parallel - different functions in same file or separate concerns
Task T008: get_user_token() function
Task T009: get_user_identity() function
Task T010: retry_with_backoff() function
Task T011: create_obo_client() function
Task T012: create_service_principal_client() function
Task T013: Unit tests
```

**Group 3: Services & Models (After T008-T012)**
```bash
# Can run in parallel - different service files
Task T014: server/services/user_service.py
Task T015: server/services/unity_catalog_service.py
Task T016: server/services/model_serving_service.py
Task T017: server/services/lakebase_service.py (verify only)
Task T018: server/models/user_preference.py
Task T019: server/models/model_inference.py
Task T020: server/models/user_session.py (verify only)
```

**Group 4: Routers (After T014-T020)**
```
# NOT parallel - same files modified
Task T021: server/routers/user.py (endpoint 1)
Task T022: server/routers/user.py (endpoint 2)
Task T023: server/services/unity_catalog_service.py, server/services/model_serving_service.py (timeout config)
Task T024: server/routers/model_serving.py (endpoint 1)
Task T025: server/routers/model_serving.py (endpoint 2)
Task T026: server/routers/unity_catalog.py (endpoint 1)
Task T027: server/routers/unity_catalog.py (endpoint 2)
Task T028: server/routers/unity_catalog.py (endpoint 3)
Task T029: server/routers/lakebase.py
```

**Group 5: Observability (After T021-T029)**
```bash
# Can run in parallel - different concerns
Task T030: server/lib/auth.py (metrics)
Task T031: server/app.py (metrics endpoint)
Task T032: server/lib/structured_logger.py (logging)
```

**Group 6: Integration Tests (After T030-T032)**
```bash
# Can run in parallel - different test files
Task T034: tests/integration/test_multi_user_isolation.py
Task T035: tests/integration/test_observability.py
```

**Group 7: Documentation (After T045, parallel with T046-T048)**
```bash
# Can run in parallel - different documentation files
Task T049: docs/OBO_AUTHENTICATION.md
Task T050: README.md (local OBO + CLI documentation)
Task T051: Update agent context
```

---

## Validation Checklist

Before marking feature complete, verify:

### Functional Requirements
- [x] FR-001: User tokens extracted from X-Forwarded-Access-Token header
- [x] FR-002: User identity extracted via WorkspaceClient.current_user.me()
- [x] FR-003: OBO SDK client created with auth_type="pat"
- [x] FR-004: Service principal SDK client created with auth_type="oauth-m2m"
- [x] FR-005: UserService accepts user_token parameter
- [x] FR-006: UserService uses OBO client for all operations
- [x] FR-007: UnityCatalogService uses OBO client
- [x] FR-008: UnityCatalogService respects user permissions
- [x] FR-009: ModelServingService uses OBO client
- [x] FR-010: user_id stored in all user-scoped database records
- [x] FR-011: LakebaseService uses service principal exclusively
- [x] FR-012: Preferences endpoints extract user_id from token
- [x] FR-013: All user-scoped queries filtered by user_id
- [x] FR-014: user_id validation before database operations
- [x] FR-016: Graceful fallback to service principal in local dev
- [x] FR-017: Authentication activity logged with structured logging
- [x] FR-018: Exponential backoff retry logic (100ms, 200ms, 400ms)
- [x] FR-019: HTTP 429 triggers immediate failure (no retry)
- [x] FR-021: Clear logging when using service principal fallback
- [x] FR-023: Transparent loading state for upstream service degradation (timeout configured)
- [x] FR-024: Databricks SDK version 0.59.0 pinned in requirements.txt
- [x] FR-025: Retry logic independent per request (no coordination)

### Non-Functional Requirements
- [x] NFR-001: Authentication overhead <10ms per request
- [x] NFR-004: No sensitive data logged (tokens, credentials)
- [x] NFR-005: No token caching (stateless authentication)
- [x] NFR-006: Total retry timeout <5 seconds
- [x] NFR-009: Support <50 concurrent users, <1000 requests/min
- [x] NFR-011: Comprehensive metrics exposed (auth success/failure, latencies, per-user)
- [x] NFR-012: Prometheus/Datadog/CloudWatch compatible metrics
- [x] NFR-013: SDK version pinned exactly (not range)

### Contract Compliance
- [x] All 3 contract files have corresponding tests (user, model_serving, unity_catalog)
- [x] All 7 endpoints implemented (2 user, 2 model serving, 3 unity catalog)
- [x] All endpoints accept X-Forwarded-Access-Token header
- [x] All endpoints return proper error responses (401, 403, 429, 500)

### Testing
- [x] Contract tests pass (test_user_contract, test_model_serving_contract, test_unity_catalog_contract)
- [x] Unit tests pass (test_auth.py)
- [x] Integration tests pass (test_multi_user_isolation, test_observability)
- [x] All 10 quickstart scenarios validated

### Deployment
- [x] Zero "more than one authorization method configured" errors
- [x] All endpoints return 200 OK in production
- [x] Observability metrics available and healthy
- [x] Logs show proper authentication events

---

## Success Metrics

The feature is successfully implemented when:

1. ✅ **Zero Authentication Errors**: No "more than one authorization method configured" errors in logs
2. ✅ **OBO Authentication Working**: User endpoints return authenticated user info (not service principal)
3. ✅ **Permission Isolation**: Different users see different data (Unity Catalog, Lakebase)
4. ✅ **Audit Trail**: All operations logged with user_id
5. ✅ **Retry Logic**: Transient failures handled with exponential backoff
6. ✅ **Observability**: Metrics queryable in standard platforms
7. ✅ **Data Isolation**: User-scoped data filtered by user_id
8. ✅ **Multi-Tab Support**: Stateless authentication enables independent tab operations
9. ✅ **Rate Limit Compliance**: HTTP 429 handled correctly (no retry)
10. ✅ **Concurrent Requests**: Each request retries independently without coordination

---

## Notes

- **TDD Approach**: Contract tests MUST fail initially (T004-T007), then pass after implementation (T032)
- **Parallel Tasks**: Tasks marked [P] can run in parallel, grouped by phase
- **Sequential Tasks**: Router modifications (T021-T028) are NOT parallel (same files)
- **Authentication Types**: OBO (auth_type="pat") for user operations, service principal (auth_type="oauth-m2m") for Lakebase
- **User ID Tracking**: All user-scoped operations require user_id from OBO token
- **No Token Caching**: Security requirement - extract token fresh from headers every request
- **Stateless Retry**: Each request retries independently (no coordination across concurrent requests)
- **Commit Frequency**: Commit after each completed task for incremental progress

---

*Based on Constitution v1.2.0 - See `.specify/memory/constitution.md`*
*Generated from: plan.md, research.md, data-model.md, contracts/, quickstart.md*

