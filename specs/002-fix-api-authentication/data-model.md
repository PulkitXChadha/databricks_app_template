# Data Model: OBO Authentication

**Date**: 2025-10-09  
**Feature**: Fix API Authentication and Implement On-Behalf-Of User (OBO)  
**Status**: Design Complete

---

## Overview

This feature primarily involves authentication flow modifications rather than new data models. However, it introduces critical changes to existing entities to support user identity tracking and data isolation.

**Key Changes**:
1. Add `user_id` field to all user-scoped database tables
2. Create authentication context models for request processing
3. Define authentication configuration types

---

## Entity: User Access Token

**Description**: JWT token provided by Databricks Apps platform in request headers, represents authenticated user's identity and permissions.

**Lifecycle**: Created by platform, passed via header, extracted per-request, never persisted

**Fields**:
| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| token_value | string | Yes | JWT format | Raw token from X-Forwarded-Access-Token header |
| expires_at | datetime | Platform-managed | - | Token expiration timestamp (platform handles refresh) |
| scopes | list[string] | Platform-managed | - | User permissions scope |

**Relationships**: None (transient, not persisted)

**Validation Rules**:
- Must be present in X-Forwarded-Access-Token header for OBO operations
- Validated by Databricks SDK on each API call
- No client-side validation or caching (security requirement NFR-005)

**State Transitions**: None (stateless)

**Notes**:
- Token is extracted fresh from headers on every request
- Never stored in memory between requests
- Platform handles token refresh transparently

---

## Entity: User Identity

**Description**: Structured user information extracted from OBO token via Databricks API, used for audit logging and data isolation.

**Lifecycle**: Extracted per-request from token, used for logging and filtering, not persisted separately

**Fields**:
| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| user_id | string | Yes | UUID format | Unique Databricks user identifier |
| email | string | No | Email format | User's email address |
| username | string | Yes | - | Databricks username |
| display_name | string | No | - | User's display name |

**Relationships**: 
- References UserPreference (one-to-many)
- References ModelInferenceLog (one-to-many)
- References UserSession (one-to-many)

**Validation Rules**:
- user_id must be non-empty for all user-scoped operations (FR-014)
- Extracted via WorkspaceClient.current_user.me() API only (no client-provided values trusted)

**State Transitions**: None (extracted per-request)

**Notes**:
- Single source of truth for user identity
- Used for all audit logging and data filtering
- Constitution Principle IX compliance

---

## Entity: Service principal credentials

**Description**: OAuth client credentials for app-level operations, provided via environment variables by Databricks Apps platform.

**Lifecycle**: Set at deployment time, read from environment, used for service principal operations

**Fields**:
| Field | Type | Required | Source | Description |
|-------|------|----------|--------|-------------|
| client_id | string | Yes | DATABRICKS_CLIENT_ID env var | Service principal client ID |
| client_secret | string | Yes | DATABRICKS_CLIENT_SECRET env var | Service principal client secret |
| host | string | Yes | DATABRICKS_HOST env var | Databricks workspace URL |

**Relationships**: None (environment configuration)

**Validation Rules**:
- Must be present for service principal operations
- Never logged (NFR-004 security requirement)
- Read-only from environment (no mutation)

**State Transitions**: None (static configuration)

**Notes**:
- Used exclusively for Lakebase database connections per platform limitation (see spec.md Problem Statement lines 60-68 for detailed explanation of why Lakebase requires service principal authentication)
- Used for system-level operations when user context unavailable
- Managed by Databricks Apps platform

---

## Entity: Databricks SDK Configuration

**Description**: Configuration object for creating WorkspaceClient instances with explicit authentication type.

**Lifecycle**: Created per-request based on operation type (OBO vs service principal)

**Fields**:
| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| host | string | Yes | URL format | Databricks workspace URL |
| auth_type | enum | Yes | "pat" or "oauth-m2m" | Explicit authentication method |
| token | string | Conditional | JWT format | User token (required if auth_type="pat") |
| client_id | string | Conditional | - | Service principal client ID (required if auth_type="oauth-m2m") |
| client_secret | string | Conditional | - | Service principal client secret (required if auth_type="oauth-m2m") |

**Relationships**: None (transient configuration)

**Validation Rules**:
- auth_type must be explicitly set (FR-003, FR-004) to prevent SDK auto-detection conflicts
- If auth_type="pat", token must be provided
- If auth_type="oauth-m2m", client_id and client_secret must be provided
- host must be valid Databricks workspace URL

