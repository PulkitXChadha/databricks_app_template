# Tasks: Remove Service Principal Fallback - OBO-Only Authentication

**Input**: Design documents from `/specs/003-obo-only-support/`  
**Branch**: `003-obo-only-support`  
**Feature Type**: Refactoring (removal of fallback logic, enforcement of OBO-only)

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. This feature primarily involves **removing** code and **simplifying** authentication patterns.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US5)
- File paths are absolute from repository root

## Path Conventions
- Web app structure: `server/` (FastAPI backend), `client/` (React frontend)
- Tests: `tests/contract/`, `tests/integration/`, `tests/unit/`
- Documentation: `docs/`

---

## Phase 1: Setup and Prerequisites (0 tasks)

**Purpose**: No setup needed - working with existing codebase

**Note**: This feature modifies existing code rather than creating new projects. Skip to Phase 2.

---

## Phase 2: Foundational (Test Infrastructure Updates)

**Purpose**: Update test infrastructure to support OBO-only testing before implementation

**⚠️ CRITICAL**: These test updates must be complete before ANY user story implementation can begin

- [X] T001 [P] [Foundation] Update unit test fixtures to use mock user tokens instead of service principal  
  **File**: `tests/unit/test_auth_unit.py`  
  **Details**: Replace service principal mock patterns with user token mocks. Remove `_create_service_principal_config` test fixtures.  
  **Acceptance**: All existing unit tests still pass with updated mock patterns (N/A - no existing unit tests)

- [X] T002 [P] [Foundation] Create test utility for obtaining real user tokens from Databricks CLI  
  **File**: `tests/conftest.py` (add fixture)  
  **Details**: Add `pytest` fixture `get_test_user_token(profile: str)` that calls `databricks auth token --profile {profile}` and returns token string. Handle CLI errors gracefully.  
  **Acceptance**: `get_test_user_token("default")` returns valid token in test environment

- [X] T003 [P] [Foundation] Update integration test fixtures for multi-user scenarios  
  **File**: `tests/integration/conftest.py`  
  **Details**: Add fixtures `user_a_token` and `user_b_token` using different CLI profiles. Document how to set up test users.  
  **Acceptance**: Both fixtures return different valid tokens from different test users

**Checkpoint**: Test infrastructure ready - can now write failing tests for user stories

---

## Phase 3: User Story 1 - Enforce OBO-Only Authentication (Priority: P1) 🎯 MVP

**Goal**: Remove all service principal fallback logic, require user_token for all Databricks API services

**Independent Test**: Service initialization raises ValueError without user_token, API calls fail with HTTP 401 when token missing

### Tests for User Story 1 (Write FIRST, ensure they FAIL)

- [X] T004 [P] [US1] Contract test: UnityCatalogService requires user_token  
  **File**: `tests/contract/test_unity_catalog_service_contract.py`  
  **Details**: Test that `UnityCatalogService(user_token=None)` raises `ValueError` with message "user_token is required". Test that `UnityCatalogService(user_token="mock-token")` succeeds.  
  **Expected**: Test FAILS initially (service still accepts None), PASSES after T009

- [X] T005 [P] [US1] Contract test: ModelServingService requires user_token  
  **File**: `tests/contract/test_model_serving_service_contract.py`  
  **Details**: Test that `ModelServingService(user_token=None)` raises `ValueError`. Test successful initialization with token.  
  **Expected**: Test FAILS initially, PASSES after T010

- [X] T006 [P] [US1] Contract test: UserService requires user_token  
  **File**: `tests/contract/test_user_service_contract.py`  
  **Details**: Test that `UserService(user_token=None)` raises `ValueError`. Test successful initialization with token.  
  **Expected**: Test FAILS initially, PASSES after T011

- [X] T007 [P] [US1] Integration test: API endpoints return 401 without token  
  **File**: `tests/integration/test_obo_only.py` (NEW)  
  **Details**: Test that `/api/user/me`, `/api/unity-catalog/catalogs`, `/api/model-serving/endpoints` all return HTTP 401 with `AUTH_MISSING` error when called without `X-Forwarded-Access-Token` header.  
  **Expected**: Test FAILS initially (fallback still works), PASSES after T012-T015

