# Implementation Plan: Databricks App Template with Service Integrations

**Branch**: `001-databricks-integrations` | **Date**: Saturday, October 4, 2025 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/001-databricks-integrations/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → ✅ Loaded successfully
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → ✅ All clarifications resolved (20 Q&A from Session 2025-10-04)
3. Fill the Constitution Check section
   → ✅ Complete
4. Evaluate Constitution Check section
   → ✅ All constitutional requirements align
5. Execute Phase 0 → research.md
   → ✅ Complete (research.md exists with all technical decisions)
6. Execute Phase 1 → contracts, data-model.md, quickstart.md
   → ✅ data-model.md complete
   → ⏳ contracts/ pending update
   → ⏳ quickstart.md pending update
7. Re-evaluate Constitution Check
   → ⏳ Will re-check after Phase 1 complete
8. Plan Phase 2 → Describe task generation approach
   → ⏳ Pending
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 8. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary

This feature builds a comprehensive Databricks App template demonstrating integrations with core platform services: Unity Catalog (lakehouse data), Lakebase (transactional database), Model Serving (ML inference), Asset Bundles (deployment), Design Bricks (UI components), and observability tools. The template serves as an educational resource with production-ready patterns balanced with code clarity, supporting multi-user access with data isolation, dual authentication patterns (service principal + on-behalf-of-user), and comprehensive structured logging with correlation-ID based request tracking.

**Key Clarifications from Specification**:
- **Data Isolation Model**: All Lakebase records are strictly user-isolated (no shared records), eliminating need for concurrent edit conflict resolution
- **Rate Limiting**: Not implemented (acceptable for demo/template purposes, explicitly out of scope)
- **Accessibility**: WCAG 2.1 Level A compliance (keyboard navigation, alt text, labels, contrast ratios)
- **Pagination**: Basic limit/offset pagination for Unity Catalog queries (demonstrates scalable patterns)
- **Environments**: Dev + Prod support only (two tested configurations)
- **Performance Target**: Balanced approach - demonstrate scalable patterns while keeping code readable for learning

## Technical Context

**Language/Version**: Python 3.11+ (modern type hints), Node.js 18.0+ (TypeScript 5.2+, Vite 5.0)  
**Primary Dependencies**:
- Backend: FastAPI, Databricks SDK, SQLAlchemy, psycopg2 (Lakebase), httpx (async HTTP), Pydantic
- Frontend: React, TypeScript, Design Bricks UI, Vite, Bun
- Tooling: uv (Python), bun (frontend), ruff (linting), mypy (type checking)

**Storage**:
- Unity Catalog: Lakehouse data with fine-grained access control (read-only queries)
- Lakebase: Postgres-hosted transactional data (user preferences, application state, inference logs) with user_id-scoped records

**Testing**: 
- Contract testing from OpenAPI specs (TDD approach)
- FastAPI `/docs` endpoint validation
- Multi-user isolation testing with multiple accounts
- Integration testing via deployed app
- Log monitoring with `dba_logz.py`

**Target Platform**: Databricks Apps (serverless compute), Modern browsers (ES2020+, Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)

**Project Type**: Web application (frontend + backend)

**Performance Goals**:
- <500ms API response time for paginated Unity Catalog queries (≤100 rows per page)
- <2s model inference latency with standard input payload
- Support 10 concurrent users with <20% latency increase from baseline

**Constraints**:
- WCAG 2.1 Level A accessibility (keyboard navigation, alt text, form labels, 3:1 contrast for large text, 4.5:1 for normal text)
- No rate limiting (out of scope for template)
- No shared records in Lakebase (all user-scoped, no conflict resolution)
- Connection pooling: ≥10 connections for scalability demonstration
- Sample data limits: ≤1 catalog, ≤2 schemas, ≤3 tables with ≤100 rows each, ≤5 Lakebase sample records

**Scale/Scope**: Educational template for 10-100 developers, demonstrating 6 core service integrations, 15 functional requirements, 4 non-functional requirements, supporting dev + prod environments

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Design Bricks First ✅
- [x] All UI components use Design Bricks data design system (migration from shadcn/ui documented in research.md)
- [x] No custom UI components without Design Bricks availability check (component mapping table in research.md)
- [x] Databricks theming and design patterns maintained (Design Bricks provides native Databricks look-and-feel)

**Implementation**: Migrate WelcomePage from shadcn/ui to Design Bricks components (`<databricks-button>`, `<databricks-card>`, `<databricks-input>`, `<databricks-tag>`, `<databricks-banner>`, `<databricks-skeleton>`)

### Lakebase Integration ✅
- [x] Persistent data operations use Lakebase (Postgres in Databricks) for user preferences, application state, model inference logs
- [x] Token-based authentication for database access (connection string with token)
- [x] No external OLTP systems introduced (all transactional data in Lakebase)
- [x] SQLAlchemy ORM with psycopg2 driver, QueuePool connection pooling (5-10 connections)
- [x] Alembic for schema migrations

