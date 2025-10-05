# Tasks: Databricks Service Integrations

**Feature**: `001-databricks-integrations`  
**Branch**: `001-databricks-integrations`  
**Input**: Design documents from `/specs/001-databricks-integrations/`  
**Prerequisites**: plan.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

## Execution Status
```
Phase 0: Research complete ✅
Phase 1: Design complete ✅
Phase 2: Task planning complete ✅ (this file)
Phase 3-4: Implementation pending ⏳
Phase 5: Validation pending ⏳
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- All file paths are absolute
- TDD approach: Tests before implementation

## Path Conventions
This is a **web application** with:
- Backend: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/`
- Frontend: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/client/`
- Tests: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/tests/`
- Scripts: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/scripts/`

---

## Phase 3.1: Setup & Dependencies

### T001 [P] [X] Add Python dependencies for Databricks integrations
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/pyproject.toml`  
**Description**: Add SQLAlchemy (≥2.0.0), psycopg2-binary (≥2.9.0), alembic (≥1.13.0) for Lakebase integration  
**Validation**: Run `uv sync` and verify dependencies installed  
**Status**: ✅ COMPLETE

### T002 [P] [X] Add TypeScript dependencies for Design Bricks
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/client/package.json`  
**Description**: Add @databricks/design-bricks (≥1.0.0) dependency  
**Validation**: Run `cd client && bun install` and verify package installed  
**Status**: ✅ COMPLETE

### T003 [P] [X] Create Alembic migration for user_preferences table
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/migrations/versions/001_create_user_preferences.py`  
**Description**: Create migration with table schema: id (SERIAL PK), user_id (VARCHAR indexed), preference_key (VARCHAR), preference_value (JSONB), timestamps, UNIQUE(user_id, preference_key)  
**Validation**: Run `alembic upgrade head` in dev environment  
**Status**: ✅ COMPLETE

### T004 [P] [X] Create Alembic migration for model_inference_logs table
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/migrations/versions/002_create_model_inference_logs.py`  
**Description**: Create migration with schema: id (SERIAL PK), request_id, endpoint_name, user_id (indexed), inputs (JSONB), predictions (JSONB), status, execution_time_ms, error_message, timestamps  
**Validation**: Run `alembic upgrade head` in dev environment  
**Status**: ✅ COMPLETE

### T005 [X] Initialize Alembic configuration
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/alembic.ini`  
**Description**: Create Alembic config with Lakebase connection string pattern  
**Validation**: Run `alembic current` successfully  
**Status**: ✅ COMPLETE

---

## Phase 3.2: Contract Tests (TDD - Written Before Implementation)

### T006 [P] [X] Create Unity Catalog contract tests
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/tests/contract/test_unity_catalog_contract.py`  
**Description**: Contract tests for GET /api/unity-catalog/tables and POST /api/unity-catalog/query validating OpenAPI spec from contracts/unity_catalog_api.yaml  
**Expected**: Tests FAIL initially (no implementation yet)  
**Validation**: Run `pytest tests/contract/test_unity_catalog_contract.py` - should fail with 404  
**Status**: ✅ COMPLETE

### T007 [P] [X] Create Lakebase contract tests
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/tests/contract/test_lakebase_contract.py`  
**Description**: Contract tests for GET/POST/DELETE /api/preferences validating OpenAPI spec from contracts/lakebase_api.yaml  
**Expected**: Tests FAIL initially (no implementation yet)  
**Validation**: Run `pytest tests/contract/test_lakebase_contract.py` - should fail with 404  
**Status**: ✅ COMPLETE

### T008 [P] [X] Create Model Serving contract tests
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/tests/contract/test_model_serving_contract.py`  
**Description**: Contract tests for GET /api/model-serving/endpoints and POST /api/model-serving/invoke validating OpenAPI spec from contracts/model_serving_api.yaml  
**Expected**: Tests FAIL initially (no implementation yet)  
**Validation**: Run `pytest tests/contract/test_model_serving_contract.py` - should fail with 404  
**Status**: ✅ COMPLETE

---

## Phase 3.3: Pydantic Models (Entities from data-model.md)

### T009 [P] Create UserSession Pydantic model
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/models/user_session.py`  
**Description**: Pydantic model with fields: user_id, user_name, email, active, session_token, workspace_url, created_at, expires_at  
**Validation**: Import and instantiate model with test data

