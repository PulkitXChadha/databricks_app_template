# Tasks: Automatic Model Input Schema Detection

**Feature Branch**: `004-dynamic-endpoint-input-schema`  
**Input**: Design documents from `/specs/004-dynamic-endpoint-input-schema/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: This feature does not explicitly require TDD approach. Test tasks are NOT included - implementation will rely on existing test infrastructure and manual validation per quickstart.md scenarios.

**Organization**: Tasks are grouped by user story (US1, US2, US3) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, or SETUP/FOUNDATION)
- File paths are relative to repository root

## Path Conventions
- **Backend**: `server/` directory (FastAPI application)
- **Frontend**: `client/src/` directory (React TypeScript)
- **Database**: `migrations/versions/` (Alembic migrations)
- **Testing**: `tests/` directory (contract, integration, unit)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Database schema and shared models for all user stories

- [X] **T001** [P] [SETUP] Create Alembic migration for `schema_detection_events` table in `migrations/versions/004_create_schema_detection_events.py` per data-model.md Section 1.2
- [X] **T002** [P] [SETUP] Create `SchemaDetectionEvent` SQLAlchemy model in `server/models/schema_detection_event.py` per data-model.md Section 1.2
- [X] **T003** [P] [SETUP] Create `SchemaDetectionResult` Pydantic model in `server/models/schema_detection_result.py` with enums `EndpointType` and `DetectionStatus` per data-model.md Section 1.1
- [X] **T004** [SETUP] Run database migration to create `schema_detection_events` table: `alembic upgrade head`

**Checkpoint**: Database schema ready, shared models defined

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core service infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] **T005** [FOUNDATION] Create `SchemaDetectionService` skeleton in `server/services/schema_detection_service.py` with method signatures per data-model.md Section 5.1 (no implementations yet, just structure)
- [X] **T006** [P] [FOUNDATION] Add foundation model chat format constants in `schema_detection_service.py` (FOUNDATION_MODEL_CHAT_SCHEMA, FOUNDATION_MODEL_CHAT_EXAMPLE) per research.md Decision 7
- [X] **T007** [P] [FOUNDATION] Add generic fallback template constant (GENERIC_FALLBACK_TEMPLATE) in `schema_detection_service.py` per research.md Decision 7
- [X] **T008** [P] [FOUNDATION] Implement `log_detection_event()` method in `SchemaDetectionService` to persist events to Lakebase per data-model.md Section 5.1 and schema-logging-api.yaml
- [X] **T009** [P] [FOUNDATION] Implement correlation ID middleware enhancement in `server/lib/distributed_tracing.py` to support X-Correlation-ID header per research.md Decision 6
- [X] **T010** [FOUNDATION] Add schema detection endpoint `/api/model-serving/endpoints/{endpoint_name}/schema` to `server/routers/model_serving.py` (route only, delegate to service) per schema-detection-api.yaml

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Automatic Schema Detection for Foundation Models (Priority: P1) 🎯 MVP

**Goal**: When users select a foundation model endpoint (Claude, GPT, Llama), automatically detect the model type and populate the JSON input box with a valid chat-format example in <500ms

**Independent Test**: Select "databricks-claude-sonnet-4" endpoint from dropdown → JSON input box populates with chat format `{"messages": [{"role": "user", "content": "Hello"}], "max_tokens": 150}` → Status badge shows "Foundation Model"

### Implementation for User Story 1

- [X] **T011** [US1] Implement `detect_endpoint_type()` method in `SchemaDetectionService` to identify foundation models using heuristic-based detection per research.md Decision 1 (check endpoint name for keywords: claude, gpt, llama, mistral, chat, foundation)
- [X] **T012** [US1] Implement fast-path foundation model detection in `detect_schema()` method: when `EndpointType.FOUNDATION_MODEL` detected, return pre-built chat format example with SUCCESS status in <500ms per research.md Decision 7
- [X] **T013** [US1] Add structured logging for foundation model detection events (log endpoint_name, detected_type, status, latency_ms) using existing StructuredLogger per research.md Decision 6
- [X] **T014** [US1] Wire up foundation model detection in `/endpoints/{endpoint_name}/schema` router endpoint to call `detect_schema()` and return `SchemaDetectionResult` per schema-detection-api.yaml
- [X] **T015** [P] [US1] Create `useSchemaCache` React hook in `client/src/hooks/useSchemaCache.ts` with `getCachedSchema()` and `setCachedSchema()` methods using sessionStorage per research.md Decision 4
- [X] **T016** [P] [US1] Create `SchemaDetectionStatus` badge component in `client/src/components/SchemaDetectionStatus.tsx` using Design Bricks `<Badge>` to display detected model type per research.md Decision 5
- [X] **T017** [US1] Create `useSchemaDetection` React Query hook in `client/src/pages/DatabricksServicesPage.tsx` integrating cache check → API call → cache write per research.md Decision 8
- [X] **T018** [US1] Integrate schema detection into `DatabricksServicesPage.tsx`: on endpoint selection, trigger `useSchemaDetection()`, show loading spinner (hide JSON input), populate input box on success, display status badge per quickstart.md User Flow Section 1. Note: JSON input population may be done directly in DatabricksServicesPage or extracted to a `ModelInputEditor` component if UI complexity warrants separation
- [X] **T019** [US1] Regenerate TypeScript API client from FastAPI OpenAPI spec: `cd client && python ../scripts/make_fastapi_client.py` to generate `SchemaDetectionResult` types and `detectSchema()` service method per plan.md Principle VI

**Checkpoint**: Foundation models (Claude, GPT, Llama) should auto-populate chat format in <500ms. Test with databricks-claude-sonnet-4 endpoint per quickstart.md Example 1.

---

## Phase 4: User Story 2 - Schema Retrieval for MLflow Models (Priority: P2)

**Goal**: When users select an MLflow model endpoint registered in Unity Catalog, automatically query Model Registry to retrieve input schema and generate realistic example JSON in <3s

**Independent Test**: Select MLflow endpoint "fraud-detection-model" from dropdown → Query Model Registry for schema → JSON input box populates with generated example matching schema fields (e.g., `{"transaction_amount": 3.14, "merchant_category": "example text"}`) → Status badge shows "MLflow Model"

### Implementation for User Story 2

- [X] **T020** [US2] Implement `retrieve_mlflow_schema()` method in `SchemaDetectionService` to query Unity Catalog Model Registry using Databricks SDK `client.model_registry.get_model_version()` with OBO authentication and 5s timeout per research.md Decision 2. Include exponential backoff retry logic for 429 rate limit errors per FR-007a (retry delays: 2s, 4s, 8s max, 3 retries total)
- [X] **T021** [US2] Implement `generate_example_json()` method in `SchemaDetectionService` to generate realistic sample values from MLflow JSON Schema (strings→"example text", integers→42, floats→3.14, booleans→true, arrays→[up to 3 sample items]) per research.md Decision 3 and FR-004. For primitive arrays, generate 3 items (e.g., `[1.0, 2.0, 3.0]`). For object arrays, generate 1 nested structure example to keep payload readable
- [X] **T022** [US2] Enhance `detect_endpoint_type()` method to detect MLflow models by checking for `model_name` and `model_version` fields in endpoint.config.served_models[0] per research.md Decision 1
- [X] **T023** [US2] Implement MLflow model detection path in `detect_schema()` method: when `EndpointType.MLFLOW_MODEL` detected, call `retrieve_mlflow_schema()` with asyncio timeout, then `generate_example_json()`, return result with SUCCESS status per research.md Decision 7
- [X] **T024** [US2] Add MLflow schema parsing logic to handle MLflow ModelSignature format (parse `signature.inputs` JSON string) and convert to JSON Schema format per model-registry-api.yaml
- [X] **T025** [US2] Add structured logging for MLflow model detection including Model Registry query latency and schema retrieval success/failure per research.md Decision 6
- [X] **T026** [US2] Update frontend `useSchemaDetection` hook to handle longer loading times for MLflow models (show loading indicator for up to 5s timeout) per research.md Decision 8
- [X] **T027** [US2] Add inline helper text in `DatabricksServicesPage.tsx` to distinguish required vs optional fields in generated MLflow examples per FR-011 and quickstart.md Example 2

**Checkpoint**: MLflow models registered in Unity Catalog should auto-populate with schema-based examples in <3s. Test with fraud-detection-model endpoint per quickstart.md Example 2.

---

## Phase 5: User Story 3 - Graceful Fallback for Unknown Schemas (Priority: P3)

**Goal**: When schema detection fails (unknown model type, timeout, API error), display generic JSON template with clear warning message so users can still invoke the model manually

**Independent Test**: Select endpoint with no schema metadata or simulate timeout → JSON input box populates with `{"input": "value", "_comment": "Schema detection unavailable..."}` → Warning alert displays explaining failure → Status badge shows "Unknown"

### Implementation for User Story 3

- [X] **T028** [US3] Implement timeout fallback logic in `detect_schema()` method: catch `asyncio.TimeoutError` after 5s, return `SchemaDetectionResult` with status=TIMEOUT, detected_type=UNKNOWN, generic template, and error_message per research.md Decision 7
- [X] **T029** [US3] Implement error fallback logic in `detect_schema()` method: catch all exceptions (API errors, malformed schemas, 403 permission errors per FR-007b), return `SchemaDetectionResult` with status=FAILURE, detected_type=UNKNOWN, generic template, and error_message per research.md Decision 7. For 403 Forbidden errors, include clear "Permission Denied" message and ensure Invoke Model button is disabled in frontend
- [X] **T030** [US3] Add structured logging for timeout and failure events with error details and stack traces for debugging per research.md Decision 6
- [X] **T031** [US3] Update frontend `useSchemaDetection` hook to handle TIMEOUT and FAILURE statuses: show warning Alert component from Design Bricks, populate input box with fallback template, set status badge to "Unknown" per research.md Decision 5
- [X] **T032** [US3] Add user-friendly error messaging in `DatabricksServicesPage.tsx` for different failure types: timeout ("Schema retrieval timed out. Using generic template."), API error ("Schema detection unavailable. Consult model documentation."), malformed schema ("Schema format not supported.") per quickstart.md Error Scenarios
- [X] **T033** [US3] Ensure "Invoke Model" button remains enabled even on schema detection failure (users can manually edit and invoke) per FR-006 graceful degradation

**Checkpoint**: All failure scenarios should display helpful fallback messages without blocking user workflow. Test with invalid endpoint names and timeout simulation per quickstart.md Example 3.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements and validation across all user stories

- [X] **T034** [P] [POLISH] Add performance logging to track schema detection latency by endpoint type (foundation: <500ms target, mlflow: <3s target) per plan.md Performance Goals
- [X] **T035** [P] [POLISH] Add multi-user data isolation validation: verify all Lakebase queries filter by `user_id` per data-model.md Section 7 and plan.md Principle IX
- [X] **T036** [P] [POLISH] Validate browser session cache behavior: verify schemas persist until tab close, verify cache hit avoids API calls, verify page reload clears cache per research.md Decision 4
- [X] **T037** [P] [POLISH] Run quickstart.md validation scenarios: foundation model example, MLflow model example, timeout fallback example per quickstart.md Testing Scenarios
- [X] **T038** [POLISH] Verify correlation ID propagation: test with client-provided X-Correlation-ID header, verify it appears in both application logs (StructuredLogger JSON output) AND Lakebase `schema_detection_events` table, verify server-generated UUID fallback when header not provided per research.md Decision 6
- [X] **T039** [P] [POLISH] Code cleanup: remove any hardcoded test values, add docstrings to all service methods, ensure consistent error handling patterns
- [X] **T040** [P] [POLISH] Update `CLAUDE.md` agent context if new patterns or technologies were introduced per plan.md Constitution Check

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - **BLOCKS all user stories**
- **User Stories (Phase 3, 4, 5)**: All depend on Foundational phase completion
  - User stories can then proceed in **parallel** (if staffed for parallel work)
  - Or sequentially in priority order: **US1 (P1) → US2 (P2) → US3 (P3)**
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - **No dependencies on other stories** - Foundation model detection is self-contained
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - **No dependencies on US1** - MLflow model detection uses separate code path
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - **Depends on US1 and US2** for complete fallback logic (needs to know what "success" looks like to handle failures)

### Within Each User Story

- **Backend before frontend**: Service implementation must complete before frontend integration
- **TypeScript client regeneration** (T019): Must run after backend schema detection endpoint is complete
- **Models → Services → Routers**: Standard layered architecture pattern
- Each story should be independently testable at its checkpoint

### Parallel Opportunities

- **Phase 1 (Setup)**: T001, T002, T003 can run in parallel (different files)
- **Phase 2 (Foundation)**: T006, T007, T008, T009 can run in parallel (different files/methods)
- **User Story 1**: T015 (frontend hook), T016 (status badge component) can start in parallel after T014 (backend complete)
- **User Story 2**: T024 (schema parsing), T025 (logging) can run in parallel with other US2 tasks (independent concerns)
- **Phase 6 (Polish)**: T034, T035, T036, T037, T039, T040 can run in parallel (independent validations)
- **Cross-story parallelism**: If team capacity allows, US1 and US2 can be developed in parallel after Foundation phase completes (separate developers)

---

## Parallel Example: User Story 1 Backend

```bash
# After Foundation phase completes, launch US1 backend tasks:
Task T011: "Implement detect_endpoint_type() for foundation models"
Task T012: "Implement fast-path foundation model detection in detect_schema()"
Task T013: "Add structured logging for foundation model events"

