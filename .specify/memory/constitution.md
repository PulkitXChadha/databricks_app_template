<!--
Sync Impact Report:
Version: 1.3.0 → 1.4.0 (MINOR bump - new TDD principle added)
Changes:
  - Added Principle XII: Test Driven Development (NON-NEGOTIABLE) - mandates TDD for all production code
  - Enhanced Testing Philosophy section with explicit TDD workflow requirements (RED-GREEN-REFACTOR)
  - Updated Deployment Validation to include test suite execution as pre-deployment gate
Templates Status:
  ✅ plan-template.md - Updated Constitution Check with TDD requirements and testing gates
  ✅ spec-template.md - Updated to emphasize TDD and map acceptance scenarios to test types/locations
  ✅ tasks-template.md - Updated with explicit RED-GREEN-REFACTOR phases for all user stories
  ✅ README.md - Testing section already mentions TDD patterns, no changes needed
Follow-up TODOs:
  - None - all templates updated and aligned with Principle XII
  - Consider adding test coverage metrics in future PATCH version
  - Consider documenting TDD best practices in a dedicated guide
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
All deployments MUST be managed through Databricks Asset Bundles with validation gates.

**Rules:**
- `databricks.yml` configuration at repository root
- All app resources defined as bundle resources
- Support for dev, staging, and prod target environments
- Deployment via `databricks bundle deploy` command only
- No manual workspace file uploads or ad-hoc deployments
- **MUST validate bundles** before deployment with `databricks bundle validate` (exit code 1 on validation errors)
- Invalid bundle configurations MUST NOT be deployed
- **CI/CD Integration**: Validation MUST run in CI/CD pipeline as deployment gate
- **Pre-deployment Checklist**: Run validation locally before pushing changes
- All bundle validation errors MUST be resolved before merge to main

**Rationale:** Asset Bundles ensure reproducible, version-controlled, auditable deployments aligned with Databricks platform best practices. Validation gates prevent deployment of broken configurations (EC-005 edge cases from spec 001).

### IV. Type Safety Throughout
Full type coverage MUST be maintained across Python backend and TypeScript frontend with contract testing as deployment gate.

**Rules:**
- Python: Type hints on all functions, Pydantic models for validation
- TypeScript: Strict mode enabled, no `any` types without justification
- Auto-generated TypeScript client from FastAPI OpenAPI spec
- Type checking in CI/CD pipeline (ruff, ty for Python; tsc for TypeScript)
- **Contract Testing (TDD)**: Generate contract tests from OpenAPI specs BEFORE implementation
- **Test Organization**: One test file per router in `tests/contract/` (e.g., `test_lakebase_contract.py`)
- **Red-Green-Refactor**: Contract tests MUST fail initially, pass after implementation
- **Deployment Gate**: All contract tests MUST pass before deployment
- Contract tests validate request/response schemas, status codes, and error formats

**Rationale:** Type safety prevents runtime errors, improves developer experience, and enables reliable refactoring. Contract testing ensures API implementation matches specifications before deployment, catching breaking changes early.

### V. Model Serving Integration
Applications MUST be ready to integrate with Databricks Model Serving endpoints with automatic schema detection.

**Rules:**
- Service layer abstractions for model inference calls
- Configuration-based model endpoint URLs (via environment variables)
- Error handling for model serving failures
- Response parsing for model outputs (JSON, streaming, batch)
- OAuth token authentication for serving endpoint access (via Databricks SDK authentication context)
- Timeout configuration (default 30s, max 300s)
- Retry logic with exponential backoff for transient errors
- **Inference logging**: All model inference requests MUST be logged to Lakebase with request/response details for auditability and debugging
- **History UI**: Applications SHOULD provide user-facing history views for tracking inference requests with pagination and filtering
- **Schema Detection**: Automatically detect model input schemas for foundation models (chat format) and MLflow models (Model Registry API)
- **Example Generation**: Generate realistic example JSON payloads based on detected schemas
- **Graceful Fallback**: Fall back to generic templates with clear guidance when schema detection fails
- **Schema Caching**: Cache successfully retrieved schemas in browser session to avoid repeated API calls

