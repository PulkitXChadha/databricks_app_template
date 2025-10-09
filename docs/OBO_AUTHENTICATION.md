# On-Behalf-Of-User (OBO) Authentication

This document explains how the Databricks App Template implements on-behalf-of-user (OBO) authentication for API calls and database access.

## Overview

On-behalf-of-user (OBO) authentication allows the application to make API calls and database queries using the **actual end user's credentials** instead of the app's service principal credentials. This ensures that:

1. **Permissions are properly enforced** - Users can only access data they have permissions for in Unity Catalog
2. **Audit trails are accurate** - Actions are logged under the actual user, not the service principal
3. **Security is enhanced** - No privilege escalation through the app

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

The `get_user_token` dependency in `server/lib/auth.py` makes the token available to route handlers:

```python
async def get_user_token(request: Request) -> str | None:
    """Extract user access token from request state."""
    return getattr(request.state, 'user_token', None)
```

### 3. Service Initialization

Services (UnityCatalogService, ModelServingService, etc.) accept an optional `user_token` parameter:

```python
# With OBO (uses user's permissions)
service = UnityCatalogService(user_token=user_token)

# Without OBO (uses service principal permissions)
service = UnityCatalogService()
```

### 4. WorkspaceClient Configuration

When a user token is provided, the service creates a WorkspaceClient using **ONLY** that token:

```python
if user_token:
    # OBO: Use ONLY the user's token
    cfg = Config(host=databricks_host, token=user_token)
    self.client = WorkspaceClient(config=cfg)
else:
    # App authorization: Use service principal OAuth M2M
    cfg = Config(
        host=databricks_host,
        client_id=client_id,
        client_secret=client_secret,
        auth_type="oauth-m2m"
    )
    self.client = WorkspaceClient(config=cfg)
```

**Important**: When using OBO, we do NOT mix OAuth service principal credentials with the user token. This prevents the "more than one authorization method configured" error.

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
    user_token: str | None = Depends(get_user_token)
):
    """List catalogs with user's permissions."""
    # Service uses user token for OBO
    service = UnityCatalogService(user_token=user_token)
    catalogs = await service.list_catalogs(user_id=user_id)
    return catalogs
```

### Database Access with OBO

For Lakebase (PostgreSQL) database access with OBO:

```python
from server.lib.database import get_db_session_obo
from server.services.lakebase_service import LakebaseService

# Option 1: Using the service
service = LakebaseService(user_token=user_token)
preferences = await service.get_preferences(user_id=user_id)

# Option 2: Direct database session
for session in get_db_session_obo(user_token):
    result = session.query(UserPreference).filter_by(user_id=user_id).all()
```

## Configuration

### Environment Variables

The following environment variables are required for OBO to work properly:

```bash
# Databricks workspace (required for OBO)
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com

# SQL Warehouse (required for Unity Catalog queries)
DATABRICKS_WAREHOUSE_ID=your-warehouse-id

# Service principal (for fallback/admin operations)
DATABRICKS_CLIENT_ID=your-client-id
DATABRICKS_CLIENT_SECRET=your-client-secret

# Lakebase configuration (for database OBO)
PGHOST=instance-xyz.database.cloud.databricks.com
LAKEBASE_DATABASE=your-database-name
LAKEBASE_INSTANCE_NAME=instance-xyz
```

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

**Problem**: This error occurs when both OAuth credentials and PAT tokens are present.

**Solution**: Ensure services explicitly use `auth_type="oauth-m2m"` for service principal mode:

```python
cfg = Config(
    host=databricks_host,
    client_id=client_id,
    client_secret=client_secret,
    auth_type="oauth-m2m"  # This forces OAuth and ignores PAT tokens
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

**Solution**: OBO only works when deployed to Databricks Apps. For local development:
- The app automatically falls back to service principal authentication
- Or, manually set a user token for testing:

```python
# For local testing only
import os
test_token = os.getenv('TEST_USER_TOKEN')
service = UnityCatalogService(user_token=test_token)
```

## Security Considerations

1. **Token Validation**: The Databricks platform validates all user tokens before forwarding requests
2. **Token Expiration**: User tokens automatically expire and are refreshed by the platform
3. **No Token Storage**: Never store user tokens in databases or logs
4. **Fallback Mode**: Service principal mode is used when user token is not available (e.g., background jobs)

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