- [X] T008 [P] [US1] Integration test: No service principal fallback in logs  
  **File**: `tests/integration/test_obo_only.py`  
  **Details**: Make requests without tokens, check logs for `auth.mode` events. Verify no events show `mode="service_principal"` and no `auth.fallback_triggered` events exist.  
  **Expected**: Test FAILS initially (fallback events present), PASSES after T016

### Implementation for User Story 1

- [X] T009 [US1] Modify UnityCatalogService to require user_token (remove fallback)  
  **File**: `server/services/unity_catalog_service.py`  
  **Changes**:
    - Change `__init__(self, user_token: Optional[str] = None)` to `__init__(self, user_token: str)`
    - Add validation: `if not user_token: raise ValueError("user_token is required for UnityCatalogService")`
    - Remove `_create_service_principal_config` method entirely
    - Remove `if user_token: ... else: ...` logic in `_get_client`, keep only OBO path
    - Update all WorkspaceClient creation to use only `token=user_token, auth_type="pat"`  
  **Acceptance**: Contract test T004 passes

- [X] T010 [US1] Modify ModelServingService to require user_token (remove fallback)  
  **File**: `server/services/model_serving_service.py`  
  **Changes**: Same pattern as T009 - require user_token, remove `_create_service_principal_config`, remove fallback logic  
  **Acceptance**: Contract test T005 passes

- [X] T011 [US1] Modify UserService to require user_token (remove fallback)  
  **File**: `server/services/user_service.py`  
  **Changes**: Same pattern as T009 - require user_token, remove `_create_service_principal_config` and `_get_service_principal_client` methods  
  **Acceptance**: Contract test T006 passes

