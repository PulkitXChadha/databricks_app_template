# Quickstart: Testing OBO Authentication Implementation

**Feature**: Fix API Authentication and Implement On-Behalf-Of User (OBO) Authentication  
**Date**: 2025-10-10  
**Estimated Time**: 30 minutes

---

## Overview

This quickstart guide provides step-by-step instructions to manually test the dual authentication implementation (On-Behalf-Of-User for Databricks APIs and Service Principal for Lakebase) in both local development and Databricks Apps deployment environments.

---

## Prerequisites

### Required Tools
- ✅ Python 3.11+ installed
- ✅ `uv` package manager installed
- ✅ Databricks CLI installed and configured
- ✅ Access to Databricks workspace
- ✅ Service principal credentials (for local dev)

### Environment Variables (Local Development)

Create `.env.local` file in repository root:

```bash
# Databricks workspace
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com

# Service principal credentials (for local dev)
DATABRICKS_CLIENT_ID=your-service-principal-client-id
DATABRICKS_CLIENT_SECRET=your-service-principal-client-secret

# Lakebase connection (if testing locally with Lakebase)
PGHOST=your-lakebase-host
PGDATABASE=your-database
PGUSER=your-service-principal-role
PGPORT=5432
PGSSLMODE=require
```

### Installation

1. **Clone repository and install dependencies**:
   ```bash
   cd /path/to/databricks-app-template
   uv sync
   ```

2. **Verify Databricks SDK version**:
   ```bash
   uv pip list | grep databricks-sdk
   # Should show: databricks-sdk==0.67.0
   ```

3. **Install Databricks CLI** (if not already installed):
   ```bash
   curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
   databricks --version
   ```

4. **Authenticate Databricks CLI**:
   ```bash
   databricks auth login --host https://your-workspace.cloud.databricks.com
   ```

---

## Success Criteria Traceability

This traceability matrix maps each quickstart phase to the specific requirements it validates:

| Quickstart Phase | Validates Requirements | Success Criteria |
|------------------|------------------------|------------------|
| Phase 1: Local Development | FR-016, FR-020, FR-021 | Service principal fallback works automatically when X-Forwarded-Access-Token header missing. System logs fallback events. No configuration flags required. |
| Phase 2: Local OBO Testing | FR-001, FR-002, FR-010, FR-022 | Token extraction from header works. User identity retrieved via API call. UserService.get_user_info() returns userName field. Real Databricks CLI tokens accepted. |
| Phase 3: Multi-User Isolation | FR-010, FR-013, FR-014 | user_id extracted and stored with database records. All user-scoped queries include WHERE user_id = ?. Cross-user data access prevented. user_id validation returns 401 when missing. |
| Phase 4: Error Handling | FR-015, FR-018, FR-019 | Structured JSON errors with error_code field. Exponential backoff retry (100ms/200ms/400ms). Total timeout <5s. Rate limit (429) fails immediately. |
| Phase 5: Observability | FR-017, NFR-001, NFR-011, NFR-012 | Correlation IDs mandatory in all logs. Auth overhead <10ms (P95). Comprehensive metrics exposed. Prometheus-compatible format. |
| Phase 6: Deployment | All FRs + NFRs | End-to-end validation in Databricks Apps platform. Platform auto-injects user tokens. No authentication errors. Multi-user isolation verified. |

---

## Test Plan

### Phase 1: Local Development Testing (Service Principal Fallback)

#### 1.1 Start Local Development Server

```bash
# Start backend and frontend with hot reloading
./watch.sh

# Monitor logs in separate terminal
tail -f nohup.out | grep -E "(auth\.|ERROR)"
```

**Expected Output**:
```
{"timestamp": "2025-10-10T12:00:00Z", "level": "INFO", "event": "server.start", "port": 8000}
```

#### 1.2 Test Health Check (No Authentication Required)

```bash
# Test basic endpoint with service principal fallback
curl http://localhost:8000/api/health | jq .
```

**Expected Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-10T12:00:00Z"
}
```

**Expected Logs**:
```json
{"level": "INFO", "event": "auth.fallback_triggered", "reason": "missing_token", "environment": "local"}
{"level": "INFO", "event": "auth.mode", "mode": "service_principal", "auth_type": "oauth-m2m"}
```

#### 1.3 Test Authentication Status Endpoint

```bash
# Check authentication status (should show service principal mode)
curl http://localhost:8000/api/auth/status | jq .
```

**Expected Response**:
```json
{
  "authenticated": true,
  "auth_mode": "service_principal",
  "has_user_identity": false,
  "user_id": null
}
```

---

### Phase 2: Local OBO Testing (Real User Tokens)

#### 2.1 Fetch User Access Token

```bash
# Get user access token from Databricks CLI
export DATABRICKS_USER_TOKEN=$(databricks auth token)

