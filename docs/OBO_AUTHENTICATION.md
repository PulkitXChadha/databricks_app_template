# On-Behalf-Of-User (OBO) Authentication

This document explains how the Databricks App Template implements **OBO-only authentication** for all Databricks API operations.

> **Note**: This application uses OBO-only authentication for Databricks APIs. Service principal fallback has been removed to enforce proper security boundaries and ensure all operations respect user-level permissions.

## Overview

On-behalf-of-user (OBO) authentication requires the application to make all Databricks API calls using the **actual end user's credentials**. This ensures that:

1. **Permissions are properly enforced** - Users can only access data they have permissions for in Unity Catalog
2. **Audit trails are accurate** - Actions are logged under the actual user, not a service principal
3. **Security is enhanced** - No privilege escalation through the app
4. **No fallback behavior** - Missing user tokens result in clear authentication errors

## How It Works

### 1. Token Extraction

When a user accesses the deployed Databricks App, the platform automatically adds the user's access token to every request via the `X-Forwarded-Access-Token` header.

The FastAPI middleware in `server/app.py` extracts this token:

```python
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    # Extract user access token from Databricks Apps header
    user_token = request.headers.get('x-forwarded-access-token')
    request.state.user_token = user_token
    # ... rest of middleware
```

### 2. Token Propagation

The `get_user_token` dependency in `server/lib/auth.py` makes the token available to route handlers and **raises HTTP 401 if missing**:

```python
async def get_user_token(request: Request) -> str:
    """Extract required user access token from request state.
    
    Raises:
        HTTPException: 401 if token is missing or empty (no fallback)
    """
    user_token = getattr(request.state, 'user_token', None)
    
    if not user_token:
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "AUTH_MISSING",
                "message": "User authentication required. Please provide a valid user access token."
            }
        )
    
    return user_token
```

### 3. Service Initialization

Services (UnityCatalogService, ModelServingService, UserService) **require** a `user_token` parameter:

```python
# OBO-only - user_token is REQUIRED (not Optional)
service = UnityCatalogService(user_token=user_token)  # ✅ Works

# Missing token raises ValueError at initialization
service = UnityCatalogService(user_token=None)  # ❌ Raises ValueError
service = UnityCatalogService(user_token="")    # ❌ Raises ValueError
```

**No Fallback**: Services validate that `user_token` is provided and non-empty during initialization. There is no automatic fallback to service principal credentials.

### 4. WorkspaceClient Configuration

Services create a WorkspaceClient using **ONLY** the user token, letting the SDK auto-detect the token type:

```python
# OBO-only pattern - the ONLY way to initialize services
def __init__(self, user_token: str):
    """Initialize service with OBO authentication.
    
    Args:
        user_token: User access token (REQUIRED)
        
    Raises:
        ValueError: If user_token is None or empty
    """
    if not user_token:
        raise ValueError("user_token is required for UnityCatalogService")
    
    self.user_token = user_token
    self.workspace_url = os.getenv('DATABRICKS_HOST')
    
    # Create WorkspaceClient with user token ONLY
    # IMPORTANT: Do NOT specify auth_type for Databricks Apps tokens
    # Let the SDK auto-detect the token type to avoid OAuth scope errors
    self.client = WorkspaceClient(
        host=self.workspace_url,
        token=self.user_token,
        # No auth_type parameter - SDK auto-detects
    )
```

**Why not specify `auth_type='pat'`?**

Databricks Apps forwards user tokens via the `X-Forwarded-Access-Token` header. These are special platform-managed tokens, not traditional Personal Access Tokens (PATs). Explicitly setting `auth_type='pat'` forces the SDK to validate them as OAuth tokens with specific scopes, causing "Provided OAuth token does not have required scopes" errors. By omitting the `auth_type` parameter, the SDK correctly auto-detects and uses the token.

**Critical**: 
- Do NOT specify `auth_type` parameter when using Databricks Apps tokens - let SDK auto-detect
- For local development with traditional PATs, `auth_type='pat'` may be needed, but not for Databricks Apps
- Services no longer support initialization without a user token
- No service principal fallback exists for Databricks API operations

## Implementation Guide

### FastAPI Router Example

