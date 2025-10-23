# Databricks Apps Token Authentication Fix

## Issue Summary

When deployed as a Databricks App, the following API endpoints were returning 503 errors with "Provided OAuth token does not have required scopes" error:
- `/api/unity-catalog/catalogs`
- `/api/model-serving/endpoints`
- `/api/preferences`

Meanwhile, `/api/user/me` was working correctly.

## Root Cause (Multiple Issues)

### Issue 1: Direct WorkspaceClient with auth_type='pat' (Initial Problem)
The services were passing `auth_type='pat'` directly to `WorkspaceClient()`, which caused OAuth scope validation errors with Databricks Apps tokens.

### Issue 2: No auth_type causes "multiple auth methods" error (Second Problem)
When we removed `auth_type='pat'`, the SDK detected BOTH the user token AND OAuth environment variables (DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET), resulting in: **"validate: more than one authorization method configured: oauth and pat"**

## Solution

Use an **explicit Config object** with `auth_type='pat'` to isolate the user token from OAuth environment variables:

```python
# ✅ CORRECT - Use explicit Config to isolate token from env vars
from databricks.sdk.core import Config

cfg = Config(
    host=databricks_host,
    token=user_token,
    auth_type='pat',  # Forces SDK to use ONLY the token, ignoring OAuth env vars
)
self.client = WorkspaceClient(config=cfg)
```

**Why this works:**
1. Creating an explicit `Config` object prevents the SDK from auto-detecting OAuth credentials from environment variables
2. `auth_type='pat'` tells the SDK to treat the token as the ONLY authentication method
3. This matches the pattern used successfully in `database.py` for Lakebase connections
4. The token is isolated from OAuth M2M credentials that exist in the Databricks Apps environment

**Why the previous attempts failed:**

❌ **Attempt 1:** Direct `WorkspaceClient(token=..., auth_type='pat')`
- SDK still checked OAuth env vars and got confused about token type

❌ **Attempt 2:** Direct `WorkspaceClient(token=...)` without auth_type
- SDK detected BOTH token and OAuth env vars, refused to proceed

✅ **Final Solution:** Explicit `Config(token=..., auth_type='pat')` passed to `WorkspaceClient(config=cfg)`
- Config isolates credentials, auth_type ensures token-only authentication

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

