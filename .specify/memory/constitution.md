<!--
Sync Impact Report:
Version: 1.0.0 → 1.1.0 (MINOR bump - new principles added)
Changes:
  - Added Principle VIII: Observability First (structured logging, correlation IDs, metrics)
  - Added Principle IX: Multi-User Data Isolation (security patterns for multi-tenant scenarios)
  - Enhanced Principle III: Asset Bundle Deployment with validation requirements (EC-005 compliance)
  - Expanded Security & Authentication with dual authentication patterns (service principal + on-behalf-of-user per FR-009)
  - Enhanced Testing Philosophy with contract testing requirements
  - Clarified Development Tooling Standards with specific version requirements
Templates Status:
  ⚠ plan-template.md - Needs review for new observability and data isolation principles
  ⚠ spec-template.md - Needs review for authentication patterns and observability requirements
  ⚠ tasks-template.md - Needs review for contract testing and observability task categories
  ✅ CLAUDE.md - Will be auto-updated by update-agent-context.sh script
Follow-up TODOs:
  - Review and update plan-template.md for Principles VIII and IX
  - Review and update spec-template.md for dual authentication patterns
  - Review and update tasks-template.md for contract testing phase
  - Validate templates align with enhanced constitution requirements
-->

# Databricks React App Template Constitution

## Core Principles

### I. Design Bricks First (NON-NEGOTIABLE)
All UI components MUST use the Design Bricks data design system to ensure Databricks look-and-feel consistency.

**Rules:**
- Every user-facing component uses Design Bricks components from https://pulkitxchadha.github.io/DesignBricks
- No custom UI component creation without first checking Design Bricks availability
- Consistent Databricks theming and design patterns across the entire application
- shadcn/ui components used only when Design Bricks equivalent does not exist
- Progressive disclosure patterns (e.g., cascading dropdowns, conditional fields) encouraged for complex data selection

**Rationale:** Users expect a native Databricks experience; custom components create visual inconsistency and reduce trust. Progressive disclosure patterns improve usability by guiding users through complex selections.

### II. Lakebase Integration
All persistent data operations MUST use Lakebase (Postgres hosted in Databricks) as the primary database.

**Rules:**
- Database connections through Lakebase endpoints
- Use SQLAlchemy or similar ORMs with Postgres dialect
- OAuth token authentication for Lakebase access (tokens generated via Databricks SDK `generate_database_credential()` API)
- No external OLTP systems or manual database management
- Transaction support for data integrity
- Alembic for database schema migrations and versioning

**Rationale:** Lakebase provides integrated, secure, transactional storage within the Databricks platform, eliminating external dependencies.

### III. Asset Bundle Deployment (NON-NEGOTIABLE)
All deployments MUST be managed through Databricks Asset Bundles.

**Rules:**
- `databricks.yml` configuration at repository root
- All app resources defined as bundle resources
- Support for dev, staging, and prod target environments
- Deployment via `databricks bundle deploy` command only
- No manual workspace file uploads or ad-hoc deployments
- **MUST validate bundles** before deployment with `databricks bundle validate` (exit code 1 on validation errors)
- Invalid bundle configurations MUST NOT be deployed

**Rationale:** Asset Bundles ensure reproducible, version-controlled, auditable deployments aligned with Databricks platform best practices.

### IV. Type Safety Throughout
Full type coverage MUST be maintained across Python backend and TypeScript frontend.

**Rules:**
- Python: Type hints on all functions, Pydantic models for validation
- TypeScript: Strict mode enabled, no `any` types without justification
- Auto-generated TypeScript client from FastAPI OpenAPI spec
- Type checking in CI/CD pipeline (ruff, ty for Python; tsc for TypeScript)

**Rationale:** Type safety prevents runtime errors, improves developer experience, and enables reliable refactoring.

### V. Model Serving Integration
Applications MUST be ready to integrate with Databricks Model Serving endpoints.

**Rules:**
- Service layer abstractions for model inference calls
- Configuration-based model endpoint URLs (via environment variables)
- Error handling for model serving failures
- Response parsing for model outputs (JSON, streaming, batch)
- OAuth token authentication for serving endpoint access (via Databricks SDK authentication context)
- Timeout configuration (default 30s, max 300s)
- Retry logic with exponential backoff for transient errors