### T010 [P] Create DataSource Pydantic model
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/models/data_source.py`  
**Description**: Pydantic model with fields: catalog_name, schema_name, table_name, columns (list[ColumnDefinition]), row_count, size_bytes, owner, access_level (enum), full_name (computed property)  
**Validation**: Test full_name property returns "catalog.schema.table"

### T011 [P] Create QueryResult Pydantic model
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/models/query_result.py`  
**Description**: Pydantic model with fields: query_id, data_source (DataSource), sql_statement, rows (list[dict]), row_count, execution_time_ms, user_id, executed_at, status (enum), error_message  
**Validation**: Test sql_statement validator rejects non-SELECT queries

### T012 [P] Create UserPreference SQLAlchemy model
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/models/user_preference.py`  
**Description**: SQLAlchemy model mapped to user_preferences table with columns: id (PK), user_id (indexed), preference_key, preference_value (JSON), created_at, updated_at  
**Validation**: Test model can be imported and used in query

### T013 [P] Create ModelEndpoint Pydantic model
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/models/model_endpoint.py`  
**Description**: Pydantic model with fields: endpoint_name, endpoint_id, model_name, model_version, state (enum: CREATING/READY/UPDATING/FAILED), workload_url, creation_timestamp, last_updated_timestamp, config (dict)  
**Validation**: Test state validator enforces READY state for inference

### T014 [P] Create ModelInferenceRequest Pydantic model
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/models/model_inference.py`  
**Description**: Pydantic models for ModelInferenceRequest (request_id, endpoint_name, inputs, user_id, created_at, timeout_seconds) and ModelInferenceResponse (request_id, endpoint_name, predictions, status, execution_time_ms, error_message, completed_at)  
**Validation**: Test timeout_seconds validator enforces 1-300 range

### T015 [P] Create ModelInferenceResponse Pydantic model
**File**: Same as T014 (both models in same file)  
**Description**: Included in T014  
**Validation**: Test error_message validator enforces presence when status=ERROR

---

## Phase 3.4: Observability Infrastructure

### T016 [P] Implement StructuredLogger with JSON formatting
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/lib/structured_logger.py`  
**Description**: Logger class with JSONFormatter including fields: timestamp, level, message, module, function, user_id, duration_ms. No PII logging.  
**Validation**: Test log output is valid JSON with all required fields

### T017 [P] Implement correlation ID contextvars
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/lib/distributed_tracing.py`  
**Description**: ContextVar for request_id with get_correlation_id() and set_correlation_id() functions  
**Validation**: Test context propagates through async calls

### T018 Add FastAPI middleware for correlation ID injection
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/app.py`  
**Description**: Middleware to extract X-Request-ID header or generate UUID, call set_correlation_id(), add X-Request-ID to response headers  
**Depends on**: T017  
**Validation**: Test request without header gets UUID, request with header preserves it

---

## Phase 3.5: Database Connection Infrastructure

### T019 Create Lakebase database connection module
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/lib/database.py`  
**Description**: SQLAlchemy engine with QueuePool (pool_size=5, max_overflow=10), pool_pre_ping=True, token-based connection string builder  
**Depends on**: T001, T012  
**Validation**: Test connection pool creation and verify connections with pool_pre_ping

---

## Phase 3.6: Service Layer Implementation

### T020 Implement UnityCatalogService
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/services/unity_catalog_service.py`  
**Description**: Service with methods: list_tables(catalog, schema, user_context) and query_table(catalog, schema, table, limit, offset, user_context). Use WorkspaceClient for SQL Warehouse execution. Include error handling for EC-002 (database unavailable) and EC-004 (permission denied).  
**Depends on**: T009, T010, T011, T016  
**Validation**: Mock WorkspaceClient and test list_tables returns DataSource objects

### T021 Implement LakebaseService
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/services/lakebase_service.py`  
**Description**: Service with methods: get_preferences(user_id), save_preference(user_id, key, value), delete_preference(user_id, key). All queries filter by user_id. Include error handling for EC-002 (database unavailable).  
**Depends on**: T012, T019, T016  
**Validation**: Test user_id filtering in WHERE clauses, verify data isolation

### T022 Implement ModelServingService
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/services/model_serving_service.py`  
**Description**: Service with methods: list_endpoints() and invoke_model(endpoint_name, inputs, timeout). Use httpx for async HTTP with timeout, exponential backoff retry (max 3 attempts). Include error handling for EC-001 (model unavailable), log inference to Lakebase model_inference_logs table.  
**Depends on**: T013, T014, T015, T016, T019  
**Validation**: Mock httpx and test timeout enforcement, retry logic

---

## Phase 3.7: API Routers (FastAPI Endpoints)

