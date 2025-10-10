# Data Model: Authentication and User Identity

**Feature**: Fix API Authentication and Implement On-Behalf-Of User (OBO) Authentication  
**Date**: 2025-10-10  
**Status**: Complete

---

## Overview

This document defines the data structures and models required for dual authentication (On-Behalf-Of-User for Databricks APIs and Service Principal for Lakebase) with proper user identity management and multi-user data isolation.

---

## 1. User Access Token (Runtime)

**Type**: Request State / Header Value  
**Storage**: None (extracted per request, never cached or persisted)  
**Source**: Databricks Apps platform via `X-Forwarded-Access-Token` header

### Structure
```python
# Not stored as object, but conceptual representation
UserAccessToken = str  # JWT token from Databricks platform

# Example header:
# X-Forwarded-Access-Token: eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Properties
| Property | Type | Description | Constraints |
|----------|------|-------------|-------------|
| value | str | JWT token string | - Provided by platform<br>- Never logged or cached<br>- Extracted fresh per request |
| presence | bool | Whether token exists in header | - True in Databricks Apps<br>- False in local dev (triggers fallback) |

### Lifecycle
- **Creation**: Provided by Databricks Apps platform automatically
- **Extraction**: FastAPI middleware reads `X-Forwarded-Access-Token` header per request
- **Validation**: Delegated to Databricks SDK (no local validation)
- **Expiration**: Platform handles token refresh automatically
- **Deletion**: Discarded after request completes (not cached)

### Security Constraints
- MUST NOT be logged (per NFR-004)
- MUST NOT be cached in memory (per NFR-005)
- MUST NOT be persisted to disk (per NFR-005)
- MUST be extracted fresh on every request (per FR-001)

### Related Requirements
- FR-001: Extract tokens fresh per request
- FR-017: Log token presence (not value)
- NFR-004: Never log credentials
- NFR-005: No caching or persistence

---

## 2. User Identity (user_id)

**Type**: Application Model  
**Storage**: Extracted from Databricks API, stored in database records  
**Source**: `UserService.get_user_info()` API call with user access token

### Structure
```python
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserIdentity(BaseModel):
    """User identity extracted from Databricks authentication."""
    
    user_id: EmailStr  # Email address from userName field
    display_name: str
    active: bool
    extracted_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user@example.com",
                "display_name": "Jane Doe",
                "active": True,
                "extracted_at": "2025-10-10T12:34:56Z"
            }
        }
```

### Properties
| Property | Type | Description | Constraints |
|----------|------|-------------|-------------|
| user_id | EmailStr | User's email address | - Primary identifier<br>- From Databricks userName field<br>- Used for database filtering |
| display_name | str | Human-readable name | - For UI display<br>- Not used for authorization |
| active | bool | Account active status | - From Databricks user info<br>- Inactive users should not access app |
| extracted_at | datetime | When identity was extracted | - For logging/debugging<br>- UTC timestamp |

### Extraction Process
1. Receive user access token from request header
2. Call `WorkspaceClient.current_user.me()` with user token
3. Extract `userName` field → `user_id`
4. Extract `displayName` field → `display_name`
5. Extract `active` field → `active`
6. Return UserIdentity object

### Error Handling
- API call fails → Return HTTP 401 "Failed to extract user identity"
- Malformed response → Return HTTP 401 "Invalid user identity format"
- Missing userName field → Return HTTP 401 "User identifier missing"
- Token missing → Automatic fallback to service principal (system operations only)

### Validation Rules
- `user_id` MUST be valid email format
- `user_id` MUST NOT be empty string
- `user_id` MUST be extracted from API (never from client request)

### Related Requirements
- FR-010: Extract user_id via API call
- FR-014: Validate user_id presence before database operations
- Constitution Principle IX: Multi-User Data Isolation

---

## 3. Authentication Context

**Type**: Request State Model  
**Storage**: FastAPI Request.state (per-request only)  
**Source**: Middleware extracts token and creates context

### Structure
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class AuthenticationContext:
    """Authentication context for a single request."""
    
    user_token: Optional[str]
    has_user_token: bool
    auth_mode: str  # "obo" or "service_principal"
    correlation_id: str
    user_id: Optional[str] = None  # Lazy-loaded when needed
    
    @property
    def is_obo_mode(self) -> bool:
        """Check if using On-Behalf-Of-User authentication."""
        return self.auth_mode == "obo"
    
    @property
    def is_service_principal_mode(self) -> bool:
        """Check if using Service Principal authentication."""
        return self.auth_mode == "service_principal"
```