# After T011-T013 complete, launch US1 frontend tasks in parallel:
Task T015: "Create useSchemaCache React hook" 
Task T016: "Create SchemaDetectionStatus badge component"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

**Recommended approach for fastest time-to-value:**

1. ✅ Complete **Phase 1: Setup** (T001-T004) → Database ready
2. ✅ Complete **Phase 2: Foundational** (T005-T010) → Service infrastructure ready
3. ✅ Complete **Phase 3: User Story 1** (T011-T019) → Foundation models working
4. **🛑 STOP and VALIDATE**: 
   - Test with databricks-claude-sonnet-4 endpoint
   - Verify chat format populates in <500ms
   - Verify status badge shows "Foundation Model"
   - Verify browser session cache works
   - Run quickstart.md Example 1 scenario
5. **Deploy/Demo MVP** → Foundation models are the most common use case (addresses 80% of users)

### Incremental Delivery (Recommended)

**Add value progressively after MVP:**

1. MVP deployed → Foundation models working (P1)
2. Add **Phase 4: User Story 2** (T020-T027) → Deploy → MLflow models now supported (P2)
3. Add **Phase 5: User Story 3** (T028-T033) → Deploy → All edge cases handled (P3)
4. Complete **Phase 6: Polish** (T034-T040) → Final production-ready state
5. Each phase adds new capabilities without breaking previous functionality

