# Implementation Plan: Fix API Authentication and Implement On-Behalf-Of User (OBO) Authentication

**Branch**: `002-fix-api-authentication` | **Date**: 2025-10-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/specs/002-fix-api-authentication/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code, or `AGENTS.md` for all other agents).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Recent Updates (2025-10-13)

**Documentation Alignment**: The specification and plan have been updated to accurately reflect the current implementation state of Lakebase local connectivity:

- ✅ **spec.md FR-011** now correctly describes OAuth JWT token generation via `generate_database_credential()` API
- ✅ **spec.md FR-012** updated with correct environment variables: PGHOST/LAKEBASE_HOST, LAKEBASE_DATABASE, LAKEBASE_PORT, LAKEBASE_INSTANCE_NAME
- ✅ **Connection string format** corrected to `postgresql+psycopg://<username>:<jwt_token>@...?sslmode=require`
- ✅ **Username extraction** from JWT token's 'sub' field (email) is documented and implemented
- ✅ **Local development** fully functional with automated configuration via `scripts/configure_lakebase.py`
- ✅ **Token auto-refresh** behavior (1-hour expiration) is documented
- ✅ **Documentation references** added: `LAKEBASE_LOCAL_SETUP.md`, `LAKEBASE_FIX_SUMMARY.md`

These changes ensure the specification accurately represents what has been implemented and verified, reducing confusion for future developers and maintainers.

## Summary
Fix the authentication error "more than one authorization method configured: oauth and pat" by implementing proper On-Behalf-Of (OBO) user authentication for Databricks API calls while maintaining service principal authentication for Lakebase database connections. The solution extracts user access tokens from the X-Forwarded-Access-Token header, passes them to Databricks SDK clients with explicit auth_type configuration, and implements comprehensive retry logic, observability, and multi-user data isolation patterns.

**Lakebase Implementation Status**: Local Lakebase connectivity has been successfully implemented and verified. The system uses OAuth JWT tokens generated via `generate_database_credential()` API with service principal credentials. PostgreSQL username is dynamically extracted from the JWT token's 'sub' field using base64 decoding. Tokens expire after 1 hour and are automatically refreshed by the SDK. See `docs/LAKEBASE_LOCAL_SETUP.md` and `LAKEBASE_FIX_SUMMARY.md` for complete implementation details.

## Technical Context
**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, Databricks SDK 0.67.0 (pinned), SQLAlchemy, Pydantic  
**Storage**: Lakebase (PostgreSQL in Databricks) with service principal OAuth JWT token authentication. Username extracted from token's 'sub' field, connection string format: postgresql+psycopg://<username>:<jwt_token>@host:port/db?sslmode=require  
**Testing**: pytest with contract tests, integration tests  
**Target Platform**: Databricks Apps (Linux containers in Databricks platform)
**Project Type**: Web application (React frontend + FastAPI backend)  
**Performance Goals**: <50 concurrent users, <1000 requests/min, authentication adds <10ms per request  
**Constraints**: Authentication retries complete within 5 seconds, upstream API timeout 30 seconds, P95/P99 latencies tracked  
**Scale/Scope**: Multi-user application with row-level data isolation, 25 functional requirements, 13 non-functional requirements

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Design Bricks First
- [x] All UI components use Design Bricks data design system *(N/A - backend authentication only, no UI changes)*
- [x] No custom UI components without Design Bricks availability check *(N/A - no UI changes)*
- [x] Databricks theming and design patterns maintained *(N/A - no UI changes)*

### Lakebase Integration
- [x] Persistent data operations use Lakebase (Postgres in Databricks) *(Already implemented; maintaining service principal auth)*
- [x] Token-based authentication for database access *(Service principal OAuth JWT tokens with username extraction from 'sub' field)*
- [x] Local development configured via environment variables *(PGHOST, LAKEBASE_DATABASE, LAKEBASE_PORT, LAKEBASE_INSTANCE_NAME documented in LAKEBASE_LOCAL_SETUP.md)*
- [x] No external OLTP systems introduced *(No new storage systems)*

