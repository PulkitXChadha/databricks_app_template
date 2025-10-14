# Data Model: OBO-Only Authentication

**Feature**: Remove Service Principal Fallback - OBO-Only Authentication  
**Date**: 2025-10-14  
**Status**: Complete

## Overview

This document defines the data models, error structures, and service contracts for OBO-only authentication. Unlike the 002 feature which added new models, this feature primarily **removes** and **simplifies** existing authentication patterns.

---

## 1. AuthenticationContext Model (Modified)

**Purpose**: Represents the authentication state of a request. Simplified to OBO-only.

**Changes from 002**:
- `auth_mode` field removed (always "obo" now)
- `has_user_token` becomes critical validation point
- Simplified structure

```python
# server/models/user_session.py

from pydantic import BaseModel, Field

class AuthenticationContext(BaseModel):
    """Authentication context for a request - OBO-only."""
    
    user_token: str = Field(
        ...,  # Required (not optional)
        description="User access token from X-Forwarded-Access-Token header"
    )
    
    correlation_id: str = Field(
        ...,
        description="Request correlation ID for tracing"
    )
    
    # REMOVED: auth_mode field (was "obo" | "service_principal")
    # REMOVED: has_user_token field (token is always required now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_token": "dapi...",
                "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
```

**Validation Rules**:
- `user_token` must be present and non-empty
- `correlation_id` must be valid UUID format
- No nullable fields (all required for OBO)

---

## 2. Error Response Models (Enhanced)

**Purpose**: Structured error responses for authentication failures.

```python
# server/models/user_session.py

from enum import Enum
from typing import Optional

class AuthErrorCode(str, Enum):
    """Standardized authentication error codes."""
    AUTH_MISSING = "AUTH_MISSING"  # Token not provided
    AUTH_INVALID = "AUTH_INVALID"  # Token malformed or invalid
    AUTH_EXPIRED = "AUTH_EXPIRED"  # Token has expired
    AUTH_USER_IDENTITY_FAILED = "AUTH_USER_IDENTITY_FAILED"  # Can't extract user info
    AUTH_RATE_LIMITED = "AUTH_RATE_LIMITED"  # Platform rate limit hit

class AuthenticationError(BaseModel):
    """Standard authentication error response."""
    
    error_code: AuthErrorCode = Field(
        ...,
        description="Machine-readable error code"
    )
    
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    
    detail: Optional[str] = Field(
        None,
        description="Additional error details (not for end users)"
    )
    
    retry_after: Optional[int] = Field(
        None,
        description="Seconds to wait before retry (for rate limiting)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "error_code": "AUTH_MISSING",
                "message": "User authentication required. Please provide a valid user access token.",
                "detail": None,
                "retry_after": None
            }
        }
```

**Error Response Examples**:
```json
// Missing token (HTTP 401)
{
    "error_code": "AUTH_MISSING",
    "message": "User authentication required. Please provide a valid user access token.",
    "detail": null,
    "retry_after": null
}

// Invalid token (HTTP 401)
{
    "error_code": "AUTH_INVALID",
    "message": "The provided access token is invalid or malformed.",
    "detail": "Token validation failed",
    "retry_after": null
}

// Expired token (HTTP 401)
{
    "error_code": "AUTH_EXPIRED",
    "message": "The provided access token has expired.",
    "detail": "Token lifetime exceeded",
    "retry_after": null
}

// Rate limiting (HTTP 429)
{
    "error_code": "AUTH_RATE_LIMITED",
    "message": "Platform rate limit exceeded. Please retry after indicated delay.",
    "detail": "Too many authentication attempts",
    "retry_after": 60
}
```

---

## 3. Service Initialization Pattern (Modified)

**Purpose**: All Databricks API services require user_token parameter.

**Pattern BEFORE (002 - dual authentication)**:
```python
class UnityCatalogService:
    def __init__(self, user_token: Optional[str] = None):
        # Optional token - automatic fallback to service principal
        self.user_token = user_token
```

**Pattern AFTER (003 - OBO-only)**:
```python
class UnityCatalogService:
    def __init__(self, user_token: str):  # Required, not Optional
        """Initialize Unity Catalog service with OBO authentication.
        
        Args:
            user_token: User access token (required for all operations)
            
        Raises:
            ValueError: If user_token is None or empty
        """
        if not user_token:
            raise ValueError("user_token is required for UnityCatalogService")
        
        self.user_token = user_token
        self.workspace_url = os.getenv('DATABRICKS_HOST')
        
    # REMOVED: _create_service_principal_config method
    # REMOVED: Automatic fallback logic in _get_client
```

**Services Affected**:
1. `UnityCatalogService` - Unity Catalog operations
2. `ModelServingService` - Model inference operations
3. `UserService` - User identity operations