```python
from fastapi import APIRouter, Depends
from server.lib.auth import get_current_user_id, get_user_token
from server.services.unity_catalog_service import UnityCatalogService

router = APIRouter()

@router.get("/catalogs")
async def list_catalogs(
    user_id: str = Depends(get_current_user_id),
    user_token: str = Depends(get_user_token)  # REQUIRED (not Optional)
):
    """List catalogs with user's permissions.
    
    Raises:
        HTTPException: 401 if user_token is missing (automatic via dependency)
    """
    # Service requires user token (no fallback)
    service = UnityCatalogService(user_token=user_token)
    catalogs = await service.list_catalogs(user_id=user_id)
    return catalogs
```

**Key Changes in OBO-Only**:
- `user_token` parameter type is `str` (not `str | None`)
- `get_user_token` dependency automatically raises 401 if token is missing
- No need for manual None checks - dependency handles validation
- Service initialization requires the token

### Database Access (Lakebase - Hybrid Approach)

LakebaseService uses a **hybrid approach** distinct from Databricks API services:

```python
from server.services.lakebase_service import LakebaseService
from server.services.user_service import UserService

# Step 1: Extract user_id using OBO-authenticated UserService
user_service = UserService(user_token=user_token)  # Requires token
user_id = await user_service.get_user_id()

# Step 2: Use LakebaseService with application-level credentials
lakebase_service = LakebaseService()  # NO user_token parameter
preferences = await lakebase_service.get_preferences(user_id=user_id)
```

**Important**:
- **LakebaseService does NOT accept user_token** - it uses application-level database credentials
- **User isolation enforced via user_id filtering** in SQL queries (`WHERE user_id = :user_id`)
- **user_id must be obtained from OBO-authenticated UserService** to ensure security
- All user-scoped queries include explicit user_id filtering

This hybrid approach is necessary because:
1. Lakebase OAuth JWT tokens use service principal credentials (not per-user tokens)
2. Database connection pooling is incompatible with per-user credentials
3. User_id filtering at the application level provides proper data isolation

## Configuration

### Environment Variables

**Required** environment variables for OBO-only operation:

```bash
# Databricks workspace (REQUIRED)
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com

# SQL Warehouse (REQUIRED for Unity Catalog queries)
DATABRICKS_WAREHOUSE_ID=your-warehouse-id

# Lakebase configuration (for database access with user_id filtering)
PGHOST=instance-xyz.database.cloud.databricks.com
LAKEBASE_DATABASE=your-database-name
LAKEBASE_INSTANCE_NAME=instance-xyz
```

**Legacy/Optional** environment variables (not used for Databricks APIs):

```bash
# Service principal credentials (OPTIONAL - not used)
# These variables may remain in your environment but are ignored for Databricks API operations
DATABRICKS_CLIENT_ID=your-client-id      # Not used (legacy)
DATABRICKS_CLIENT_SECRET=your-client-secret  # Not used (legacy)
```

**Note**: `DATABRICKS_CLIENT_ID` and `DATABRICKS_CLIENT_SECRET` are **not required** and **not used** for Databricks API operations in OBO-only mode. They may remain in your environment without affecting functionality. LakebaseService uses its own OAuth JWT credentials via `generate_database_credential()`.

### app.yaml Configuration

For Databricks Apps deployment, ensure OBO is enabled in your `app.yaml`:

```yaml
resources:
  - name: databricks-app
    display_name: "Databricks App Template"
    
    # Enable on-behalf-of-user authentication
    authorization:
      - user  # Allow user-level access
```

## Benefits of OBO

### 1. Unity Catalog Permission Enforcement

Without OBO:
```python
# ❌ Service principal sees ALL tables (regardless of user permissions)
service = UnityCatalogService()
tables = await service.list_tables()  # Returns all tables SP can access
```

With OBO:
```python
# ✅ User sees ONLY tables they have permissions for
service = UnityCatalogService(user_token=user_token)
tables = await service.list_tables()  # Returns only user's accessible tables
```

### 2. Accurate Audit Logs

- **Without OBO**: All queries logged as service principal
- **With OBO**: Queries logged under actual user's identity

### 3. Row-Level Security

Unity Catalog row filters and column masks are properly enforced when using OBO.

## Troubleshooting

### Error: "more than one authorization method configured"

**Problem**: This error occurs when the Databricks SDK detects multiple authentication methods:
- Databricks Apps automatically sets OAuth env vars (`DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`)
- Your code passes a user token for OBO
- SDK sees BOTH and throws an error

**Root Cause**: When creating a WorkspaceClient with just `token=user_token`, the SDK still scans environment variables and detects the OAuth credentials, even though we only want to use the token.