### Properties
| Property | Type | Description | Constraints |
|----------|------|-------------|-------------|
| user_token | Optional[str] | User access token value | - None if header missing<br>- Never logged |
| has_user_token | bool | Token presence indicator | - Logged for observability<br>- Determines auth mode |
| auth_mode | str | Authentication mode | - "obo" or "service_principal"<br>- Logged per FR-017 |
| correlation_id | str | Request correlation ID | - UUID v4 or client-provided<br>- For request tracing |
| user_id | Optional[str] | User email (lazy) | - Extracted on first access<br>- Cached for request duration |

### Lifecycle
1. **Middleware**: Creates context from header
2. **Dependency Injection**: Passed to endpoints via FastAPI Depends
3. **Service Layer**: Services use context to configure authentication
4. **Request End**: Context discarded

### State Transitions
```
Request Start
    ↓
Middleware extracts token
    ↓
    ├─ Token present → auth_mode = "obo"
    └─ Token missing → auth_mode = "service_principal"
    ↓
Store in request.state
    ↓
Endpoint accesses via Depends(get_auth_context)
    ↓
Service uses context.auth_mode to configure SDK client
    ↓
Request completes → Context discarded
```

### Related Requirements
- FR-002: Pass tokens to service layer
- FR-016: Automatic fallback when token missing
- FR-017: Log auth mode and token presence
- Constitution Principle VIII: Correlation IDs

---

## 4. Databricks SDK Client Creation Pattern

**Type**: Implementation Pattern (not a data model)  
**Storage**: None (created per request)  
**Source**: Constructed from AuthenticationContext

### Pattern Overview

Services use inline client creation with explicit `auth_type` parameter. For timeout configuration, use the Databricks SDK's built-in `databricks.sdk.config.Config` class (see T037).

**IMPORTANT**: Do NOT create a custom `ClientConfig` class. The SDK provides all necessary configuration options through its built-in `Config` class.

### Standard Pattern (Without Timeout Configuration)

```python
from databricks.sdk import WorkspaceClient

# Basic pattern in service _get_client() method:
def _get_client(self) -> WorkspaceClient:
    """Get WorkspaceClient with appropriate authentication."""
    
    if self.user_token:
        # Pattern B: On-Behalf-Of-User Authentication
        return WorkspaceClient(
            host=self.workspace_url,
            token=self.user_token,
            auth_type="pat"  # REQUIRED: Explicit authentication type
        )
    else:
        # Pattern A: Service Principal Authentication
        return WorkspaceClient(
            host=self.workspace_url,
            client_id=os.environ["DATABRICKS_CLIENT_ID"],
            client_secret=os.environ["DATABRICKS_CLIENT_SECRET"],
            auth_type="oauth-m2m"  # REQUIRED: Explicit authentication type
        )
```

### Extended Pattern (With Timeout Configuration for NFR-010)

When upstream service timeout configuration is needed (30 seconds per NFR-010), use the SDK's `Config` class:

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.config import Config

def _get_client(self) -> WorkspaceClient:
    """Get WorkspaceClient with appropriate authentication and timeout."""
    
    # Configure timeout using SDK's built-in Config class
    config = Config()
    config.timeout = 30  # 30-second timeout per NFR-010
    config.retry_timeout = 30  # Allow full timeout window
    
    if self.user_token:
        # Pattern B: On-Behalf-Of-User Authentication with timeout
        return WorkspaceClient(
            host=self.workspace_url,
            token=self.user_token,
            auth_type="pat",
            config=config
        )
    else:
        # Pattern A: Service Principal Authentication with timeout
        return WorkspaceClient(
            host=self.workspace_url,
            client_id=os.environ["DATABRICKS_CLIENT_ID"],
            client_secret=os.environ["DATABRICKS_CLIENT_SECRET"],
            auth_type="oauth-m2m",
            config=config
        )
```

### Public Service Methods (Exception to Inline Pattern)

While the general pattern is to use `_get_client()` internally, certain service methods MUST be exposed as public APIs for router endpoints per FR-006a. These methods encapsulate authentication logic and should NOT expose the internal `_get_client()` method to endpoint handlers.

**Example: UserService.get_workspace_info()** (Required by FR-006a):

```python
class UserService:
    def __init__(self, user_token: Optional[str] = None):
        self.user_token = user_token
        self.workspace_url = os.environ["DATABRICKS_HOST"]
    
    def _get_client(self) -> WorkspaceClient:
        """Internal method - creates authenticated client."""
        # (implementation as shown in Standard Pattern above)
        ...
    
    async def get_workspace_info(self) -> WorkspaceInfo:
        """Public method: Get workspace information.
        
        This method encapsulates authentication mode selection (OBO vs service principal)
        and MUST NOT expose internal client creation logic to endpoint handlers.
        
        Required by FR-006a for /api/user/me/workspace endpoint.
        """
        client = self._get_client()
        workspace = await client.workspace.get_workspace()
        
        return WorkspaceInfo(
            workspace_id=workspace.workspace_id,
            workspace_url=self.workspace_url,
            workspace_name=workspace.workspace_name
        )