### T023 Implement Unity Catalog router
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/routers/unity_catalog.py`  
**Description**: FastAPI router with endpoints: GET /api/unity-catalog/tables and POST /api/unity-catalog/query. Use Depends(get_current_user_id) for user context. Return responses matching contracts/unity_catalog_api.yaml.  
**Depends on**: T020  
**Validation**: Run contract tests from T006 - should PASS

### T024 Implement Lakebase router
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/routers/lakebase.py`  
**Description**: FastAPI router with endpoints: GET /api/preferences, POST /api/preferences, DELETE /api/preferences/{preference_key}. Use Depends(get_current_user_id) for data isolation. Return responses matching contracts/lakebase_api.yaml.  
**Depends on**: T021  
**Validation**: Run contract tests from T007 - should PASS

### T025 Implement Model Serving router
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/routers/model_serving.py`  
**Description**: FastAPI router with endpoints: GET /api/model-serving/endpoints and POST /api/model-serving/invoke. Return responses matching contracts/model_serving_api.yaml.  
**Depends on**: T022  
**Validation**: Run contract tests from T008 - should PASS

### T026 Integrate new routers into FastAPI app
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/server/app.py`  
**Description**: Import and register unity_catalog, lakebase, and model_serving routers with app.include_router()  
**Depends on**: T023, T024, T025  
**Validation**: Run `python server/app.py` and verify /docs shows all new endpoints

---

## Phase 3.8: Contract Test Validation (GATE)

### T027 Run all contract tests - MUST PASS before continuing
**File**: N/A (validation task)  
**Description**: Execute `pytest tests/contract/` and verify all tests pass. If any fail, fix violations before proceeding.  
**Depends on**: T023, T024, T025  
**Validation**: `pytest tests/contract/ -v` returns 0 exit code

---

## Phase 3.9: Frontend Migration to Design Bricks

### T028 Migrate WelcomePage to Design Bricks components
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/client/src/pages/WelcomePage.tsx`  
**Description**: Replace shadcn/ui components with Design Bricks equivalents: Button → databricks-button, Card → databricks-card, Badge → databricks-tag, Alert → databricks-banner  
**Depends on**: T002  
**Validation**: Run dev server, verify page renders with Databricks styling

### T029 [P] Create DataTable component with pagination
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/client/src/components/ui/DataTable.tsx`  
**Description**: React component using Design Bricks databricks-table with pagination controls (limit/offset), displays Unity Catalog query results  
**Depends on**: T002  
**Validation**: Render with mock data, verify pagination controls work

### T030 [P] Create PreferencesForm component
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/client/src/components/ui/PreferencesForm.tsx`  
**Description**: React component using Design Bricks databricks-input and databricks-button for CRUD operations on user preferences  
**Depends on**: T002  
**Validation**: Render form, verify all CRUD actions work

### T031 [P] Create ModelInvokeForm component
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/client/src/components/ui/ModelInvokeForm.tsx`  
**Description**: React component using Design Bricks databricks-input for model inference inputs, databricks-button for invoke action, displays predictions  
**Depends on**: T002  
**Validation**: Render form, verify input validation and result display

---

## Phase 3.10: Frontend API Integration

### T032 Regenerate TypeScript client from OpenAPI spec
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/client/src/fastapi_client/`  
**Description**: Run `python scripts/make_fastapi_client.py` to generate TypeScript client with UnityCatalogService, LakebaseService, ModelServingService  
**Depends on**: T026  
**Validation**: Verify client/src/fastapi_client/services/ contains new service files

### T033 Integrate Unity Catalog API in DataTable component
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/client/src/components/ui/DataTable.tsx`  
**Description**: Connect DataTable to UnityCatalogService.queryTable() API, handle loading/error states  
**Depends on**: T029, T032  
**Validation**: Run app, select table, verify data loads in table

### T034 Integrate Lakebase API in PreferencesForm component
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/client/src/components/ui/PreferencesForm.tsx`  
**Description**: Connect form to LakebaseService GET/POST/DELETE methods, handle success/error states  
**Depends on**: T030, T032  
**Validation**: Run app, create/update/delete preference, verify persistence

### T035 Integrate Model Serving API in ModelInvokeForm component
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/client/src/components/ui/ModelInvokeForm.tsx`  
**Description**: Connect form to ModelServingService.invokeModel() API, display predictions, handle timeout/errors  
**Depends on**: T031, T032  
**Validation**: Run app, invoke model, verify predictions display

---

## Phase 3.11: Integration Testing