**State Transitions**:
```
Configuration Created → WorkspaceClient Initialized → API Calls → Configuration Discarded
```

**Notes**:
- Key to fixing "more than one authorization method configured" error
- Two patterns: OBO (auth_type="pat") and service principal (auth_type="oauth-m2m")
- **SDK Version Requirement**: Minimum version 0.33.0 for auth_type parameter support
- **Version Pinning**: Exact version 0.59.0 pinned in requirements.txt (FR-024, NFR-013) to prevent breaking changes

---

## Modified Entity: UserPreference

**Description**: User-specific application preferences stored in Lakebase (EXISTING TABLE - MODIFIED).

**Changes**: Add `user_id` field for data isolation, add index for query performance

**Fields**:
| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| id | UUID | Yes | Primary key | Unique preference record ID |
| user_id | string | Yes | Indexed, not null | Databricks user ID (NEW FIELD) |
| key | string | Yes | Not null | Preference key name |
| value | JSON | Yes | Not null | Preference value (structured) |
| created_at | datetime | Yes | Auto-set | Record creation timestamp |
| updated_at | datetime | Yes | Auto-update | Record last update timestamp |

**Relationships**:
- Belongs to User (via user_id foreign key concept - not enforced at DB level)

**Validation Rules**:
- user_id must be present before INSERT/UPDATE operations (FR-014)
- Unique constraint on (user_id, key) combination
- All queries must include WHERE user_id = ? clause (FR-013)

**State Transitions**:
```
Created (user_id, key, value) → Updated (value changed) → Deleted
```

**Database Schema**:
```sql
ALTER TABLE user_preferences
ADD COLUMN user_id VARCHAR(255) NOT NULL;

CREATE INDEX ix_user_preferences_user_id ON user_preferences(user_id);

CREATE UNIQUE INDEX ix_user_preferences_user_id_key 
ON user_preferences(user_id, key);
```

**Notes**:
- Migration required to add user_id to existing records (default to service principal for historical data)
- Application-level enforcement of user_id filtering (DB-level isolation not possible)

---

## Modified Entity: ModelInferenceLog

**Description**: Audit log of model inference requests (EXISTING TABLE - MODIFIED).

**Changes**: Add `user_id` field for audit trail and user-specific history

**Fields**:
| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| id | UUID | Yes | Primary key | Unique log record ID |
| user_id | string | Yes | Indexed, not null | Databricks user ID (NEW FIELD) |
| model_endpoint | string | Yes | Not null | Model serving endpoint name |
| request_payload | JSON | Yes | Not null | Inference request data |
| response_payload | JSON | Yes | - | Inference response data |
| status | enum | Yes | success/error | Request status |
| error_message | string | No | - | Error details if status=error |
| latency_ms | integer | Yes | Positive | Request processing time |
| created_at | datetime | Yes | Auto-set | Request timestamp |

**Relationships**:
- Belongs to User (via user_id foreign key concept)

**Validation Rules**:
- user_id must be present before INSERT (FR-014)
- All queries must include WHERE user_id = ? clause for user-scoped operations (FR-013)
- latency_ms must be positive

**State Transitions**:
```
Request Logged (status=pending) → Response Recorded (status=success/error) → [Immutable]
```

**Database Schema**:
```sql
ALTER TABLE model_inference_logs
ADD COLUMN user_id VARCHAR(255) NOT NULL;

CREATE INDEX ix_model_inference_logs_user_id ON model_inference_logs(user_id);
CREATE INDEX ix_model_inference_logs_created_at ON model_inference_logs(created_at);
```