```

**Rationale**: This public method pattern provides better encapsulation than exposing `_get_client()` to routers. Endpoints call high-level service methods, not low-level client creation utilities.

### Configuration Options

| Auth Mode | host | token | client_id | client_secret | auth_type | config |
|-----------|------|-------|-----------|---------------|-----------|--------|
| OBO | workspace_url | user_token | - | - | "pat" | Optional (SDK Config for timeouts) |
| Service Principal | workspace_url | - | from env | from env | "oauth-m2m" | Optional (SDK Config for timeouts) |

### Validation Rules

- `auth_type` MUST be specified explicitly (per FR-003, FR-004)
- OBO mode REQUIRES non-empty token
- Service Principal mode REQUIRES client_id and client_secret in environment
- Workspace URL MUST be valid HTTPS endpoint
- For timeout configuration, use SDK's `databricks.sdk.config.Config` class only
- Do NOT create custom configuration classes

### Related Requirements

- FR-003: Explicit auth_type for OBO
- FR-004: Explicit auth_type for service principal
- FR-024: SDK version 0.67.0 pinned
- NFR-010: 30-second timeout configuration
- Research Decision 1: Explicit auth_type parameter
- Task T037: Timeout configuration implementation

---

## 5. Database Models (Enhanced for User Isolation)

### 5.1 User Preferences (Enhanced)

**Table**: `user_preferences`  
**Changes**: Add user_id column for isolation

```python
from sqlalchemy import Column, String, Text, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class UserPreference(Base):
    """User preference with multi-user isolation."""
    __tablename__ = "user_preferences"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)  # NEW: for isolation
    preference_key = Column(String, nullable=False)
    preference_value = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Composite unique constraint
    __table_args__ = (
        UniqueConstraint('user_id', 'preference_key', name='uq_user_preference'),
    )
```

### 5.2 Model Inference Log (Enhanced)

**Table**: `model_inference_logs`  
**Changes**: Add user_id column for audit trail

```python
class ModelInferenceLog(Base):
    """Model inference request log with user tracking."""
    __tablename__ = "model_inference_logs"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)  # NEW: for audit
    model_endpoint = Column(String, nullable=False)
    request_payload = Column(Text, nullable=False)
    response_payload = Column(Text, nullable=True)
    status = Column(String, nullable=False)
    duration_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

### 5.3 Saved Queries (New/Enhanced)

**Table**: `saved_queries`  
**Changes**: Ensure user_id filtering

```python
class SavedQuery(Base):
    """User-saved queries with isolation."""
    __tablename__ = "saved_queries"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)  # For isolation
    query_name = Column(String, nullable=False)
    query_text = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

### Database Isolation Pattern

**Query Pattern** (REQUIRED for all user-scoped queries):
```python
# CORRECT: Always filter by user_id
query = select(UserPreference).where(
    UserPreference.user_id == user_id
)

# INCORRECT: Missing user_id filter (security violation)
query = select(UserPreference)  # ❌ NEVER DO THIS
```

### Related Requirements
- FR-010: Store user_id with all user-specific records
- FR-013: Filter all user-scoped queries by user_id
- FR-014: Validate user_id presence before query execution
- Constitution Principle IX: Multi-User Data Isolation

---

## 6. API Response Models

### 6.1 User Info Response

```python
from pydantic import BaseModel, EmailStr

class UserInfoResponse(BaseModel):
    """Response from /api/user/me endpoint."""
    
    user_id: EmailStr
    display_name: str
    active: bool
    workspace_url: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user@example.com",
                "display_name": "Jane Doe",
                "active": True,
                "workspace_url": "https://workspace.cloud.databricks.com"
            }
        }
```

### 6.2 Authentication Status Response

```python
class AuthenticationStatusResponse(BaseModel):
    """Response showing current authentication status."""
    
    authenticated: bool
    auth_mode: str  # "obo" or "service_principal"
    has_user_identity: bool
    user_id: Optional[EmailStr] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "authenticated": True,
                "auth_mode": "obo",
                "has_user_identity": True,
                "user_id": "user@example.com"
            }
        }