**Tables**: `user_preferences`, `model_inference_logs` (defined in data-model.md)

### Asset Bundle Deployment ✅
- [x] Deployment managed through Databricks Asset Bundles (`databricks bundle deploy`)
- [x] `databricks.yml` configuration present with dev and prod targets (research.md section 7)
- [x] No manual workspace uploads or ad-hoc deployments
- [x] Validation with `databricks bundle validate` before deployment (EC-005 compliance)

### Type Safety Throughout ✅
- [x] Python type hints on all functions (≥80% type coverage, verified via mypy --strict)
- [x] TypeScript strict mode, no `any` types without justification
- [x] Auto-generated TypeScript client from OpenAPI spec (FastAPI auto-generates spec)
- [x] Pydantic models for all entities (data-model.md defines 7 entity models)

### Model Serving Integration ✅
- [x] Service abstractions ready for model inference (ModelServingService in research.md)
- [x] Model endpoint configuration via environment variables (`MODEL_SERVING_ENDPOINT`, `MODEL_SERVING_TIMEOUT`)
- [x] Error handling for model serving failures (EC-001: MODEL_UNAVAILABLE error response)
- [x] Timeout configuration (30s default, 300s max)
- [x] Retry logic with exponential backoff for transient errors

**Capabilities**: Mandatory invoke_model (inference), SHOULD list_endpoints/get_endpoint (metadata for UI/debugging)

### Auto-Generated API Clients ✅
- [x] OpenAPI spec generated from FastAPI (accessible at `/docs` and `/openapi.json`)
- [x] TypeScript client auto-generated on schema changes (scripts/make_fastapi_client.py)
- [x] No manual API client code
- [x] Client regeneration in watch/dev workflow

### Development Tooling Standards ✅
- [x] uv for Python package management (not pip/poetry)
- [x] bun for frontend package management (not npm/yarn)
- [x] Hot reloading enabled for dev workflow (`./watch.sh` with nohup and logging)
- [x] Python 3.11+ required (modern type hints and performance)
- [x] Node.js 18.0+ required (TypeScript 5.2+ and Vite 5.0)

### Observability First ✅
- [x] Structured logging in JSON format (timestamp, log level, message, module, function, user_id, duration_ms)
- [x] Correlation IDs for request tracking (contextvars-based, not full OpenTelemetry)
- [x] ERROR level logging for all failures with full context (EC-001 through EC-005 specify error logging)
- [x] No PII/tokens in logs
- [x] Performance tracking (log execution time for API calls, DB queries, model inference)

**Implementation**: StructuredLogger class with JSONFormatter, FastAPI middleware for correlation ID injection (research.md section 5)

### Multi-User Data Isolation ✅
- [x] User identity extracted from Databricks authentication context (`WorkspaceClient.current_user.me()`)
- [x] Unity Catalog enforces table/column permissions automatically (user context passed to queries)
- [x] Lakebase queries always filter by user_id in WHERE clauses (all records user-scoped)
- [x] FastAPI dependency injection for user_id in endpoints
- [x] Multi-user isolation testing required (multiple accounts)
- [x] Audit logging with user_id for compliance

**Data Model**: All Lakebase records strictly user-isolated (no shared records, no concurrent edit conflicts - clarification from spec)

## Project Structure

### Documentation (this feature)
```
specs/001-databricks-integrations/
├── spec.md              # Feature specification (COMPLETE)
├── plan.md              # This file (IN PROGRESS)
├── research.md          # Phase 0 output (COMPLETE)
├── data-model.md        # Phase 1 output (COMPLETE)
├── quickstart.md        # Phase 1 output (PENDING)
├── contracts/           # Phase 1 output (PENDING UPDATE)
│   ├── lakebase_api.yaml         # Lakebase CRUD endpoints
│   ├── unity_catalog_api.yaml    # Unity Catalog query endpoints
│   └── model_serving_api.yaml    # Model inference endpoints
├── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
├── ANALYSIS_REMEDIATION.md  # Existing analysis document
└── [Other docs]
```