# Verify token is set
echo ${DATABRICKS_USER_TOKEN:0:20}...
# Should output: eyJhbGciOiJSUzI1NiIs...
```

#### 2.2 Test User Info Endpoint with OBO

```bash
# Call /api/user/me with user token
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
     http://localhost:8000/api/user/me | jq .
```

**Expected Response**:
```json
{
  "user_id": "your-email@example.com",
  "display_name": "Your Name",
  "active": true,
  "workspace_url": "https://your-workspace.cloud.databricks.com"
}
```

**Expected Logs**:
```json
{"level": "INFO", "event": "auth.token_extraction", "has_token": true}
{"level": "INFO", "event": "auth.mode", "mode": "obo", "auth_type": "pat"}
{"level": "INFO", "event": "auth.user_id_extracted", "user_id": "your-email@example.com"}
```

#### 2.3 Test Workspace Info Endpoint

```bash
# Call /api/user/me/workspace with user token
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
     http://localhost:8000/api/user/me/workspace | jq .
```

**Expected Response**:
```json
{
  "workspace_id": "1234567890123456",
  "workspace_url": "https://your-workspace.cloud.databricks.com",
  "workspace_name": "Your Workspace"
}
```

#### 2.4 Test Unity Catalog Permissions (OBO)

```bash
# List catalogs user can access (OBO enforces permissions)
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
     http://localhost:8000/api/unity-catalog/catalogs | jq .
```

**Expected Response** (user sees only their accessible catalogs):
```json
[
  {
    "name": "main",
    "owner": "workspace-admin",
    "comment": "Main catalog"
  }
]
```

**Validation**: Different users with different permissions should see different catalogs.

#### 2.5 Test Model Serving Endpoints (OBO)

```bash
# List model serving endpoints user can access
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
     http://localhost:8000/api/model-serving/endpoints | jq .
```

**Expected Response**:
```json
[
  {
    "name": "my-model-endpoint",
    "state": "READY",
    "creator": "your-email@example.com"
  }
]
```

---

### Phase 3: Multi-User Data Isolation Testing (Lakebase)

#### 3.1 Test User Preferences (User A)

```bash
# Save preference as User A
curl -X POST \
     -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"preference_key": "theme", "preference_value": "dark"}' \
     http://localhost:8000/api/preferences | jq .
```

**Expected Response**:
```json
{
  "preference_key": "theme",
  "preference_value": "dark",
  "created_at": "2025-10-10T12:00:00Z",
  "updated_at": "2025-10-10T12:00:00Z"
}
```

**Expected Logs**:
```json
{"level": "INFO", "event": "service.database_query", "query_type": "insert", "user_id": "user-a@example.com"}
{"level": "INFO", "event": "lakebase.preference_saved", "user_id": "user-a@example.com", "key": "theme"}
```

#### 3.2 Retrieve Preferences (User A)

```bash
# Get preferences as User A
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
     http://localhost:8000/api/preferences | jq .
```

**Expected Response**:
```json
[
  {
    "preference_key": "theme",
    "preference_value": "dark",
    "created_at": "2025-10-10T12:00:00Z",
    "updated_at": "2025-10-10T12:00:00Z"
  }
]
```

#### 3.3 Test Cross-User Isolation (User B)

```bash
# Get token for different user (User B)
# RECOMMENDED: Use named profiles (cleaner, allows switching without re-auth)

# Option 1: Named profiles (RECOMMENDED)
databricks auth login --profile user-b --host https://your-workspace.cloud.databricks.com
export DATABRICKS_USER_B_TOKEN=$(databricks auth token --profile user-b)

# Option 2: Re-authenticate with default profile (requires logout)
# Only use if named profiles are not available in your CLI version
# databricks auth login --host https://your-workspace.cloud.databricks.com
# export DATABRICKS_USER_B_TOKEN=$(databricks auth token)

# Try to get preferences as User B
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_B_TOKEN" \
     http://localhost:8000/api/preferences | jq .
