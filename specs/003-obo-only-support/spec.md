# Feature Specification: Remove Service Principal Fallback - OBO-Only Authentication

**Feature Branch**: `003-obo-only-support`  
**Created**: October 14, 2025  
**Status**: Draft  
**Input**: User description: "The app falls back to service principle authentication when the user token is not present. I want to remove this fallback. This project will now only support OBO authentication. There is no need for backward compatibility. For local development, figure out a way not to leverage service principle-based authenticiation."

## Clarifications

### Session 2025-10-14

- Q: How should health check and metrics endpoints handle authentication? → A: Conditional - `/health` public/unauthenticated for monitoring systems, `/metrics` requires user authentication due to sensitive data
- Q: How should database (Lakebase) connections handle authentication in the OBO-only model? → A: Hybrid approach - Database uses application-level credentials but enforces user_id filtering in queries
- Q: What should happen to background jobs, scheduled tasks, or automated processes? → A: None exist - Application has no background jobs, this edge case is theoretical only
- Q: How should tests handle scenarios requiring different user permission levels? → A: Mixed approach - Unit tests use mocks, integration tests use real tokens from test users
- Q: What should happen to existing DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET environment variables? → A: No special handling - Variables can remain but are simply not used, no validation or warnings needed

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enforce OBO-Only Authentication in Production (Priority: P1)

As a security-conscious organization, I want the application to ONLY use On-Behalf-Of-User (OBO) authentication so that all operations are performed with the user's actual permissions, ensuring proper audit trails and preventing privilege escalation.

**Why this priority**: This is the core security requirement. Without this, the application could bypass user-level permissions by falling back to service principal credentials, which violates the principle of least privilege and creates audit compliance issues.

**Independent Test**: Can be fully tested by deploying to Databricks Apps and verifying that all API calls use only user tokens. Any request without a valid user token should fail with a clear authentication error rather than falling back to service principal.

**Acceptance Scenarios**:

1. **Given** the application is deployed to Databricks Apps, **When** a user makes a request to list Unity Catalog tables, **Then** the request uses ONLY the user's token (X-Forwarded-Access-Token header) and returns tables the user has permission to access.

2. **Given** a request is made without a user token, **When** the service attempts to create a WorkspaceClient, **Then** the service raises an authentication error with clear error message and HTTP 401 status code.

3. **Given** multiple services (UnityCatalogService, ModelServingService, UserService), **When** initialized without a user_token parameter, **Then** all services raise a ValueError indicating that user_token is required.

4. **Given** the application is running, **When** examining the logs, **Then** there are NO "service principal fallback" events and all auth.mode events show "obo" not "service_principal".

---

### User Story 2 - Local Development with User Tokens (Priority: P1)

As a developer, I want to develop and test locally using my own Databricks user token instead of service principal credentials, so that I can test with realistic user-level permissions and catch permission issues early in development.

**Why this priority**: Local development is critical for developer productivity. Without a clear alternative to service principal authentication, developers will be blocked or forced to deploy to test every change. This priority is P1 because it's a prerequisite for maintaining development velocity.

**Independent Test**: Can be fully tested by following the local development setup guide, obtaining a user token via Databricks CLI, and verifying that all API endpoints work correctly with the token and fail appropriately without it.

**Acceptance Scenarios**:

1. **Given** a developer has authenticated with Databricks CLI, **When** they run `databricks auth token` and export the token, **Then** they can start the local development server and make API calls using their user token.

2. **Given** the local development server is running, **When** a developer makes a request with their user token in the X-Forwarded-Access-Token header, **Then** the request succeeds and the response reflects their actual permissions (not elevated service principal permissions).

3. **Given** the local development server is running, **When** a developer makes a request WITHOUT a user token, **Then** the request fails with HTTP 401 and a clear error message explaining that user authentication is required.

4. **Given** the developer documentation, **When** a new developer follows the local development setup guide, **Then** they can successfully set up and test the application in under 10 minutes without needing service principal credentials.

---

### User Story 3 - Clear Error Messages for Missing Authentication (Priority: P2)

As a user or developer, I want to receive clear, actionable error messages when authentication fails, so that I can quickly understand what went wrong and how to fix it.

**Why this priority**: Good error handling improves user experience and reduces support burden. However, it's P2 because the core functionality (P1 stories) must work first.

**Independent Test**: Can be tested independently by making requests with various authentication states (no token, invalid token, expired token) and verifying the error responses are helpful and structured correctly.

**Acceptance Scenarios**:

1. **Given** a request is made without a user token, **When** the authentication check occurs, **Then** the response includes HTTP 401 status, error_code "AUTH_MISSING", and a message explaining "User authentication required. Please provide a valid user access token."