```

### 6.3 Error Response

```python
class AuthenticationErrorResponse(BaseModel):
    """Error response for authentication failures."""
    
    detail: str
    error_code: str
    retry_after: Optional[int] = None  # Seconds, for rate limiting
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Failed to extract user identity",
                "error_code": "AUTH_USER_IDENTITY_FAILED",
                "retry_after": None
            }
        }
```

---

## 7. Metrics Models

### 7.1 Authentication Metrics

```python
from dataclasses import dataclass
from typing import Literal

AuthMode = Literal["obo", "service_principal"]
AuthStatus = Literal["success", "failure", "retry"]

@dataclass
class AuthenticationMetric:
    """Single authentication event metric."""
    
    timestamp: datetime
    endpoint: str
    method: str
    auth_mode: AuthMode
    status: AuthStatus
    duration_ms: float
    retry_count: int = 0
    error_type: Optional[str] = None
```

### 7.2 Performance Metrics

```python
@dataclass
class PerformanceMetric:
    """Request performance metric."""
    
    timestamp: datetime
    endpoint: str
    method: str
    status_code: int
    duration_ms: float
    auth_overhead_ms: float
    upstream_api_duration_ms: Optional[float] = None
```

---

## 8. Log Event Models

### 8.1 Structured Log Entry

```python
from typing import Any, Dict

class StructuredLogEntry(BaseModel):
    """Structured log entry for authentication events."""
    
    timestamp: datetime
    level: str  # INFO, WARNING, ERROR
    event: str  # e.g., "auth.token_extraction"
    correlation_id: str
    context: Dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-10-10T12:34:56.789Z",
                "level": "INFO",
                "event": "auth.mode",
                "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
                "context": {
                    "mode": "obo",
                    "auth_type": "pat",
                    "endpoint": "/api/user/me"
                }
            }
        }
```

### 8.2 Authentication Log Events

| Event Name | Level | Context Fields | Trigger |
|------------|-------|----------------|---------|
| `auth.token_extraction` | INFO | has_token, endpoint | Middleware extracts token |
| `auth.mode` | INFO | mode, auth_type | SDK client created |
| `auth.user_id_extracted` | INFO | user_id, method | UserService.get_user_info() succeeds |
| `auth.token_validation_failed` | WARNING | error_type, endpoint | Token validation fails. All token errors (expired, malformed, cryptographically invalid) raise the same `DatabricksError` exception type and are handled identically with unified retry logic (see research.md section 4, line 203). SDK does not distinguish between error subtypes at exception level. |
| `auth.retry_attempt` | WARNING | attempt, error_type, endpoint | Authentication retry triggered |
| `auth.fallback_triggered` | INFO | reason, environment | Service principal fallback |
| `auth.failed` | ERROR | error_type, error_message, has_token | Authentication failure after retries |
| `auth.rate_limit` | ERROR | error | Platform rate limit detected |

---

## 9. Entity Relationships

```
Request
    ├─ has AuthenticationContext (1:1, per-request)
    │   ├─ contains user_token (0:1)
    │   └─ contains correlation_id (1:1)
    │
    ├─ may have UserIdentity (0:1, lazy-loaded)
    │   └─ used for database filtering
    │
    └─ creates WorkspaceClient (1:1)
        ├─ configured with auth_type
        └─ uses OBO or Service Principal auth

UserPreference
    ├─ belongs to user_id (N:1)
    └─ enforced by WHERE user_id = ?

ModelInferenceLog
    ├─ belongs to user_id (N:1)
    └─ audit trail with user identity

SavedQuery
    ├─ belongs to user_id (N:1)
    └─ enforced by WHERE user_id = ?
```

---

## 10. State Machines

### Authentication Mode State Machine

```
┌─────────────────────────────────────────┐
│           Request Received               │
└───────────────┬─────────────────────────┘
                │
                ↓
    ┌───────────────────────────┐
    │ Check X-Forwarded-Access- │
    │      Token Header          │
    └───────────┬───────────────┘
                │
        ┌───────┴───────┐
        │               │
    Present         Missing
        │               │
        ↓               ↓