### Source Code (repository root)
```
# Web application structure (frontend + backend detected)
backend/
├── server/
│   ├── __init__.py
│   ├── app.py                          # FastAPI app with correlation ID middleware
│   ├── make_openapi.py                 # OpenAPI spec generator
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── user.py                     # User info endpoints (EXISTING)
│   │   ├── unity_catalog.py            # Unity Catalog query endpoints (NEW)
│   │   ├── lakebase.py                 # Lakebase CRUD endpoints (NEW)
│   │   └── model_serving.py            # Model inference endpoints (NEW)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── user_service.py             # User info service (EXISTING)
│   │   ├── unity_catalog_service.py    # Unity Catalog integration (NEW)
│   │   ├── lakebase_service.py         # Lakebase integration (NEW)
│   │   └── model_serving_service.py    # Model Serving integration (NEW)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user_session.py             # UserSession Pydantic model (NEW)
│   │   ├── data_source.py              # DataSource model (NEW)
│   │   ├── query_result.py             # QueryResult model (NEW)
│   │   ├── user_preference.py          # UserPreference SQLAlchemy model (NEW)
│   │   ├── model_endpoint.py           # ModelEndpoint model (NEW)
│   │   └── model_inference.py          # Inference request/response models (NEW)
│   └── lib/
│       ├── __init__.py
│       ├── structured_logger.py        # StructuredLogger with JSON formatting (NEW)
│       ├── distributed_tracing.py      # Correlation ID contextvars (NEW)
│       └── database.py                 # Lakebase connection pooling (NEW)
└── tests/
    ├── contract/
    │   ├── test_unity_catalog_contract.py    # Contract tests for UC API (NEW)
    │   ├── test_lakebase_contract.py         # Contract tests for Lakebase API (NEW)
    │   └── test_model_serving_contract.py    # Contract tests for Model Serving API (NEW)
    ├── integration/
    │   ├── test_multi_user_isolation.py      # Multi-user data isolation tests (NEW)
    │   └── test_observability.py             # Logging/correlation ID tests (NEW)
    └── unit/

frontend/
├── client/
│   ├── src/
│   │   ├── App.tsx                     # Main app component (EXISTING)
│   │   ├── main.tsx                    # App entry point (EXISTING)
│   │   ├── components/
│   │   │   └── ui/                     # Design Bricks components (MIGRATE from shadcn/ui)
│   │   │       ├── DataTable.tsx       # Unity Catalog data table with pagination (NEW)
│   │   │       ├── PreferencesForm.tsx # User preferences CRUD form (NEW)
│   │   │       └── ModelInvokeForm.tsx # Model inference form (NEW)
│   │   ├── pages/
│   │   │   └── WelcomePage.tsx         # Welcome page (MIGRATE to Design Bricks)
│   │   ├── fastapi_client/             # Auto-generated API client (REGENERATE)
│   │   │   ├── services/
│   │   │   │   ├── UnityCatalogService.ts  # UC endpoints (NEW)
│   │   │   │   ├── LakebaseService.ts      # Lakebase endpoints (NEW)
│   │   │   │   └── ModelServingService.ts  # Model Serving endpoints (NEW)
│   │   │   └── models/                     # TypeScript models (NEW)
│   │   └── lib/
│   │       └── utils.ts                # Utilities (EXISTING)
│   └── tests/

scripts/
├── setup_sample_data.py                # Sample data creation (NEW - per research.md)
├── make_fastapi_client.py              # Client generator (EXISTING)
└── generate_semver_requirements.py     # Dependency generator (EXISTING)

migrations/                             # Alembic migrations for Lakebase schemas (NEW)
├── env.py
├── script.py.mako
└── versions/
    ├── 001_create_user_preferences.py
    └── 002_create_model_inference_logs.py

databricks.yml                          # Asset Bundle config (UPDATE with new env vars)
requirements.txt                        # Python dependencies (UPDATE - add SQLAlchemy, psycopg2, alembic)
pyproject.toml                          # Python project config (UPDATE)
```

**Structure Decision**: Web application with backend (FastAPI) and frontend (React + TypeScript + Design Bricks). Existing structure maintained with new routers, services, models, and UI components added for Databricks service integrations.

## Phase 0: Outline & Research ✅

**Status**: COMPLETE

**Output**: research.md with 8 comprehensive sections covering all technical decisions:

1. **Unity Catalog Integration**: Databricks SDK `WorkspaceClient` with SQL Warehouse execution, built-in access control
2. **Lakebase Integration**: SQLAlchemy + psycopg2 with QueuePool (5-10 connections), token-based auth
3. **Model Serving Integration**: Databricks SDK + httpx, 30s timeout, exponential backoff retry
4. **Design Bricks UI Migration**: Component mapping from shadcn/ui to Design Bricks, incremental migration plan
5. **Observability Patterns**: StructuredLogger with JSON formatting, correlation-ID based tracing (contextvars, not OpenTelemetry)
6. **Multi-User Data Isolation**: Unity Catalog ACLs + Lakebase user_id filtering, FastAPI dependency injection
7. **Asset Bundle Configuration**: databricks.yml with dev/prod targets, environment variables, permissions
8. **Sample Data Setup**: Python script for minimal UC/Lakebase sample data (≤100 rows per table)

**Dependencies Identified**:
- Python: sqlalchemy>=2.0.0, psycopg2-binary>=2.9.0, alembic>=1.13.0, httpx>=0.25.0
- TypeScript: @databricks/design-bricks>=1.0.0

