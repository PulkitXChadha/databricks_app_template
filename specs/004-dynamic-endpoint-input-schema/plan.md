# Implementation Plan: Automatic Model Input Schema Detection

**Branch**: `004-dynamic-endpoint-input-schema` | **Date**: October 17, 2025 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-dynamic-endpoint-input-schema/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement automatic detection and population of model input schemas for Databricks Model Serving endpoints. When users select an endpoint from the dropdown, the system will automatically identify the endpoint type (foundation model, MLflow model, or unknown), retrieve or generate the appropriate input schema, and populate the JSON input box with a valid example. This eliminates manual schema lookup, reduces input errors, and improves time-to-first-inference for data scientists and ML engineers. The feature includes browser session caching, graceful fallback for unknown schemas, comprehensive observability logging to Lakebase, and a persistent status badge showing the detected model type.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript 5.2+ (frontend)  
**Primary Dependencies**: FastAPI 0.104+, React 18.3, Databricks SDK 0.67.0, Design Bricks UI components, Vite 5.0  
**Storage**: Lakebase (PostgreSQL) via SQLAlchemy 2.0 for schema caching and event logging  
**Testing**: pytest (backend contract/integration/unit tests), Playwright (frontend automation)  
**Target Platform**: Databricks Apps platform (Linux server backend, modern browsers for frontend)
**Project Type**: Web application (FastAPI backend + React TypeScript frontend)  
**Performance Goals**: Schema detection <500ms for foundation models, <3s for MLflow models, 5s timeout for external API calls  
**Constraints**: Must not block UI during schema retrieval, must cache schemas in browser session, must log all detection events to Lakebase  
**Scale/Scope**: Single-page feature enhancement to existing Model Inference UI, ~3-5 new API endpoints, ~5-8 React components modified/added

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Design Bricks First ✅ COMPLIANT
- **Requirement**: Use Design Bricks UI components for all user-facing elements
- **Compliance**: Feature will use Design Bricks Select/Dropdown for endpoint selection, Input/TextArea for JSON display, Badge for status indicator, and Spinner for loading state
- **Action**: Verify Design Bricks components availability during Phase 0 research

### Principle II: Lakebase Integration ✅ COMPLIANT
- **Requirement**: Use Lakebase for persistent data operations
- **Compliance**: Schema detection events will be logged to Lakebase with correlation ID, endpoint name, detected type, latency, and error details (FR-013)
- **Action**: Create Alembic migration for schema_detection_events table in Phase 1

### Principle III: Asset Bundle Deployment ✅ COMPLIANT
- **Requirement**: Deploy via Databricks Asset Bundles
- **Compliance**: Feature uses existing deployment infrastructure, no new deployment configuration needed
- **Action**: None required

### Principle IV: Type Safety Throughout ✅ COMPLIANT
- **Requirement**: Full type coverage in Python and TypeScript
- **Compliance**: Backend uses Pydantic models for schema definitions, frontend uses auto-generated TypeScript client from OpenAPI spec
- **Action**: Generate TypeScript client after backend schema definitions complete

### Principle V: Model Serving Integration ✅ COMPLIANT
- **Requirement**: Use Databricks Model Serving endpoints with OAuth authentication
- **Compliance**: Feature enhances existing Model Serving integration by detecting and populating input schemas
- **Action**: None required (already compliant)

### Principle VI: Auto-Generated API Clients ✅ COMPLIANT
- **Requirement**: TypeScript client auto-generated from OpenAPI spec
- **Compliance**: New endpoints will be added to FastAPI, OpenAPI spec will be regenerated, TypeScript client will be auto-generated via `scripts/make_fastapi_client.py`
- **Action**: Regenerate client after backend implementation

### Principle VII: Development Tooling Standards ✅ COMPLIANT
- **Requirement**: Use uv (Python) and bun (frontend)
- **Compliance**: Feature uses existing tooling, no new dependencies outside standard stack
- **Action**: None required

### Principle VIII: Observability First ✅ COMPLIANT
- **Requirement**: Structured logging, correlation IDs, metrics
- **Compliance**: FR-013 mandates logging all schema detection events with correlation ID, latency, status, and error details. Support for client-provided X-Correlation-ID header for end-to-end tracing
- **Action**: Implement structured logging with correlation ID propagation in Phase 2

### Principle IX: Multi-User Data Isolation ✅ COMPLIANT
- **Requirement**: Filter Lakebase queries by user_id
- **Compliance**: Schema detection logs will include user_id from authenticated context. Logs are queryable per user for debugging
- **Action**: Extract user_id from authentication context and include in all log entries

### Dual Authentication Patterns ✅ COMPLIANT
- **Requirement**: Use Service Principal for system ops, On-Behalf-Of-User for user data
- **Compliance**: Schema detection uses On-Behalf-Of-User pattern to query Model Registry with user's permissions (ensures users only see schemas for endpoints they can access)
- **Action**: Use OBO pattern for Model Registry API calls in Phase 2

**GATE STATUS**: ✅ **PASS** - All constitutional principles are satisfied. No violations require justification.

---

## Post-Design Constitution Re-Check

*Re-evaluated after Phase 1 design completion*

### Design Artifacts Review

