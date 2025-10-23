# Databricks Apps Token Authentication Fix

## Issue Summary

When deployed as a Databricks App, the following API endpoints were returning 503 errors with "Provided OAuth token does not have required scopes" error:
- `/api/unity-catalog/catalogs`
- `/api/model-serving/endpoints`
- `/api/preferences`

Meanwhile, `/api/user/me` was working correctly.

## Root Cause

The services were explicitly setting `auth_type='pat'` when creating `WorkspaceClient` instances with the user token from the `X-Forwarded-Access-Token` header.

```python
# ❌ WRONG - Causes OAuth scope validation errors
self.client = WorkspaceClient(
    host=databricks_host,
    token=user_token,
    auth_type='pat',  # Forces SDK to validate as PAT with OAuth scopes
)
```

**Why this failed:**
1. Databricks Apps forwards user tokens via the `X-Forwarded-Access-Token` header
2. These are special platform-managed tokens, NOT traditional Personal Access Tokens (PATs)
3. By explicitly setting `auth_type='pat'`, the SDK was forcing these tokens to be validated as OAuth tokens with specific scopes
4. The tokens don't have those OAuth scopes, causing the "Provided OAuth token does not have required scopes" error

**Why `/api/user/me` worked initially:**
- The simpler API call to get current user info succeeded
- More complex API calls (listing catalogs, endpoints) triggered the OAuth scope validation
- The dependency `get_current_user_id()` used by all failing endpoints calls `UserService.get_user_info()` which was also hitting the same error

## Solution

Remove the explicit `auth_type='pat'` parameter and let the Databricks SDK auto-detect the token type:

```python
# ✅ CORRECT - Auto-detect token type
self.client = WorkspaceClient(
    host=databricks_host,
    token=user_token,
    # No auth_type parameter - SDK auto-detects
)
```

## Files Modified

### Services Fixed
1. **`server/services/unity_catalog_service.py`**
   - Line 53-60: Removed `auth_type='pat'` from OBO WorkspaceClient initialization
   - Added comment explaining why not to specify auth_type

2. **`server/services/model_serving_service.py`**
   - Line 59-66: Removed `auth_type='pat'` from OBO WorkspaceClient initialization
   - Added comment explaining why not to specify auth_type

3. **`server/services/user_service.py`**
   - Line 76-81: Removed `auth_type='pat'` from OBO WorkspaceClient initialization
   - Added comment explaining why not to specify auth_type

4. **`server/services/schema_detection_service.py`**
   - Line 72-74: Removed `auth_type='pat'` from WorkspaceClient initialization
   - Added comment explaining why not to specify auth_type

### Documentation Updated
5. **`CLAUDE.md`**
   - Added troubleshooting section under "Common Issues"
   - Documented the error pattern, root cause, and correct implementation pattern
   - Includes code examples showing correct vs incorrect patterns

## Files NOT Modified

**`server/lib/database.py`** - Intentionally kept `auth_type='pat'`
- This file uses `auth_type='pat'` for a **different purpose**: authenticating with Databricks to get Lakebase (Postgres) database credentials
- The context is different from making Databricks API calls
- Uses service principal (OAuth M2M) when user token is not available
- This usage is correct and should not be changed

## Testing Checklist

After deployment, verify these endpoints work correctly:

1. **Unity Catalog APIs:**
   ```bash
   curl -H "X-Forwarded-Access-Token: $USER_TOKEN" \
        https://<app-url>/api/unity-catalog/catalogs
   ```

2. **Model Serving APIs:**
   ```bash
   curl -H "X-Forwarded-Access-Token: $USER_TOKEN" \
        https://<app-url>/api/model-serving/endpoints
   ```

3. **User Preferences:**
   ```bash
   curl -H "X-Forwarded-Access-Token: $USER_TOKEN" \
        https://<app-url>/api/preferences
   ```

4. **User Info (should still work):**
   ```bash
   curl -H "X-Forwarded-Access-Token: $USER_TOKEN" \
        https://<app-url>/api/user/me
   ```

All should return 200 status codes with appropriate data (not 503 errors).

## Deployment Instructions

1. **Validate changes locally (optional):**
   ```bash
   ./fix.sh  # Format and type check
   uv run pytest tests/  # Run test suite
   ```

2. **Deploy to Databricks Apps:**
   ```bash
   databricks bundle deploy
   ```

3. **Monitor logs for errors:**
   ```bash
   uv run python dba_logz.py <app-url> --duration 60
   ```

4. **Test endpoints** using the testing checklist above

## Key Takeaways

1. **Never use `auth_type='pat'` with Databricks Apps forwarded tokens**
   - Let the SDK auto-detect the token type
   - Databricks Apps tokens are platform-managed, not traditional PATs

2. **The pattern affects ALL services that use WorkspaceClient with user tokens:**
   - `UnityCatalogService`
   - `ModelServingService` 
   - `UserService`
   - `SchemaDetectionService`

3. **Exception: Database authentication is different**
   - `database.py` correctly uses `auth_type='pat'` for a different purpose
   - Don't change database authentication code

4. **Update pattern documented in CLAUDE.md**
   - Future services should follow the corrected pattern
   - Clear examples of correct vs incorrect implementation

## Related Documentation

- `docs/OBO_AUTHENTICATION.md` - On-Behalf-Of authentication guide
- `CLAUDE.md` - Common Issues section (now includes this fix)
- Databricks SDK documentation on authentication types

