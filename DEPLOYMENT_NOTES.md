# Deployment Notes - Databricks Apps Authentication Fix

## Issue Resolved

**Problem:** All API endpoints returning 401 "more than one authorization method configured: oauth and pat"

**Root Cause:** In Databricks Apps environments, both OAuth M2M credentials (DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET) and user tokens (from X-Forwarded-Access-Token) are present. The Databricks SDK was detecting both authentication methods and refusing to proceed.

## Solution Implemented

Changed all services to use **explicit `Config` objects** that isolate the user token from OAuth environment variables:

```python
from databricks.sdk.core import Config

cfg = Config(
    host=databricks_host,
    token=user_token,
    auth_type='pat',  # Forces SDK to use ONLY the token, ignoring OAuth env vars
)
self.client = WorkspaceClient(config=cfg)
```

## Files Changed

1. **server/services/user_service.py** - Updated _get_client() method
2. **server/services/unity_catalog_service.py** - Updated __init__ method
3. **server/services/model_serving_service.py** - Updated __init__ method
4. **server/services/schema_detection_service.py** - Updated __init__ method

## Documentation Updated

1. **CLAUDE.md** - Updated troubleshooting section
2. **docs/OBO_AUTHENTICATION.md** - Updated WorkspaceClient configuration pattern
3. **DATABRICKS_APPS_TOKEN_FIX.md** - Comprehensive fix documentation

## Deployment Steps

```bash
# 1. Deploy to Databricks Apps
databricks bundle deploy

# 2. Monitor logs immediately after deployment (60 seconds)
uv run python dba_logz.py <app-url> --duration 60

# 3. Look for these success indicators:
#    - "Application startup complete" in logs
#    - No "more than one authorization method" errors
#    - No circuit breaker errors
```

## Testing Checklist

Test these endpoints (should all return 200, not 401):

```bash
# Set your app URL
APP_URL="https://your-app.databricksapps.com"

# Test user info
curl -s "${APP_URL}/api/user/me" | jq .

# Test Unity Catalog
curl -s "${APP_URL}/api/unity-catalog/catalogs" | jq .

# Test Model Serving
curl -s "${APP_URL}/api/model-serving/endpoints" | jq .

# Test Preferences
curl -s "${APP_URL}/api/preferences" | jq .
```

All endpoints should return:
- **Status: 200 OK**
- Valid JSON response data
- No authentication errors

## Rollback Plan

If issues persist after deployment:

```bash
# Revert to previous commit
git log --oneline -10  # Find previous commit hash
git revert <commit-hash>
databricks bundle deploy
```

## Expected Behavior After Fix

- ✅ All API endpoints return 200 with valid data
- ✅ No "more than one authorization method" errors
- ✅ No "circuit breaker open" errors  
- ✅ User token properly extracted from X-Forwarded-Access-Token header
- ✅ WorkspaceClient uses only the user token, ignoring OAuth env vars

## Monitoring

After deployment, monitor for:
1. **Application startup logs** - Should show "Application startup complete"
2. **API request logs** - Should show 200 status codes
3. **Error logs** - Should have no authentication-related errors
4. **Circuit breaker state** - Should remain "closed" (not open)

## Support

If issues persist:
1. Check logs with: `uv run python dba_logz.py <app-url> --duration 120 --search ERROR`
2. Verify environment variables are set in Databricks Apps console
3. Ensure DATABRICKS_HOST, DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET are configured
4. Check that X-Forwarded-Access-Token header is being forwarded by the platform

## References

- **DATABRICKS_APPS_TOKEN_FIX.md** - Detailed explanation of the fix
- **docs/OBO_AUTHENTICATION.md** - OBO authentication patterns
- **CLAUDE.md** - Common Issues section
- **server/lib/database.py** - Reference implementation of Config pattern

