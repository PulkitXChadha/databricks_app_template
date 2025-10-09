# OBO Authentication Migration Summary

This document summarizes the changes made to implement on-behalf-of-user (OBO) authentication in the Databricks App Template.

## Problem Statement

The deployed app was experiencing authentication failures with these errors:

1. **"more than one authorization method configured: oauth and pat"** - The SDK detected both OAuth service principal credentials and PAT tokens, causing conflicts
2. **"role 'token' does not exist"** - Database connections were failing because Lakebase authentication was incorrectly configured

## Root Cause

The original implementation had two key issues:

1. **Mixed authentication methods**: Services were trying to use OAuth service principal credentials even when a user token was available, causing SDK validation errors
2. **Database authentication**: The Lakebase connection was using a literal "token" string as the PostgreSQL username instead of properly generating per-user database credentials

## Changes Made

### 1. Database Layer (`server/lib/database.py`)

**Before**:
```python
def _create_workspace_client() -> WorkspaceClient:
    # Always used OAuth with service principal
    if databricks_host and client_id and client_secret:
        cfg = Config(host=databricks_host, client_id=client_id, 
                    client_secret=client_secret, auth_type="oauth-m2m")
        return WorkspaceClient(config=cfg)
    return WorkspaceClient()
```

**After**:
```python
def _create_workspace_client(user_token: str | None = None) -> WorkspaceClient:
    # OBO: Use ONLY user token when provided
    if user_token:
        cfg = Config(host=databricks_host, token=user_token)
        return WorkspaceClient(config=cfg)
    
    # Service principal: Use OAuth M2M for app-level access
    if databricks_host and client_id and client_secret:
        cfg = Config(host=databricks_host, client_id=client_id, 
                    client_secret=client_secret, auth_type="oauth-m2m")
        return WorkspaceClient(config=cfg)
    return WorkspaceClient()
```

**Key improvements**:
- Added `user_token` parameter to support OBO
- When user token is present, use ONLY that token (no mixing with OAuth)
- Added `get_db_session_obo()` function for per-user database sessions
- Updated `create_lakebase_engine()` to accept `user_token` parameter

### 2. Unity Catalog Service (`server/services/unity_catalog_service.py`)

**Changes**:
- Updated `__init__()` to properly handle OBO mode
- When `user_token` is provided, create WorkspaceClient with ONLY that token
- Improved documentation to clarify OBO vs service principal modes
- Set `auth_type="oauth-m2m"` explicitly in service principal mode to prevent PAT token conflicts

### 3. Model Serving Service (`server/services/model_serving_service.py`)

**Changes**:
- Same pattern as Unity Catalog Service
- Use ONLY user token when provided for OBO
- Explicit `auth_type="oauth-m2m"` for service principal mode
- Updated logging to distinguish between OBO and service principal modes

### 4. User Service (`server/services/user_service.py`)

**Changes**:
- Simplified initialization logic - removed complex error handling
- Clear separation between OBO mode (user token) and service principal mode
- Consistent pattern with other services

### 5. Lakebase Service (`server/services/lakebase_service.py`)

**Before**:
```python
class LakebaseService:
    def __init__(self, db_session: Session | None = None):
        self.db_session = db_session
```

**After**:
```python
class LakebaseService:
    def __init__(self, db_session: Session | None = None, user_token: str | None = None):
        self.db_session = db_session
        self.user_token = user_token
    
    async def get_preferences(self, user_id: str, preference_key: str | None = None):
        if self.user_token:
            # Use OBO session with user's database credentials
            for session in get_db_session_obo(self.user_token):
                return self._query_preferences(session, user_id, preference_key)
        else:
            # Use service principal session
            for session in get_db_session():
                return self._query_preferences(session, user_id, preference_key)
```

**Key improvements**:
- Added `user_token` parameter
- Automatically uses OBO database sessions when token is available
- Updated all methods: `get_preferences()`, `save_preference()`, `delete_preference()`

### 6. Lakebase Router (`server/routers/lakebase.py`)

**Before**:
```python
@router.get("/preferences")
async def get_preferences(
    request: Request,
    user_id: str = Depends(get_current_user_id)
):
    service = LakebaseService()
    # ...
```

**After**:
```python
@router.get("/preferences")
async def get_preferences(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    user_token: str | None = Depends(get_user_token)
):
    service = LakebaseService(user_token=user_token)
    # ...
```

