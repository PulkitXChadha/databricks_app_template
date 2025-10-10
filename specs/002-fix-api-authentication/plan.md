# Implementation Plan: Fix API Authentication and Implement OBO Authentication

**Branch**: `002-fix-api-authentication` | **Date**: 2025-10-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-fix-api-authentication/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path → ✅ COMPLETE
2. Fill Technical Context (scan for NEEDS CLARIFICATION) → ✅ COMPLETE
   → Project Type: web (frontend + backend) → ✅ CONFIRMED
   → Structure Decision: Existing backend/frontend structure → ✅ CONFIRMED
3. Fill the Constitution Check section → ✅ COMPLETE
4. Evaluate Constitution Check section → ✅ PASS
   → No violations detected
   → Update Progress Tracking: Initial Constitution Check → ✅ COMPLETE
5. Execute Phase 0 → research.md → ✅ COMPLETE
   → All NEEDS CLARIFICATION resolved
6. Execute Phase 1 → contracts, data-model.md, quickstart.md → ✅ COMPLETE
7. Re-evaluate Constitution Check section → ✅ PASS
   → No new violations
   → Update Progress Tracking: Post-Design Constitution Check → ✅ COMPLETE
8. Plan Phase 2 → Describe task generation approach → ✅ COMPLETE
9. STOP - Ready for /tasks command → ✅ READY
```

**IMPORTANT**: The /plan command STOPS at step 9. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary

The Databricks App is deployed successfully and the UI loads correctly, but all API endpoints are failing with the error: "more than one authorization method configured: oauth and pat". 

**Root Cause**: The Databricks SDK detects BOTH OAuth credentials (from environment variables automatically set by the platform) AND token parameters, causing a validation error.

**Technical Approach**: Implement dual authentication patterns:
1. **On-Behalf-Of User (OBO)** authentication for Databricks API calls (Unity Catalog, Model Serving, User endpoints) using explicit `auth_type="pat"` parameter
2. **Service Principal** authentication for Lakebase database connections using explicit `auth_type="oauth-m2m"` parameter
3. Extract user tokens from `X-Forwarded-Access-Token` header via FastAPI dependency injection
4. Add user_id tracking to all user-scoped database tables for application-level data isolation
5. Implement exponential backoff retry logic for authentication failures

## Technical Context
**Language/Version**: Python 3.11+ (confirmed in pyproject.toml)  
**Primary Dependencies**: FastAPI 0.104+, Databricks SDK==0.59.0 (exact version pinned, not range), SQLAlchemy 2.0+, Psycopg 3.1+  
**Storage**: Lakebase (PostgreSQL in Databricks) via service principal authentication  
**Testing**: pytest 7.4+, httpx 0.25+, contract testing with OpenAPI validation  
**Target Platform**: Databricks Apps platform (deployed) + local development environment  
**Project Type**: web (frontend: React 18.3 + TypeScript 5.2+, backend: Python + FastAPI)  
**Performance Goals**: <10ms auth overhead per request, <50 concurrent users, <1000 requests/min  
**Constraints**: <5s total retry timeout, no token caching (NFR-005), Lakebase requires service principal (platform limitation)  
**Scale/Scope**: 25 functional requirements, 13 non-functional requirements, 4 affected endpoints, 3 database table migrations

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Design Bricks First
- [x] All UI components use Design Bricks data design system (no UI changes in this feature)
- [x] No custom UI components without Design Bricks availability check (N/A - backend-only feature)
- [x] Databricks theming and design patterns maintained (no frontend changes)

**Status**: ✅ PASS - No UI changes required, existing frontend uses Design Bricks

### Lakebase Integration
- [x] Persistent data operations use Lakebase (Postgres in Databricks)
- [x] Token-based authentication for database access (service principal OAuth via generate_database_credential())
- [x] No external OLTP systems introduced

**Status**: ✅ PASS - Lakebase integration maintained, enhanced with user_id tracking for data isolation

### Asset Bundle Deployment
- [x] Deployment managed through Databricks Asset Bundles
- [x] `databricks.yml` configuration present and complete (existing at repository root)
- [x] No manual workspace uploads or ad-hoc deployments

**Status**: ✅ PASS - Existing Asset Bundle deployment unchanged, authentication fixes compatible

### Type Safety Throughout
- [x] Python type hints on all functions (auth dependencies, service methods)
- [x] TypeScript strict mode, no `any` types (no frontend changes)
- [x] Auto-generated TypeScript client from OpenAPI spec (regeneration needed for auth changes)

**Status**: ✅ PASS - Type safety maintained, OpenAPI spec updated with auth headers

### Model Serving Integration
- [x] Service abstractions ready for model inference (existing ModelServingService)
- [x] Model endpoint configuration via environment variables (no changes)
- [x] Error handling for model serving failures (enhanced with retry logic)

**Status**: ✅ PASS - Model serving integration enhanced with OBO authentication

### Auto-Generated API Clients
- [x] OpenAPI spec generated from FastAPI (automatic)
- [x] TypeScript client auto-generated on schema changes (via scripts/make_fastapi_client.py)
- [x] No manual API client code

**Status**: ✅ PASS - Client regeneration required after auth header changes

### Development Tooling Standards
- [x] uv for Python package management (not pip/poetry)
- [x] bun for frontend package management (not npm/yarn)
- [x] Hot reloading enabled for dev workflow (watch.sh)

**Status**: ✅ PASS - Existing tooling unchanged

### Observability First (Constitution v1.1.0+)
- [x] Structured JSON logging implemented (existing structured_logger.py)
- [x] Correlation IDs for request tracking (existing middleware)
- [x] Authentication activity logging added (FR-017: token presence, auth_type, retry attempts)
- [x] Performance metrics exposed (NFR-011: auth success/failure, latencies, per-user metrics)
- [x] No sensitive data logged (NFR-004: no tokens or credentials)

**Status**: ✅ PASS - Observability requirements integrated into authentication implementation

### Multi-User Data Isolation (Constitution v1.1.0+)
- [x] User identity extracted from Databricks authentication context (WorkspaceClient.current_user.me())
- [x] Unity Catalog isolation automatic (platform-enforced based on user token)
- [x] Lakebase queries filtered by user_id in WHERE clauses (FR-013, FR-014)
- [x] Authorization via dependency injection (FastAPI Depends pattern)
- [x] Multi-user isolation testing planned (Scenario 2 & 4 in quickstart.md)
- [x] Audit logging includes user_id (FR-017, Success Metric #4)

**Status**: ✅ PASS - Data isolation architecture implemented per Constitution Principle IX

**Overall Constitution Check**: ✅ PASS - All constitutional principles satisfied, no violations

## Project Structure

### Documentation (this feature)
```
specs/002-fix-api-authentication/
├── plan.md              # This file (/plan command output) - UPDATED
├── research.md          # Phase 0 output (/plan command) - COMPLETE
├── data-model.md        # Phase 1 output (/plan command) - COMPLETE
├── quickstart.md        # Phase 1 output (/plan command) - COMPLETE
├── contracts/           # Phase 1 output (/plan command) - COMPLETE
│   ├── user_api.yaml
│   ├── model_serving_api.yaml
│   └── unity_catalog_api.yaml
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Web application structure (frontend + backend)
server/
├── app.py                    # FastAPI application (MODIFY: add auth dependencies)
├── lib/
│   ├── auth.py              # Authentication utilities (MODIFY: add OBO token extraction)
│   ├── database.py          # Lakebase connection (MODIFY: ensure service principal auth)
│   ├── distributed_tracing.py # Correlation ID middleware (existing)
│   └── structured_logger.py # JSON logging (existing)
├── models/
│   ├── user_preference.py   # User preferences model (MODIFY: add user_id column)
│   ├── model_inference.py   # Model inference logs (MODIFY: add user_id column)
│   └── user_session.py      # User sessions (VERIFY: user_id exists)
├── routers/
│   ├── user.py              # User endpoints (MODIFY: add OBO auth)
│   ├── model_serving.py     # Model serving endpoints (MODIFY: add OBO auth)
│   ├── unity_catalog.py     # Unity Catalog endpoints (MODIFY: add OBO auth)
│   └── lakebase.py          # Preferences endpoints (MODIFY: add user_id filtering)
└── services/
    ├── user_service.py      # User operations (MODIFY: accept user_token)
    ├── model_serving_service.py # Model serving ops (MODIFY: accept user_token)
    ├── unity_catalog_service.py # Unity Catalog ops (MODIFY: accept user_token)
    └── lakebase_service.py  # Lakebase ops (VERIFY: service principal only)