**Rationale:** Model serving is core to Databricks AI/ML capabilities; apps should leverage platform-native inference infrastructure. Automatic schema detection reduces input errors and improves user experience (spec 004). Comprehensive logging enables auditability, debugging, and usage tracking.

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
Applications MUST implement comprehensive observability from the start using structured logging, correlation IDs, and metrics with defined retention policies.

**Rules:**
- **Structured Logging**: All logs in JSON format with timestamp, log level, message, module, function
- **Correlation IDs**: Every request generates a unique request_id propagated across all operations (using contextvars). Support optional client-provided correlation IDs via X-Correlation-ID header for end-to-end tracing across services. If header present, use client ID; otherwise generate server-side UUID.
- **Context Enrichment**: Include user_id, duration_ms, and relevant technical details in all logs
- **Log Levels**: INFO for normal operations, WARNING for retries, ERROR for failures with full context
- **Error Logging**: All errors logged with ERROR level including timestamp, error type, message, request context, technical details
- **Sensitive Data Protection**: Never log tokens, passwords, or PII
- **Performance Tracking**: Log execution time for all API calls, database queries, and model inferences
- **Simplified Tracing**: Use correlation-ID based request tracking (not full OpenTelemetry for templates)
- **Feature-Level Events**: Log feature-specific operations (schema detection, catalog queries, user interactions) with correlation IDs for debugging
- **Retention Policy**: 7 days raw metrics/logs, 90 days aggregated data for compliance and audit requirements (spec 002)
- **User Isolation Logging**: Include user_id in all logs for audit trail and data isolation verification

**Rationale:** Observability is essential for debugging production issues, monitoring performance, and understanding user behavior. Structured logs enable automated analysis and alerting. Feature-level logging supports debugging complex user interactions beyond infrastructure events.

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

### X. Specification-First Development (NON-NEGOTIABLE)
All features MUST have comprehensive specifications written and approved before implementation begins.