**All NEEDS CLARIFICATION Resolved**: No unknowns remain (20 clarifications answered in spec Session 2025-10-04)

## Phase 1: Design & Contracts

*Prerequisites: research.md complete ✅*

### 1. Data Model ✅
**Status**: COMPLETE (data-model.md exists)

**Entities Defined** (7 total):
1. **UserSession**: Authenticated user session (in-memory, ephemeral)
2. **DataSource**: Unity Catalog table metadata (UC-managed)
3. **QueryResult**: Unity Catalog query execution result (in-memory)
4. **UserPreference**: User-specific application state (Lakebase table, user_id-scoped)
5. **ModelEndpoint**: Model Serving endpoint metadata (Databricks Model Serving)
6. **ModelInferenceRequest**: Model inference request (in-memory)
7. **ModelInferenceResponse**: Model inference result (Lakebase logs table)

**Database Schemas** (Lakebase):
- `user_preferences` table: id (PK), user_id (indexed), preference_key, preference_value (JSONB), timestamps
- `model_inference_logs` table: id (PK), request_id, endpoint_name, user_id (indexed), inputs, predictions, status, execution_time_ms, error_message, timestamps

**Uniqueness Constraints**:
- UserPreference: UNIQUE(user_id, preference_key) - user-scoped composite key
- All records strictly user-isolated (no shared records per spec clarification)

**Validation Rules**:
- All user_id fields must match authenticated user (data isolation)
- Query safety: SELECT only (no INSERT/UPDATE/DELETE)
- Access checks before operations (Unity Catalog access_level, ModelEndpoint state)

### 2. API Contracts (PENDING UPDATE)

**Contract Files to Generate/Update**:

#### A. `contracts/unity_catalog_api.yaml`
```yaml
openapi: 3.0.3
info:
  title: Unity Catalog API
  version: 1.0.0
paths:
  /api/unity-catalog/tables:
    get:
      summary: List accessible Unity Catalog tables
      parameters:
        - name: catalog
          in: query
          schema:
            type: string
          description: Catalog name filter (optional)
        - name: schema
          in: query
          schema:
            type: string
          description: Schema name filter (optional)
      responses:
        '200':
          description: List of tables user has access to
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/DataSource'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
  
  /api/unity-catalog/query:
    post:
      summary: Execute SELECT query on Unity Catalog table (with basic pagination)
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - catalog
                - schema
                - table
              properties:
                catalog:
                  type: string
                schema:
                  type: string
                table:
                  type: string
                limit:
                  type: integer
                  default: 100
                  minimum: 1
                  maximum: 1000
                  description: Number of rows per page
                offset:
                  type: integer
                  default: 0
                  minimum: 0
                  description: Offset for pagination
                filters:
                  type: object
                  description: Optional column filters
      responses:
        '200':
          description: Query executed successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/QueryResult'
        '400':
          description: Invalid query (non-SELECT or malformed)
        '403':
          $ref: '#/components/responses/CatalogPermissionDenied'
        '404':
          description: Table not found
        '503':
          description: Database unavailable (EC-002)

components:
  schemas:
    DataSource:
      type: object
      required:
        - catalog_name
        - schema_name
        - table_name
        - full_name
        - columns
        - owner
        - access_level
      properties:
        catalog_name:
          type: string
        schema_name:
          type: string
        table_name:
          type: string
        full_name:
          type: string
          description: Fully qualified name (catalog.schema.table)
        columns:
          type: array
          items:
            type: object
            required:
              - name
              - data_type
            properties:
              name:
                type: string
              data_type:
                type: string
              nullable:
                type: boolean
        row_count:
          type: integer
          nullable: true
        size_bytes:
          type: integer
          nullable: true
        owner:
          type: string
        access_level:
          type: string
          enum: [READ, WRITE, NONE]
        last_refreshed:
          type: string
          format: date-time
    
    QueryResult:
      type: object
      required:
        - query_id
        - rows
        - row_count
        - execution_time_ms
        - status
      properties:
        query_id:
          type: string
        data_source:
          $ref: '#/components/schemas/DataSource'
        sql_statement:
          type: string
        rows:
          type: array
          items:
            type: object
        row_count:
          type: integer
        execution_time_ms:
          type: integer
        user_id:
          type: string
        executed_at:
          type: string
          format: date-time
        status:
          type: string
          enum: [PENDING, RUNNING, SUCCEEDED, FAILED]
        error_message:
          type: string
          nullable: true
  
  responses:
    Unauthorized:
      description: Missing or invalid credentials (EC-003)
      content:
        application/json:
          schema:
            type: object
            properties:
              error_code:
                type: string
                example: AUTH_REQUIRED
              message:
                type: string
              technical_details:
                type: object
    Forbidden:
      description: Insufficient permissions (EC-003)
      content:
        application/json:
          schema:
            type: object
            properties:
              error_code:
                type: string
                example: PERMISSION_DENIED
              message:
                type: string
              technical_details:
                type: object
    CatalogPermissionDenied:
      description: No access to Unity Catalog table (EC-004)
      content:
        application/json:
          schema:
            type: object
            required:
              - error_code
              - message
              - technical_details
            properties:
              error_code:
                type: string
                example: CATALOG_PERMISSION_DENIED
              message:
                type: string
                example: You don't have access to this table.
              technical_details:
                type: object
                properties:
                  catalog:
                    type: string
                  schema:
                    type: string
                  table:
                    type: string
```