**Changes**:
- Added `user_token` dependency to all endpoints
- Pass `user_token` to service initialization

### 7. Documentation

**New files**:
- `docs/OBO_AUTHENTICATION.md` - Comprehensive guide to OBO implementation
- `docs/OBO_MIGRATION_SUMMARY.md` - This file

**Updated files**:
- `README.md` - Added documentation section with link to OBO guide

## How OBO Works Now

### Request Flow

```
1. User accesses app → Databricks adds X-Forwarded-Access-Token header
2. Middleware extracts token → Stores in request.state.user_token
3. Router gets token → Passes to service via Depends(get_user_token)
4. Service initialization → Uses ONLY user token if provided
5. API calls → Made with user's credentials and permissions
6. Database access → Generated per-user credentials from user token
```

### Permission Enforcement

**Before OBO**:
- All API calls used service principal permissions
- Users could access any data the service principal could access
- Audit logs showed service principal as the actor

**After OBO**:
- API calls use individual user permissions
- Users can only access data they have Unity Catalog permissions for
- Audit logs show actual user identities
- Row-level security and column masks are properly enforced

## Configuration Required

### Environment Variables

Ensure these are set in your deployment:

```bash
# Required for OBO
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_WAREHOUSE_ID=your-warehouse-id

# Service principal (for fallback/admin operations)
DATABRICKS_CLIENT_ID=your-client-id
DATABRICKS_CLIENT_SECRET=your-client-secret

# Lakebase (for database OBO)
PGHOST=instance-xyz.database.cloud.databricks.com
LAKEBASE_DATABASE=your-database-name
LAKEBASE_INSTANCE_NAME=instance-xyz
```

### app.yaml

Ensure OBO is enabled:

```yaml
resources:
  - name: databricks-app
    authorization:
      - user  # Enable on-behalf-of-user
```

## Testing the Changes

### 1. Deploy the App

```bash
databricks bundle deploy
databricks bundle run databricks-app
```

### 2. Verify OBO is Working

Check the logs for:
```
INFO: Unity Catalog service initialized with OBO user authorization
INFO: Model Serving service initialized with OBO user authorization
```

### 3. Test Permission Enforcement

1. Log in as a user with limited permissions
2. Try to access Unity Catalog tables
3. Verify you only see tables you have permissions for
4. Check audit logs - should show your actual user identity, not the service principal

### 4. Monitor for Errors

Watch for:
- ❌ "more than one authorization method" - Should NOT appear
- ❌ "role 'token' does not exist" - Should NOT appear
- ✅ "OBO user authorization" - Should appear in logs

## Rollback Plan

If issues occur, you can temporarily disable OBO by:

1. Not passing `user_token` to services:
```python
# Temporary rollback - use service principal
service = UnityCatalogService()  # No user_token
```

2. Reverting to previous version:
```bash
git revert <commit-hash>
databricks bundle deploy
```

## Benefits Achieved

### ✅ Security
- Users can only access data they have permissions for
- No privilege escalation through the app
- Proper enforcement of Unity Catalog permissions

### ✅ Compliance
- Accurate audit logs with real user identities
- Row-level security and column masks enforced
- Better data governance

### ✅ Reliability
- No more "multiple authorization methods" errors
- Proper database credential generation
- Cleaner, more maintainable code

### ✅ User Experience
- Seamless authentication (users don't notice)
- Permissions work as expected
- No manual token management required

## Next Steps

1. **Deploy to production** - Test with real users
2. **Monitor logs** - Ensure no authentication errors
3. **Verify permissions** - Check that users see correct data
4. **Review audit logs** - Confirm user identities are correct
5. **Update tests** - Add OBO-specific integration tests

## References

- [OBO Authentication Guide](./OBO_AUTHENTICATION.md) - Full implementation guide
- [Databricks Apps Cookbook](https://apps-cookbook.dev/docs/streamlit/authentication/users_obo) - Official OBO documentation
- [Databricks SDK Python](https://databricks-sdk-py.readthedocs.io/) - SDK documentation

## Support

For issues or questions:
1. Check the [OBO Authentication Guide](./OBO_AUTHENTICATION.md) troubleshooting section
2. Review deployment logs for specific error messages
3. Verify environment variables are correctly set
4. Ensure app.yaml has `authorization: [user]` configured