client/
├── src/
│   ├── fastapi_client/      # Auto-generated API client (REGENERATE after backend changes)
│   ├── components/          # React components (NO CHANGES)
│   └── pages/               # Application pages (NO CHANGES)
└── package.json

migrations/
└── versions/
    └── 003_add_user_id_to_tables.py  # NEW: Add user_id columns and indexes

tests/
├── contract/
│   ├── test_user_contract.py         # EXISTING: User API contract tests
│   ├── test_model_serving_contract.py # EXISTING: Model serving contract tests
│   └── test_unity_catalog_contract.py # EXISTING: Unity Catalog contract tests
├── integration/
│   ├── test_multi_user_isolation.py  # EXISTING: Multi-user data isolation tests
│   └── test_observability.py         # EXISTING: Logging and metrics tests
└── unit/
    └── test_auth.py                   # NEW: Authentication utility unit tests

docs/
└── OBO_AUTHENTICATION.md     # MODIFY: Update with implementation details
```

**Structure Decision**: Existing web application structure maintained. Backend modifications in `server/` directory for authentication logic, frontend requires only API client regeneration. No new projects or structural changes needed.

## Phase 0: Outline & Research

**Status**: ✅ COMPLETE

### Research Summary

All technical unknowns resolved and documented in `research.md`:

1. **Databricks SDK Authentication Configuration** - Use explicit `auth_type` parameter to prevent multi-method conflicts
2. **FastAPI Dependency Injection** - Implement `get_user_token()` dependency for header extraction
3. **Exponential Backoff Retry Logic** - 3 attempts with 100ms, 200ms, 400ms delays, 5s total timeout
4. **Lakebase Service Principal Authentication** - Platform limitation requires service principal, application-level user_id filtering
5. **User Identity Extraction** - Use `WorkspaceClient.current_user.me()` API for secure identity extraction
6. **Multi-User Data Isolation** - Application-level WHERE clauses with user_id mandatory validation

**Key Decisions**:
- Auth Type Pattern: `auth_type="pat"` for OBO, `auth_type="oauth-m2m"` for service principal
- No token caching (security requirement NFR-005)
- Stateless authentication (enables multi-tab, token refresh transparency)
- Independent retry per request (no coordination across concurrent requests)

**Output**: research.md with all NEEDS CLARIFICATION resolved ✅

## Phase 1: Design & Contracts

**Status**: ✅ COMPLETE

### Design Artifacts Generated

1. **Data Model** (`data-model.md`) ✅
   - Entity: User Access Token (transient, extracted from headers)
   - Entity: User Identity (user_id, email, username, display_name)
   - Entity: Service principal credentials (from environment variables)
   - Entity: Databricks SDK Configuration (auth_type, token/credentials)
   - Entity: AuthenticationContext (request-scoped dependency injection)
   - Modified: UserPreference (add user_id column, indexes)
   - Modified: ModelInferenceLog (add user_id column, indexes)
   - Modified: UserSession (verify user_id exists)
   - Migration: 003_add_user_id_to_tables.py

2. **API Contracts** (`contracts/`) ✅
   - `user_api.yaml` - User information endpoints with X-Forwarded-Access-Token header
   - `model_serving_api.yaml` - Model serving endpoints with OBO authentication
   - `unity_catalog_api.yaml` - Unity Catalog endpoints with permission filtering

3. **Validation Scenarios** (`quickstart.md`) ✅
   - Scenario 1: Basic OBO Authentication - User Information Endpoint
   - Scenario 2: Unity Catalog Permission Isolation
   - Scenario 3: Model Serving Endpoint Access with OBO
   - Scenario 4: Lakebase Service Principal Authentication
   - Scenario 5: Local Development Fallback (No OBO Token)
   - Scenario 6: Authentication Retry with Exponential Backoff
   - Scenario 7: Multi-Tab User Session (Stateless Auth)
   - Scenario 8: Token Expiration and Platform Refresh
   - Scenario 9: Rate Limiting Compliance (HTTP 429)

4. **Contract Tests** (existing in tests/contract/) ✅
   - `test_user_contract.py` - Validates user API endpoints
   - `test_model_serving_contract.py` - Validates model serving endpoints
   - `test_unity_catalog_contract.py` - Validates Unity Catalog endpoints
   - Tests currently PASS (need modification to enforce OBO auth headers)

5. **Agent Context Update** ✅
   - Run `.specify/scripts/bash/update-agent-context.sh cursor` after Phase 1 complete
   - Update CLAUDE.md with OBO authentication patterns
   - Add recent changes: dual authentication, user_id tracking, retry logic

**Output**: data-model.md, /contracts/*, quickstart.md, contract tests, CLAUDE.md update ✅

### Post-Design Constitution Check

**Re-evaluation**: ✅ PASS - No new violations introduced by design

- Design Bricks: No UI changes required
- Lakebase: Service principal auth maintained, user_id filtering added
- Asset Bundle: No deployment changes required
- Type Safety: All new functions type-annotated
- Model Serving: Enhanced with OBO authentication
- API Clients: Regeneration planned post-implementation
- Tooling: No changes to uv/bun workflow
- Observability: Structured logging and metrics integrated
- Data Isolation: user_id filtering enforced application-level

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:

The /tasks command will load `.specify/templates/tasks-template.md` and generate tasks based on Phase 1 design artifacts:

1. **Contract Test Modification Tasks** [P] - Parallel, independent
   - Update test_user_contract.py to require X-Forwarded-Access-Token header
   - Update test_model_serving_contract.py to require OBO authentication
   - Update test_unity_catalog_contract.py to require OBO authentication
   - Verify all contract tests FAIL before implementation (TDD)

2. **Database Migration Tasks** - Sequential (must run before service changes)
   - Create migration 003_add_user_id_to_tables.py
   - Add user_id column to user_preferences table
   - Add user_id column to model_inference_logs table
   - Create indexes for user_id columns
   - Test migration upgrade/downgrade

3. **Authentication Utility Tasks** [P] - Parallel, foundational
   - Implement get_user_token() FastAPI dependency in server/lib/auth.py
   - Implement get_user_identity() function using WorkspaceClient.current_user.me()
   - Implement retry_with_backoff() decorator with exponential backoff
   - Add SDK client factory functions (create_obo_client, create_service_principal_client)
   - Write unit tests for auth utilities (test_auth.py)

4. **Service Layer Modification Tasks** [P] - Parallel (after auth utilities)
   - Modify UserService to accept user_token parameter (use create_obo_client)
   - Modify UnityCatalogService to accept user_token parameter
   - Modify ModelServingService to accept user_token parameter
   - Verify LakebaseService uses service principal only (no user_token)
   - Add user_id validation to all user-scoped service operations

5. **Router Modification Tasks** [P] - Parallel (after services)
   - Update /api/user/me endpoint to use get_user_token dependency
   - Update /api/user/me/workspace endpoint to use get_user_token dependency
   - Update /api/model-serving/endpoints to use get_user_token dependency
   - Update /api/unity-catalog/catalogs to use get_user_token dependency
   - Update /api/preferences to extract user_id and filter queries

6. **Logging and Observability Tasks** [P] - Parallel
   - Add structured logging for authentication events (token presence, auth_type, retries)
   - Implement metrics collection (auth success/failure, retry counts, latencies)
   - Add per-user request counting
   - Expose metrics endpoint for monitoring

7. **Integration Testing Tasks** - Sequential (after implementation)
   - Run contract tests - verify all PASS after implementation
   - Run multi-user isolation tests (test_multi_user_isolation.py)
   - Run observability tests (test_observability.py)
   - Execute quickstart.md validation scenarios 1-9

8. **Frontend API Client Tasks** - Sequential (after backend complete)
   - Regenerate TypeScript client via scripts/make_fastapi_client.py
   - Verify no TypeScript compilation errors
   - Test frontend connectivity with new auth headers

9. **Documentation Tasks** [P] - Parallel (can do anytime)
   - Update docs/OBO_AUTHENTICATION.md with implementation details
   - Update README.md with local OBO testing instructions
   - Document environment variables for local development

10. **Deployment Validation Tasks** - Sequential (final phase)
    - Run databricks bundle validate
    - Deploy to dev/staging environment
    - Monitor logs with dba_logz.py for 60 seconds
    - Test endpoints with dba_client.py
    - Verify zero authentication errors
    - Check observability metrics

**Ordering Strategy**:
- TDD order: Contract tests modified first (must fail before implementation)
- Dependency order: Database migrations → Auth utilities → Services → Routers → Tests
- Parallelization: Mark [P] for tasks within same layer that can run concurrently
- Critical path: Contract tests → Migrations → Auth utilities → Services → Routers → Integration tests → Deployment

**Estimated Output**: 35-40 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

No violations detected - table not needed.

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command) ✅
- [x] Phase 1: Design complete (/plan command) ✅
- [x] Phase 2: Task planning complete (/plan command - describe approach only) ✅
- [ ] Phase 3: Tasks generated (/tasks command) - NEXT STEP
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS ✅
- [x] Post-Design Constitution Check: PASS ✅
- [x] All NEEDS CLARIFICATION resolved ✅
- [x] Complexity deviations documented (N/A - no violations) ✅

**Artifact Status**:
- [x] research.md generated ✅
- [x] data-model.md generated ✅
- [x] contracts/ generated (user_api.yaml, model_serving_api.yaml, unity_catalog_api.yaml) ✅
- [x] quickstart.md generated ✅
- [ ] tasks.md generated (awaiting /tasks command)

---

**Next Command**: Run `/tasks` to generate implementation tasks from this plan

---
*Based on Constitution v1.2.0 - See `.specify/memory/constitution.md`*
