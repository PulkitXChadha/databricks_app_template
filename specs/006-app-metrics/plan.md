# Implementation Plan: App Usage and Performance Metrics

**Branch**: `006-app-metrics` | **Date**: 2025-10-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-app-metrics/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement comprehensive application usage and performance metrics collection, persistence, and visualization within the Databricks app. The system will automatically collect performance metrics for all API requests and usage events for all user interactions, persist data to Lakebase tables with hybrid retention (7 days raw + 90 days aggregated), and provide an admin-only dashboard for monitoring application health, identifying bottlenecks, and understanding user behavior patterns.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript 5.2+ (frontend)  
**Primary Dependencies**: FastAPI (backend API), React + Vite (frontend), SQLAlchemy (ORM), Recharts (visualization), Design Bricks (UI components)  
**Storage**: Lakebase (Postgres hosted in Databricks) with OAuth token authentication  
**Testing**: pytest (contract/integration/unit tests following TDD methodology)  
**Target Platform**: Databricks workspace (deployed via Asset Bundle)  
**Project Type**: Web application (backend + frontend)  
**Performance Goals**: <5ms overhead per request for metrics collection, <3s dashboard load, <5s for 30-day historical data queries  
**Constraints**: Admin-only access (Databricks workspace admin check), 7-day raw retention / 90-day aggregated retention, daily aggregation job at 2 AM UTC  
**Scale/Scope**: App-wide metrics (all endpoints, all user actions), single dashboard page with custom date range picker, 3 database tables (raw performance, raw usage, aggregated metrics)

**Key Design Decisions** (from clarifications):
- **Alerting**: Databricks job failure notifications for aggregation job errors
- **Percentile Calculation**: Pre-computed during aggregation (p50/p95/p99) for 8-90d old data; on-demand for <7d recent data
- **Batch Retry Strategy**: Client-side exponential backoff (1s, 2s delays; 3 attempts max) for usage event submissions
- **Element Tracking**: Hybrid identifier strategy (data-track-id > id > tagName.textContent; 100 char limit)
- **Time Range UI**: Predefined quick-select buttons (24h, 7d, 30d, 90d) + custom date range picker with validation
- **Rate Limiting**: None (admin-only access control provides sufficient protection against abuse)
- **Transaction Isolation**: Database defaults (READ COMMITTED) for raw metric writes; SERIALIZABLE for aggregation job
- **Dashboard UI**: Full endpoint breakdown table (all endpoints, sortable columns, no pagination)
- **Data Refresh**: Manual refresh only via "Refresh" button; no automatic polling to minimize server load
- **Connection Pool Exhaustion**: Block and wait for available connection (prioritizes data completeness over latency)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Mandatory Requirements (from Constitution):**
- [x] Design Bricks First: Dashboard UI will use Design Bricks components (tables, date pickers, navigation) and Recharts charting library (Design Bricks equivalent does not exist per Constitution Principle I exception for missing components)
- [x] Lakebase Integration: All metrics persisted to Lakebase tables (performance_metrics, usage_events, aggregated_metrics)
- [x] Asset Bundle Deployment: New bundle resource added - resources.jobs.metrics_aggregation_job in databricks.yml for scheduled aggregation (runs daily at 2 AM UTC); uses existing app deployment for API endpoints
- [x] Type Safety Throughout: FastAPI with Pydantic models, TypeScript with strict mode, contract tests for metrics API
- [N/A] Model Serving Integration: Feature does not involve model serving
- [x] Auto-Generated API Clients: Will use existing make_fastapi_client.py workflow for metrics endpoints
- [x] Observability First: This feature IMPLEMENTS observability - adds metrics collection with correlation IDs
- [x] Multi-User Data Isolation: Metrics filtered by user_id; admin-only access via Databricks workspace admin check
- [x] Specification-First Development: Spec exists at specs/006-app-metrics/spec.md
- [x] Test Driven Development: Will follow TDD for all metrics collection, aggregation, and API code
- [x] OBO Authentication: Admin check uses existing OBO token to verify workspace admin privileges