### Asset Bundle Deployment
- [x] Deployment managed through Databricks Asset Bundles *(Existing `databricks.yml` will be used)*
- [x] `databricks.yml` configuration present and complete *(Already exists at repository root)*
- [x] No manual workspace uploads or ad-hoc deployments *(Using existing deployment process)*

### Type Safety Throughout
- [x] Python type hints on all functions *(All new auth functions will have type hints)*
- [x] TypeScript strict mode, no `any` types *(Backend-only changes; existing frontend unchanged)*
- [x] Auto-generated TypeScript client from OpenAPI spec *(Will regenerate if endpoint signatures change)*

### Model Serving Integration
- [x] Service abstractions ready for model inference *(Existing ModelServingService will use OBO auth)*
- [x] Model endpoint configuration via environment variables *(No changes to model serving config)*
- [x] Error handling for model serving failures *(Enhanced with retry logic per FR-018)*

### Auto-Generated API Clients
- [x] OpenAPI spec generated from FastAPI *(Automatic via FastAPI)*
- [x] TypeScript client auto-generated on schema changes *(Will regenerate via make_fastapi_client.py)*
- [x] No manual API client code *(Following existing pattern)*

### Development Tooling Standards
- [x] uv for Python package management (not pip/poetry) *(Databricks SDK pinning will use uv)*
- [x] bun for frontend package management (not npm/yarn) *(No frontend dependency changes)*
- [x] Hot reloading enabled for dev workflow *(Existing watch.sh preserved)*

### Observability First (Constitution v1.1.0+)
- [x] Structured logging in JSON format *(FR-017: Log token presence, auth_type, retry attempts, fallback events)*
- [x] Correlation IDs for request tracking *(Will add request_id to all auth logs)*
- [x] Context enrichment with user_id and duration_ms *(FR-010: user_id extraction; NFR-001: <10ms overhead)*
- [x] Performance tracking for API calls *(NFR-011: P95/P99 latencies, retry rates, per-endpoint metrics)*

### Multi-User Data Isolation (Constitution v1.1.0+)
- [x] User identity from Databricks auth context *(FR-010: Extract user_id via UserService.get_user_info())*
- [x] Unity Catalog auto-enforces permissions *(FR-008: User-level permissions enforced)*
- [x] Lakebase queries filtered by user_id *(FR-013: WHERE user_id = ? for all user-scoped queries)*
- [x] Authorization via dependency injection *(FR-002: Pass user token to service layers)*
- [x] Audit logging with user_id *(FR-017: Detailed auth activity logging)*

### Dual Authentication Patterns (Constitution v1.2.0+)
- [x] Service Principal for system operations *(FR-004, FR-011: Lakebase uses service principal auth)*
- [x] On-Behalf-Of-User for user data access *(FR-001, FR-002, FR-003: OBO for Databricks APIs)*
- [x] Clear documentation of both patterns *(Will document in code comments and update docs/)*

## Project Structure