#### B. `contracts/lakebase_api.yaml`
```yaml
openapi: 3.0.3
info:
  title: Lakebase (Transactional Data) API
  version: 1.0.0
paths:
  /api/preferences:
    get:
      summary: Get user preferences (user-scoped, data isolated)
      parameters:
        - name: preference_key
          in: query
          schema:
            type: string
          description: Specific preference key (optional, returns all if omitted)
      responses:
        '200':
          description: User preferences retrieved
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/UserPreference'
        '503':
          $ref: '#/components/responses/DatabaseUnavailable'
    
    post:
      summary: Create or update user preference (user-scoped)
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - preference_key
                - preference_value
              properties:
                preference_key:
                  type: string
                  enum: [dashboard_layout, favorite_tables, theme]
                preference_value:
                  type: object
                  description: JSON preference data
      responses:
        '200':
          description: Preference created/updated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserPreference'
        '400':
          description: Invalid preference data
        '503':
          $ref: '#/components/responses/DatabaseUnavailable'
  
  /api/preferences/{preference_key}:
    delete:
      summary: Delete user preference (user-scoped)
      parameters:
        - name: preference_key
          in: path
          required: true
          schema:
            type: string
      responses:
        '204':
          description: Preference deleted
        '404':
          description: Preference not found for this user
        '503':
          $ref: '#/components/responses/DatabaseUnavailable'

components:
  schemas:
    UserPreference:
      type: object
      required:
        - id
        - user_id
        - preference_key
        - preference_value
        - created_at
        - updated_at
      properties:
        id:
          type: integer
        user_id:
          type: string
          description: Always matches authenticated user (data isolation)
        preference_key:
          type: string
          enum: [dashboard_layout, favorite_tables, theme]
        preference_value:
          type: object
          description: JSON preference data (max 100KB)
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time
  
  responses:
    DatabaseUnavailable:
      description: Lakebase connection failure (EC-002)
      content:
        application/json:
          schema:
            type: object
            required:
              - error_code
              - message
              - technical_details
              - retry_after
            properties:
              error_code:
                type: string
                example: DATABASE_UNAVAILABLE
              message:
                type: string
                example: Database service temporarily unavailable.
              technical_details:
                type: object
                properties:
                  error_type:
                    type: string
              retry_after:
                type: integer
                example: 10
```

#### C. `contracts/model_serving_api.yaml`
```yaml
openapi: 3.0.3
info:
  title: Model Serving API
  version: 1.0.0
paths:
  /api/model-serving/endpoints:
    get:
      summary: List available Model Serving endpoints (SHOULD capability for UI/debugging)
      responses:
        '200':
          description: List of endpoints
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/ModelEndpoint'
        '401':
          $ref: '#/components/responses/Unauthorized'
  
  /api/model-serving/invoke:
    post:
      summary: Invoke model for inference (MUST capability - mandatory)
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - endpoint_name
                - inputs
              properties:
                endpoint_name:
                  type: string
                inputs:
                  type: object
                  description: Model input data (format depends on model)
                timeout_seconds:
                  type: integer
                  default: 30
                  minimum: 1
                  maximum: 300
      responses:
        '200':
          description: Inference successful
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ModelInferenceResponse'
        '400':
          description: Invalid input data
        '503':
          $ref: '#/components/responses/ModelUnavailable'

components:
  schemas:
    ModelEndpoint:
      type: object
      required:
        - endpoint_name
        - model_name
        - state
      properties:
        endpoint_name:
          type: string
        endpoint_id:
          type: string
        model_name:
          type: string
        model_version:
          type: string
        state:
          type: string
          enum: [CREATING, READY, UPDATING, FAILED]
        workload_url:
          type: string
        creation_timestamp:
          type: string
          format: date-time
        last_updated_timestamp:
          type: string
          format: date-time
    
    ModelInferenceResponse:
      type: object
      required:
        - request_id
        - endpoint_name
        - status
        - execution_time_ms
        - completed_at
      properties:
        request_id:
          type: string
        endpoint_name:
          type: string
        predictions:
          type: object
        status:
          type: string
          enum: [SUCCESS, ERROR, TIMEOUT]
        execution_time_ms:
          type: integer
        error_message:
          type: string
          nullable: true
        completed_at:
          type: string
          format: date-time
  
  responses:
    ModelUnavailable:
      description: Model Serving endpoint unavailable (EC-001)
      content:
        application/json:
          schema:
            type: object
            required:
              - error_code
              - message
              - technical_details
              - retry_after
            properties:
              error_code:
                type: string
                example: MODEL_UNAVAILABLE
              message:
                type: string
                example: Model service temporarily unavailable. Please try again in a few moments.
              technical_details:
                type: object
                properties:
                  endpoint:
                    type: string
                  status:
                    type: integer
              retry_after:
                type: integer
                example: 30
    Unauthorized:
      description: Missing or invalid credentials (EC-003)
      content:
        application/json:
          schema:
            type: object
            properties:
              error_code:
                type: string
                example: AUTH_REQUIRED
              message:
                type: string
              technical_details:
                type: object
```