**Service NOT Affected**:
- `LakebaseService` - Maintains application-level credentials (no user_token parameter)

---

## 4. Health Check Response Model

**Purpose**: Public health endpoint response structure.

```python
# server/models/health.py (NEW or ADD to existing)

from pydantic import BaseModel
from datetime import datetime

class HealthCheckResponse(BaseModel):
    """Response for public /health endpoint."""
    
    status: str = Field(
        ...,
        description="Health status indicator",
        pattern="^(healthy|unhealthy|degraded)$"
    )
    
    timestamp: datetime = Field(
        ...,
        description="Server timestamp (UTC)"
    )
    
    version: Optional[str] = Field(
        None,
        description="Application version (if available)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-10-14T10:30:00.000Z",
                "version": "1.0.0"
            }
        }
```

---

## 5. Database Models (No Changes)

**Purpose**: Document that database schema remains unchanged.

**Existing Models** (no modifications):
- `UserPreference` - User preferences table
- `ModelInferenceLog` - Model inference history
- Both tables have `user_id` column (added in 002)

**No New Migrations Needed**:
- Schema is stable
- user_id filtering logic unchanged
- No new columns or indices required

**Verification**:
```python
# Existing models remain valid
class UserPreference(Base):
    __tablename__ = 'user_preferences'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, index=True)  # ← Already exists
    preference_key = Column(String, nullable=False)
    preference_value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## 6. Middleware Request State (Modified)

**Purpose**: Request state structure set by middleware.

**BEFORE (002 pattern)**:
```python
# Middleware sets these attributes
request.state.user_token = user_token  # Optional[str]
request.state.has_user_token = user_token is not None  # bool
request.state.auth_mode = "obo" if user_token else "service_principal"  # str
request.state.correlation_id = correlation_id  # str
```

**AFTER (003 pattern)**:
```python
# Simplified middleware state
request.state.user_token = user_token  # Optional[str] (but required for most endpoints)
request.state.correlation_id = correlation_id  # str

# REMOVED: has_user_token (redundant with checking user_token directly)
# REMOVED: auth_mode (always OBO when token present)
```

**Dependency Functions**:
```python
# In server/lib/auth.py

async def get_user_token(request: Request) -> str:
    """Extract required user token from request state.
    
    This dependency MUST be used for all authenticated endpoints.
    Raises HTTPException 401 with structured error response if token is missing or empty.
    
    Args:
        request: FastAPI request object with state.user_token set by middleware
    
    Returns:
        str: Valid user access token
    
    Raises:
        HTTPException: 401 if token is missing or empty string
    """
    user_token = getattr(request.state, 'user_token', None)
    
    # Treat None and empty string the same way
    if not user_token:
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "AUTH_MISSING",
                "message": "User authentication required. Please provide a valid user access token."
            }
        )
    
    return user_token

async def get_user_token_optional(request: Request) -> Optional[str]:
    """Extract optional user token without raising exceptions.
    
    This dependency is ONLY for endpoints that support unauthenticated access,
    such as /health (public monitoring endpoint).
    
    Args:
        request: FastAPI request object with state.user_token set by middleware
    
    Returns:
        Optional[str]: User access token if present, None otherwise
    """
    return getattr(request.state, 'user_token', None)
```

**Usage Examples**:
```python
# Authenticated endpoint (requires token)
@router.get("/api/unity-catalog/catalogs")
async def list_catalogs(user_token: str = Depends(get_user_token)):
    # user_token is guaranteed to be present (dependency raises 401 if not)
    service = UnityCatalogService(user_token=user_token)
    return await service.list_catalogs()

# Public endpoint (token optional)
@app.get("/health")
async def health(user_token: Optional[str] = Depends(get_user_token_optional)):
    # user_token may be None (no authentication required)
    return {"status": "healthy", "authenticated": user_token is not None}
```

---

## 7. Service Method Signatures (Modified)

**Purpose**: Document signature changes for service methods.

**BEFORE (002 pattern)**:
```python
class UnityCatalogService:
    async def list_catalogs(self, user_id: Optional[str] = None) -> List[str]:
        # Works with or without user context
        pass
```

**AFTER (003 pattern)**:
```python
class UnityCatalogService:
    async def list_catalogs(self, user_id: str) -> List[str]:
        """List catalogs with user's permissions.
        
        Args:
            user_id: User identifier (required for audit logging)
            
        Returns:
            List of catalog names accessible to user
            
        Raises:
            HTTPException: 401 if service not initialized with user_token
        """
        # All operations require user context
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="User identity required for catalog operations"
            )
        
        # Use OBO-authenticated client
        catalogs = []
        catalog_list = self.client.catalogs.list()  # Uses user's permissions
        # ...
        return catalogs