2. **Given** a request is made with an invalid or malformed token, **When** token validation fails, **Then** the response includes HTTP 401 status, error_code "AUTH_INVALID", and a message explaining the token is invalid.

3. **Given** a request is made with an expired token, **When** the Databricks SDK validates the token, **Then** the response includes HTTP 401 status, error_code "AUTH_EXPIRED", and a message explaining the token has expired.

4. **Given** error responses are returned, **When** viewed in the application logs, **Then** the logs include structured error events with correlation IDs for debugging.

---

### User Story 4 - Update Documentation and Configuration (Priority: P2)

As a developer or operator, I want comprehensive documentation that reflects the OBO-only authentication model, so that I understand how to deploy, configure, and troubleshoot the application.

**Why this priority**: Documentation is critical for adoption and maintenance, but it's P2 because the implementation must be complete first before documentation can be finalized.

**Independent Test**: Can be tested by following the documentation to deploy and operate the application, verifying that all instructions are accurate and complete.

**Acceptance Scenarios**:

1. **Given** the OBO_AUTHENTICATION.md document, **When** reviewing the content, **Then** it clearly states the application is OBO-only and removes all references to service principal fallback.

2. **Given** the LOCAL_DEVELOPMENT.md document, **When** following the setup instructions, **Then** the instructions guide developers to use user tokens for local testing and explain how to obtain them via Databricks CLI.

3. **Given** the environment variable documentation, **When** reviewing required vs optional variables, **Then** DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET are marked as NOT REQUIRED, and the user token flow is clearly documented.

4. **Given** the deployment documentation, **When** deploying to Databricks Apps, **Then** the documentation explains that OBO is automatically enabled via the X-Forwarded-Access-Token header.

---

### User Story 5 - Remove Service Principal Configuration (Priority: P3)

As a security administrator, I want to remove service principal credentials from the application configuration, so that there's no possibility of bypassing user-level permissions even if the code changes in the future.

**Why this priority**: This is a cleanup task that improves security posture, but it's P3 because the application can still function securely if service principal credentials exist but are never used. This is more about defense-in-depth.

**Independent Test**: Can be tested by verifying that the application works correctly without DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET environment variables set.

**Acceptance Scenarios**:

1. **Given** the application is deployed without DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET set, **When** a user makes authenticated requests, **Then** the application functions normally using only user tokens.

2. **Given** the application configuration files (app.yaml, .env templates), **When** reviewing the configuration, **Then** there are no references to DATABRICKS_CLIENT_ID or DATABRICKS_CLIENT_SECRET as required variables.

3. **Given** the service initialization code, **When** examining the _create_service_principal_config methods, **Then** these methods are removed since they are no longer needed.

4. **Given** the deployment checklist, **When** preparing for deployment, **Then** the checklist does not require service principal credentials to be configured.

---

### Edge Cases

- **What happens when a user token expires during a long-running request?** The Databricks SDK automatically detects token expiration during API calls and raises an authentication error. The application surfaces this as HTTP 401 with AUTH_EXPIRED error code. No special retry logic needed—clients should re-authenticate and retry the request with a fresh token.

- **How does the system handle unauthenticated health check endpoints?** The `/health` endpoint is public/unauthenticated to support monitoring infrastructure (uses `get_user_token_optional()` dependency). The `/metrics` endpoint requires user authentication via `get_user_token()` dependency due to potentially sensitive operational data it exposes.

- **What happens when X-Forwarded-Access-Token header is present but empty?** The application treats empty strings the same as missing tokens: `get_user_token()` dependency raises HTTP 401 with AUTH_MISSING error code.

- **What happens during testing when multiple developers share a workspace?** Each developer uses their own user token (obtained via `databricks auth token --profile <name>`), which enforces isolation through Unity Catalog permissions. Tests should document this behavior and use appropriate test data that's accessible to test users. See FR-010 for testing strategy.

- **How is LakebaseService user_id filtering enforced?** LakebaseService router endpoints MUST extract user_id using OBO-authenticated UserService (requires user_token), then pass user_id to LakebaseService methods which enforce `WHERE user_id = :user_id` filtering in all user-scoped queries. See research.md section 3 for detailed pattern.

- **Note on background jobs**: This application has no background jobs, scheduled tasks, or automated processes. All operations are user-initiated and authenticated with user tokens.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST require a valid user access token for ALL authenticated API endpoints, with NO fallback to service principal authentication.

- **FR-002**: All Databricks API services (UnityCatalogService, ModelServingService, UserService) MUST require `user_token` parameter in their `__init__` methods and raise ValueError if not provided. LakebaseService (database) uses application-level credentials but enforces user_id filtering in all queries to maintain data isolation.