**Testing Requirements (TDD - Principle XII):**
- [x] Contract tests written BEFORE endpoint implementation (test_metrics_api.py)
- [x] Integration tests written BEFORE service layer implementation (test_metrics_collection.py, test_metrics_aggregation.py, test_usage_metrics.py)
- [x] Unit tests written BEFORE complex business logic (aggregation logic, admin checks)
- [x] All tests MUST fail initially (RED phase) before implementation
- [x] Test suite execution required in deployment gates

**Constitution Compliance**: ✅ PASS - No violations. All constitutional requirements are satisfied by this feature design.

**Post-Phase-1 Re-evaluation (2025-10-18)**:
After completing Phase 0 (research) and Phase 1 (data model, contracts, quickstart, agent context), all constitutional requirements remain satisfied:
- ✅ Design Bricks components confirmed for dashboard UI (Recharts with Design Bricks styling)
- ✅ Lakebase tables defined with proper schemas, indexes, and lifecycle management
- ✅ OpenAPI contracts created with full request/response schemas and error formats
- ✅ TDD workflow documented with red-green-refactor methodology in quickstart guide
- ✅ Admin privilege checking via Databricks Workspace API with caching strategy
- ✅ Middleware-based automatic metrics collection for zero-touch instrumentation
- ✅ Agent context (CLAUDE.md) updated with metrics service patterns and new technologies

**Final Verdict**: ✅ CONSTITUTION CHECK PASSED - Ready for Phase 2 (tasks breakdown and implementation)

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - run AFTER plan.md complete)
```

### Source Code (repository root)

```
server/                         # Backend (Python/FastAPI)
├── models/
│   ├── performance_metric.py  # NEW: Performance metric model
│   ├── usage_event.py         # NEW: Usage event model
│   └── aggregated_metric.py   # NEW: Aggregated metric model
├── services/
│   ├── metrics_service.py     # NEW: Metrics collection & query service
│   └── admin_service.py       # NEW: Admin privilege check service
├── routers/
│   └── metrics.py             # NEW: Metrics API endpoints
└── lib/
    └── metrics_middleware.py  # NEW: FastAPI middleware for auto-collection

client/                         # Frontend (React/TypeScript)
├── src/
│   ├── components/
│   │   ├── MetricsDashboard.tsx    # NEW: Main dashboard component
│   │   ├── PerformanceChart.tsx    # NEW: Performance metrics chart
│   │   ├── UsageChart.tsx          # NEW: Usage metrics chart
│   │   └── MetricsTable.tsx        # NEW: Metrics data table
│   ├── pages/
│   │   └── MetricsPage.tsx         # NEW: Metrics page route
│   └── services/
│       ├── metricsClient.ts        # GENERATED: Auto-gen from OpenAPI
│       └── usageTracker.ts         # NEW: Frontend usage event tracker

migrations/                     # Database migrations (Alembic)
└── versions/
    └── xxx_add_metrics_tables.py   # NEW: Metrics tables migration

scripts/                        # Utility scripts
└── aggregate_metrics.py        # NEW: Aggregation job script (console entry point)

tests/                          # Test suite (pytest)
├── contract/
│   └── test_metrics_api.py         # NEW: Contract tests for metrics API
├── integration/
│   ├── test_metrics_collection.py  # NEW: Performance metrics collection
│   ├── test_metrics_aggregation.py # NEW: Aggregation job tests
│   ├── test_usage_metrics.py       # NEW: Usage event tracking tests
│   └── test_metrics_visualization.py # NEW: Dashboard integration tests
└── unit/
    ├── test_metrics_service.py     # NEW: Service layer unit tests
    └── test_admin_service.py       # NEW: Admin check unit tests
```

**Structure Decision**: This is a web application (Option 2) with separate backend (server/) and frontend (client/) directories. The feature adds new models, services, routers, components, and comprehensive tests following the existing project structure. Database migrations use Alembic for schema versioning.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

No constitutional violations. This feature follows all constitutional requirements and introduces no additional complexity beyond what is specified and justified in the feature specification.
