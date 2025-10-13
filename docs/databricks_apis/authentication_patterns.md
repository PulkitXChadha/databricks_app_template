# Authentication Patterns

This document defines the three authentication patterns used in the Databricks App Template and provides guidance on when to use each pattern.

## Overview

The template implements **dual authentication** to support both user-specific operations (On-Behalf-Of-User) and system operations (Service Principal). This enables:

- **User-level permission enforcement** via Unity Catalog
- **Multi-user data isolation** via application-level filtering
- **Automatic fallback** for development and system operations

## Pattern Summary

| Pattern | Use Case | Authentication Type | User Token Required? | Database Connection |
|---------|----------|---------------------|----------------------|---------------------|
| **A: Service Principal** | System operations | OAuth M2M | No | Service principal |
| **B: On-Behalf-Of-User** | User operations (Databricks APIs) | PAT | Yes | N/A |
| **C: Lakebase Data Isolation** | User operations (Database) | Service principal | Yes (for user_id extraction) | Service principal |

## Pattern A: Service Principal

**Use for**: System operations, health checks, operations that don't require user-specific permissions.

### When to Use
- Health checks and status endpoints
- System-wide queries (non-user-specific data)
- Scheduled jobs or background tasks
- Automatic fallback when user token is missing

### Implementation

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
import os

def create_service_principal_client() -> WorkspaceClient:
    """Create WorkspaceClient with service principal authentication."""
    
    config = Config(
        host=os.environ["DATABRICKS_HOST"],
        client_id=os.environ["DATABRICKS_CLIENT_ID"],
        client_secret=os.environ["DATABRICKS_CLIENT_SECRET"],
        auth_type="oauth-m2m",  # REQUIRED: Explicit OAuth M2M
        timeout=30,  # 30-second timeout per NFR-010
        retry_timeout=30
    )
    
    return WorkspaceClient(config=config)
```

### Service Example

```python
class UnityCatalogService:
    def __init__(self, user_token: Optional[str] = None):
        self.user_token = user_token
        self.workspace_url = os.environ["DATABRICKS_HOST"]
    
    def _get_client(self) -> WorkspaceClient:
        if self.user_token:
            # Pattern B: OBO (see below)
            ...
        else:
            # Pattern A: Service Principal
            return self._create_service_principal_config()
```

### Environment Variables Required
```bash
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_CLIENT_ID=your-service-principal-client-id
DATABRICKS_CLIENT_SECRET=your-service-principal-secret
```

### Key Points
- Always specify `auth_type="oauth-m2m"` explicitly
- Never pass user tokens when using service principal
- Service principal sees all resources it has permissions for
- Use for system operations, not user-specific data access

---

## Pattern B: On-Behalf-Of-User (OBO)

**Use for**: User-specific operations that need to respect user-level permissions (Unity Catalog, Model Serving).

### When to Use
- Querying Unity Catalog tables (enforces user permissions)
- Listing model serving endpoints user has access to
- Any operation where **Unity Catalog enforces row/column/table-level permissions**
- Operations that should see only what the authenticated user can see

### Implementation

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
import os

def create_obo_client(user_token: str) -> WorkspaceClient:
    """Create WorkspaceClient with OBO authentication."""
    
    config = Config(
        host=os.environ["DATABRICKS_HOST"],
        token=user_token,  # User access token from X-Forwarded-Access-Token header
        auth_type="pat",  # REQUIRED: Explicit PAT authentication
        timeout=30,  # 30-second timeout per NFR-010
        retry_timeout=30
    )
    
    return WorkspaceClient(config=config)
```

### Service Example

```python
class UnityCatalogService:
    def __init__(self, user_token: Optional[str] = None):
        self.user_token = user_token
    
    def _get_client(self) -> WorkspaceClient:
        if self.user_token:
            # Pattern B: On-Behalf-Of-User
            config = Config(
                host=self.workspace_url,
                token=self.user_token,
                auth_type="pat",  # REQUIRED
                timeout=30,
                retry_timeout=30
            )
            return WorkspaceClient(config=config)
        else:
            # Fallback to Pattern A (service principal)
            return self._create_service_principal_config()
    
    async def list_catalogs(self, user_id: Optional[str] = None) -> list[str]:
        """List catalogs user has access to (OBO enforces permissions)."""
        client = self._get_client()
        catalogs = client.catalogs.list()
        return [cat.name for cat in catalogs]
```

### Token Extraction (Middleware)