```

**Why Option 1 is preferred**: Named profiles maintain multiple authenticated sessions simultaneously, allowing easy switching between users without re-authentication. This is essential for efficient multi-user testing.

**Expected Response** (empty array - User B sees no preferences):
```json
[]
```

**Validation**: User B should NOT see User A's preferences (data isolation working).

#### 3.4 Test Database Query Filtering

Check application logs to verify SQL queries include `user_id` filtering:

```bash
# Search logs for database queries
grep "service.database_query" nohup.out | tail -5
```

**Expected Log Entries**:
```json
{"event": "service.database_query", "query_type": "select", "user_id": "user-a@example.com", "correlation_id": "..."}
{"event": "service.database_query", "query_type": "select", "user_id": "user-b@example.com", "correlation_id": "..."}
```

All queries should include `user_id` field.

---

### Phase 4: Error Handling and Retry Logic

#### 4.1 Test Missing User Token (Requires user_id)

```bash
# Try to save preference without user token (should fail)
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"preference_key": "theme", "preference_value": "dark"}' \
     http://localhost:8000/api/preferences
```

**Expected Response** (HTTP 401):
```json
{
  "detail": "User authentication required for this operation",
  "error_code": "AUTH_TOKEN_MISSING"
}
```

#### 4.2 Test Invalid/Expired Token

```bash
# Use invalid token
curl -H "X-Forwarded-Access-Token: invalid-token-12345" \
     http://localhost:8000/api/user/me | jq .
```

**Expected Response** (HTTP 401 after retries):
```json
{
  "detail": "Failed to extract user identity from access token",
  "error_code": "AUTH_USER_IDENTITY_FAILED"
}
```

**Expected Logs** (shows retry attempts per spec.md Edge Cases section):
```json
{"level": "WARNING", "event": "auth.retry_attempt", "attempt": 1, "error_type": "AuthenticationError"}
{"level": "WARNING", "event": "auth.retry_attempt", "attempt": 2, "error_type": "AuthenticationError"}
{"level": "WARNING", "event": "auth.retry_attempt", "attempt": 3, "error_type": "AuthenticationError"}
{"level": "ERROR", "event": "auth.failed", "retry_count": 3}
```

**Validation** (per spec.md FR-018): 
- Should see 3 retry attempts with delays (100ms, 200ms, 400ms)
- Total time should be < 5 seconds

#### 4.3 Test Correlation ID Propagation

```bash
# Send request with custom correlation ID
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
     -H "X-Correlation-ID: 12345678-1234-1234-1234-123456789abc" \
     http://localhost:8000/api/user/me -v 2>&1 | grep -i correlation
```

**Expected Output**:
```
< X-Correlation-ID: 12345678-1234-1234-1234-123456789abc
```

**Expected Logs** (all logs should have same correlation_id):
```json
{"correlation_id": "12345678-1234-1234-1234-123456789abc", "event": "auth.token_extraction"}
{"correlation_id": "12345678-1234-1234-1234-123456789abc", "event": "auth.mode"}
{"correlation_id": "12345678-1234-1234-1234-123456789abc", "event": "auth.user_id_extracted"}
```

---

### Phase 5: Observability Validation

#### 5.1 Check Structured Logging

```bash
# View structured logs (JSON format)
tail -50 nohup.out | jq 'select(.event | startswith("auth."))'
```

**Expected Events** (all should be present):
- `auth.token_extraction`
- `auth.mode`
- `auth.user_id_extracted`
- `auth.fallback_triggered`
- `auth.retry_attempt` (when errors occur)
- `auth.failed` (when retries exhausted)

#### 5.2 Check Metrics Endpoint

```bash
# View Prometheus metrics
curl http://localhost:8000/metrics | grep auth_
```

**Expected Metrics**:
```
auth_requests_total{endpoint="/api/user/me",mode="obo",status="success"} 5.0
auth_requests_total{endpoint="/api/health",mode="service_principal",status="success"} 2.0
auth_retry_total{endpoint="/api/user/me",attempt_number="1"} 1.0
auth_fallback_total{reason="missing_token"} 2.0
auth_overhead_seconds_bucket{mode="obo",le="0.01"} 5.0
```

#### 5.3 Verify Performance Metrics

```bash
# Check that auth overhead is < 10ms
curl http://localhost:8000/metrics | grep "auth_overhead_seconds_bucket{mode=\"obo\",le=\"0.01\"}"
```

**Validation**: Most requests should fall into the `le="0.01"` bucket (< 10ms).

---

### Phase 6: Databricks Apps Deployment Testing

#### 6.1 Deploy to Databricks Apps

```bash
# Validate bundle configuration
databricks bundle validate

# Deploy to dev environment
databricks bundle deploy -t dev
```

**Expected Output**:
```
✓ Bundle configuration is valid
✓ Deploying resources...
✓ Deployment complete
```

#### 6.2 Monitor Deployment Logs

```bash
# Monitor logs for 60 seconds after deployment
python dba_logz.py
```

**Expected Logs**:
```json
{"level": "INFO", "event": "server.start", "port": 8000}
{"level": "INFO", "event": "auth.token_extraction", "has_token": true}
{"level": "INFO", "event": "auth.mode", "mode": "obo", "auth_type": "pat"}
```

**Validation**:
- No error logs
- No "more than one authorization method configured" errors
- All API calls succeed

#### 6.3 Test Deployed App Endpoints

```bash
# Get app URL from deployment output
export APP_URL=$(databricks bundle deploy -t dev 2>&1 | grep "App URL" | awk '{print $NF}')