**Notes**:
- Enables per-user inference history views
- Critical for audit compliance (Success Metric #4)
- Migration required for existing records

---

## Modified Entity: UserSession

**Description**: User session tracking for analytics (EXISTING TABLE - MODIFIED).

**Changes**: Ensure `user_id` field exists and is properly indexed

**Fields**:
| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| id | UUID | Yes | Primary key | Unique session ID |
| user_id | string | Yes | Indexed, not null | Databricks user ID |
| started_at | datetime | Yes | Auto-set | Session start timestamp |
| last_activity_at | datetime | Yes | Auto-update | Last request timestamp |
| ip_address | string | No | - | Client IP address |
| user_agent | string | No | - | Client user agent |

**Relationships**:
- Belongs to User (via user_id)

**Validation Rules**:
- user_id must be present before INSERT (FR-014)
- All queries must include WHERE user_id = ? clause (FR-013)
- last_activity_at must be >= started_at

**State Transitions**:
```
Session Created → Activity Updated (on each request) → Session Expired (timeout)
```

**Database Schema**:
```sql
-- Verify user_id column exists with proper index
CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_user_sessions_last_activity ON user_sessions(last_activity_at);
```

**Notes**:
- User_id should already exist in this table
- Verify proper indexing for query performance

---

## New Entity: AuthenticationContext

**Description**: Request-scoped context object carrying authentication information through the application (in-memory only, not persisted).

**Lifecycle**: Created per-request, passed via dependency injection, discarded after response

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_token | string \| None | Conditional | OBO token if present in headers |
| user_id | string \| None | Conditional | Extracted user ID (only if token present) |
| is_service_principal | bool | Yes | True if no user token (fallback mode) |
| correlation_id | string | Yes | Request correlation ID for tracing |

**Relationships**: None (transient)

**Validation Rules**:
- If user_token is present, user_id must be extracted and populated
- If user_token is None, is_service_principal must be True
- correlation_id must be non-empty UUID

**State Transitions**:
```
Request Start → Context Created → Injected via Depends → Used in Services → Discarded
```

**Notes**:
- Passed via FastAPI dependency injection
- Enables clean separation of auth logic
- Not persisted to database

---

## Database Migration Summary

### Migration: 003_add_user_id_to_tables.py

**Operations**:
1. Add `user_id` column to `user_preferences` table
2. Add `user_id` column to `model_inference_logs` table
3. Create indexes on `user_id` columns for query performance
4. Create unique index on `user_preferences(user_id, key)`
5. Backfill existing records with service principal identifier (historical data)

**Rollback Strategy**:
- Drop indexes
- Drop user_id columns
- Restore from backup if data corruption occurs

**Testing**:
- Verify indexes created successfully
- Verify unique constraint on user_preferences
- Verify query performance with user_id filtering

---

## Data Flow Diagrams

### OBO Authentication Data Flow
```
1. Request arrives with X-Forwarded-Access-Token header
2. FastAPI dependency extracts token → AuthenticationContext(user_token=token)
3. Service receives AuthenticationContext
4. Service calls WorkspaceClient.current_user.me() → User Identity extracted
5. User Identity used for:
   a. Audit logging (user_id in structured logs)
   b. Database filtering (WHERE user_id = ?)
   c. Unity Catalog permission enforcement (automatic via SDK)
```

### Service Principal Data Flow
```
1. Request arrives without X-Forwarded-Access-Token (local dev or system operation)
2. FastAPI dependency creates AuthenticationContext(user_token=None, is_service_principal=True)
3. Service receives context
4. Service uses WorkspaceClient(client_id, client_secret, auth_type="oauth-m2m")
5. Operations proceed with service principal permissions
6. Audit logs indicate service principal mode
```

### Lakebase Data Isolation Flow
```
1. Request arrives with user token
2. User Identity extracted → user_id
3. LakebaseService receives user_id
4. LakebaseService validates user_id is present (FR-014)
5. Query built with WHERE user_id = ? clause (FR-013)
6. Database connection uses service principal (FR-011)
7. Application-level filtering enforces data isolation
```

---

## Query Patterns

### User-Scoped Query Pattern (REQUIRED)
```python
# Correct: Always include user_id filter
query = select(UserPreference).where(UserPreference.user_id == user_id)

# WRONG: Missing user_id filter (security vulnerability)
query = select(UserPreference).where(UserPreference.key == "theme")
```

### Service Constructor Pattern (REQUIRED)
```python
class UserPreferenceService:
    def __init__(self, user_id: str):
        if not user_id:
            raise ValueError("user_id is required for user preference operations")
        self.user_id = user_id
    
    async def get_preferences(self):
        # user_id automatically included from self.user_id
        query = select(UserPreference).where(UserPreference.user_id == self.user_id)
        ...
```

---

## Validation Checklist

- [x] All user-scoped entities include user_id field
- [x] Database indexes defined for query performance
- [x] Validation rules prevent operations without user_id
- [x] Migration strategy defined for existing tables
- [x] Authentication context model enables dependency injection
- [x] SDK configuration patterns support both auth types
- [x] Data flow diagrams show user identity propagation
- [x] Query patterns enforce data isolation
- [x] No sensitive data persisted (tokens, secrets)
- [x] Audit logging requirements satisfied

---

**Status**: ✅ Design Complete - Ready for Contract Generation (Phase 1 continued)

