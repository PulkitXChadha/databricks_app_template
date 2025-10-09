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

6. **Given** the app runs in local development mode without Databricks Apps, **When** API calls are made, **Then** the system gracefully falls back to service principal or development credentials

### Edge Cases

- **What happens when the user's access token expires?** The system must implement automatic retry with exponential backoff (e.g., 100ms, 200ms, 400ms delays) before returning authentication errors to the client
- **How does the system handle API calls in background jobs?** Background tasks should use service principal credentials since no user context exists
- **What if Databricks SDK environment variables conflict?** The system must explicitly specify authentication type to prevent SDK auto-detection conflicts
- **How are database queries authenticated?** Lakebase connections use service principal authentication (platform limitation - PostgreSQL roles are service principal-only). Application-level `user_id` filtering must enforce data isolation
- **What happens when a user has multiple browser tabs open?** Each tab operates independently with stateless authentication - tokens are extracted fresh from headers on every request, so token refreshes automatically work across all tabs without coordination
- **How does the system prevent cross-user data access in Lakebase?** All user-scoped queries must include `WHERE user_id = ?` clauses; missing user_id validation should cause query rejection

---

## Requirements *(mandatory)*

### Functional Requirements

#### Core Authentication (Databricks APIs)
- **FR-001**: System MUST extract user access tokens from the `X-Forwarded-Access-Token` header fresh on every request without caching or persistence between requests
- **FR-002**: System MUST pass user access tokens to Databricks API service layer components (UserService, UnityCatalogService, ModelServingService) but NOT to LakebaseService
- **FR-003**: System MUST explicitly specify `auth_type="pat"` when initializing Databricks SDK clients with user tokens to prevent authentication method conflicts
- **FR-004**: System MUST explicitly specify `auth_type="oauth-m2m"` when initializing Databricks SDK clients with service principal credentials

#### User Information Endpoints
- **FR-005**: The `/api/user/me` endpoint MUST accept and use user access tokens to retrieve the actual authenticated user's information
- **FR-006**: The `/api/user/me/workspace` endpoint MUST accept and use user access tokens to retrieve workspace information for the authenticated user
- **FR-007**: User information endpoints MUST NOT create service-only clients that bypass user authentication

#### Permission Enforcement (Databricks APIs)
- **FR-008**: System MUST enforce Unity Catalog permissions at the user level (users see only resources they can access)
- **FR-009**: Model serving API calls MUST use user credentials to respect endpoint-level permissions
- **FR-010**: System MUST store the authenticated user's identity (user_id) with all user-specific database records including preferences, saved queries, and inference logs to ensure proper data isolation

#### Lakebase Authentication (Service Principal)
- **FR-011**: LakebaseService MUST use service principal credentials exclusively (NOT user OBO tokens) for all database connections
- **FR-012**: System MUST read Lakebase connection parameters from platform-provided environment variables (`PGHOST`, `PGDATABASE`, `PGUSER`, `PGPORT`, `PGSSLMODE`)
- **FR-013**: System MUST filter all user-scoped database queries by `user_id` to enforce application-level data isolation
- **FR-014**: System MUST validate that `user_id` is present before executing user-scoped database operations (preferences, saved queries, inference logs)

#### Error Handling
- **FR-015**: System MUST return clear error messages when authentication fails (not internal SDK validation errors)
- **FR-016**: System MUST gracefully fall back to service principal mode when user tokens are unavailable (local development)
- **FR-017**: System MUST log detailed authentication activity including: token presence (yes/no), SDK config auth_type, retry attempt numbers, and fallback trigger events for debugging and audit purposes
- **FR-018**: System MUST implement exponential backoff retry logic (minimum 3 attempts with delays: 100ms, 200ms, 400ms) for authentication failures with a maximum total timeout of 5 seconds before returning errors to clients
- **FR-019**: System MUST detect Databricks platform rate limit responses (HTTP 429) during retry attempts and immediately fail the request by returning HTTP 429 to the user without further retries to respect platform limits

#### Local Development Support
- **FR-020**: System MUST work in local development environments where `X-Forwarded-Access-Token` is not present
- **FR-021**: Local development mode MUST clearly indicate when using service principal instead of user credentials
- **FR-022**: System MUST provide a way to test OBO authentication locally using environment variables