### Documentation (this feature)
```
specs/002-fix-api-authentication/
├── spec.md              # Feature specification (input)
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
│   ├── auth_models.yaml
│   ├── user_endpoints.yaml
│   └── service_layers.yaml
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
server/                  # FastAPI backend (authentication changes here)
├── lib/
│   ├── auth.py          # Authentication middleware and token extraction (MODIFY)
│   ├── structured_logger.py  # Structured logging (ENHANCE with auth details)
│   └── database.py      # Lakebase connection (VERIFY service principal auth)
├── services/
│   ├── user_service.py  # User info retrieval (MODIFY for OBO)
│   ├── unity_catalog_service.py  # UC operations (MODIFY for OBO)
│   ├── model_serving_service.py  # Model serving (MODIFY for OBO)
│   └── lakebase_service.py  # Database operations (VERIFY service principal)
├── routers/
│   ├── user.py          # User endpoints (MODIFY to pass user tokens)
│   ├── unity_catalog.py # UC endpoints (MODIFY to pass user tokens)
│   ├── model_serving.py # Model serving endpoints (MODIFY to pass user tokens)
│   └── lakebase.py      # Lakebase endpoints (VERIFY user_id filtering)
└── models/
    └── user_session.py  # User session model (NEW for user identity)

client/                  # React frontend (minimal changes)
└── src/
    └── fastapi_client/  # Auto-generated API client (REGENERATE)

tests/
├── contract/            # Contract tests (NEW tests for auth behavior)
│   ├── test_auth_contract.py
│   ├── test_user_contract.py
│   └── test_obo_behavior.py
├── integration/
│   ├── test_multi_user_isolation.py  # ENHANCE with auth scenarios
│   └── test_observability.py  # ENHANCE with auth metrics
└── unit/
    └── test_auth_unit.py  # NEW unit tests for auth functions

docs/
├── OBO_AUTHENTICATION.md  # Existing OBO documentation (UPDATE)
├── LAKEBASE_LOCAL_SETUP.md  # Lakebase local setup guide (EXISTING - JWT token extraction documented)
├── LOCAL_DEVELOPMENT.md  # General local development guide (EXISTING)
└── databricks_apis/
    └── authentication_patterns.md  # NEW doc for dual auth patterns

LAKEBASE_FIX_SUMMARY.md  # Historical record of Lakebase local connectivity fix (EXISTING)
```

**Structure Decision**: This is a web application (React frontend + FastAPI backend). Authentication changes are primarily backend-focused in the `server/` directory, specifically in the `lib/auth.py` middleware, service layer components, and router endpoints. Frontend changes are minimal (regenerated API client only). Tests are organized by type: contract tests for API validation, integration tests for multi-user scenarios, and unit tests for authentication logic.

## Post-Design Constitution Re-Check

**Status**: ✅ All Constitutional Requirements Satisfied

After completing Phase 1 design (data-model.md, contracts/, quickstart.md), re-evaluated all constitutional principles:

### Verification Results

1. **Design Bricks First**: ✅ No UI changes required
2. **Lakebase Integration**: ✅ Service principal OAuth JWT token auth implemented and verified. Username extraction from token's 'sub' field working. Local development configuration documented in LAKEBASE_LOCAL_SETUP.md. Enhanced with user_id filtering for data isolation
3. **Asset Bundle Deployment**: ✅ Using existing `databricks.yml`, no changes needed
4. **Type Safety Throughout**: ✅ All models use Pydantic, type hints planned for all functions
5. **Model Serving Integration**: ✅ Enhanced ModelServingService with OBO auth and retry logic
6. **Auto-Generated API Clients**: ✅ Will regenerate client after endpoint signature changes
7. **Development Tooling Standards**: ✅ Using uv to pin SDK to 0.67.0
8. **Observability First**: ✅ Comprehensive structured logging and Prometheus metrics designed
9. **Multi-User Data Isolation**: ✅ user_id filtering enforced in all user-scoped queries
10. **Dual Authentication Patterns**: ✅ Explicitly documented in contracts and research

### Design Artifacts Generated
- ✅ `research.md`: 10 technical decisions documented with rationale
- ✅ `data-model.md`: 10 data models with validation rules and state machines
- ✅ `contracts/auth_models.yaml`: Authentication models and middleware contracts
- ✅ `contracts/user_endpoints.yaml`: User API endpoint contracts with data isolation requirements
- ✅ `contracts/service_layers.yaml`: Service layer patterns and authentication matrix
- ✅ `quickstart.md`: 6-phase testing guide with success criteria

### Complexity Assessment
- **No constitutional violations detected**
- **No deviations requiring justification**
- **All design patterns align with constitutional principles**
- **Stateless authentication design supports future zero-downtime rolling updates** (greenfield deployment but future-ready)