```

**Pattern Changes**:
- `user_id` parameters change from `Optional[str]` to `str` (required)
- Methods validate user_id presence
- No fallback handling in method bodies

---

## 8. Router Dependency Injection (Modified)

**Purpose**: Document router-level dependency changes.

**BEFORE (002 pattern)**:
```python
@router.get("/api/unity-catalog/catalogs")
async def list_catalogs(
    user_id: str = Depends(get_current_user_id),
    user_token: Optional[str] = Depends(get_user_token)  # Optional
):
    service = UnityCatalogService(user_token=user_token)  # Works without token
    return await service.list_catalogs(user_id=user_id)
```

**AFTER (003 pattern)**:
```python
@router.get("/api/unity-catalog/catalogs")
async def list_catalogs(
    user_id: str = Depends(get_current_user_id),  # Raises 401 if no token
    user_token: str = Depends(get_user_token)  # Required, raises 401 if missing
):
    service = UnityCatalogService(user_token=user_token)  # Requires token
    return await service.list_catalogs(user_id=user_id)
```

**Exception Handling**:
```python
# Automatic 401 responses from dependencies
# No try/catch needed in route handlers

# get_current_user_id raises HTTPException(401) if token missing
# get_user_token raises HTTPException(401) if token missing
# Service initialization raises ValueError if token None
```

---

## 9. Logging Event Structures (Modified)

**Purpose**: Document simplified logging events.

**REMOVED Log Events**:
- `auth.mode` with `mode="service_principal"` 
- `auth.fallback_triggered` events
- `auth.service_principal_config_created` events

**REMAINING Log Events**:
```json
// Token extraction
{
    "timestamp": "2025-10-14T10:30:00.000Z",
    "level": "INFO",
    "event": "auth.token_extraction",
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "has_token": true,
    "endpoint": "/api/unity-catalog/catalogs"
}

// OBO mode selection (hardcoded in log statement, not from model field)
{
    "timestamp": "2025-10-14T10:30:00.100Z",
    "level": "INFO",
    "event": "auth.mode",
    "mode": "obo",  // HARDCODED - always "obo" since it's the only pattern
    "auth_type": "pat",  // HARDCODED - always "pat" for OBO
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}

// User identity extracted
{
    "timestamp": "2025-10-14T10:30:00.200Z",
    "level": "INFO",
    "event": "auth.user_id_extracted",
    "user_id": "user@example.com",
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}

// Authentication failure
{
    "timestamp": "2025-10-14T10:30:00.300Z",
    "level": "ERROR",
    "event": "auth.failed",
    "error_code": "AUTH_MISSING",
    "error_message": "User authentication required",
    "endpoint": "/api/unity-catalog/catalogs",
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Important Note**: The `auth.mode` log event shows `mode="obo"` but this value is HARDCODED in the logging statement, NOT derived from the AuthenticationContext model (which no longer has an auth_mode field). Since OBO is the only supported authentication pattern, the mode value is static.

---

## 10. Metrics Definitions (Modified)

**Purpose**: Document simplified Prometheus metrics.

**REMOVED Metrics**:
- `auth_fallback_total` (no fallback behavior)
- Labels with `mode="service_principal"` values

**REMAINING Metrics**:
```python
# Authentication request counter (simplified)
auth_requests_total = Counter(
    'auth_requests_total',
    'Total OBO authentication attempts',
    ['endpoint', 'status']  # Removed 'mode' label
)

# Examples:
# auth_requests_total{endpoint="/api/user/me",status="success"} 150
# auth_requests_total{endpoint="/api/catalogs",status="failure"} 3

# Authentication overhead histogram
auth_overhead_seconds = Histogram(
    'auth_overhead_seconds',
    'OBO authentication overhead in seconds',
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1]
)

# Request duration (unchanged)
request_duration_seconds = Histogram(
    'request_duration_seconds',
    'Request duration in seconds',
    ['endpoint', 'method', 'status']
)
```

---

## Summary

### Models Changed
1. ✅ `AuthenticationContext` - Simplified (removed auth_mode field)
2. ✅ `AuthenticationError` - Enhanced error codes
3. ✅ Service initialization patterns - Required user_token
4. ✅ Request state structure - Simplified
5. ✅ Router dependencies - Required user_token

### Models Added
1. ✅ `HealthCheckResponse` - Public health endpoint
2. ✅ `AuthErrorCode` - Standardized error codes

### Models Unchanged
1. ✅ `UserPreference` - Database model stable
2. ✅ `ModelInferenceLog` - Database model stable
3. ✅ `UserInfo` - User identity structure stable

### No Database Migrations Needed
- Existing schema supports OBO-only authentication
- No new columns or indices required
- All changes are application-level logic

---

**Status**: ✅ Data model design complete  
**Next**: Contract definitions and quickstart guide

