# Feature Specification: Fix API Authentication and Implement On-Behalf-Of User (OBO) Authentication

**Feature Branch**: `002-fix-api-authentication`  
**Created**: 2025-10-09  
**Status**: Draft  
**Input**: 
- Original: "These are the error log snippets from the app deployed in Databricks. The apps UI is working and the deployment is successful but all the API calls are failing."
- Clarification (2025-10-09): "Connection to lakebase from the App is only supported with service principles so we should continue using that and not the OBO token."

## Execution Flow (main)
```
1. Parse user description from Input
   → ERROR identified: "more than one authorization method configured: oauth and pat"
   → CLARIFICATION added: Lakebase requires service principal authentication
2. Extract key concepts from description
   → Actors: End users, Databricks platform, Service principal
   → Actions: API calls (list endpoints, query catalogs, get user info), Database operations
   → Data: User credentials, OAuth tokens, PAT tokens, Database connections
   → Constraints: Must work in Databricks Apps deployment, Lakebase platform limitation
3. No unclear aspects identified - error is well-documented in logs, platform constraint documented
4. Fill User Scenarios & Testing section
   → Primary flow: User accesses app → API calls use user's permissions (OBO)
   → Database flow: App connects to Lakebase → Uses service principal
5. Generate Functional Requirements
   → All requirements are testable based on API behavior and database connections
6. Identify Key Entities
   → User tokens, Service configuration, Databricks SDK clients, Database connections
7. Run Review Checklist
   → No [NEEDS CLARIFICATION] markers
   → Implementation details avoided
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Problem Statement

The Databricks App is deployed successfully and the UI loads correctly, but all API endpoints are failing with the error:

```
"more than one authorization method configured: oauth and pat"
```

### Root Cause Analysis

1. **Environment Context**: When deployed in Databricks Apps, the platform automatically sets OAuth environment variables (`DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`)
2. **OBO Token Available**: The platform also provides user access tokens via the `X-Forwarded-Access-Token` header for on-behalf-of-user authentication
3. **SDK Confusion**: The Databricks SDK detects BOTH OAuth credentials AND token parameters, causing a validation error
4. **Missing Configuration**: The `/api/user/me` endpoint creates `UserService` instances without passing the user token, defaulting to service principal mode which conflicts with OAuth environment variables

### Affected Endpoints

Based on error logs, the following endpoints are failing:
- `/api/user/me` - User information retrieval
- `/api/model-serving/endpoints` - Model serving endpoint listing
- `/api/unity-catalog/catalogs` - Unity Catalog browsing
- `/api/preferences` - User preferences access

### Lakebase Authentication Exception

**Important Platform Constraint**: According to [Databricks Lakebase documentation](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/lakebase), Lakebase database connections do NOT support OBO authentication and MUST continue using service principal credentials because:

1. Lakebase creates PostgreSQL roles based on the **service principal's client ID** only
2. The platform grants the **service principal** CONNECT and CREATE privileges
3. The `PGUSER` environment variable contains the **service principal's client ID and role name**
4. No mechanism exists for per-user database authentication at the PostgreSQL level

**Implication**: While OBO tokens will be used for Databricks API calls (Unity Catalog, Model Serving, User endpoints), Lakebase connections must continue using service principal authentication. Application-level `user_id` filtering must enforce data isolation since database-level user authentication is not possible.

### Scope Boundaries

**In Scope:**
- Authentication layer fixes (OBO token extraction, SDK configuration, service principal fallback)
- Database schema changes required to support user_id filtering (migrations for preferences, saved queries, inference logs)
- Minimal UI error message improvements to display structured authentication failure responses to users

**Explicitly Out of Scope:**
- Changes to core business logic beyond authentication requirements
- UI/UX redesigns or enhancements unrelated to authentication error display
- Data visualization or dashboard components
- Performance optimizations beyond authentication-related requirements
- New feature development unrelated to authentication fix

---

## Clarifications

### Session 2025-10-09

- Q: When a user's access token expires mid-session, what should the API endpoints return? → A: Automatic retry with exponential backoff before returning error
- Q: Should user access tokens be cached in memory between requests, or extracted fresh from the header for each API call? → A: Extract fresh from header every request (slower, more secure)
- Q: What level of authentication activity should be logged for observability and audit purposes? → A: Detailed: Token presence, SDK config type, retry attempts, fallback triggers
- Q: Should the database schema store the requesting user's identity alongside query results and preferences? → A: Yes, store user_id with all user-specific records (preferences, saved queries)
- Q: What is the maximum total time the system should spend on authentication retries before failing the request? → A: 5 seconds (generous for slow networks)
- Q: If Databricks platform itself rate-limits authentication attempts during the 3-retry exponential backoff period, should the system: → A: Fail immediately and return HTTP 429 to user (respect platform limits)
- Q: When the same user has multiple browser tabs/sessions open simultaneously and one session's token gets refreshed by the platform, should: → A: All tabs automatically work with no special handling (each request is independent)
- Q: During deployment of this authentication fix to production Databricks Apps, should the rollout strategy be: → A: Deploy in-place with zero downtime (rolling update, users may see brief errors during cutover)
- Q: What is the expected scale of concurrent users and API request volume for this application in production? → A: Small scale: <50 concurrent users, <1000 requests/min
- Q: When upstream Databricks services (Unity Catalog, Model Serving) are temporarily unavailable or slow (beyond authentication issues), what should the user experience be? → A: Transparent: Show loading state indefinitely until service recovers (with timeout)
- Q: Beyond detailed logging, what operational metrics should be exposed for monitoring authentication health and system performance? → A: Comprehensive: All above plus per-user metrics, P95/P99 latencies, circuit breaker states
- Q: When a user access token is present in the X-Forwarded-Access-Token header but is malformed or invalid (not expired, but structurally broken or cryptographically invalid), what should the system do? → A: Retry with exponential backoff (same as expiration handling per FR-018) and provide detailed logger messages (see Edge Cases section for full retry behavior specification)
- Q: For local development testing of OBO authentication (FR-022 mentions "provide a way" but lacks specifics), which approach should be supported? → A: CLI command to fetch real tokens from Databricks workspace (Databricks CLI auth commands to get real user OAuth)
- Q: This authentication fix changes how API requests are handled. Are there existing deployed instances or users who would be affected by this change? → A: No, this is the first production deployment (greenfield)
- Q: The solution depends on Databricks SDK behavior for authentication configuration. Should specific SDK version constraints be documented? → A: Yes, specify minimum SDK version with required auth_type parameter support AND pin exact SDK version to prevent breaking changes
- Q: When the same user makes multiple concurrent API requests and some fail with authentication errors triggering retries, how should the retry logic coordinate across these parallel requests? → A: Each request retries independently (no coordination, potentially N×3 retries to backend)

### Session 2025-10-10

- Q: What is the minimum Databricks SDK version that introduced support for the explicit `auth_type` parameter? → A: Pin to version 0.67.0 (current stable version)
- Q: When the Databricks SDK version 0.67.0 (currently pinned) releases a security patch version (e.g., 0.67.1), how should the system handle version updates? → A: Auto-accept patch versions (0.67.x) - security fixes only
- Q: For the 90-day orphaned data retention policy mentioned in FR-010a, what should trigger the detection of an "inactive" user account? → A: User hasn't authenticated for 90+ days
- Q: When multiple application instances are deployed (for scaling), should the circuit breaker state be shared across instances? → A: Per-instance (each maintains own state) - simpler but less coordinated
- Q: For the comprehensive metrics mentioned in NFR-011 and NFR-012, what specific format should be used for exposing metrics to observability platforms? → A: JSON format at custom /api/metrics endpoint
- Q: When a malformed or invalid token is detected (not just expired), what level of detail should be logged for debugging? → A: Log error type + JWT claims (no token value)
- Q: What JWT claim should be used to extract the user identifier, and what format does it have? → A: Email address from userName field via UserService.get_user_info()
- Q: When user_id cannot be extracted from the user token (API call fails, malformed response, etc.), what should user-scoped database operations do? → A: Reject with HTTP 401 Unauthorized (authentication required)
- Q: What is the actual timeout value for upstream Databricks API calls (Unity Catalog, Model Serving) before the system gives up and returns an error? → A: 30 seconds (minimum acceptable)
- Q: When should the system fall back from OBO authentication to service principal mode? → A: Always automatic when X-Forwarded-Access-Token header is missing
- Q: Which of the following should be explicitly excluded from this authentication fix? → A: Authentication + database + minimal UI error message improvements for auth failures
- Q: Should the system implement circuit breaker logic to prevent retry storms during widespread authentication failures? → A: Yes, circuit breaker: After 10 consecutive auth failures system-wide, disable retries for 30 seconds
- Q: Should the system use email as the permanent user_id, or extract a different immutable identifier? → A: Use email (userName field) - accept risk of orphaned data if emails change
- Q: How long should operational metrics be retained before aggregation/deletion? → A: 7 days raw metrics, 90 days aggregated (compliance/audit-friendly retention)
- Q: What error response format should authentication failures return to the client? → A: Simple JSON with error_code and message fields - {error_code: "AUTH_EXPIRED", message: "..."}

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story

As a **Databricks App user**, when I open the deployed application and interact with the UI, I expect all API calls to execute successfully using my personal Databricks credentials, so that I can only see and access data that I have permissions for in Unity Catalog.

### Acceptance Scenarios

1. **Given** the app is deployed to Databricks Apps platform, **When** a user accesses `/api/user/me`, **Then** the system returns the authenticated user's information without authentication errors

2. **Given** a user has access to specific Unity Catalog tables, **When** the user requests `/api/unity-catalog/catalogs`, **Then** the system returns only catalogs the user has permissions to access

3. **Given** a user attempts to list model serving endpoints, **When** the request includes the user's access token, **Then** the system uses the user's credentials (not service principal) to query Databricks APIs

4. **Given** multiple users with different permission levels access the app, **When** each user queries Unity Catalog, **Then** each user sees only their authorized resources (proper permission isolation)

5. **Given** a user saves preferences to Lakebase, **When** the database connection is established, **Then** the system uses service principal credentials (not user OBO token) and stores the user's identity (user_id) with the preference record

6. **Given** the app runs in local development mode without Databricks Apps, **When** API calls are made without X-Forwarded-Access-Token header, **Then** the system automatically falls back to service principal credentials and logs the fallback event

### Edge Cases

- **What happens when the user's access token expires, is malformed, or is invalid?** See FR-018 for complete retry behavior specification (exponential backoff with 100ms/200ms/400ms delays, circuit breaker logic, stateless pattern)
- **How does the system handle API calls in background jobs?** Background tasks should use service principal credentials since no user context exists
- **What if Databricks SDK environment variables conflict?** The system must explicitly specify authentication type to prevent SDK auto-detection conflicts
- **How are database queries authenticated?** Lakebase connections use service principal authentication (platform limitation - PostgreSQL roles are service principal-only). Application-level `user_id` filtering must enforce data isolation, with user_id extracted from email addresses (userName field) accepting the risk of orphaned data if emails change
- **What happens when a user has multiple browser tabs open?** Each tab operates independently with stateless authentication - tokens are extracted fresh from headers on every request, so token refreshes automatically work across all tabs without coordination
- **How do concurrent API requests from the same user handle authentication retries?** Each request implements retry logic independently without coordination, meaning if 5 parallel requests all fail authentication, each will perform its own 3 retry attempts (potentially 15 total retry calls to the backend) following the stateless pattern, unless the circuit breaker opens to prevent excessive backend load
- **How does the system prevent cross-user data access in Lakebase?** All user-scoped queries must include `WHERE user_id = ?` clauses; missing user_id validation should cause query rejection with structured error responses
- **What happens when user_id extraction fails?** System returns HTTP 401 Unauthorized with structured JSON error format when UserService.get_user_info() fails or returns malformed response, preventing database operations from executing with missing or invalid user identity
- **How does the system handle upstream service degradation?** The system implements "transparent loading state" behavior: when upstream Databricks services are slow or temporarily unavailable (beyond authentication issues), the backend continues waiting without immediately returning an error response (up to 30-second timeout per NFR-010), allowing the frontend to display loading indicators or skeleton UI. This provides better UX than immediate failures during transient outages
- **What happens during widespread authentication outages?** The circuit breaker (FR-018a) detects 10 consecutive authentication failures system-wide and opens for 30 seconds, immediately failing subsequent requests without retries to protect backend services, while logging circuit breaker state transitions for operational visibility

---

## Requirements *(mandatory)*

### Functional Requirements

#### Core Authentication (Databricks APIs)
- **FR-001**: System MUST extract user access tokens from the `X-Forwarded-Access-Token` header fresh on every request without caching or persistence between requests (see also NFR-005 for security rationale). If X-Forwarded-Access-Token header is present but contains empty string or malformed value (e.g., truncated base64, invalid JWT structure), system MUST treat as missing token: log WARNING event 'auth.malformed_token_header' with details, fall back to service principal mode per FR-016. Rationale: Platform should never send malformed tokens; presence indicates deployment/configuration issue requiring investigation but should not block request
- **FR-002**: System MUST pass user access tokens to Databricks API service layer components (UserService, UnityCatalogService, ModelServingService) but NOT to LakebaseService
- **FR-003**: System MUST explicitly specify `auth_type="pat"` when initializing Databricks SDK clients with user tokens to prevent authentication method conflicts
- **FR-004**: System MUST explicitly specify `auth_type="oauth-m2m"` when initializing Databricks SDK clients with service principal credentials
- **FR-024**: System MUST use Databricks SDK version 0.67.0 (pinned exactly in dependency files) which supports explicit auth_type parameter configuration to prevent breaking changes

#### User Information Endpoints
- **FR-005**: The `/api/user/me` endpoint MUST retrieve the actual authenticated user's information (not service principal) using the user access token passed per FR-002
- **FR-006**: The `/api/user/me/workspace` endpoint MUST retrieve workspace information for the authenticated user (not service principal) using the user access token passed per FR-002
- **FR-006a**: UserService MUST provide a public `get_workspace_info()` method that returns workspace information using the appropriate authentication mode (OBO or service principal) without exposing internal client creation logic to endpoint handlers. **Rationale**: Public get_workspace_info() method maintains encapsulation per Constitution Principle IV (Type Safety) - router endpoints call high-level service methods rather than low-level client creation utilities (_get_client). This separation of concerns improves testability and prevents routers from needing knowledge of SDK client configuration details
- **FR-007**: User information endpoints MUST NOT create service-only clients that bypass user authentication

#### Permission Enforcement (Databricks APIs)
- **FR-008**: System MUST enforce Unity Catalog permissions at the user level (users see only resources they can access)
- **FR-009**: Model serving API calls MUST use user credentials to respect endpoint-level permissions
- **FR-010**: System MUST extract user_id (email address) by calling UserService.get_user_info() with the user access token and retrieving the userName field, then store this user_id with all user-specific database records including preferences, saved queries, and inference logs to ensure proper data isolation (Note: Using email as permanent identifier accepts the risk of orphaned data if user email addresses change in the identity system - this tradeoff prioritizes implementation simplicity over immutable user tracking)
- **FR-010a**: System MUST provide orphaned data management via admin endpoint `/api/admin/orphaned-records` that lists preferences, saved queries, and inference logs associated with inactive user accounts. Inactivity definition: User hasn't authenticated for 90+ consecutive days (tracked via last_authenticated timestamp in user_preferences table). Orphaned data retention policy: Records remain queryable by old email for 90 days after inactivity threshold reached, then automatically purged via scheduled cleanup job. Admin endpoint requires elevated permissions (admin users defined in `ADMIN_USERS` environment variable as comma-separated email list) and logs all access for audit compliance. Admin authentication mechanism: Environment variable-based whitelist approach chosen for simplicity over role-based access control (RBAC) given small user scale (<50 users per NFR-009).

#### Lakebase Authentication (Service Principal)
- **FR-011**: LakebaseService MUST use service principal credentials exclusively (NOT user OBO tokens) for all database connections. Connection tokens obtained via Databricks SDK WorkspaceClient.generate_database_credential() API call (using service principal authentication per Constitution Principle II line 45). Generated tokens are short-lived with platform-managed expiration. Connection string format: postgresql+psycopg2://token:<generated_token>@<PGHOST>:<PGPORT>/<PGDATABASE> where <generated_token> is result of generate_database_credential() call
- **FR-012**: System MUST read Lakebase connection parameters from platform-provided environment variables (`PGHOST`, `PGDATABASE`, `PGUSER`, `PGPORT`, `PGSSLMODE`)
- **FR-013**: System MUST filter all user-scoped database queries by `user_id` to enforce application-level data isolation
- **FR-014**: System MUST validate `user_id` before executing user-scoped database operations using the following validation rules: (1) user_id MUST be non-empty string, (2) user_id MUST match valid email format (EmailStr validation via Pydantic), (3) user_id MUST be extracted from UserService.get_user_info() API call result (NEVER trust client-provided values in headers/query params/request body), (4) user_id extraction MUST succeed (return HTTP 401 Unauthorized if UserService.get_user_info() fails or returns malformed response). Optional validation: Check active=True status (business requirement dependent). Validation function signature: `async def validate_user_id(user_id: Optional[str]) -> str` raising HTTPException(401) on validation failure

#### Error Handling
- **FR-015**: System MUST return clear error messages when authentication fails using structured JSON format with error_code and message fields (e.g., `{"error_code": "AUTH_EXPIRED", "message": "User access token has expired"}`) to enable consistent client-side error handling and minimal UI error message display improvements
- **FR-016**: System MUST automatically fall back to service principal mode when the X-Forwarded-Access-Token header is missing from requests (typical in local development environments), without requiring explicit configuration flags or environment variables
- **FR-017**: System MUST log detailed authentication activity including: token presence (yes/no), SDK config auth_type, retry attempt numbers, fallback trigger events, token validation failure details (error type plus JWT claims but NEVER the token value itself), and circuit breaker state transitions for debugging and audit purposes. Token validation logging detail: Log validation error type (malformed/invalid/expired) plus decoded JWT claims (sub, email, exp, iat) when available, but NEVER log the actual token string per SC-001. All log entries MUST include correlation IDs per Constitution Principle VIII: correlation ID generation is mandatory (server generates UUID v4 when X-Correlation-ID header missing), client-provided correlation IDs are accepted for end-to-end tracing when present
- **FR-018**: System MUST implement comprehensive retry logic for authentication failures with the following subsections:
  - **FR-018a (Exponential Backoff)**: Retry authentication failures minimum 3 attempts with exponential delays (100ms, 200ms, 400ms). Total timeout MUST NOT exceed 5 seconds across all retries. Applies to all authentication failures including malformed, invalid, and expired tokens
  - **FR-018b (Circuit Breaker)**: After detecting 10 consecutive authentication failures system-wide, disable retry attempts for 30 seconds (circuit open state) to prevent retry storms during widespread authentication outages. **Circuit breaker scope**: Per-instance (each application process maintains its own circuit breaker state in memory) - not shared across multiple deployed instances. This per-instance pattern simplifies implementation (no distributed state management, no Redis/cache/database coordination required) and provides sufficient protection since each instance handles ~10-20 concurrent users per NFR-009 scale target. Trade-off accepted: During partial outages, some instances may have open circuit breakers while others remain closed, providing degraded but not completely blocked service. Log circuit breaker state transitions per FR-017
  - **FR-018c (Stateless Pattern)**: Implement retry logic independently per request without coordination across concurrent requests from the same user. Multiple parallel requests each perform their own retry attempts (no shared state or coordination)
- **FR-019**: System MUST detect Databricks platform rate limit responses (HTTP 429) during retry attempts and immediately fail the request by returning HTTP 429 to the user without further retries to respect platform limits
- **FR-023**: When upstream Databricks services (Unity Catalog, Model Serving) are temporarily unavailable or degraded, system MUST maintain HTTP connection open without intermediate responses (no streaming, keep-alive, or progress updates) until service responds or 30-second timeout reached per NFR-010. Frontend detects pending response via standard HTTP loading indicators (spinners, skeleton UI). Backend implementation: simple await pattern, no special handling. Example: `curl http://localhost:8000/api/unity-catalog/catalogs` waits up to 30s before returning response or timeout error