# Test user info endpoint (token auto-injected by platform)
curl $APP_URL/api/user/me | jq .
```

**Expected Response**:
```json
{
  "user_id": "your-email@example.com",
  "display_name": "Your Name",
  "active": true,
  "workspace_url": "https://your-workspace.cloud.databricks.com"
}
```

**Validation**: Platform automatically injects `X-Forwarded-Access-Token` header.

#### 6.4 Test Multi-User Isolation in Deployed App

1. **User A**: Open app in browser, save preference
2. **User B**: Open app in different browser/incognito, check preferences
3. **Validation**: User B should not see User A's preferences

---

## Success Criteria Checklist

### ✅ Authentication Working
- [ ] Local dev works with service principal fallback
- [ ] Local dev works with real user tokens (OBO)
- [ ] Deployed app uses OBO authentication automatically
- [ ] No "more than one authorization method configured" errors

### ✅ User Identity Extraction
- [ ] `/api/user/me` returns authenticated user's info
- [ ] `user_id` (email) is correctly extracted
- [ ] Missing token returns appropriate error (401)
- [ ] Invalid token triggers retry and eventual 401

### ✅ Permission Enforcement
- [ ] Unity Catalog lists show only user's accessible resources
- [ ] Model serving lists show only user's accessible endpoints
- [ ] Different users see different resources (permission isolation)

### ✅ Multi-User Data Isolation
- [ ] User A's preferences not visible to User B
- [ ] Database queries include `WHERE user_id = ?`
- [ ] Missing user_id returns 401 error
- [ ] Cross-user data access prevented

### ✅ Error Handling
- [ ] Retry logic triggers on authentication failures
- [ ] 3 retry attempts with exponential backoff (100/200/400ms)
- [ ] Total retry time < 5 seconds
- [ ] Rate limiting (429) fails immediately without retry
- [ ] Correlation IDs propagated through all logs

### ✅ Observability
- [ ] Structured logs in JSON format
- [ ] All authentication events logged
- [ ] Correlation IDs in all log entries
- [ ] Metrics endpoint exposes auth metrics
- [ ] Auth overhead < 10ms (check metrics)

### ✅ Deployment
- [ ] Bundle validation passes
- [ ] Deployment succeeds without errors
- [ ] App logs show no authentication errors
- [ ] All endpoints return successful responses

---

## Troubleshooting

### Issue: "more than one authorization method configured"

**Cause**: SDK detecting multiple auth methods  
**Solution**: Verify explicit `auth_type` parameter in all client creations

```python
# Check server/services/*_service.py for:
WorkspaceClient(auth_type="pat")  # For OBO
WorkspaceClient(auth_type="oauth-m2m")  # For service principal
```

### Issue: User seeing other users' data

**Cause**: Missing `WHERE user_id = ?` in database queries  
**Solution**: Check all Lakebase queries in `server/services/lakebase_service.py`

```python
# All user-scoped queries MUST include user_id filter
query = "SELECT * FROM table WHERE user_id = :user_id"
```

### Issue: 401 errors even with valid token

**Cause**: Token extraction failing in middleware  
**Solution**: Check middleware logs for token presence

```bash
grep "auth.token_extraction" nohup.out | tail -10
```

### Issue: Slow authentication (> 10ms overhead)

**Cause**: Unnecessary API calls or blocking operations  
**Solution**: Check metrics and optimize hot paths

```bash
curl http://localhost:8000/metrics | grep auth_overhead_seconds_bucket
```

---

## Next Steps

After completing this quickstart:

1. **Run automated tests**: `pytest tests/contract/ tests/integration/`
2. **Review implementation**: Check code aligns with contracts in `contracts/`
3. **Update documentation**: Ensure `docs/OBO_AUTHENTICATION.md` reflects implementation
4. **Monitor production**: Set up alerts for authentication metrics
5. **Performance tuning**: Optimize if auth overhead > 10ms

---

## Related Documentation

- [Feature Specification](./spec.md)
- [Research Document](./research.md)
- [Data Model](./data-model.md)
- [API Contracts](./contracts/)
- [Implementation Plan](./plan.md)

---

**Validation Status**: ✅ Ready for implementation  
**Estimated Implementation Time**: 3-5 days  
**Risk Level**: Medium (touching authentication layer)