┌──────────────┐   ┌──────────────────┐
│  OBO Mode    │   │ Service Principal│
│ auth_type:   │   │     Mode         │
│    "pat"     │   │  auth_type:      │
└──────┬───────┘   │  "oauth-m2m"     │
       │           └────────┬─────────┘
       │                    │
       │    ┌───────────────┘
       │    │
       ↓    ↓
    ┌──────────────┐
    │ Create SDK   │
    │   Client     │
    └──────┬───────┘
           │
           ↓
    ┌──────────────┐
    │ Make API Call│
    └──────┬───────┘
           │
     ┌─────┴─────┐
     │           │
  Success     Failure
     │           │
     ↓           ↓
┌─────────┐  ┌───────────┐
│ Return  │  │  Retry?   │
│Response │  │ (<5 sec)  │
└─────────┘  └─────┬─────┘
                   │
            ┌──────┴──────┐
            │             │
          Yes           No
            │             │
            ↓             ↓
      [Exponential]  [Return Error]
      [Backoff   ]   [HTTP 401/429]
```

### User Identity Extraction State Machine

```
┌─────────────────────────────────────────┐
│   Endpoint Needs user_id                │
└───────────────┬─────────────────────────┘
                │
                ↓
    ┌────────────────────────┐
    │ Check AuthContext      │
    │   has user_token?      │
    └───────────┬────────────┘
                │
        ┌───────┴────────┐
        │                │
      Yes              No
        │                │
        ↓                ↓
┌──────────────┐   ┌─────────────┐
│ Call User    │   │ Return HTTP │
│ Service      │   │   401       │
│ get_user_id()│   └─────────────┘
└──────┬───────┘
       │
       ↓
┌──────────────────┐
│ API Call:        │
│ current_user.me()│
└──────┬───────────┘
       │
   ┌───┴────┐
   │        │
Success  Failure
   │        │
   ↓        ↓
┌──────┐  ┌─────────┐
│Extract│ │ Return  │
│userName│ │HTTP 401│
└───┬──┘  └─────────┘
    │
    ↓
┌───────────┐
│ Return    │
│ user_id   │
└─────┬─────┘
      │
      ↓
┌──────────────┐
│ Use in       │
│ Database     │
│ WHERE clause │
└──────────────┘
```

---

## Validation Rules Summary

### Security Validations (CRITICAL)
1. **User Token**: NEVER log token value (only presence)
2. **User Identity**: ALWAYS extract from API (never trust client)
3. **Database Queries**: ALWAYS filter by user_id for user-scoped data
4. **Auth Type**: ALWAYS specify explicit `auth_type` parameter

### Data Validations
1. **user_id**: Must be valid email format (EmailStr)
2. **user_id**: Must not be empty string
3. **user_id**: Must exist before database query execution
4. **auth_mode**: Must be "obo" or "service_principal"
5. **correlation_id**: Must be UUID v4 format

### Business Logic Validations
1. **OBO Mode**: Requires non-empty user_token
2. **Service Principal Mode**: Requires DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET
3. **User-Scoped Operations**: Require user_id extraction success
4. **Retry Logic**: Total timeout must not exceed 5 seconds
5. **Rate Limiting**: HTTP 429 must trigger immediate failure (no retries)

---

## Migration Notes

### Database Schema Changes Required

```sql
-- Add user_id column to user_preferences (if not exists)
ALTER TABLE user_preferences 
ADD COLUMN IF NOT EXISTS user_id VARCHAR(255) NOT NULL;

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id 
ON user_preferences(user_id);

-- Add unique constraint
ALTER TABLE user_preferences 
ADD CONSTRAINT uq_user_preference 
UNIQUE (user_id, preference_key);

-- Add user_id column to model_inference_logs (if not exists)
ALTER TABLE model_inference_logs 
ADD COLUMN IF NOT EXISTS user_id VARCHAR(255) NOT NULL;

-- Add index for audit queries
CREATE INDEX IF NOT EXISTS idx_model_inference_logs_user_id 
ON model_inference_logs(user_id);

-- Backfill existing records (if any) with placeholder
-- NOTE: Manual intervention needed for production data
UPDATE user_preferences 
SET user_id = 'migration-placeholder@example.com' 
WHERE user_id IS NULL;

UPDATE model_inference_logs 
SET user_id = 'migration-placeholder@example.com' 
WHERE user_id IS NULL;
```

### Alembic Migration

Will be created in `migrations/versions/003_add_user_id_columns.py` during implementation phase.

---

## Related Documents

- [Feature Specification](./spec.md)
- [Research Document](./research.md)
- [API Contracts](./contracts/)
- [Quickstart Guide](./quickstart.md)

---

**Alignment**: This data model satisfies all requirements in the feature specification and adheres to Constitution Principles IV (Type Safety), VIII (Observability), and IX (Multi-User Data Isolation).