#### Local Development Support
- **FR-020**: System MUST work in local development environments where `X-Forwarded-Access-Token` is not present by automatically falling back to service principal credentials per FR-016
- **FR-021**: System MUST log when automatic fallback to service principal mode occurs due to missing X-Forwarded-Access-Token header to clearly indicate authentication mode in use
- **FR-022**: System MUST support testing OBO authentication locally by accepting user OAuth tokens obtained via Databricks CLI command `databricks auth token`, allowing developers to test with real authentication credentials in their development environment (Usage: `export DATABRICKS_USER_TOKEN=$(databricks auth token)`)

### Non-Functional Requirements

- **NFR-001**: Authentication token extraction and validation must add less than 10ms to request processing time
- **NFR-002**: All authentication configuration must be documented in code comments and external documentation
- **NFR-003**: The solution must be compatible with existing Databricks Apps deployment patterns
- **NFR-004**: No user tokens or credentials should be logged (security requirement)
- **NFR-005**: User access tokens MUST NOT be cached, stored in memory between requests, or persisted to disk to minimize security exposure and ensure token revocation takes immediate effect (implementation: FR-001)
- **NFR-006**: Authentication retry operations MUST complete within 5 seconds total (including all retry attempts and network overhead) to prevent request timeouts and degraded user experience
- **NFR-007**: Deployment to production MUST support in-place rolling updates with zero planned downtime, accepting brief transient errors during cutover as acceptable degradation (Note: This is the first production deployment/greenfield, but design must support future updates)
- **NFR-008**: Lakebase database connection pooling must efficiently handle concurrent user requests under a single service principal authentication without performance degradation
- **NFR-009**: System MUST support up to 50 concurrent users and handle up to 1000 API requests per minute without degradation in authentication response times or error rates
- **NFR-010**: Upstream service timeout for Databricks API calls (Unity Catalog, Model Serving) MUST be configured to exactly 30 seconds to allow sufficient time for service recovery and enable transparent loading state behavior
- **NFR-011**: System MUST expose comprehensive operational metrics including: authentication success/failure counts per endpoint, authentication retry rates, token extraction time, average and P95/P99 request latencies, per-user request counts, circuit breaker state changes, and upstream service availability indicators for monitoring dashboards and alerting
- **NFR-012**: Metrics MUST be collected and exposed via JSON format at `/api/metrics` endpoint. JSON structure must include nested objects for metric categories (authentication, requests, latencies, circuit_breaker) with standardized field names. Example: `{"authentication": {"success_count": 100, "failure_count": 5}, "latencies": {"p95_ms": 250, "p99_ms": 500}}`. Observability platforms can poll this endpoint and transform JSON to their native formats (Prometheus exporters, Datadog agents, CloudWatch custom metrics)
- **NFR-012a**: Operational metrics MUST be retained with the following durability policy: raw metrics stored for 7 days minimum, aggregated metrics (hourly/daily rollups) stored for 90 days minimum to support compliance and audit requirements while managing storage costs. Aggregation implementation: Prometheus recording rules execute hourly rollups (sum, avg, p95, p99 by endpoint). Rules defined in config/prometheus-rules.yml. Aggregated metrics stored in same Prometheus instance with longer retention policy. Manual aggregation fallback: scripts/aggregate_metrics.py for environments without recording rule support
- **NFR-013**: Databricks SDK MUST be pinned to version 0.67.x in dependency management files (requirements.txt), allowing patch updates for security fixes while preventing minor/major version changes that could introduce breaking changes. Acceptable versions: 0.67.0 through 0.67.999. Version constraint syntax: `databricks-sdk>=0.67.0,<0.68.0`
- **NFR-014**: System MUST provide admin tooling for orphaned data management per FR-010a, including: (1) Admin endpoint `/api/admin/orphaned-records` with pagination support, (2) Scheduled cleanup job running daily to purge records >90 days after user deactivation (scheduled via Databricks Jobs with quartz cron expression "0 0 2 * * ?" for 2 AM daily execution), (3) Admin access logging for audit compliance, (4) Cleanup dry-run mode for pre-deletion verification. Scheduling mechanism: Databricks Jobs chosen over cron/systemd for platform-native integration and reliability