- **FR-003**: System MUST remove all code paths that create WorkspaceClient instances using service principal OAuth M2M credentials (DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET).

- **FR-004**: System MUST configure WorkspaceClient instances with ONLY `token=user_token` and `auth_type="pat"` parameters, ensuring no fallback authentication methods exist.

- **FR-005**: System MUST return HTTP 401 status code with structured error responses (including error_code field) when user token is missing, invalid, or expired.

- **FR-006**: System MUST log authentication events with structured logging. Authentication log events MUST show `mode="obo"` and `auth_type="pat"` (never `mode="service_principal"` or fallback-related events). The mode value should be hardcoded as "obo" in log statements since OBO is the only supported authentication pattern.

- **FR-007**: Local development setup MUST document how to obtain and use user tokens via Databricks CLI (`databricks auth token`), including profile-based authentication for multi-user testing.

- **FR-008**: System MUST implement conditional authentication for monitoring endpoints: `/health` endpoint MUST be public/unauthenticated to support infrastructure monitoring, while `/metrics` endpoint MUST require user token authentication due to potentially sensitive operational data.

- **FR-009**: Environment variable configuration MUST NOT require DATABRICKS_CLIENT_ID or DATABRICKS_CLIENT_SECRET. These legacy variables may remain in deployed environments but are simply not used by the application (no validation, warnings, or error handling needed).

- **FR-010**: System MUST update all tests using a mixed approach: unit tests use mock/fake tokens for speed and isolation, while integration tests use real user tokens from test users with different permission levels to validate actual Databricks permission enforcement.

- **FR-011**: System MUST remove or update retry logic and circuit breaker code that may have been designed around service principal fallback scenarios. Standard retry logic for transient network errors should be maintained using tenacity library with exponential backoff.

- **FR-012**: System MUST remove the `_create_service_principal_config` and `_get_service_principal_client` methods from all Databricks API service classes (UnityCatalogService, ModelServingService, UserService).

- **FR-013**: System MUST define both `get_user_token()` (required, raises 401) and `get_user_token_optional()` (returns Optional[str]) dependency functions in `server/lib/auth.py` for conditional authentication requirements (health endpoint vs authenticated endpoints).

### Key Entities

- **AuthenticationContext**: Represents the authentication state of a request. The `auth_mode` field is removed from the model entirely. Authentication mode logging is handled separately by hardcoding `mode="obo"` in log statements.

- **WorkspaceClient**: Databricks SDK client. Must be initialized with ONLY user token authentication (`token=user_token, auth_type="pat"`), never with OAuth M2M credentials (`auth_type="oauth-m2m"`).

- **UserToken**: The user's access token extracted from the X-Forwarded-Access-Token header. Now required (str, not Optional[str]) for all authenticated operations.

- **Service Classes**: UnityCatalogService, ModelServingService, UserService all require user_token parameter (type: str, not Optional[str]) and raise ValueError if not provided. Service principal fallback logic and `_create_service_principal_config` methods are removed. LakebaseService uses application-level database credentials but enforces user_id-based query filtering (`WHERE user_id = :user_id`) for data isolation—user_id must be extracted via OBO-authenticated UserService.

- **ErrorResponse**: Structured error response model with error_code (AuthErrorCode enum), message, optional detail, and optional retry_after. Used for all authentication failures (HTTP 401) and rate limiting (HTTP 429).

- **Dependency Functions**: `get_user_token()` (raises HTTPException 401 if missing) and `get_user_token_optional()` (returns Optional[str]) enable conditional authentication patterns.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of API endpoints (excluding `/health` which is public for monitoring) require user token authentication and return HTTP 401 when token is missing.

- **SC-002**: Zero instances of "service_principal" or "auth.fallback" events in application logs during normal operation.

- **SC-003**: All three Databricks API service classes (UnityCatalogService, ModelServingService, UserService) raise ValueError when initialized without user_token parameter. LakebaseService is excluded as it uses application-level database credentials with user_id filtering.

- **SC-004**: Local development documentation enables a new developer to set up and test the application using user tokens in under 10 minutes.

- **SC-005**: All existing integration tests pass when updated to use user tokens instead of service principal credentials.

- **SC-006**: Code search for "oauth-m2m", "_create_service_principal_config", and "_get_service_principal_client" returns zero results in `server/services/` directory.

- **SC-007**: Application successfully deploys and operates in Databricks Apps environment with only OBO authentication, verified through production logs showing only `mode="obo"` in auth events and zero service principal or fallback events.

- **SC-008**: Authentication error responses include structured error codes (AUTH_MISSING, AUTH_INVALID, AUTH_EXPIRED) in 100% of authentication failure scenarios.