### Non-Functional Requirements

- **NFR-001**: Authentication token extraction and validation must add less than 10ms to request processing time
- **NFR-002**: All authentication configuration must be documented in code comments and external documentation
- **NFR-003**: The solution must be compatible with existing Databricks Apps deployment patterns
- **NFR-004**: No user tokens or credentials should be logged (security requirement)
- **NFR-005**: User access tokens MUST NOT be cached, stored in memory between requests, or persisted to disk to minimize security exposure and ensure token revocation takes immediate effect
- **NFR-006**: Authentication retry operations MUST complete within 5 seconds total (including all retry attempts and network overhead) to prevent request timeouts and degraded user experience
- **NFR-007**: Deployment to production MUST support in-place rolling updates with zero planned downtime, accepting brief transient errors during cutover as acceptable degradation
- **NFR-008**: Lakebase database connection pooling must efficiently handle concurrent user requests under a single service principal authentication without performance degradation

### Key Entities *(included - feature involves authentication data)*

- **User Access Token**: JWT token provided by Databricks Apps in `X-Forwarded-Access-Token` header, represents authenticated user's identity and permissions, expires and is refreshed by platform, used ONLY for Databricks APIs (not Lakebase)
- **User Identity (user_id)**: Unique identifier extracted from user access token, stored with all user-specific database records (preferences, saved queries, inference logs) to enforce data isolation and enable per-user queries
- **Service Principal Credentials**: OAuth client credentials (`DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`) for app-level operations, used for Lakebase connections and when user context is unavailable
- **Databricks SDK Config**: Configuration object that specifies authentication method, must include explicit `auth_type` to prevent multi-method detection errors
- **Request Context**: FastAPI request state that carries user token from middleware through to service layer dependencies
- **Lakebase Database Connection**: PostgreSQL connection authenticated with service principal role (matching service principal's client ID), shared across all user sessions
- **Database Role**: PostgreSQL role created by Databricks platform with name matching service principal's client ID, granted CONNECT and CREATE privileges

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
- [x] Ambiguities clarified (8 questions answered covering rate limiting, multi-tab behavior, deployment strategy)
- [x] User scenarios defined (authenticated API access with proper permissions, Lakebase service principal usage)
- [x] Requirements generated (22 functional, 8 non-functional)
- [x] Entities identified (tokens, user identity, credentials, SDK config, request context, database connections, database role)
- [x] Review checklist passed

---

## Success Metrics

The feature is considered successfully implemented when:

1. **Zero authentication errors** in deployed Databricks App logs after fix
2. **All API endpoints** (`/api/user/me`, `/api/model-serving/endpoints`, `/api/unity-catalog/catalogs`, `/api/preferences`) return successful responses
3. **Permission isolation verified**: Different users see different resources based on their Unity Catalog permissions
4. **Audit logs accurate**: 
   - Databricks API operations (Unity Catalog, Model Serving) are logged under actual user identities
   - Lakebase database operations are logged under service principal (platform limitation)
   - Application logs capture actual user_id for all operations for audit trail
5. **Local development works**: Application runs successfully in local mode with appropriate fallback behavior
6. **Observability validated**: Logs contain detailed authentication information (token presence, SDK auth_type, retry attempts, fallback triggers) for all requests
7. **Data isolation verified**: User-specific database records (preferences, saved queries, inference logs) contain user_id and queries filter results by authenticated user
8. **Lakebase security validated**: No user OBO tokens are passed to Lakebase connections; all database queries properly filter by user_id
9. **Deployment resilience confirmed**: Rolling update deployment completes successfully with stateless authentication enabling zero-downtime cutover (brief transient errors during deployment are acceptable)

---

## Related Documentation

- Databricks Apps Cookbook - OBO Authentication: https://apps-cookbook.dev/docs/streamlit/authentication/users_obo
- Databricks Lakebase Documentation: https://docs.databricks.com/aws/en/dev-tools/databricks-apps/lakebase
- Existing codebase documentation: `docs/OBO_AUTHENTICATION.md`
- Databricks SDK Python documentation for authentication configuration

---

*Aligned with Constitution v1.0.0 - See `.specify/memory/constitution.md`*