```python
from fastapi import Request

@app.middleware("http")
async def extract_user_token(request: Request, call_next):
    """Extract user token from Databricks Apps platform header."""
    user_token = request.headers.get("X-Forwarded-Access-Token")
    request.state.user_token = user_token
    request.state.has_user_token = user_token is not None
    
    return await call_next(request)

def get_user_token(request: Request) -> Optional[str]:
    """FastAPI dependency to extract user token from request state."""
    return getattr(request.state, "user_token", None)
```

### Endpoint Example

```python
@router.get("/api/unity-catalog/catalogs")
async def list_catalogs(user_token: Optional[str] = Depends(get_user_token)):
    """List catalogs user has access to."""
    service = UnityCatalogService(user_token=user_token)
    catalogs = await service.list_catalogs()
    return {"catalogs": catalogs}
```

### Key Points
- Always specify `auth_type="pat"` explicitly
- Extract token from `X-Forwarded-Access-Token` header
- Token automatically injected by Databricks Apps platform
- Unity Catalog automatically enforces user-level permissions
- Different users see different resources based on their permissions
- Never log token values (only log presence)

---

## Pattern C: Lakebase Data Isolation

**Use for**: User-specific database operations (user preferences, saved queries, application state).

### When to Use
- Storing user preferences
- Saving user-specific application state
- Any data in Lakebase (PostgreSQL) that belongs to a specific user
- Operations requiring **application-level** data isolation (not Unity Catalog)

### Why This Pattern Exists

Lakebase uses **service principal database credentials** for connections (OAuth token-based connection pooling). However, we still need user isolation. Solution: **Application-level filtering** with `WHERE user_id = ?`.

### Implementation

```python
from fastapi import HTTPException
from sqlalchemy import text

class LakebaseService:
    """Service for Lakebase operations with user_id isolation."""
    
    def __init__(self):
        # NEVER accept user_token parameter
        # Always use service principal for database connection
        self.engine = get_engine()  # Service principal connection
    
    async def get_user_preferences(self, user_id: str) -> List[UserPreference]:
        """Get preferences for specific user."""
        
        # CRITICAL: Validate user_id BEFORE query execution
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="User identity required for data access"
            )
        
        # CRITICAL: Filter by user_id
        query = text("""
            SELECT preference_key, preference_value, created_at, updated_at
            FROM user_preferences
            WHERE user_id = :user_id
            ORDER BY updated_at DESC
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {"user_id": user_id})
            return [UserPreference(**row) for row in result]
    
    async def save_user_preference(
        self, 
        user_id: str, 
        key: str, 
        value: str
    ):
        """Save preference for specific user."""
        
        # CRITICAL: Validate user_id
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="User identity required"
            )
        
        # CRITICAL: Store with user_id
        query = text("""
            INSERT INTO user_preferences (user_id, preference_key, preference_value)
            VALUES (:user_id, :key, :value)
            ON CONFLICT (user_id, preference_key)
            DO UPDATE SET preference_value = :value, updated_at = NOW()
        """)
        
        with self.engine.connect() as conn:
            conn.execute(query, {"user_id": user_id, "key": key, "value": value})
            conn.commit()
```

### User ID Extraction

```python
from server.services.user_service import UserService

@router.get("/api/preferences")
async def get_preferences(user_token: Optional[str] = Depends(get_user_token)):
    """Get user preferences with proper isolation."""
    
    # Step 1: Extract user_id from token (Pattern B - OBO)
    user_service = UserService(user_token=user_token)
    user_id = await user_service.get_user_id()  # Returns email address
    
    # Step 2: Query database with user_id filtering (Pattern C)
    lakebase_service = LakebaseService()
    preferences = await lakebase_service.get_user_preferences(user_id=user_id)
    
    return preferences
```

### Database Schema

```sql
-- user_preferences table
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,  -- Email address from UserService
    preference_key VARCHAR(255) NOT NULL,
    preference_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- CRITICAL: Unique constraint includes user_id
    CONSTRAINT uq_user_preference UNIQUE (user_id, preference_key)
);

-- CRITICAL: Index for efficient filtering
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
```

### Key Points
- LakebaseService **NEVER** accepts `user_token` parameter
- Always use service principal for database connection
- **ALWAYS** filter queries by `user_id` (extracted via Pattern B)
- Validate `user_id` presence before query execution (return 401 if missing)
- Use parameterized queries (SQL injection protection)
- Extract `user_id` via `UserService.get_user_id()` (Pattern B)

---

## Decision Matrix

Use this matrix to decide which pattern to use:

| Scenario | Pattern | Reason |
|----------|---------|--------|
| Health check endpoint | A (Service Principal) | No user context needed |
| List Unity Catalog catalogs for user | B (OBO) | User-level permissions enforced by Unity Catalog |
| Query Unity Catalog table for user | B (OBO) | User-level permissions enforced by Unity Catalog |
| List Model Serving endpoints for user | B (OBO) | User-level permissions enforced |
| Save user preference to Lakebase | C (Lakebase) | User_id extraction (Pattern B) + database filtering |
| Get user preferences from Lakebase | C (Lakebase) | User_id extraction (Pattern B) + database filtering |
| Scheduled job querying Unity Catalog | A (Service Principal) | System operation, no user context |
| Background task saving system logs | A (Service Principal) | System operation, not user-specific |

## Common Patterns by Service

### UserService
- **Pattern B (OBO)** when user_token provided
- **Pattern A (Service Principal)** as fallback

```python
service = UserService(user_token=user_token)  # Accepts optional user_token
user_info = await service.get_user_info()  # Uses OBO if token present
```

### UnityCatalogService
- **Pattern B (OBO)** when user_token provided (enforces user permissions)
- **Pattern A (Service Principal)** as fallback

```python
service = UnityCatalogService(user_token=user_token)  # Accepts optional user_token
catalogs = await service.list_catalogs()  # User sees only their accessible catalogs
```

### ModelServingService
- **Pattern B (OBO)** when user_token provided (enforces endpoint permissions)
- **Pattern A (Service Principal)** as fallback

```python
service = ModelServingService(user_token=user_token)  # Accepts optional user_token
endpoints = await service.list_endpoints()  # User sees only their accessible endpoints
```

### LakebaseService
- **Pattern C (Lakebase)** ONLY - never accepts user_token
- Always uses service principal for database connection
- Requires explicit `user_id` parameter for all user-scoped operations

```python
service = LakebaseService()  # NEVER accepts user_token
preferences = await service.get_user_preferences(user_id=user_id)  # MUST provide user_id
```

## Security Checklist

### For Databricks API Operations (Pattern A/B)
- [ ] Explicit `auth_type` parameter specified (`"pat"` or `"oauth-m2m"`)
- [ ] Never log token values (only presence)
- [ ] 30-second timeout configured
- [ ] Retry logic implemented for transient failures
- [ ] User token extracted from `X-Forwarded-Access-Token` header only

### For Database Operations (Pattern C)
- [ ] LakebaseService **never** accepts `user_token` parameter
- [ ] All user-scoped queries include `WHERE user_id = :user_id`
- [ ] User_id validated before query execution (return 401 if missing)
- [ ] Parameterized queries used (SQL injection protection)
- [ ] User_id extracted via `UserService.get_user_id()` (Pattern B)
- [ ] Database connection uses service principal credentials

## Testing Patterns

### Test Pattern A (Service Principal)

```bash
# No user token = automatic service principal fallback
curl http://localhost:8000/api/health
```

### Test Pattern B (OBO)

```bash
# Get user token from Databricks CLI
export DATABRICKS_USER_TOKEN=$(databricks auth token)

# Call endpoint with user token
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
     http://localhost:8000/api/unity-catalog/catalogs
```

### Test Pattern C (Lakebase)

```bash
# User_id automatically extracted from token, database filtered by user_id
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
     http://localhost:8000/api/preferences
```

## Troubleshooting

### "more than one authorization method configured"

**Problem**: SDK detecting multiple auth methods (OAuth + PAT)

**Solution**: Always specify explicit `auth_type`:
- `auth_type="pat"` for Pattern B (OBO)
- `auth_type="oauth-m2m"` for Pattern A (Service Principal)

### Users seeing other users' data

**Problem**: Missing user_id filtering in Lakebase queries

**Solution**: Verify all queries in LakebaseService include:
```python
WHERE user_id = :user_id
```

### 401 errors with valid token

**Problem**: Token not being extracted or user_id validation failing

**Solution**: Check logs for:
- `auth.token_extraction` events
- `auth.user_id_extracted` events
- Verify middleware is registered

## Additional Resources

- [Databricks SDK Authentication](https://databricks-sdk-py.readthedocs.io/en/latest/authentication.html)
- [OBO Authentication Documentation](../OBO_AUTHENTICATION.md)
- [Local Development Guide](../LOCAL_DEVELOPMENT.md)
- [Unity Catalog Permissions](https://docs.databricks.com/data-governance/unity-catalog/manage-privileges/)