### 3. Contract Tests (TO GENERATE)

**Contract test files to create** (TDD approach - tests created before implementation):

- `tests/contract/test_unity_catalog_contract.py`: Validate Unity Catalog API endpoints match OpenAPI spec
- `tests/contract/test_lakebase_contract.py`: Validate Lakebase API endpoints match OpenAPI spec
- `tests/contract/test_model_serving_contract.py`: Validate Model Serving API endpoints match OpenAPI spec

**Test Structure** (example for Unity Catalog):
```python
import pytest
from fastapi.testclient import TestClient
from server.app import app

client = TestClient(app)

def test_list_tables_contract():
    """Contract test: GET /api/unity-catalog/tables matches OpenAPI spec."""
    response = client.get("/api/unity-catalog/tables")
    assert response.status_code in [200, 401, 403]
    
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)
        for table in data:
            assert "catalog_name" in table
            assert "schema_name" in table
            assert "table_name" in table
            assert "full_name" in table
            assert "access_level" in table
            assert table["access_level"] in ["READ", "WRITE", "NONE"]

def test_query_table_contract():
    """Contract test: POST /api/unity-catalog/query matches OpenAPI spec."""
    payload = {
        "catalog": "main",
        "schema": "samples",
        "table": "demo_data",
        "limit": 10,
        "offset": 0
    }
    response = client.post("/api/unity-catalog/query", json=payload)
    assert response.status_code in [200, 400, 403, 404, 503]
    
    if response.status_code == 200:
        data = response.json()
        assert "query_id" in data
        assert "rows" in data
        assert "row_count" in data
        assert "execution_time_ms" in data
        assert "status" in data
        assert data["status"] in ["PENDING", "RUNNING", "SUCCEEDED", "FAILED"]
        assert isinstance(data["rows"], list)
        assert data["row_count"] == len(data["rows"])
```

**Expected Result**: All contract tests MUST fail initially (no implementation yet). This validates TDD approach.

### 4. Quickstart Documentation (TO CREATE)

**File**: `quickstart.md`

**Structure**:
```markdown
# Quickstart: Databricks App Template

## Prerequisites
- Python 3.11+, Node.js 18.0+
- Databricks workspace with Unity Catalog enabled
- Lakebase provisioned
- Model Serving endpoint created (see docs/databricks_apis/model_serving_setup.md)

## Setup

### 1. Install Dependencies
```bash
# Backend
uv sync

# Frontend
cd client && bun install
```

### 2. Configure Environment
```bash
cp .env.local.example .env.local
# Edit .env.local with your Databricks credentials and resource IDs
```

### 3. Create Sample Data (Optional)
```bash
python scripts/setup_sample_data.py --create-all
```

### 4. Run Database Migrations
```bash
alembic upgrade head
```

### 5. Start Development Server
```bash
./watch.sh
```

### 6. Verify Deployment
```bash
# Check logs
python dba_logz.py

# Test endpoints
python dba_client.py
```

## Testing User Stories

### Story 1: View Unity Catalog Data
1. Navigate to http://localhost:8000
2. Click "Unity Catalog" tab
3. Select catalog/schema/table from dropdowns
4. Click "Query" - table displays with pagination controls
5. **Success**: Data displays, page navigation works, <500ms response time

### Story 2: Manage User Preferences (CRUD Operations)
1. Navigate to "Preferences" tab
2. Create new preference: theme = "dark"
3. Update preference: theme = "light"
4. Delete preference
5. **Success**: All CRUD operations complete, confirmation shown, data isolated to your user

### Story 3: Invoke Model for Inference
1. Navigate to "Model Serving" tab
2. Select endpoint from dropdown
3. Enter input data (JSON format)
4. Click "Invoke"
5. **Success**: Predictions display, <2s latency, inference logged

### Story 4: Deploy to Production
```bash
# Validate bundle
databricks bundle validate

# Deploy to dev
databricks bundle deploy -t dev