**Conclusion**: Design is constitutionally compliant and ready for task generation (Phase 2).

---

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/bash/update-agent-context.sh cursor`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

### Task Generation Strategy

The `/tasks` command will:
1. Load `.specify/templates/tasks-template.md` as base template
2. Analyze completed design artifacts from Phase 1
3. Generate implementation tasks following TDD principles
4. Order tasks by dependencies and parallel execution opportunities

### Task Categories (Estimated Breakdown)

#### A. Contract Test Tasks (TDD - Write tests first)
From `contracts/*.yaml`:
- Test authentication middleware and token extraction (auth_models.yaml)
- Test user endpoints with OBO authentication (user_endpoints.yaml)
- Test service layer authentication patterns (service_layers.yaml)
- Test retry logic and error handling
- Test multi-user data isolation
- **Estimated**: 8-10 contract test tasks [P] (parallelizable)

#### B. Database Migration Tasks
From `data-model.md` section 5:
- Create Alembic migration for user_id columns
- Add indices for user_id in user_preferences
- Add indices for user_id in model_inference_logs
- Backfill existing records with migration placeholder
- **Estimated**: 2-3 migration tasks (sequential)

#### C. Authentication Implementation Tasks
From `research.md` decisions 1-2:
- Implement middleware for token extraction and correlation IDs
- Implement AuthenticationContext model and request state
- Implement retry decorator with exponential backoff
- Implement automatic fallback logic
- Update structured logger with auth event types
- **Estimated**: 4-5 implementation tasks (some [P])

#### D. Service Layer Modification Tasks
From `contracts/service_layers.yaml`:
- Modify UserService for OBO authentication
- Modify UnityCatalogService for OBO authentication
- Modify ModelServingService for OBO authentication
- Verify LakebaseService uses service principal only
- Add user_id filtering to all Lakebase queries
- **Estimated**: 5-6 modification tasks [P] (parallelizable per service)

#### E. Router/Endpoint Updates
From `contracts/user_endpoints.yaml`:
- Update /api/user/me endpoint to pass user token
- Update /api/user/me/workspace endpoint
- Update /api/preferences endpoints with user_id validation
- Update /api/unity-catalog/* endpoints
- Update /api/model-serving/* endpoints
- **Estimated**: 5-6 endpoint tasks [P] (parallelizable)

#### F. Observability Tasks
From `research.md` decisions 7-8:
- Implement metrics.py with Prometheus metrics
- Add /metrics endpoint
- Update structured_logger.py with correlation ID support
- Add performance tracking to middleware
- **Estimated**: 3-4 observability tasks (some [P])

#### G. Dependency and Configuration Tasks
From `research.md` decision 10:
- Pin Databricks SDK to 0.67.0 using uv
- Update environment variable documentation
- Create scripts/get_user_token.py for local testing
- **Estimated**: 2-3 configuration tasks [P]

#### H. Integration Testing Tasks
From `quickstart.md`:
- Implement multi-user isolation integration tests
- Implement observability validation tests
- Implement error handling integration tests
- **Estimated**: 3-4 integration test tasks

#### I. Documentation Tasks
From project requirements:
- Update docs/OBO_AUTHENTICATION.md
- Create docs/databricks_apis/authentication_patterns.md
- Update README.md with OBO testing instructions
- **Estimated**: 2-3 documentation tasks [P]

#### J. Validation and Deployment Tasks
From `quickstart.md` Phase 6:
- Run contract tests and verify all pass
- Run integration tests and verify isolation
- Test local development with real tokens
- Deploy to dev environment and validate
- Run quickstart manual test scenarios
- **Estimated**: 3-5 validation tasks (sequential)

### Task Ordering Strategy

**Dependency Layers** (execute in order):
1. **Layer 1 (Foundation)**: Dependencies, database migrations, contract tests [P]
2. **Layer 2 (Core Auth)**: Middleware, AuthenticationContext, retry logic [P]
3. **Layer 3 (Services)**: Service layer modifications [P]
4. **Layer 4 (Endpoints)**: Router updates [P]
5. **Layer 5 (Observability)**: Metrics, logging enhancements [P]
6. **Layer 6 (Testing)**: Integration tests, multi-user tests
7. **Layer 7 (Validation)**: Run tests, manual validation, deployment

**Parallel Execution Markers**:
- Tasks marked [P] can be executed in parallel within their layer
- Example: All service modifications can be done simultaneously
- Reduces total implementation time significantly

### Estimated Totals

- **Total Tasks**: 40-50 numbered, ordered tasks
- **Parallelizable Tasks**: ~25-30 tasks (marked [P])
- **Sequential Tasks**: ~15-20 tasks (dependencies)
- **Estimated Implementation Time**: 3-5 days (with parallel execution)
- **Critical Path**: Contract tests → Auth implementation → Service layer → Validation

### Task Template Structure

Each task will include:
```markdown
## Task N: [Task Title]
**Type**: [Contract Test | Implementation | Configuration | Documentation | Validation]
**Priority**: [High | Medium | Low]
**Parallel**: [Yes | No]
**Dependencies**: [List of task numbers]
**Estimated Time**: [Time estimate]

### Description
[What needs to be done]

### Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

### Related Files
- file/path.py (MODIFY)
- test/path.py (CREATE)

### Related Requirements
- FR-XXX: Requirement description
- NFR-XXX: Non-functional requirement
```

### Success Metrics for Phase 2

Phase 2 is complete when:
- All ~40-50 tasks are generated in tasks.md
- Tasks are properly ordered by dependencies
- Parallel execution markers are correct
- Each task has clear acceptance criteria
- Task estimates sum to realistic implementation timeline
- Traceability to requirements is complete

**IMPORTANT**: This phase is executed by the `/tasks` command, NOT by `/plan`

**Next Command**: Run `/tasks` to generate tasks.md from the design artifacts

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command) ✅ 2025-10-10
- [x] Phase 1: Design complete (/plan command) ✅ 2025-10-10
- [x] Phase 2: Task planning approach documented (/plan command) ✅ 2025-10-10
- [ ] Phase 3: Tasks generated (/tasks command) - **NEXT STEP**
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS ✅
- [x] Post-Design Constitution Check: PASS ✅
- [x] All NEEDS CLARIFICATION resolved ✅ (All technical unknowns addressed in research.md)
- [x] Complexity deviations documented: N/A (No deviations required)

**Artifacts Generated**:
- [x] `/specs/002-fix-api-authentication/plan.md` (this file - updated with Lakebase implementation status)
- [x] `/specs/002-fix-api-authentication/spec.md` (updated with JWT username extraction details)
- [x] `/specs/002-fix-api-authentication/research.md` (10 technical decisions)
- [x] `/specs/002-fix-api-authentication/data-model.md` (10 data models)
- [x] `/specs/002-fix-api-authentication/contracts/auth_models.yaml`
- [x] `/specs/002-fix-api-authentication/contracts/user_endpoints.yaml`
- [x] `/specs/002-fix-api-authentication/contracts/service_layers.yaml`
- [x] `/specs/002-fix-api-authentication/quickstart.md` (6-phase test guide)
- [x] `.cursor/rules/specify-rules.mdc` (updated with feature context)
- [x] `docs/LAKEBASE_LOCAL_SETUP.md` (Lakebase local setup guide with JWT token extraction)
- [x] `LAKEBASE_FIX_SUMMARY.md` (Historical record of Lakebase connectivity fix)
- [x] `server/lib/database.py` (OAuth JWT token authentication with username extraction implemented)

**Ready for Phase 3**: Yes - Run `/tasks` command to generate implementation tasks

---
*Based on Constitution v1.2.0 - See `.specify/memory/constitution.md`*