**Solution**: Explicitly set `auth_type="pat"` when using a user token to tell the SDK to ONLY use the token:

```python
# ✅ CORRECT - Forces SDK to use only the token
cfg = Config(
    host=databricks_host,
    token=user_token,
    auth_type="pat"  # Critical: Tells SDK to ignore OAuth env vars
)

# ❌ WRONG - SDK will detect OAuth env vars
cfg = Config(
    host=databricks_host,
    token=user_token  # Without auth_type="pat", SDK checks env vars
)
```

For service principal mode, use `auth_type="oauth-m2m"`:

```python
cfg = Config(
    host=databricks_host,
    client_id=client_id,
    client_secret=client_secret,
    auth_type="oauth-m2m"  # Explicit OAuth, ignores PAT tokens in env
)
```

### Error: 'role "token" does not exist' (Lakebase)

**Problem**: Database connection using literal "token" as username.

**Solution**: Use the `get_db_session_obo` function which properly generates database credentials from the user token:

```python
# ✅ Correct
for session in get_db_session_obo(user_token):
    result = session.query(UserPreference).all()

# ❌ Wrong - don't use global engine for OBO
engine = get_engine()  # This uses service principal
```

### OBO Not Working in Local Development

**Problem**: `X-Forwarded-Access-Token` header not present in local development.

**Solution**: OBO-only authentication requires user tokens in local development. Use Databricks CLI to obtain tokens:

```bash
# Install and authenticate with Databricks CLI
databricks auth login --host https://your-workspace.cloud.databricks.com

# Obtain user access token
export DATABRICKS_USER_TOKEN=$(databricks auth token)

# Use token in requests
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
     http://localhost:8000/api/user/me
```

**No Fallback**: The application no longer falls back to service principal authentication. Missing tokens result in HTTP 401 errors with clear error messages.

See [LOCAL_DEVELOPMENT.md](./LOCAL_DEVELOPMENT.md) for detailed local development setup.

## Security Considerations

1. **Token Validation**: The Databricks platform validates all user tokens before forwarding requests
2. **Token Expiration**: User tokens automatically expire and are refreshed by the platform
3. **No Token Storage**: Never store user tokens in databases or logs
4. **No Fallback**: Missing tokens result in HTTP 401 errors - no automatic fallback to service principal
5. **User Isolation**: All operations respect user-level permissions enforced by Unity Catalog
6. **Audit Trail**: All actions are logged under the actual user's identity

## Testing OBO

### Integration Test Example

```python
import pytest
from fastapi.testclient import TestClient
from server.app import app

def test_list_catalogs_with_obo():
    """Test catalog listing with user permissions."""
    client = TestClient(app)
    
    # Simulate user token in headers
    headers = {
        "X-Forwarded-Access-Token": "user-token-here"
    }
    
    response = client.get("/api/unity-catalog/catalogs", headers=headers)
    assert response.status_code == 200
    
    # Verify service used user token (not service principal)
    catalogs = response.json()
    assert isinstance(catalogs, list)
```

## References