**Rationale:** Model serving is core to Databricks AI/ML capabilities; apps should leverage platform-native inference infrastructure.

### VI. Auto-Generated API Clients
API clients MUST be automatically generated from OpenAPI specifications.

**Rules:**
- FastAPI generates OpenAPI spec automatically
- TypeScript client generated via `scripts/make_fastapi_client.py`
- Client regeneration on every backend schema change
- Version client generation as part of watch/dev workflow
- No manual API client code

**Rationale:** Hand-written clients diverge from actual APIs; auto-generation ensures frontend-backend contract consistency.

### VII. Development Tooling Standards
Modern, fast development tools MUST be used for optimal developer experience.

**Rules:**
- Python: uv for package management (not pip/poetry)
- Frontend: bun for package management (not npm/yarn)
- Hot reloading enabled for both frontend and backend
- Background process management with proper logging
- Code formatting enforced (ruff, prettier)
- Python 3.11+ required for modern type hints and performance
- Node.js 18.0+ required for TypeScript 5.2+ and Vite 5.0

**Rationale:** Fast tools accelerate iteration; standardization reduces cognitive load and onboarding friction.

### VIII. Observability First
Applications MUST implement comprehensive observability from the start using structured logging, correlation IDs, and metrics.

**Rules:**
- **Structured Logging**: All logs in JSON format with timestamp, log level, message, module, function
- **Correlation IDs**: Every request generates a unique request_id propagated across all operations (using contextvars). Support optional client-provided correlation IDs via X-Correlation-ID header for end-to-end tracing across services. If header present, use client ID; otherwise generate server-side UUID.
- **Context Enrichment**: Include user_id, duration_ms, and relevant technical details in all logs
- **Log Levels**: INFO for normal operations, WARNING for retries, ERROR for failures with full context
- **Error Logging**: All errors logged with ERROR level including timestamp, error type, message, request context, technical details
- **Sensitive Data Protection**: Never log tokens, passwords, or PII
- **Performance Tracking**: Log execution time for all API calls, database queries, and model inferences
- **Simplified Tracing**: Use correlation-ID based request tracking (not full OpenTelemetry for templates)

**Rationale:** Observability is essential for debugging production issues, monitoring performance, and understanding user behavior. Structured logs enable automated analysis and alerting.

### IX. Multi-User Data Isolation
Applications MUST implement comprehensive data isolation for multi-user scenarios using Unity Catalog access control and Lakebase row-level security.

**Rules:**
- **User Identity**: Extract user_id from Databricks authentication context (never trust client-provided values)
- **Unity Catalog Isolation**: Unity Catalog automatically enforces table/column permissions based on user identity
- **Lakebase Isolation**: Always filter Lakebase queries by user_id in WHERE clauses
- **Authorization Pattern**: Use dependency injection to inject authenticated user_id into all endpoints
- **Testing**: Multi-user isolation MUST be tested with multiple user accounts
- **Audit Logging**: Log all data access operations with user_id for compliance

**Rationale:** Multi-user applications require strong data isolation to prevent unauthorized access and meet security/compliance requirements.

## Security & Authentication

### Databricks Platform Authentication
Applications MUST use Databricks Apps built-in authentication (via Databricks SDK) with dual patterns for system and user operations.

**Requirements:**
- Support Personal Access Token (PAT) authentication for development
- Support OAuth/CLI profile authentication for production
- Credentials stored in `.env.local` (never committed)
- Token refresh handling for long-running sessions
- User info retrieval via Databricks SDK APIs (`WorkspaceClient.current_user.me()`)

### Dual Authentication Patterns (NON-NEGOTIABLE)
Applications MUST implement two distinct authentication patterns based on operation type.

**Pattern A: Service Principal Authentication (App-Level Authorization)**
- Use Service Principal for shared/system-level operations
- Examples: health checks, system-level queries, batch operations
- Configuration: `DATABRICKS_APP_SERVICE_PRINCIPAL_*` environment variables
- No user context required

**Pattern B: On-Behalf-Of-User Authentication (User-Level Authorization)**
- Use On-Behalf-Of-User authorization for user-specific data access
- Examples: querying Unity Catalog with user's permissions, saving user preferences
- User identity extracted from authentication context via `WorkspaceClient.current_user.me()`
- Unity Catalog enforces user's table/column permissions automatically