### T036 [P] Create multi-user data isolation test
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/tests/integration/test_multi_user_isolation.py`  
**Description**: Integration test with 2+ mock users, verify User A preferences not visible to User B, Unity Catalog enforces table permissions per user  
**Depends on**: T024  
**Validation**: Run `pytest tests/integration/test_multi_user_isolation.py` - should pass

### T037 [P] Create observability integration test
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/tests/integration/test_observability.py`  
**Description**: Test that all API calls include correlation ID in logs, verify JSON log format with required fields  
**Depends on**: T018  
**Validation**: Run test, check stdout for JSON logs with request_id field

### T038 Test WCAG 2.1 Level A accessibility compliance
**File**: N/A (manual testing task)  
**Description**: Test keyboard navigation (Tab, Enter, Escape), verify alt text on images, check form labels, validate contrast ratios (4.5:1 normal, 3:1 large text)  
**Depends on**: T028, T033, T034, T035  
**Validation**: Use browser DevTools Accessibility tab, lighthouse audit

### T039 Test pagination performance (NFR-003)
**File**: N/A (performance testing task)  
**Description**: Query Unity Catalog table with 100 rows, verify response time <500ms. Test with 10 concurrent users, verify <20% latency increase.  
**Depends on**: T033  
**Validation**: Use `dba_client.py` for load testing, measure response times

---

## Phase 3.12: Sample Data & Deployment Configuration

### T040 Implement sample data setup script
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/scripts/setup_sample_data.py`  
**Description**: Script to create Unity Catalog sample table (main.samples.demo_data with ≤100 rows) and seed Lakebase with 5 sample user_preferences records. Include --create-all, --unity-catalog, --lakebase flags.  
**Depends on**: T020, T021  
**Validation**: Run script, verify sample data exists in UC and Lakebase

### T041 Update databricks.yml with new environment variables
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/databricks.yml`  
**Description**: Add environment variables: LAKEBASE_HOST, LAKEBASE_PORT, LAKEBASE_DATABASE, LAKEBASE_TOKEN, MODEL_SERVING_ENDPOINT, MODEL_SERVING_TIMEOUT  
**Validation**: Run `databricks bundle validate` - should pass

### T042 Validate Asset Bundle configuration
**File**: N/A (validation task)  
**Description**: Run `databricks bundle validate` to check databricks.yml syntax and resource definitions  
**Depends on**: T041  
**Validation**: Command exits with 0, no errors reported

---

## Phase 3.13: Documentation

### T043 Write quickstart.md with user stories
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/specs/001-databricks-integrations/quickstart.md`  
**Description**: Complete quickstart guide with Prerequisites, Setup (6 steps), Testing User Stories (9 stories from spec), Multi-User Testing, Troubleshooting (EC-001 through EC-005)  
**Validation**: Follow quickstart end-to-end as new developer

### T044 Update README with integration instructions
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/README.md`  
**Description**: Add section on Databricks service integrations (Unity Catalog, Lakebase, Model Serving), link to quickstart.md and contracts/  
**Validation**: Review README for completeness and clarity

### T045 Update agent context file (CLAUDE.md)
**File**: `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/CLAUDE.md`  
**Description**: Run `.specify/scripts/bash/update-agent-context.sh cursor` to update CLAUDE.md with new commands, dependencies, environment variables  
**Validation**: Verify CLAUDE.md updated, preserved manual additions

---

## Phase 3.14: End-to-End Validation (FINAL GATE)

### T046 Execute quickstart.md end-to-end
**File**: N/A (validation task)  
**Description**: Follow quickstart.md as a new developer, verify all setup steps work, test all 9 user stories  
**Depends on**: T043  
**Validation**: All stories pass, no errors encountered

### T047 Verify structured logging with correlation IDs
**File**: N/A (validation task)  
**Description**: Run `python dba_logz.py`, verify logs are JSON formatted with timestamp, level, message, request_id, user_id fields. Search logs by correlation ID.  
**Depends on**: T018  
**Validation**: Logs are structured JSON, correlation IDs present

### T048 Deploy to dev environment and test
**File**: N/A (deployment task)  
**Description**: Run `databricks bundle deploy -t dev`, verify app accessible in workspace, test all 3 integrations (Unity Catalog query, preferences CRUD, model invoke)  
**Depends on**: T042  
**Validation**: App deployed, all features work in dev environment

### T049 Deploy to prod environment and validate permissions
**File**: N/A (deployment task)  
**Description**: Run `databricks bundle deploy -t prod`, verify permissions (CAN_MANAGE for admins, CAN_VIEW for users), test with non-admin account  
**Depends on**: T048  
**Validation**: Prod deployment successful, permissions enforced

---

## Dependencies Graph

