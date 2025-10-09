# Critical OBO Fix - Deployment Guide

## The Problem

You were experiencing this error in production:
```
validate: more than one authorization method configured: oauth and pat
```

## Root Cause

When Databricks Apps deploys your application, it automatically sets these environment variables:
- `DATABRICKS_HOST`
- `DATABRICKS_CLIENT_ID`
- `DATABRICKS_CLIENT_SECRET`
- `DATABRICKS_WAREHOUSE_ID`

When your code created a `WorkspaceClient` with a user token like this:
```python
# This was causing the problem
cfg = Config(host=databricks_host, token=user_token)
```

The Databricks SDK would:
1. See the user token you passed
2. **Also scan environment variables** and find OAuth credentials
3. Detect "multiple auth methods" and throw an error

## The Fix

We now explicitly tell the SDK which auth method to use by setting `auth_type`:

### For OBO (User Token)
```python
# ✅ NEW - Forces SDK to use ONLY the token
cfg = Config(
    host=databricks_host,
    token=user_token,
    auth_type="pat"  # Critical: Tells SDK to ignore OAuth env vars
)
```

### For Service Principal
```python
# Already working correctly
cfg = Config(
    host=databricks_host,
    client_id=client_id,
    client_secret=client_secret,
    auth_type="oauth-m2m"  # Tells SDK to ignore PAT tokens
)
```

## Files Changed

All authentication logic has been updated in these files:

1. ✅ `server/lib/database.py` - Database layer
2. ✅ `server/services/unity_catalog_service.py` - Unity Catalog
3. ✅ `server/services/model_serving_service.py` - Model Serving
4. ✅ `server/services/user_service.py` - User Service

All changes follow the same pattern: **add `auth_type="pat"` when using user tokens**.

## How to Deploy

### Step 1: Verify Changes Locally

```bash
# Check the changes
git status
git diff

# You should see auth_type="pat" added in all services
```

### Step 2: Deploy to Databricks

```bash
# Deploy the updated code
databricks bundle deploy

# Restart the app
databricks bundle run databricks-app
```

### Step 3: Verify the Fix

Watch the logs for these indicators:

#### ✅ Success Indicators
```
INFO: Unity Catalog service initialized with OBO user authorization
INFO: Model Serving service initialized with OBO user authorization
INFO: Retrieved X catalogs  # Actual successful API call
```

#### ❌ Errors That Should NOT Appear
```
ERROR: validate: more than one authorization method configured  # Should be GONE
ERROR: role "token" does not exist  # Should be GONE
```

### Step 4: Test User Permissions

1. Log in as yourself (or test user)
2. Navigate to the app
3. Check Unity Catalog tab - should load catalogs successfully
4. Check Model Serving tab - should load endpoints successfully
5. Try accessing a table you DON'T have permissions for - should get permission denied (this is correct!)

## Rollback (If Needed)

If issues occur, you can rollback:

```bash
# Find the previous deployment
git log --oneline

# Rollback to previous commit
git revert <commit-hash>

# Redeploy
databricks bundle deploy
databricks bundle run databricks-app
```

## What You Should See

### Before the Fix
```json
{
  "level": "ERROR",
  "message": "Error listing catalogs: validate: more than one authorization method configured: oauth and pat",
  "status_code": 503
}
```

### After the Fix
```json
{
  "level": "INFO", 
  "message": "Unity Catalog service initialized with OBO user authorization"
},
{
  "level": "INFO",
  "message": "Retrieved 5 catalogs",
  "status_code": 200
}
```

## Technical Details

The key insight is that the Databricks SDK's `Config` class has a validation step that:

1. Scans for ALL possible auth sources (env vars, config file, explicit params)
2. If it finds more than one, it throws an error
3. Setting `auth_type` explicitly tells it "use THIS method and ignore everything else"

This is by design for security - the SDK wants to ensure you know exactly which credentials are being used.

## Support

If you encounter any issues:

1. Check logs for the specific error message
2. Verify environment variables are set correctly
3. Ensure `app.yaml` has `authorization: [user]` configured
4. Check the [OBO Authentication Guide](./OBO_AUTHENTICATION.md) for detailed troubleshooting

## Summary

- ✅ Added `auth_type="pat"` to all OBO `Config` instances
- ✅ Prevents SDK from scanning environment variables
- ✅ Fixes "multiple auth methods" error
- ✅ No changes to `app.yaml` or environment variables needed
- ✅ Deploy and the error should be gone!