- [Databricks Apps Cookbook - OBO Authentication](https://apps-cookbook.dev/docs/streamlit/authentication/users_obo)
- [Databricks SDK Python Documentation](https://databricks-sdk-py.readthedocs.io/)
- [Unity Catalog Authorization](https://docs.databricks.com/data-governance/unity-catalog/manage-privileges/index.html)

## Migration from Service Principal to OBO

If you're migrating existing code from service principal to OBO:

1. **Update Router Dependencies**:
   ```python
   # Add user_token dependency
   user_token: str | None = Depends(get_user_token)
   ```

2. **Update Service Initialization**:
   ```python
   # Pass user_token to service
   service = YourService(user_token=user_token)
   ```

3. **Test Permission Enforcement**:
   - Verify users can only access their permitted resources
   - Check audit logs show actual user identities

4. **Deploy and Verify**:
   - Deploy to Databricks Apps (OBO only works when deployed)
   - Test with users having different permission levels
   - Monitor logs for authentication errors

## Implementation Details

### OBO-Only Authentication Pattern

The application enforces OBO-only authentication for all Databricks API operations:

1. **Databricks API Services (OBO-Only)** - UnityCatalogService, ModelServingService, UserService
   ```python
   # ONLY supported pattern - requires user_token
   client = WorkspaceClient(
       host=workspace_url,
       token=user_token,
       auth_type="pat"  # Explicit OBO authentication
   )
   ```
   
   **No Fallback**: Services raise `ValueError` if `user_token` is None or empty. No automatic fallback to service principal.

2. **LakebaseService (Hybrid Approach)** - Uses application-level credentials with user_id filtering
   ```python
   # Database connection uses application-level credentials
   # User isolation enforced via user_id filtering in queries
   query = "SELECT * FROM table WHERE user_id = :user_id"
   ```
   
   **Rationale**: Database connection pooling requires application-level credentials. User isolation is enforced at the SQL query level rather than the connection level.

### Retry Logic and Error Handling

Authentication failures are automatically retried with exponential backoff:

- **Retry Attempts**: Up to 3 attempts (initial + 2 retries)
- **Backoff Delays**: 100ms, 200ms, 400ms (exponential)
- **Total Timeout**: Maximum 5 seconds
- **Rate Limiting**: HTTP 429 errors fail immediately without retry
- **Circuit Breaker**: Per-instance protection against retry storms

```python
from server.lib.auth import with_auth_retry

@with_auth_retry
async def fetch_data():
    client = self._get_client()
    return await client.some_api_call()
```

### Multi-User Data Isolation

User-specific data in Lakebase is isolated using `user_id` filtering:

```python
# All user-scoped queries include WHERE user_id = ?
async def get_user_preferences(self, user_id: str):
    if not user_id:
        raise HTTPException(status_code=401, detail="User identity required")
    
    query = "SELECT * FROM user_preferences WHERE user_id = :user_id"
    return await self.db.execute(query, {"user_id": user_id})
```

### Observability and Metrics

Authentication operations are fully observable:

1. **Structured Logging**: All auth events logged with correlation IDs
   ```json
   {
     "event": "auth.mode",
     "mode": "obo",
     "auth_type": "pat",
     "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
   }
   ```
   
   **Note**: The `mode` field is hardcoded to `"obo"` in log statements since it's the only supported authentication mode.

2. **Prometheus Metrics**: Exposed at `/metrics` endpoint (requires authentication)
   - `auth_requests_total`: Total OBO authentication attempts (success/failure)
   - `auth_overhead_seconds`: Authentication overhead (target: <10ms)
   - `request_duration_seconds`: Request duration including authentication
   - `upstream_api_duration_seconds`: Upstream API call latencies
   
   **Removed Metrics**:
   - ~~`auth_fallback_total`~~ - No fallback behavior in OBO-only
   - ~~`auth_requests_total{mode="service_principal"}`~~ - Only OBO mode exists

3. **Performance Targets**:
   - Authentication overhead: <10ms (P95)
   - Request timeout: 30 seconds
   - No retry logic for missing tokens (fails immediately with 401)

### Local Development Testing

For local OBO testing without Databricks Apps:

1. **Fetch User Token**:
   ```bash
   # Install and authenticate Databricks CLI
   databricks auth login --host https://your-workspace.cloud.databricks.com
   
   # Get user access token
   export DATABRICKS_USER_TOKEN=$(python scripts/get_user_token.py)
   ```

2. **Test Endpoints**:
   ```bash
   # Test with user token (OBO mode)
   curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
        http://localhost:8000/api/user/me
   
   # Test without token (service principal fallback)
   curl http://localhost:8000/api/health
   ```

3. **Verify Multi-User Isolation**:
   ```bash
   # Save preference as User A
   curl -X POST \
        -H "X-Forwarded-Access-Token: $USER_A_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"preference_key": "theme", "preference_value": "dark"}' \
        http://localhost:8000/api/preferences
   
   # Verify User B cannot see User A's preferences
   curl -H "X-Forwarded-Access-Token: $USER_B_TOKEN" \
        http://localhost:8000/api/preferences
   ```

See [quickstart.md](../specs/002-fix-api-authentication/quickstart.md) for comprehensive testing scenarios.

### Error Codes

Structured authentication errors use standardized error codes:

- `AUTH_EXPIRED`: User access token has expired
- `AUTH_INVALID`: Token validation failed
- `AUTH_MISSING`: Token required but not provided
- `AUTH_USER_IDENTITY_FAILED`: Unable to extract user identity
- `AUTH_RATE_LIMITED`: Platform rate limit exceeded
- `AUTH_MALFORMED`: Token format is invalid

Example error response:
```json
{
  "detail": "User access token has expired",
  "error_code": "AUTH_EXPIRED",
  "retry_after": null
}
```