```
Setup (T001-T005)
  ↓
Contract Tests (T006-T008) [P]
  ↓
Models (T009-T015) [P] + Observability (T016-T018) + Database (T019)
  ↓
Services (T020-T022)
  ↓
Routers (T023-T026)
  ↓
Contract Validation (T027) ← GATE
  ↓
Frontend Migration (T028-T031) [P] + Client Regen (T032)
  ↓
Frontend Integration (T033-T035)
  ↓
Integration Tests (T036-T039) [P]
  ↓
Sample Data & Config (T040-T042)
  ↓
Documentation (T043-T045) [P]
  ↓
Validation (T046-T049) ← FINAL GATE
```

---

## Parallel Execution Examples

### Launch Setup Tasks (T001-T004)
```bash
# Terminal 1
Task: "Add Python dependencies (SQLAlchemy, psycopg2, alembic) to pyproject.toml"

# Terminal 2
Task: "Add @databricks/design-bricks to client/package.json"

# Terminal 3
Task: "Create Alembic migration 001_create_user_preferences.py"

# Terminal 4
Task: "Create Alembic migration 002_create_model_inference_logs.py"
```

### Launch Contract Tests (T006-T008)
```bash
# Terminal 1
Task: "Write contract tests for Unity Catalog API in tests/contract/test_unity_catalog_contract.py"

# Terminal 2
Task: "Write contract tests for Lakebase API in tests/contract/test_lakebase_contract.py"

# Terminal 3
Task: "Write contract tests for Model Serving API in tests/contract/test_model_serving_contract.py"
```

### Launch Model Creation Tasks (T009-T015)
```bash
# All can run in parallel - different files
Task: "Create UserSession model in server/models/user_session.py"
Task: "Create DataSource model in server/models/data_source.py"
Task: "Create QueryResult model in server/models/query_result.py"
Task: "Create UserPreference model in server/models/user_preference.py"
Task: "Create ModelEndpoint model in server/models/model_endpoint.py"
Task: "Create ModelInference models in server/models/model_inference.py"
```

### Launch Frontend Components (T029-T031)
```bash
# Terminal 1
Task: "Create DataTable component in client/src/components/ui/DataTable.tsx"

# Terminal 2
Task: "Create PreferencesForm component in client/src/components/ui/PreferencesForm.tsx"

# Terminal 3
Task: "Create ModelInvokeForm component in client/src/components/ui/ModelInvokeForm.tsx"
```

---

## Task Summary

**Total Tasks**: 49  
**Parallel Tasks**: 23 (marked with [P])  
**Sequential Tasks**: 26  
**Gates**: 2 (T027 contract validation, T046-T049 final validation)

### By Phase
- **Setup**: 5 tasks (T001-T005)
- **Contract Tests**: 3 tasks (T006-T008)
- **Models**: 7 tasks (T009-T015)
- **Observability**: 3 tasks (T016-T018)
- **Database**: 1 task (T019)
- **Services**: 3 tasks (T020-T022)
- **Routers**: 4 tasks (T023-T026)
- **Contract Validation**: 1 task (T027)
- **Frontend Migration**: 4 tasks (T028-T031)
- **Frontend Integration**: 4 tasks (T032-T035)
- **Integration Testing**: 4 tasks (T036-T039)
- **Sample Data & Config**: 3 tasks (T040-T042)
- **Documentation**: 3 tasks (T043-T045)
- **Final Validation**: 4 tasks (T046-T049)

---

## Notes

- **TDD Approach**: All contract tests (T006-T008) written before implementation (T020-T026)
- **Data Isolation**: All Lakebase queries filter by `user_id` from authenticated context
- **Error Handling**: Implement error codes EC-001 through EC-005 as specified in contracts
- **Observability**: All API calls must log with correlation ID (request_id)
- **Accessibility**: Design Bricks components provide WCAG 2.1 Level A compliance
- **Performance**: Unity Catalog queries must respond <500ms for ≤100 rows
- **Commit Strategy**: Commit after each task completion
- **Testing**: Run contract tests after each router implementation to ensure compliance

---

## Validation Checklist
*GATE: Verify before marking tasks complete*

- [x] All 3 contracts have corresponding test tasks (T006-T008)
- [x] All 7 entities have model creation tasks (T009-T015)
- [x] All contract tests come before implementation (T006-T008 before T023-T026)
- [x] Parallel tasks are truly independent (verified - different files)
- [x] Each task specifies exact absolute file path
- [x] No [P] task modifies same file as another [P] task
- [x] Gate at T027 ensures contract compliance before frontend work
- [x] Final gate (T046-T049) ensures end-to-end validation

---

*Based on Constitution v1.1.0 - See `.specify/memory/constitution.md`*  
*Generated from plan.md, data-model.md, research.md, and contracts/*