### Parallel Team Strategy

**If multiple developers available:**

1. **Week 1**: Entire team completes Setup + Foundational together (T001-T010)
2. **Week 2** (after Foundation ready):
   - **Developer A**: User Story 1 (T011-T019) → Foundation models
   - **Developer B**: User Story 2 (T020-T027) → MLflow models
   - **Developer C**: User Story 3 (T028-T033) → Error handling
3. **Week 3**: Team integrates and completes Polish phase together (T034-T040)
4. Stories merge independently without conflicts (different code paths)

---

## Task Count Summary

**Total Tasks**: 40

**By Phase**:
- Phase 1 (Setup): 4 tasks
- Phase 2 (Foundational): 6 tasks
- Phase 3 (User Story 1 - P1): 9 tasks
- Phase 4 (User Story 2 - P2): 8 tasks  
- Phase 5 (User Story 3 - P3): 6 tasks
- Phase 6 (Polish): 7 tasks

**By Story**:
- Setup: 4 tasks
- Foundation: 6 tasks (BLOCKS all user stories)
- User Story 1 (Foundation models): 9 tasks 🎯 MVP
- User Story 2 (MLflow models): 8 tasks
- User Story 3 (Fallback handling): 6 tasks
- Polish/Cross-cutting: 7 tasks