**Implementation:**
- Document both patterns in `docs/databricks_apis/authentication_patterns.md`
- Use FastAPI dependency injection to inject user context where needed
- Clear code comments indicating which pattern is used and why

**Rationale:** Separating system and user operations ensures proper access control and auditability while maintaining security best practices.

### Lakebase Access Control
Database access MUST follow Databricks security best practices.

**Requirements:**
- OAuth token authentication for Lakebase connections (via Databricks SDK `generate_database_credential()` API)
- Row-level security via user_id filtering for multi-tenant scenarios
- Audit logging of data access operations
- Least privilege principle for service accounts

## Deployment Standards

### Databricks Asset Bundle Configuration
Bundle configuration MUST include:
- App name, source code path, description
- Target environments (dev, prod) with distinct workspace paths
- Permissions configuration (CAN_MANAGE, CAN_VIEW)
- Environment variables for configuration
- Build and deployment workflows
- **Validation command**: `databricks bundle validate` MUST pass before deployment

### Environment Management
- **Development**: Local testing with `./watch.sh`, hot reloading enabled
- **Staging**: Optional pre-production environment in separate workspace path
- **Production**: Locked-down permissions, monitored deployments

## Development Workflow

### Package Management
- Python dependencies: `uv add/remove` (never manual pyproject.toml edits)
- Frontend dependencies: `bun add/remove` (never manual package.json edits)
- Dependency audits before adding new packages

### Development Server
- ALWAYS run via `./watch.sh` with nohup and logging
- NEVER run uvicorn or frontend directly
- Kill processes via PID file or pkill, ensuring port cleanup

### Code Quality Gates
- Format code with `./fix.sh` before commits
- Type checking passes (Python: ty/ruff, TypeScript: tsc)
- Linter errors resolved before deployment
- FastAPI endpoints tested with curl after creation

### Testing Philosophy
While TDD is ideal, practical testing includes:
- **Contract Testing**: Validate API endpoints match OpenAPI specifications before implementation (TDD approach)
- Endpoint verification with curl and FastAPI docs
- UI validation via Playwright browser automation
- Integration testing with deployed app
- Log monitoring post-deployment for runtime errors
- Multi-user testing for data isolation verification

**Contract Testing Requirements:**
- Generate contract tests from OpenAPI specs
- One test file per API contract (e.g., `test_lakebase_contract.py`)
- Tests MUST fail initially (before implementation)
- All contract tests MUST pass before deployment

### Deployment Validation (NON-NEGOTIABLE)
After every deployment, MUST:
1. Run `databricks bundle validate` before deployment (catches EC-005 errors)
2. Run `dba_logz.py` to monitor logs for 60 seconds
3. Verify uvicorn startup messages appear
4. Check for Python exceptions or dependency errors
5. Test core endpoints with `dba_client.py`
6. Fix and redeploy immediately if errors found

## Governance

### Constitution Authority
This constitution supersedes all other development practices. When conflicts arise between convenience and constitutional principles, principles win.

### Amendment Process
1. Propose amendment with rationale in project discussion
2. Document impact on existing code and workflows
3. Update this document with version bump (semantic versioning)
4. Update all dependent templates and documentation
5. Communicate changes to all contributors

### Versioning Policy
- **MAJOR**: Breaking changes to principles or mandatory workflows
- **MINOR**: New principles added or existing principles expanded
- **PATCH**: Clarifications, typo fixes, non-semantic improvements

### Compliance Review
- All pull requests reviewed against constitution principles
- Design reviews validate adherence before implementation
- Complexity and deviations documented and justified
- Regular constitution review (quarterly) for relevance

### Agent-Specific Guidance
Runtime development guidance available in `CLAUDE.md` for Claude Code and similar agents. This file provides operational commands and workflows aligned with constitutional principles.

**Version**: 1.1.1 | **Ratified**: 2025-10-04 | **Last Amended**: 2025-10-08

---

## Changelog

### Version 1.1.1 (2025-10-08) - PATCH
**Changes:**
- Enhanced Principle I (Design Bricks First) with guidance on progressive disclosure patterns
- Added note encouraging cascading dropdowns and conditional fields for complex data selection
- Documented Unity Catalog cascading dropdown implementation as exemplar of good UX practices

**Impact:** Clarification only - no breaking changes. Existing implementations remain compliant.