### Key Entities *(included - feature involves authentication data)*

- **User Access Token**: JWT token provided by Databricks Apps in `X-Forwarded-Access-Token` header, represents authenticated user's identity and permissions, expires and is refreshed by platform, used ONLY for Databricks APIs (not Lakebase)
- **User Identity (user_id)**: Email address extracted by calling UserService.get_user_info() with the user access token (returns userName field), stored with all user-specific database records (preferences, saved queries, inference logs) to enforce data isolation and enable per-user queries (Note: Risk of orphaned data if emails change)
- **Service principal credentials**: OAuth client credentials (`DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`) for app-level operations, used for Lakebase connections and when user context is unavailable
- **Databricks SDK Config**: Configuration object that specifies authentication method, must include explicit `auth_type` to prevent multi-method detection errors
- **Request Context**: FastAPI request state that carries user token from middleware through to service layer dependencies
- **Lakebase Database Connection**: PostgreSQL connection authenticated with service principal role (matching service principal's client ID), shared across all user sessions
- **Database Role**: PostgreSQL role created by Databricks platform with name matching service principal's client ID, granted CONNECT and CREATE privileges
- **Circuit Breaker State**: System-wide authentication health tracking entity that counts consecutive authentication failures (threshold: 10) and manages open/closed states with 30-second cooldown periods to prevent retry storms
- **Authentication Error Response**: Structured JSON error format with error_code field (e.g., "AUTH_EXPIRED", "AUTH_INVALID", "AUTH_MISSING") and human-readable message field for consistent client-side error handling and UI display
- **Operational Metrics**: Time-series data tracking authentication events, retained as raw metrics (7 days) and aggregated rollups (90 days) for observability and compliance

---

## Terminology Glossary

- **User Access Token** (formal): JWT token provided by Databricks Apps platform in `X-Forwarded-Access-Token` header representing authenticated user's identity and permissions
- **OBO Token** (shorthand): Abbreviation for "On-Behalf-Of token", synonymous with user access token, commonly used in implementation code
- **User Token** (informal): Generic reference to user access token, used in variable names and casual documentation
- **Service Principal Credentials**: OAuth M2M client credentials (`DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`) for app-level operations

**Usage Guideline**: 
- **In spec.md requirements**: Use "user access token" (formal)
- **In code variable names**: Use `user_token` (informal, Pythonic)
- **In documentation prose**: Use "OBO authentication" and "user access token" interchangeably
- **In contracts/*.yaml**: Use "user_token" for parameters, "User Access Token" for descriptions
- **NEVER**: Mix terms within same sentence or paragraph

---

## Security Constraints Reference

**AUTHORITATIVE: This section defines security constraints referenced throughout this specification and implementation documents.**

### SC-001: Token Security (Critical)
User access tokens MUST NEVER be:
- Logged to any destination (files, console, observability platforms)
- Cached in memory between requests
- Persisted to disk or database
- Included in error messages or stack traces

**Implementation**: Extract fresh from `X-Forwarded-Access-Token` header on every request per FR-001. Only log token **presence** (boolean), never the token **value** per FR-017 and NFR-004.

**Rationale**: Immediate token revocation and minimal security exposure per NFR-005.

**References**: FR-001, FR-017, NFR-004, NFR-005, data-model.md section 1

### SC-002: User Identity Trust (Critical)
User identity (`user_id`) MUST ALWAYS be:
- Extracted from Databricks API response (via `UserService.get_user_info()`)
- NEVER trusted from client-provided values (headers, query params, request body)
- Validated for presence before database operations

**Implementation**: Call `WorkspaceClient.current_user.me()` with user access token per FR-010. Reject operations with HTTP 401 if extraction fails per FR-014.

**Rationale**: Prevents identity spoofing and ensures authoritative user identity per Constitution Principle IX.

**References**: FR-010, FR-014, Constitution Principle IX, data-model.md section 2

### SC-003: Credentials in Logs (Critical)
Application logs MUST NEVER contain:
- User access tokens
- Service principal secrets
- Passwords or API keys
- Any credential material

**Implementation**: Structured logger actively filters sensitive fields per research.md section 7. All authentication events log only metadata (token presence, auth mode, correlation ID).

**Rationale**: Compliance, security audits, GDPR considerations per NFR-004.

**References**: NFR-004, FR-017, research.md section 7, data-model.md section 8

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous  
- [x] Success criteria are measurable (API calls succeed, no auth errors)
- [x] Scope is clearly bounded (authentication layer only)
- [x] Dependencies and assumptions identified (Databricks Apps platform, SDK behavior)

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed (authentication error identified, Lakebase clarification added)
- [x] Key concepts extracted (OBO for APIs, service principal for Lakebase, SDK configuration, token passing)
- [x] Ambiguities clarified (26 questions answered covering rate limiting, multi-tab behavior, deployment strategy, scale targets, service degradation handling, comprehensive metrics, malformed token handling, local OBO testing, greenfield deployment context, SDK version constraints, concurrent request retry coordination, SDK version pinning, user_id extraction method, user_id extraction failure handling, upstream timeout values, automatic service principal fallback, scope boundaries, circuit breaker logic, email identifier risk acceptance, metrics retention policy, error response format)
- [x] User scenarios defined (authenticated API access with proper permissions, Lakebase service principal usage, circuit breaker protection during outages)
- [x] Requirements generated (27 functional including FR-018a and FR-015 updates, 14 non-functional including NFR-012a)
- [x] Entities identified (tokens, user identity, credentials, SDK config, request context, database connections, database role, circuit breaker state, error response format, operational metrics)
- [x] Review checklist passed

---

## Success Metrics

The feature is considered successfully implemented when:

1. **Zero authentication errors** in deployed Databricks App logs after fix (excluding circuit breaker activation scenarios)
2. **All API endpoints** (`/api/user/me`, `/api/model-serving/endpoints`, `/api/unity-catalog/catalogs`, `/api/preferences`) return successful responses with proper authentication
3. **Permission isolation verified**: Different users see different resources based on their Unity Catalog permissions
4. **Audit logs accurate**: 
   - Databricks API operations (Unity Catalog, Model Serving) are logged under actual user identities
   - Lakebase database operations are logged under service principal (platform limitation)
   - Application logs capture actual user_id for all operations for audit trail
   - Circuit breaker state transitions are logged for operational visibility
5. **Local development works**: Application runs successfully in local mode with appropriate fallback behavior
6. **Observability validated**: 
   - Logs contain detailed authentication information (token presence, SDK auth_type, retry attempts, fallback triggers, circuit breaker states) for all requests
   - Comprehensive metrics exposed including authentication success/failure rates, retry rates, P95/P99 latencies per endpoint, per-user request counts, and circuit breaker state changes
   - Metrics are queryable in standard observability platform (Prometheus/Datadog/CloudWatch compatible)
   - Metrics retention verified: raw metrics retained 7+ days, aggregated metrics retained 90+ days
7. **Data isolation verified**: User-specific database records (preferences, saved queries, inference logs) contain user_id (email address) and queries filter results by authenticated user
8. **Lakebase security validated**: No user OBO tokens are passed to Lakebase connections; all database queries properly filter by user_id
9. **Deployment resilience confirmed**: Initial production deployment completes successfully (this is a greenfield deployment), and system design supports future rolling updates with stateless authentication pattern enabling zero-downtime cutover for subsequent releases
10. **Error handling validated**:
    - Authentication failures return structured JSON errors with error_code and message fields
    - Circuit breaker opens after 10 consecutive auth failures and closes after 30 seconds
    - UI displays minimal but clear error messages based on structured error responses
11. **Scope boundaries respected**: Implementation includes only authentication layer fixes, necessary database schema migrations for user_id, and minimal UI error message display improvements - no unrelated business logic or UI/UX changes

---

## Related Documentation

- Databricks Apps Cookbook - OBO Authentication: https://apps-cookbook.dev/docs/streamlit/authentication/users_obo
- Databricks Lakebase Documentation: https://docs.databricks.com/aws/en/dev-tools/databricks-apps/lakebase
- Existing codebase documentation: `docs/OBO_AUTHENTICATION.md`
- Databricks SDK Python documentation for authentication configuration

---

*Aligned with Constitution v1.0.0 - See `.specify/memory/constitution.md`*