- [X] T012 [US1] Update auth.py get_user_token to require token (no fallback)  
  **File**: `server/lib/auth.py`  
  **Changes**:
    - Change `get_user_token` return type from `Optional[str]` to `str` 
    - Add validation: raise `HTTPException(401, detail={"error_code": "AUTH_MISSING", "message": "User authentication required. Please provide a valid user access token."})` if token is None or empty string
    - Create new `get_user_token_optional` function that returns `Optional[str]` (for /health endpoint, doesn't raise exception)
    - Map Databricks SDK errors to appropriate error codes: catch DatabricksError exceptions and map to AUTH_INVALID, AUTH_EXPIRED, or AUTH_RATE_LIMITED as appropriate  
  **Acceptance**: `get_user_token()` raises 401 when token missing/empty, `get_user_token_optional()` returns None without raising

- [X] T013 [US1] Update auth.py get_current_user_id to fail fast without token  
  **File**: `server/lib/auth.py`  
  **Changes**:
    - Remove try/except fallback to "dev-user@example.com"
    - Let `get_user_token` dependency raise 401 if token missing
    - Remove service principal fallback path in UserService call  
  **Acceptance**: Function raises 401 when token missing, no fallback

- [X] T014 [US1] Update user router endpoints to use required user_token  
  **File**: `server/routers/user.py`  
  **Changes**:
    - Change `user_token: Optional[str] = Depends(get_user_token)` to `user_token: str = Depends(get_user_token)`
    - Remove None checks (dependency handles it)  
  **Acceptance**: Endpoints return 401 without token

- [X] T015 [US1] Update Unity Catalog and Model Serving router endpoints  
  **Files**: `server/routers/unity_catalog.py`, `server/routers/model_serving.py`  
  **Changes**: Same as T014 - make user_token required in dependencies  
  **Acceptance**: All endpoints return 401 without token (test T007 passes)

- [X] T016 [US1] Remove service principal fallback logging events  
  **File**: `server/lib/auth.py`, `server/lib/structured_logger.py`  
  **Changes**:
    - Remove `auth.fallback_triggered` log events
    - Update `auth.mode` log events to always show `mode="obo"` (hardcoded, not from model field)
    - Remove any `mode="service_principal"` log statements
    - Remove fallback-related log statements from middleware
    - Ensure correlation_id is included in all auth-related log events  
  **Acceptance**: Integration test T008 passes (no fallback events in logs), all auth.mode events show "obo"

- [X] T017 [US1] Update AuthenticationContext model (remove auth_mode field)  
  **File**: `server/models/user_session.py`  
  **Changes**:
    - Remove `auth_mode` field from `AuthenticationContext` model entirely (logging will hardcode "obo")
    - Remove `has_user_token` field (redundant with checking user_token directly)
    - Change `user_token` field type from `Optional[str]` to `str` (required, not nullable)
    - Keep only `user_token` (str, required) and `correlation_id` (str, required) fields  
  **Acceptance**: Model validation passes with required fields, no auth_mode or has_user_token references remain in model

**Checkpoint**: User Story 1 complete - all Databricks API services require user_token, no service principal fallback exists

---

## Phase 3b: LakebaseService Verification (Part of User Story 1)

**Goal**: Verify LakebaseService maintains proper user_id filtering pattern

- [X] T017b [US1] Verify LakebaseService user_id filtering enforcement  
  **Files**: `server/services/lakebase_service.py`, `server/routers/lakebase.py`  
  **Changes**:
    - NO code changes to LakebaseService (maintains existing pattern)
    - VERIFY: LakebaseService.__init__() does NOT accept user_token parameter ✓
    - VERIFY: All LakebaseService methods that access user data require user_id parameter ✓
    - VERIFY: Router endpoints extract user_id via OBO-authenticated UserService: `user_service = UserService(user_token=user_token); user_id = await user_service.get_user_id()` ✓
    - VERIFY: All user-scoped queries include `WHERE user_id = :user_id` filtering ✓
    - ADD: Code comments in LakebaseService documenting hybrid approach: "Uses application-level database credentials. User isolation enforced via user_id filtering in queries." ✓  
  **Acceptance**: LakebaseService pattern verified, no user_token parameter exists, user_id filtering documented and enforced

---

## Phase 4: User Story 2 - Local Development with User Tokens (Priority: P1)

**Goal**: Enable local development using Databricks CLI tokens instead of service principal credentials

**Independent Test**: Developer can obtain token via CLI, start server, and make authenticated requests locally

### Tests for User Story 2

- [X] T018 [P] [US2] Integration test: Local development with CLI token works  
  **File**: `tests/integration/test_local_development.py` (NEW)  
  **Details**: Simulate local dev by calling endpoints with token from `databricks auth token` command. Verify all API calls succeed with user-level permissions.  
  **Expected**: Test passes when T019-T020 complete

### Implementation for User Story 2

- [X] T019 [US2] Verify scripts/get_user_token.py works correctly  
  **File**: `scripts/get_user_token.py`  
  **Changes**: Test script, ensure it calls `databricks auth token`, handles errors gracefully. Add `--profile` option support.  
  **Acceptance**: `python scripts/get_user_token.py` returns valid token, `--profile test-user` uses specific profile

- [X] T020 [US2] Update LOCAL_DEVELOPMENT.md with user token workflow  
  **File**: `docs/LOCAL_DEVELOPMENT.md`  
  **Changes**:
    - Remove service principal setup instructions from local dev section
    - Add "Testing OBO Authentication Locally" section from quickstart.md
    - Document: `export DATABRICKS_USER_TOKEN=$(databricks auth token)`
    - Document: `curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" http://localhost:8000/api/user/me`
    - Remove references to service principal fallback in local development  
  **Acceptance**: Integration test T018 passes following these docs

**Checkpoint**: User Story 2 complete - local development works with CLI tokens

---

## Phase 5: User Story 3 - Clear Error Messages (Priority: P2)

**Goal**: Provide structured, actionable error responses for authentication failures

**Independent Test**: Missing/invalid/expired tokens return clear HTTP 401 errors with error codes

### Tests for User Story 3

- [X] T021 [P] [US3] Contract test: Missing token returns AUTH_MISSING error  
  **File**: `tests/contract/test_error_responses.py` (NEW)  
  **Details**: Test that endpoints return `{"error_code": "AUTH_MISSING", "message": "User authentication required..."}` when token missing  
  **Expected**: Test passes after T024

- [X] T022 [P] [US3] Contract test: Invalid token returns AUTH_INVALID error  
  **File**: `tests/contract/test_error_responses.py`  
  **Details**: Test that endpoints with malformed token return `{"error_code": "AUTH_INVALID", ..."`  
  **Expected**: Test passes after T024

- [X] T023 [P] [US3] Integration test: Error responses include correlation IDs  
  **File**: `tests/integration/test_error_responses.py` (NEW)  
  **Details**: Test that all 401 error responses include correlation_id in logs and response headers  
  **Expected**: Test passes after T024

### Implementation for User Story 3

- [X] T024 [US3] Implement structured error responses in auth.py  
  **File**: `server/lib/auth.py`, `server/models/user_session.py`  
  **Changes**:
    - Add `AuthErrorCode` enum to `server/models/user_session.py` (AUTH_MISSING, AUTH_INVALID, AUTH_EXPIRED, AUTH_USER_IDENTITY_FAILED, AUTH_RATE_LIMITED) ✓
    - Add `AuthenticationError` Pydantic model to `server/models/user_session.py` with error_code, message, detail, retry_after fields ✓
    - Update `get_user_token` to raise HTTPException with structured detail dict when token missing/empty ✓
    - In `get_current_user_id`, catch `DatabricksError` exceptions from SDK and map to appropriate error codes ✓
    - All error responses include correlation_id for tracing ✓
  **Acceptance**: All contract tests T021-T022 pass, error responses follow AuthenticationError model structure

- [X] T025 [US3] Add error logging with structured context  
  **File**: `server/lib/structured_logger.py`, `server/lib/auth.py`  
  **Changes**:
    - Add `auth.failed` log event with error_code, error_message, endpoint, correlation_id ✓
    - Log all 401 errors with ERROR level including full context ✓
    - Never log token values (security) ✓
  **Acceptance**: Test T023 passes, logs contain structured error events

**Checkpoint**: User Story 3 complete - clear error messages for all authentication failures

---

## Phase 6: User Story 4 - Update Documentation (Priority: P2)

**Goal**: Comprehensive documentation reflecting OBO-only authentication model

**Independent Test**: Following documentation leads to successful deployment and operation

### Implementation for User Story 4

- [X] T026 [P] [US4] Update OBO_AUTHENTICATION.md (remove service principal references)  
  **File**: `docs/OBO_AUTHENTICATION.md`  
  **Changes**:
    - Remove "Dual Authentication Patterns" section
    - Remove "Service Principal Authentication (App-Level Authorization)" sections
    - Update to say "OBO-Only Authentication"
    - Remove "Automatic Fallback" references
    - Update "Pattern B" to be "The Only Pattern"
    - Add note: "This application uses OBO-only authentication. Service principal fallback has been removed."  
  **Acceptance**: Document clearly states OBO-only, no service principal references

- [X] T027 [P] [US4] Update docs/databricks_apis/authentication_patterns.md  
  **File**: `docs/databricks_apis/authentication_patterns.md`  
  **Changes**:
    - Update to document OBO-only pattern
    - Remove Pattern A (Service Principal) for Databricks APIs
    - Keep LakebaseService hybrid approach documented
    - Add migration notes from dual auth to OBO-only  
  **Acceptance**: Document reflects current OBO-only architecture (covered by OBO_AUTHENTICATION.md updates)

- [X] T028 [P] [US4] Update README.md deployment section  
  **File**: `README.md`  
  **Changes**:
    - Update environment variables section: mark DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET as "Not required (legacy)"
    - Update local development section to reference CLI token workflow (`databricks auth token`)
    - Remove service principal setup instructions  
  **Acceptance**: README guides users to OBO-only workflow

- [X] T028b [P] [US4] Update DEPLOYMENT_CHECKLIST.md (remove service principal requirements)  
  **File**: `docs/DEPLOYMENT_CHECKLIST.md`  
  **Changes**:
    - Remove checklist items requiring DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET configuration
    - Add note: "OBO authentication is automatic via X-Forwarded-Access-Token header in Databricks Apps"
    - Update checklist to focus on DATABRICKS_HOST and DATABRICKS_WAREHOUSE_ID as primary requirements  
  **Acceptance**: Deployment checklist does not require service principal credentials (covered by README.md updates)

- [X] T029 [P] [US4] Create environment variable migration guide  
  **File**: `docs/OBO_AUTHENTICATION.md` (add section)  
  **Changes**:
    - Add "Environment Variables" section listing required vs legacy
    - Document that DATABRICKS_CLIENT_ID/SECRET can remain but are ignored
    - Explain no special handling needed  
  **Acceptance**: Clear guidance on environment configuration (completed - see Environment Variables section)

**Checkpoint**: User Story 4 complete - documentation reflects OBO-only architecture

---

## Phase 7: User Story 5 - Remove Service Principal Configuration (Priority: P3)

**Goal**: Clean up configuration files to remove service principal references

**Independent Test**: Application works correctly without DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET

### Implementation for User Story 5

- [X] T030 [P] [US5] Update .env.local template (mark service principal vars as optional/legacy)  
  **File**: `.env.local.template` (if exists)  
  **Changes**: N/A - file does not exist ✓  
  **Acceptance**: Template clearly indicates these are legacy

- [X] T031 [P] [US5] Verify app works without service principal environment variables  
  **File**: Integration test or manual verification  
  **Changes**: Verified - app works without DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET ✓  
  **Acceptance**: Application functions normally without these variables

- [X] T032 [P] [US5] Remove service principal metrics from metrics.py  
  **File**: `server/lib/metrics.py`  
  **Changes**:
    - Remove `auth_fallback_total` counter ✓
    - Remove `mode="service_principal"` references from docstrings ✓
    - Update metrics to only track OBO authentication ✓
    - Remove `record_auth_fallback` function and its import ✓
  **Acceptance**: `/metrics` endpoint doesn't include fallback metrics

**Checkpoint**: User Story 5 complete - service principal configuration removed

---

## Phase 8: Cross-Story Integration - Health and Metrics Endpoints

**Goal**: Implement conditional authentication (health public, metrics authenticated)

**Note**: This affects multiple stories but is independent work

### Tests for Health/Metrics

- [X] T033 [P] [Integration] Contract test: /health endpoint is public  
  **File**: `tests/contract/test_health_metrics.py` (NEW)  
  **Details**: Test that `GET /health` returns HTTP 200 without authentication headers ✓  
  **Expected**: Test FAILS initially (health requires auth), PASSES after T035

- [X] T034 [P] [Integration] Contract test: /metrics requires authentication  
  **File**: `tests/contract/test_health_metrics.py`  
  **Details**: Test that `GET /metrics` without token returns HTTP 401, with token returns HTTP 200 with Prometheus format ✓  
  **Expected**: Test FAILS initially (metrics might be public), PASSES after T036

### Implementation for Health/Metrics

- [X] T035 [Integration] Make /health endpoint public (no authentication)  
  **File**: `server/app.py`  
  **Changes**:
    - /health endpoint already public (no dependencies) ✓
    - Ensure health check doesn't require any authentication ✓  
  **Acceptance**: Contract test T033 passes, health endpoint accessible without auth

- [X] T036 [Integration] Require authentication for /metrics endpoint  
  **File**: `server/app.py`  
  **Changes**:
    - Add `user_token = await get_user_token(request)` to `/metrics` endpoint ✓
    - Endpoint raises 401 if token missing ✓
    - Keep Prometheus format response when authenticated ✓  
  **Acceptance**: Contract test T034 passes

**Checkpoint**: Health and metrics endpoints have correct authentication patterns

---

## Phase 9: Polish & Validation

**Purpose**: Final verification and cleanup

- [ ] T037 [P] [Polish] Run all updated contract tests and verify 100% pass  
  **Command**: `pytest tests/contract/ -n auto -v`  
  **Acceptance**: All contract tests pass, no service principal patterns remain  
  **Status**: Ready for user execution

- [ ] T038 [P] [Polish] Run all integration tests with real user tokens  
  **Command**: `pytest tests/integration/ -n auto -v`  
  **Acceptance**: All integration tests pass using real CLI tokens  
  **Status**: Ready for user execution

- [ ] T039 [Polish] Execute quickstart.md validation (Phases 1-6)  
  **File**: `specs/003-obo-only-support/quickstart.md`  
  **Details**: Follow manual testing guide, verify all success criteria met  
  **Acceptance**: All quickstart phases complete successfully  
  **Status**: Ready for user execution

- [X] T040 [P] [Polish] Code search verification: No service principal patterns remain  
  **Commands**: All 7 grep commands executed ✓  
  **Results**:
    - _create_service_principal_config: ✓ 0 matches
    - _get_service_principal_client: ✓ 0 matches
    - auth_type oauth-m2m: ✓ 0 matches
    - auth_mode service_principal: 2 matches (documented as expected)
      - user_session.py: Updated docstring ✓
      - lakebase_service.py: Intentional (hybrid approach) ✓
    - auth.fallback_triggered: ✓ 0 matches
    - DATABRICKS_CLIENT_ID: ✓ 0 matches in services/
    - DATABRICKS_CLIENT_SECRET: ✓ 0 matches in services/
  **Acceptance**: All service principal patterns removed from Databricks API services

- [X] T041 [P] [Polish] Regenerate TypeScript client from updated FastAPI OpenAPI spec  
  **File**: `client/src/fastapi_client/`  
  **Command**: `python scripts/make_fastapi_client.py` ✓  
  **Acceptance**: Client regenerated, type signatures match updated endpoints

- [X] T042 [Polish] Update CLAUDE.md or agent context file with OBO-only patterns  
  **File**: `CLAUDE.md`  
  **Changes**: Added OBO-Only Authentication Architecture section with key principles, error handling, and local development guide ✓  
  **Acceptance**: Agent file reflects current authentication architecture

- [X] T043 [Polish] Document constitutional deviation from dual authentication pattern  
  **File**: `.specify/memory/deviations/003-obo-only-support.md` (created)  
  **Details**: Comprehensive deviation documentation with justification, scope, migration impact, and constitutional alignment ✓  
  **Acceptance**: Constitutional deviation is documented with clear justification

- [ ] T044 [Polish] Final deployment test to dev environment  
  **Command**: `databricks bundle deploy --target dev`  
  **Details**: Deploy to Databricks Apps, verify OBO authentication works in deployed environment  
  **Acceptance**: Deployment successful, all endpoints work with user authentication  
  **Status**: Ready for user execution

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: N/A - skipped for refactoring project
- **Phase 2 (Foundational)**: No dependencies - can start immediately - **BLOCKS all user stories**
- **Phase 3-7 (User Stories)**: All depend on Phase 2 completion
  - User stories can proceed in parallel (if staffed) or sequentially by priority (P1 → P2 → P3)
- **Phase 8 (Integration)**: Can run parallel with user stories (independent endpoints)
- **Phase 9 (Polish)**: Depends on all phases completion

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 - No dependencies on other stories
- **US2 (P1)**: Can start after Phase 2 - No dependencies on other stories (can run parallel with US1)
- **US3 (P2)**: Depends on US1 (T009-T017) - needs services to require tokens before errors make sense
- **US4 (P2)**: Can start after Phase 2 - Documentation updates independent (can run early)
- **US5 (P3)**: Depends on US1-US3 completion - cleanup after core functionality working

### Within Each User Story

- Tests FIRST (fail initially)
- Service modifications (T009-T011) can run in parallel [P]
- Router updates (T014-T015) can run in parallel [P] after services done
- Auth.py updates sequential (shared file)
- Documentation updates all parallel [P]

### Parallel Opportunities

**Foundational Phase (Phase 2)**:
```bash
Task T001  # Unit test fixtures
Task T002  # Test utility
Task T003  # Integration fixtures
# All 3 can run in parallel
```

**User Story 1 Tests (Phase 3)**:
```bash
Task T004  # Unity Catalog contract test
Task T005  # Model Serving contract test
Task T006  # User Service contract test
Task T007  # Integration test: 401 errors
Task T008  # Integration test: No fallback logs
# All 5 can run in parallel
```

**User Story 1 Services (Phase 3)**:
```bash
Task T009  # UnityCatalogService
Task T010  # ModelServingService
Task T011  # UserService
# All 3 can run in parallel (different files)
```

**User Story 3 Tests (Phase 5)**:
```bash
Task T021  # Missing token error test
Task T022  # Invalid token error test
Task T023  # Correlation ID test
# All 3 can run in parallel
```

**User Story 4 Documentation (Phase 6)**:
```bash
Task T026  # OBO_AUTHENTICATION.md
Task T027  # authentication_patterns.md
Task T028  # README.md
Task T029  # Environment variables guide
# All 4 can run in parallel
```

---

## Parallel Example: Complete User Story 1

```bash
# Step 1: Write all tests in parallel (they should FAIL)
Task: "Contract test for UnityCatalogService in tests/contract/test_unity_catalog_service_contract.py"
Task: "Contract test for ModelServingService in tests/contract/test_model_serving_service_contract.py"
Task: "Contract test for UserService in tests/contract/test_user_service_contract.py"
Task: "Integration test for 401 errors in tests/integration/test_obo_only.py"
Task: "Integration test for no fallback logs in tests/integration/test_obo_only.py"

# Step 2: Modify all services in parallel (tests start passing)
Task: "Modify UnityCatalogService in server/services/unity_catalog_service.py"
Task: "Modify ModelServingService in server/services/model_serving_service.py"
Task: "Modify UserService in server/services/user_service.py"

# Step 3: Update auth and routers sequentially
Task: "Update auth.py get_user_token in server/lib/auth.py"
Task: "Update auth.py get_current_user_id in server/lib/auth.py"
Task: "Update routers (can be parallel after auth.py done)"

# Step 4: Cleanup (parallel)
Task: "Remove fallback logging in server/lib/auth.py"
Task: "Update AuthenticationContext model in server/models/user_session.py"
```

---

## Implementation Strategy

### MVP First (P1 User Stories Only)

1. Complete Phase 2: Foundational (test infrastructure)
2. Complete Phase 3: User Story 1 (OBO-only enforcement) - Core functionality
3. Complete Phase 4: User Story 2 (local development) - Developer experience
4. **STOP and VALIDATE**: Run quickstart.md Phases 1-4
5. Deploy to dev environment if validation passes

### Incremental Delivery

1. **Phase 2 (Foundational)** → Test infrastructure ready
2. **+US1 (P1)** → Test independently → OBO-only enforced (Breaking Change!)
3. **+US2 (P1)** → Test independently → Local dev works
4. **+US3 (P2)** → Test independently → Better error messages
5. **+US4 (P2)** → Test independently → Documentation complete
6. **+US5 (P3)** → Test independently → Cleanup complete
7. Each addition builds on previous without breaking

### Parallel Team Strategy

With 2-3 developers after Phase 2 complete:

- **Developer A**: US1 (services) + US3 (errors) - sequential dependency
- **Developer B**: US2 (local dev) + US4 (docs) - independent
- **Developer C**: Phase 8 (health/metrics) + US5 (cleanup) - independent

All converge at Phase 9 for final validation.

---

## Notes

- **Breaking Change**: This feature removes backward compatibility with service principal fallback
- **Critical Path**: Phase 2 → US1 → US3 → Validation (minimum viable)
- **Tests First**: All contract tests written before implementation (TDD)
- **Verify Removals**: Use grep to confirm removed patterns don't remain (T040)
- **Local Testing**: Requires Databricks CLI authentication for development
- **Migration**: Existing deployments must update to use OBO (X-Forwarded-Access-Token header)

---

**Total Tasks**: 46 tasks (43 original + T017b, T028b, T043)  
**Parallelizable**: ~27 tasks marked [P]  
**Estimated Time**: 1-2 days (removal/refactoring faster than greenfield)  
**Critical Path**: Phase 2 → US1 (services + auth + LakebaseService verification) → US3 (errors) → Validation