**Rules:**
- Every feature has a specification document in `specs/###-feature-name/` directory structure
- Specifications MUST include: problem statement, clarifications (Q&A format), user stories with acceptance criteria, functional requirements (FR-###), edge cases, and success metrics
- Use numbered feature branches matching spec directories (e.g., `001-databricks-integrations`, `002-fix-api-authentication`)
- No implementation without approved specification (exceptions: bug fixes <10 lines, documentation updates, minor refactoring)
- Specifications are living documents - update during implementation as understanding deepens
- Each spec MUST document what is explicitly OUT OF SCOPE to prevent scope creep
- Clarifications section documents all Q&A from design discussions with dates

**Rationale:** Specification-first development prevents scope creep, ensures clear acceptance criteria, documents decision rationale, and provides historical context. The git history (branches 001-004) demonstrates this pattern consistently delivers high-quality features with clear requirements.

### XI. Iterative Refinement Over Perfect First Attempts
Complex solutions are acceptable as first implementations; breaking changes that improve architecture are encouraged.

**Rules:**
- First implementations may be complex - focus on learning and validating requirements
- Refactoring to remove complexity is planned work, not technical debt
- Breaking changes are permitted when they improve security, usability, or maintainability
- Each iteration should target one quality attribute improvement (security, UX, performance, simplicity)
- Document breaking changes in specification with clear justification
- Backward compatibility is NOT always required if breaking changes are justified
- "Build then simplify" is preferred over "analyze forever then build perfectly"

**Rationale:** Real-world usage reveals better solutions than upfront analysis. Branch evolution (002→003 removing service principal fallback after learning OBO-only was sufficient) demonstrates that building, learning, then simplifying produces better architecture than attempting perfection initially.

### XII. Test Driven Development (NON-NEGOTIABLE)
All production code MUST be developed using Test Driven Development methodology with red-green-refactor cycles.

**Rules:**
- Write tests BEFORE implementation code (red phase)
- Write minimal code to make tests pass (green phase)
- Refactor for quality while keeping tests green (refactor phase)
- Contract tests MUST be written first for all API endpoints
- Integration tests MUST be written before service layer implementation
- Unit tests MUST be written before complex business logic implementation
- All tests MUST fail initially (red) before implementation begins
- Test coverage MUST be maintained - no code without corresponding tests
- Tests document expected behavior and serve as living specification
- Deployment gates MUST include all test suites passing

**Rationale:** TDD ensures code correctness from the start, creates comprehensive test coverage automatically, provides immediate regression detection, and produces better-designed code through test-first thinking. Writing tests first catches design issues before implementation, reduces debugging time, and provides confidence for refactoring. The red-green-refactor cycle enforces disciplined development and creates maintainable, well-tested codebases.

## Security & Authentication

### Databricks Platform Authentication
Applications MUST use Databricks Apps built-in authentication (via Databricks SDK) with dual patterns for system and user operations.

**Requirements:**
- Support Personal Access Token (PAT) authentication for development
- Support OAuth/CLI profile authentication for production
- Credentials stored in `.env.local` (never committed)
- Token refresh handling for long-running sessions
- User info retrieval via Databricks SDK APIs (`WorkspaceClient.current_user.me()`)

### On-Behalf-Of-User Authentication (NON-NEGOTIABLE)
Applications MUST use On-Behalf-Of-User (OBO) authentication for all user-initiated operations.

**Evolution Note:** This project initially supported dual authentication patterns (service principal + OBO) but evolved to OBO-only in branch 003 for stronger security guarantees and simpler architecture.

**Rules:**
- ALL authenticated API endpoints require valid user access token (via X-Forwarded-Access-Token header)
- No service principal fallback for user operations
- User identity extracted from authentication context via `WorkspaceClient.current_user.me()`
- Unity Catalog enforces user's table/column permissions automatically
- Lakebase uses application-level credentials but enforces user_id filtering in queries
- Health check endpoints MAY be unauthenticated for monitoring infrastructure

**Local Development:**
- Developers use personal Databricks tokens (via `databricks auth token`)
- No service principal credentials required for development
- Token passed via X-Forwarded-Access-Token header or environment variable

**Implementation:**
- Document OBO pattern in `docs/databricks_apis/authentication_patterns.md`
- Use FastAPI dependency injection: `get_user_token()` (required) or `get_user_token_optional()` (health checks)
- Clear error messages when authentication fails (HTTP 401 with structured error response)

**Rationale:** OBO-only authentication ensures all operations use user's actual permissions, preventing privilege escalation and providing clear audit trails. Removing service principal fallback simplifies code and strengthens security (spec 003).

### Lakebase Access Control
Database access MUST follow Databricks security best practices.

**Requirements:**
- OAuth token authentication for Lakebase connections (via Databricks SDK `generate_database_credential()` API)
- Row-level security via user_id filtering for multi-tenant scenarios
- Audit logging of data access operations
- Least privilege principle for service accounts

## Feature Development Workflow

### Specification-Based Development Process
All features MUST follow this structured workflow to ensure quality and traceability.

**Workflow Steps:**
1. **Create Feature Branch**: Use numbered naming pattern `###-feature-name` (e.g., `001-databricks-integrations`, `004-dynamic-endpoint-input-schema`)
2. **Create Spec Directory**: Create `specs/###-feature-name/` matching branch name
3. **Write Specification**: Create `spec.md` with:
   - Problem statement and input description
   - Clarifications section documenting all Q&A with dates
   - User stories with acceptance scenarios
   - Functional requirements (FR-###) and edge cases (EC-###)
   - Success metrics and out-of-scope items
4. **Write Plan**: Create `plan.md` breaking down technical approach (optional for simple features)
5. **Write Tasks**: Create `tasks.md` with granular, trackable task list
6. **Implement with Tracking**: Update tasks.md as work progresses
7. **Update Documentation**: Update relevant docs in `docs/` directory
8. **Run Validation**: Execute all validation gates (bundle validate, contract tests, type checking)
9. **Merge to Main**: After all acceptance criteria met and validation passes

**Rationale:** This pattern (consistently followed in branches 001-004) ensures features have clear requirements, documented decisions, and trackable progress. The numbered branch structure provides chronological feature history.

### Branch Naming Convention
- **Feature branches**: `###-feature-name` (e.g., `001-databricks-integrations`)
- **Bug fixes**: `bugfix/description` (e.g., `bugfix/auth-token-expiry`)
- **Refactoring**: `refactor/description` (e.g., `refactor/component-decomposition`)
- **Documentation**: `docs/description` (e.g., `docs/update-api-guide`)

Numbered feature branches are reserved for substantial features with specifications. Minor changes use descriptive prefixes.

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
Test Driven Development (TDD) is MANDATORY for all production code (see Principle XII).

**TDD Workflow (Red-Green-Refactor):**
1. **RED**: Write failing test that defines desired behavior
2. **GREEN**: Write minimal code to make test pass
3. **REFACTOR**: Improve code quality while keeping tests green

**Testing Layers (All Following TDD):**
- **Contract Testing**: Write contract tests from OpenAPI specs BEFORE endpoint implementation
- **Integration Testing**: Write integration tests BEFORE service layer implementation
- **Unit Testing**: Write unit tests BEFORE complex business logic implementation
- **UI Testing**: Playwright browser automation for end-to-end workflows
- **Multi-User Testing**: Data isolation verification with multiple user accounts

**Contract Testing Requirements:**
- Generate contract tests from OpenAPI specs
- One test file per API contract (e.g., `test_lakebase_contract.py`)
- Tests MUST fail initially (RED phase - before implementation)
- Implement code to make tests pass (GREEN phase)
- All contract tests MUST pass before deployment

**Additional Validation:**
- Endpoint verification with curl and FastAPI docs (post-implementation)
- Log monitoring post-deployment for runtime errors
- Integration testing with deployed app

### Deployment Validation (NON-NEGOTIABLE)
Before and after every deployment, MUST:
1. **Pre-Deployment Gates**:
   - Run full test suite (contract, integration, unit tests) - ALL MUST PASS
   - Run `databricks bundle validate` (catches EC-005 errors)
   - Type checking passes (Python: ruff, TypeScript: tsc)
   - Code formatting validated with `./fix.sh`
2. **Post-Deployment Validation**:
   - Run `dba_logz.py` to monitor logs for 60 seconds
   - Verify uvicorn startup messages appear
   - Check for Python exceptions or dependency errors
   - Test core endpoints with `dba_client.py`
   - Run smoke tests against deployed endpoints
3. **Failure Response**: Fix and redeploy immediately if any validation fails

## Governance

### Constitution Authority
This constitution supersedes all other development practices. When conflicts arise between convenience and constitutional principles, principles win.

### Breaking Changes and Migration
Breaking changes are permitted when they improve architecture, security, or user experience.

**Requirements for Breaking Changes:**
- **Specification Documentation**: Breaking changes MUST be clearly documented in feature spec with:
  - Explicit statement that backward compatibility is NOT maintained
  - Clear justification for breaking change (security, architecture simplification, etc.)
  - Migration path documentation (even if migration path is "no migration - users must adapt")
  - Impact assessment on existing deployments and users
- **Explicit Approval**: Breaking changes require explicit approval during spec review phase
- **User Impact Documentation**: Document what users/operators must do differently
- **Version Bumping**: Constitutional breaking changes require MAJOR version bump
- **Communication**: Announce breaking changes in release notes and deployment guides

**Example from Project History:**
Branch 003 (`obo-only-support`) was an intentional breaking change that:
- Removed service principal fallback authentication (simpler, more secure)
- Required developers to use personal tokens for local development
- Eliminated backward compatibility with service principal workflows
- Documented new authentication pattern clearly in spec and migration guide

**Rationale:** Real-world usage reveals better solutions than upfront analysis. Embracing breaking changes when justified (Principle XI) leads to better architecture than maintaining complexity for backward compatibility.

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

**Version**: 1.4.0 | **Ratified**: 2025-10-04 | **Last Amended**: 2025-10-18

---

## Changelog

### Version 1.4.0 (2025-10-18) - MINOR
**Changes:**
- Added Principle XII: Test Driven Development (NON-NEGOTIABLE) - mandates TDD methodology with red-green-refactor cycles for all production code
- Enhanced Testing Philosophy section with explicit TDD workflow (RED-GREEN-REFACTOR phases)
- Updated Deployment Validation with comprehensive pre-deployment gates including full test suite execution
- Clarified that tests MUST be written BEFORE implementation across all testing layers (contract, integration, unit)
- Added requirement that deployment gates MUST include all test suites passing

**Impact:** All new production code MUST follow TDD methodology. Tests must be written first and fail initially before implementation. This applies to contract tests, integration tests, and unit tests. Test suite execution is now a mandatory pre-deployment gate.

**Rationale:** TDD ensures code correctness from the start, creates comprehensive test coverage automatically, provides immediate regression detection, and produces better-designed code through test-first thinking. The red-green-refactor cycle enforces disciplined development and creates maintainable, well-tested codebases. This formalizes the TDD patterns already present in Principle IV (contract testing) and extends them to all code.

### Version 1.3.0 (2025-10-18) - MINOR
**Changes:**
- Added Principle X: Specification-First Development (NON-NEGOTIABLE) - mandates specs/ directory structure with numbered feature branches
- Added Principle XI: Iterative Refinement Over Perfect First Attempts - embraces evolutionary architecture and planned breaking changes
- Enhanced Principle III (Asset Bundle Deployment) with CI/CD validation gates and pre-deployment checklists
- Enhanced Principle IV (Type Safety) with mandatory contract testing before implementation (TDD approach)
- Enhanced Principle V (Model Serving) with automatic schema detection, example generation, and caching requirements
- Enhanced Principle VIII (Observability) with feature-level event logging, retention policies (7 days raw, 90 days aggregated), and user isolation logging
- Updated Security & Authentication section to reflect OBO-only authentication evolution (branch 003)
- Added Feature Development Workflow section documenting specification-based development process
- Added Breaking Changes and Migration governance section with requirements and project example
- Added Branch Naming Convention guidelines for feature/bugfix/refactor/docs branches

**Impact:** Major workflow and governance changes based on proven patterns from branches 001-004. All features MUST now follow specification-first workflow with numbered branches. Breaking changes are explicitly permitted when justified. Contract testing is now mandatory before deployment.

**Rationale:** Git history analysis (branches 001-004) revealed consistent patterns that deliver high quality: specification-first development, iterative refinement with breaking changes when needed, comprehensive testing, and structured workflows. Codifying these proven practices ensures continued quality.

### Version 1.2.0 (2025-10-08) - MINOR
**Changes:**
- Enhanced Principle V (Model Serving Integration) with inference logging requirements
- Added requirement for all model inference requests to be logged to Lakebase
- Added recommendation for history UI views with pagination and filtering
- Documented Model Serving History implementation as exemplar for auditability patterns

**Impact:** New requirement for inference logging. Applications MUST log all model requests to Lakebase. History UI is recommended but optional.

### Version 1.1.1 (2025-10-08) - PATCH
**Changes:**
- Enhanced Principle I (Design Bricks First) with guidance on progressive disclosure patterns
- Added note encouraging cascading dropdowns and conditional fields for complex data selection
- Documented Unity Catalog cascading dropdown implementation as exemplar of good UX practices

**Impact:** Clarification only - no breaking changes. Existing implementations remain compliant.