# Deploy to prod (with permissions check)
databricks bundle deploy -t prod
```
**Success**: Deployment completes, app accessible in Databricks workspace

### Story 5-9: [Additional stories mapped from spec acceptance scenarios]

## Multi-User Testing
```bash
# Test with User A
DATABRICKS_TOKEN=<user_a_token> python dba_client.py

# Test with User B (verify data isolation)
DATABRICKS_TOKEN=<user_b_token> python dba_client.py
```
**Success**: Each user sees only their own preferences, Unity Catalog enforces table permissions

## Troubleshooting
- **EC-001**: Model endpoint unavailable → Check endpoint state is READY
- **EC-002**: Lakebase connection failure → Verify LAKEBASE_TOKEN and connection string
- **EC-003**: Authentication failure → Regenerate DATABRICKS_TOKEN
- **EC-004**: Unity Catalog permission denied → Check table grants with `SHOW GRANTS ON TABLE`
- **EC-005**: Bundle validation failure → Run `databricks bundle validate` and fix errors
```

### 5. Update Agent Context File

**Command**: `.specify/scripts/bash/update-agent-context.sh cursor`

**Purpose**: Incrementally update CLAUDE.md with new feature context (O(1) operation, preserves manual additions)

**Expected Updates**:
- Add Unity Catalog, Lakebase, Model Serving integration commands
- Add new dependencies (SQLAlchemy, psycopg2, alembic, Design Bricks)
- Add new environment variables (LAKEBASE_*, MODEL_SERVING_*)
- Preserve existing manual additions between markers
- Keep under 150 lines for token efficiency

**Output**: CLAUDE.md at repository root

## Phase 1 Status

- [x] Data model complete (data-model.md)
- [ ] API contracts generated (unity_catalog_api.yaml, lakebase_api.yaml, model_serving_api.yaml) - **IN PROGRESS**
- [ ] Contract tests created (test_*_contract.py) - **PENDING**
- [ ] Quickstart documentation written (quickstart.md) - **PENDING**
- [ ] Agent context file updated (CLAUDE.md) - **PENDING**

**Next Action**: Generate contract YAML files, then create contract tests, then write quickstart.md, then run update-agent-context.sh

## Phase 1 Re-Evaluation (Constitution Check)

*Will re-check after all Phase 1 artifacts complete*

**Expected Result**: All constitutional requirements still satisfied after design phase

**Potential Risks**:
- Design Bricks migration may reveal missing components → Fallback to shadcn/ui with justification in Complexity Tracking (if needed)
- Lakebase connection pooling may need tuning → Adjust pool_size based on load testing
- Model Serving timeout may need adjustment per model → Make timeout configurable per endpoint

**Mitigation**: All risks have documented alternatives in research.md

## Phase 2: Task Planning Approach

*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Each contract → contract test task [P]
- Each entity → model creation task [P]
- Each user story → integration test task
- Implementation tasks to make tests pass
- Design Bricks migration tasks (page-by-page)
- Observability instrumentation tasks (logging, correlation IDs)

**Ordering Strategy** (TDD + Dependency Order):

1. **Setup Tasks** [P - parallel]:
   - Task 001: Add Python dependencies (sqlalchemy, psycopg2, alembic)
   - Task 002: Add TypeScript dependencies (@databricks/design-bricks)
   - Task 003: Create Alembic migration for user_preferences table
   - Task 004: Create Alembic migration for model_inference_logs table

2. **Contract Test Tasks** [P - all can run in parallel, will fail initially]:
   - Task 005: Generate Unity Catalog contract tests (test_unity_catalog_contract.py)
   - Task 006: Generate Lakebase contract tests (test_lakebase_contract.py)
   - Task 007: Generate Model Serving contract tests (test_model_serving_contract.py)

3. **Model Creation Tasks** [P]:
   - Task 008: Create UserSession Pydantic model (models/user_session.py)
   - Task 009: Create DataSource Pydantic model (models/data_source.py)
   - Task 010: Create QueryResult Pydantic model (models/query_result.py)
   - Task 011: Create UserPreference SQLAlchemy model (models/user_preference.py)
   - Task 012: Create ModelEndpoint Pydantic model (models/model_endpoint.py)
   - Task 013: Create ModelInference Pydantic models (models/model_inference.py)

4. **Service Layer Tasks** [depends on models]:
   - Task 014: Implement UnityCatalogService (services/unity_catalog_service.py)
   - Task 015: Implement LakebaseService (services/lakebase_service.py)
   - Task 016: Implement ModelServingService (services/model_serving_service.py)

5. **Observability Infrastructure** [P]:
   - Task 017: Implement StructuredLogger (lib/structured_logger.py)
   - Task 018: Implement correlation ID contextvars (lib/distributed_tracing.py)
   - Task 019: Add FastAPI middleware for correlation ID injection (app.py)