**Parallelizable Tasks**: 15 tasks marked [P] (37.5% can run in parallel when staffed)

**MVP Scope** (Setup + Foundation + US1): 19 tasks → Fastest path to working foundation model detection

---

## Success Metrics (from spec.md)

After completion, validate against success criteria:

- **SC-001**: Foundation model schema detection completes in <500ms ✅ US1
- **SC-002**: MLflow model schema detection completes in <3s ✅ US2
- **SC-003**: Schema detection accuracy ≥95% for model type identification ✅ US1, US2
- **SC-004**: Reduce inference input errors by 60% (measure 400 errors before/after) ✅ All stories
- **SC-005**: First-attempt success rate ≥80% without manual correction ✅ All stories
- **SC-006**: Graceful fallback handling 100% of failures without crashes ✅ US3

---

## Notes

- **[P]** indicates tasks that can run in parallel (different files, no dependencies)
- **[Story]** label maps each task to its user story for traceability (SETUP, FOUNDATION, US1, US2, US3, POLISH)
- **Foundation phase is CRITICAL** - no user story work can begin until T005-T010 are complete
- **Each user story should be independently testable** at its checkpoint before moving to next priority
- **MVP = Setup + Foundation + US1** (19 tasks) delivers foundation model detection, the highest-value feature
- **Tests are NOT included** - no explicit TDD request in spec, rely on manual validation per quickstart.md
- **Commit frequently** - after each task or logical group of related tasks
- **Constitution compliance** validated in plan.md - all principles satisfied ✅

---

**Ready for implementation** ✅ Phase 1 can start immediately