**Generated Artifacts**:
- ✅ `research.md` - 8 research decisions with rationale and alternatives
- ✅ `data-model.md` - 3 core entities, database schema, API models, validation rules
- ✅ `contracts/schema-detection-api.yaml` - Primary API contract with examples
- ✅ `contracts/model-registry-api.yaml` - External API reference
- ✅ `contracts/schema-logging-api.yaml` - Internal logging contract
- ✅ `quickstart.md` - User flows, API examples, testing scenarios
- ✅ `CLAUDE.md` updated - Agent context refreshed with new technology

### Constitutional Compliance Re-Validation

**Principle I: Design Bricks First** ✅ CONFIRMED
- Research Decision 5 explicitly maps all UI components to Design Bricks
- quickstart.md examples use Design Bricks components (Select, TextArea, Badge, Spinner, Alert)
- No custom UI components introduced

**Principle II: Lakebase Integration** ✅ CONFIRMED
- data-model.md defines `schema_detection_events` table with Alembic migration
- Service layer includes `log_detection_event()` method
- All detection events logged to Lakebase per FR-013

**Principle III: Asset Bundle Deployment** ✅ CONFIRMED
- No new deployment configuration required
- Uses existing databricks.yml bundle setup
- Follows standard deployment workflow

**Principle IV: Type Safety Throughout** ✅ CONFIRMED
- data-model.md includes Pydantic models (Python) and TypeScript interfaces
- OpenAPI contracts define strict schemas with validation
- Auto-generated TypeScript client from FastAPI OpenAPI spec

**Principle V: Model Serving Integration** ✅ CONFIRMED
- Feature enhances existing Model Serving integration
- Uses OBO authentication for endpoint queries
- Inference logging already implemented (extending with schema detection logs)

**Principle VI: Auto-Generated API Clients** ✅ CONFIRMED
- OpenAPI contracts complete in contracts/
- TypeScript client will be auto-generated via `scripts/make_fastapi_client.py`
- Frontend uses auto-generated types and services

**Principle VII: Development Tooling Standards** ✅ CONFIRMED
- No new dependencies outside standard stack
- Uses existing uv (Python) and bun (frontend) tooling
- Follows existing hot-reload and development workflows

**Principle VIII: Observability First** ✅ CONFIRMED
- Research Decision 6 enhances StructuredLogger with schema detection events
- Correlation ID propagation via existing distributed_tracing.py
- All events logged with timestamp, level, correlation_id, user_id, latency_ms
- Lakebase storage for queryable log analysis

**Principle IX: Multi-User Data Isolation** ✅ CONFIRMED
- data-model.md includes user_id in SchemaDetectionEvent
- All Lakebase queries filtered by user_id
- Service methods accept user_id parameter from auth context
- Multi-user testing documented in quickstart.md

**Dual Authentication Patterns** ✅ CONFIRMED
- OBO authentication used for Model Registry queries (respects user permissions)
- Service Principal not used (feature requires user context)
- Follows existing authentication patterns from model_serving_service.py

**FINAL GATE STATUS**: ✅ **PASS** - All constitutional principles validated in design artifacts. Ready for Phase 2 implementation.

## Project Structure

### Documentation (this feature)

```
specs/004-dynamic-endpoint-input-schema/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── schema-detection-api.yaml
│   ├── model-registry-api.yaml
│   └── schema-logging-api.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
# Backend (FastAPI)
server/
├── models/
│   ├── model_endpoint.py          # Enhanced with schema metadata
│   └── schema_detection_event.py  # New: Lakebase logging model
├── services/
│   └── schema_detection_service.py # New: Core detection logic
├── routers/
│   └── model_serving.py           # Enhanced with schema endpoints
└── lib/
    └── structured_logger.py        # Enhanced with correlation ID support

migrations/
└── versions/
    └── 004_create_schema_detection_events.py # New: Alembic migration

# Frontend (React TypeScript)
client/src/
├── components/
│   └── SchemaDetectionStatus.tsx   # New: Status badge component
├── pages/
│   └── DatabricksServicesPage.tsx  # Enhanced: Integrate schema detection
├── fastapi_client/                 # Auto-generated from OpenAPI spec
│   ├── models/
│   │   ├── SchemaDetectionResult.ts
│   │   └── ModelEndpointSchema.ts
│   └── services/
│       └── ModelServingService.ts  # Enhanced with schema endpoints
└── hooks/
    └── useSchemaCache.ts           # New: Browser session caching hook

# Testing
tests/
├── contract/
│   ├── test_schema_detection_contract.py   # New: API contract tests
│   └── test_model_registry_contract.py     # New: External API contract tests
├── integration/
│   ├── test_schema_detection_flow.py       # New: End-to-end schema detection
│   └── test_schema_caching.py              # New: Browser cache behavior
└── unit/
    ├── test_schema_detection_service.py    # New: Service layer unit tests
    └── test_schema_generation.py           # New: Example JSON generation tests
```

**Structure Decision**: Web application structure with FastAPI backend and React TypeScript frontend. New schema detection functionality spans backend services, database models, frontend components, and comprehensive testing. Follows existing architectural patterns with clear separation of concerns between data access (models), business logic (services), API layer (routers), and UI (components/pages).

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

No complexity violations. All constitutional principles are satisfied.