6. **Router/API Tasks** [depends on services]:
   - Task 020: Implement Unity Catalog router (routers/unity_catalog.py)
   - Task 021: Implement Lakebase router (routers/lakebase.py)
   - Task 022: Implement Model Serving router (routers/model_serving.py)
   - Task 023: Integrate routers into FastAPI app (app.py)

7. **Contract Test Validation** [depends on routers]:
   - Task 024: Run contract tests - ALL MUST PASS before continuing
   - Task 025: Fix any contract violations

8. **Frontend Migration Tasks** (sequential per page):
   - Task 026: Migrate WelcomePage to Design Bricks components
   - Task 027: Create DataTable component with pagination (Design Bricks)
   - Task 028: Create PreferencesForm component (Design Bricks)
   - Task 029: Create ModelInvokeForm component (Design Bricks)

9. **Frontend API Integration** [depends on components]:
   - Task 030: Regenerate TypeScript client (make_fastapi_client.py)
   - Task 031: Integrate Unity Catalog API in UI
   - Task 032: Integrate Lakebase API in UI
   - Task 033: Integrate Model Serving API in UI

10. **Integration Testing** [depends on full stack]:
    - Task 034: Test multi-user data isolation (Story 8)
    - Task 035: Test observability (correlation IDs in logs)
    - Task 036: Test WCAG 2.1 Level A accessibility (keyboard navigation, alt text)
    - Task 037: Test pagination performance (NFR-003)

11. **Sample Data & Deployment**:
    - Task 038: Implement sample data setup script (scripts/setup_sample_data.py)
    - Task 039: Update databricks.yml with new environment variables
    - Task 040: Validate Asset Bundle (databricks bundle validate)

12. **Documentation & Quickstart**:
    - Task 041: Write quickstart.md with all user stories
    - Task 042: Update README with integration instructions
    - Task 043: Update agent context file (update-agent-context.sh cursor)

13. **Validation Tasks**:
    - Task 044: Execute quickstart.md end-to-end
    - Task 045: Run dba_logz.py and verify structured logs with correlation IDs
    - Task 046: Deploy to dev and test all integrations
    - Task 047: Deploy to prod and validate permissions

**Estimated Output**: 47 numbered, ordered tasks in tasks.md

**Parallel Execution Markers**: [P] indicates tasks that can run in parallel (independent files/modules)

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation

*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md with 47 tasks)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles + TDD approach)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation per NFR-003, accessibility validation per NFR-004)

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

**Status**: No constitutional violations detected. All principles satisfied by current design.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | - | - |

**Justifications** (if needed in future):
- If Design Bricks component unavailable → Fallback to shadcn/ui with documented justification and migration plan
- If connection pooling causes issues → Reduce pool_size with performance implications documented

## Progress Tracking

*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command) - research.md exists
- [x] Phase 1: Design partially complete (/plan command) - data-model.md exists, contracts pending
- [ ] Phase 1: Contracts complete - PENDING (unity_catalog_api.yaml, lakebase_api.yaml, model_serving_api.yaml)
- [ ] Phase 1: Contract tests complete - PENDING (test_*_contract.py)
- [ ] Phase 1: Quickstart complete - PENDING (quickstart.md)
- [ ] Phase 1: Agent context updated - PENDING (CLAUDE.md)
- [ ] Phase 2: Task planning approach described - COMPLETE (see Phase 2 section above)
- [ ] Phase 3: Tasks generated (/tasks command) - NOT STARTED
- [ ] Phase 4: Implementation complete - NOT STARTED
- [ ] Phase 5: Validation passed - NOT STARTED

**Gate Status**:
- [x] Initial Constitution Check: PASS (all 8 principles satisfied)
- [ ] Post-Design Constitution Check: PENDING (will re-check after Phase 1 complete)
- [x] All NEEDS CLARIFICATION resolved (20 Q&A in spec Session 2025-10-04)
- [x] Complexity deviations documented (none required)

**Key Clarifications Integrated**:
- [x] User-isolated records (no concurrent edit conflicts)
- [x] No rate limiting (out of scope)
- [x] WCAG 2.1 Level A accessibility
- [x] Basic pagination (limit/offset)
- [x] Dev + Prod environments only
- [x] Balanced performance (scalable patterns + code clarity)

---

**Next Steps**:
1. Generate contract YAML files (unity_catalog_api.yaml, lakebase_api.yaml, model_serving_api.yaml)
2. Create contract test files (test_*_contract.py)
3. Write quickstart.md with all user stories
4. Run `.specify/scripts/bash/update-agent-context.sh cursor` to update CLAUDE.md
5. Re-evaluate Constitution Check
6. Proceed to `/tasks` command to generate tasks.md

**Status**: Phase 1 IN PROGRESS (60% complete - data model done, contracts pending)

---
*Aligned with Constitution v1.1.0 - See `.specify/memory/constitution.md`*
*Based on Feature Specification with 20 clarifications resolved (Session 2025-10-04)*