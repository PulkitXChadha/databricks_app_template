# Quickstart Guide: OBO-Only Authentication Testing

**Feature**: 003-obo-only-support  
**Purpose**: Manual testing guide for validating OBO-only authentication implementation  
**Estimated Time**: 30-45 minutes

## Prerequisites

- Databricks CLI installed and authenticated
- Access to Databricks workspace
- Application deployed or running locally
- Two test user accounts with different permissions (for multi-user testing)

---

## Phase 1: Local Development Setup (10 minutes)

### 1.1 Install and Configure Databricks CLI

```bash
# Install Databricks CLI (if not already installed)
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh

# Authenticate with your workspace
databricks auth login --host https://your-workspace.cloud.databricks.com

# Verify authentication works
databricks auth token
```

**Expected Outcome**: Token printed to console (dapi...).

### 1.2 Obtain User Access Token

```bash
# Export user token for local testing
export DATABRICKS_USER_TOKEN=$(databricks auth token)

# Verify token is set
echo "Token starts with: ${DATABRICKS_USER_TOKEN:0:20}..."
```

**Expected Outcome**: Token starts with `dapi` or similar Databricks token prefix.

### 1.3 Start Local Development Server

```bash
# Navigate to project root
cd /path/to/databricks-app-template

# Start development server
./watch.sh

# Wait for server to start (check logs for "Uvicorn running")
tail -f nohup.out | grep -i "uvicorn"
```

**Expected Outcome**: Server running on http://localhost:8000.

---

## Phase 2: Public Health Endpoint Testing (5 minutes)

### 2.1 Test Health Endpoint Without Authentication

```bash
# Health endpoint should be public (no authentication required)
curl http://localhost:8000/health | jq .
```

**Expected Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-14T10:30:00.000Z",
  "version": "1.0.0"
}
```

**Success Criteria**:
- ✅ HTTP 200 status
- ✅ Response contains "status" field
- ✅ No authentication error
- ✅ Fast response (<100ms)

### 2.2 Verify Health Endpoint Ignores Authentication Headers

```bash
# Health endpoint should work even with authentication headers present
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
     http://localhost:8000/health | jq .
```

**Expected Response**: Same as 2.1 (authentication header ignored).

**Success Criteria**:
- ✅ HTTP 200 status
- ✅ Identical response regardless of headers

---

## Phase 3: Authenticated Metrics Endpoint Testing (5 minutes)

### 3.1 Test Metrics Without Authentication (Should Fail)

```bash
# Metrics endpoint should require authentication
curl http://localhost:8000/metrics
```

**Expected Response**:
```json
{
  "error_code": "AUTH_MISSING",
  "message": "User authentication required. Please provide a valid user access token."
}
```

**Success Criteria**:
- ✅ HTTP 401 status
- ✅ error_code is "AUTH_MISSING"
- ✅ Structured error response

### 3.2 Test Metrics With Valid Authentication (Should Succeed)

```bash
# Metrics endpoint should work with user token
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
     http://localhost:8000/metrics
```

**Expected Response**: Prometheus metrics in plain text format.

**Success Criteria**:
- ✅ HTTP 200 status
- ✅ Content-Type: text/plain; version=0.0.4
- ✅ Contains metrics like `auth_requests_total`, `request_duration_seconds`
- ✅ No `auth_fallback_total` metric (removed)

---

## Phase 4: OBO-Only API Testing (10 minutes)

### 4.1 Test User Identity Endpoint With Authentication

```bash
# User identity should require authentication
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

**Success Criteria**:
- ✅ HTTP 200 status
- ✅ user_id matches your Databricks account email
- ✅ display_name is present

### 4.2 Test User Identity Without Authentication (Should Fail)

```bash
# Should return 401 when token is missing
curl http://localhost:8000/api/user/me
```

**Expected Response**:
```json
{
  "error_code": "AUTH_MISSING",
  "message": "User authentication required. Please provide a valid user access token."
}
```

**Success Criteria**:
- ✅ HTTP 401 status
- ✅ error_code is "AUTH_MISSING"
- ✅ No fallback to service principal (no valid response)

### 4.3 Test Unity Catalog Operations With Authentication

```bash
# List catalogs with user's permissions
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
     http://localhost:8000/api/unity-catalog/catalogs | jq .
```

**Expected Response**:
```json
[
  "main",
  "hive_metastore",
  "your_catalog"
]
```

**Success Criteria**:
- ✅ HTTP 200 status
- ✅ Only catalogs you have permission to access
- ✅ Different users see different catalogs (test with 2+ users)

### 4.4 Test Unity Catalog Without Authentication (Should Fail)

```bash
# Should fail without authentication
curl http://localhost:8000/api/unity-catalog/catalogs
```

**Expected Response**: HTTP 401 with AUTH_MISSING error.

**Success Criteria**:
- ✅ HTTP 401 status
- ✅ No fallback behavior
- ✅ Clear error message

---

## Phase 5: Multi-User Permission Validation (10 minutes)

### 5.1 Set Up Second Test User

```bash
# Authenticate as second user
databricks auth login --profile test-user-b \
    --host https://your-workspace.cloud.databricks.com

# Get second user's token
export USER_B_TOKEN=$(databricks auth token --profile test-user-b)
```

### 5.2 Compare User Permissions

```bash
# Test User A (your default account)
echo "User A Catalogs:"
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
     http://localhost:8000/api/unity-catalog/catalogs | jq .

# Test User B (limited permissions)
echo "User B Catalogs:"
curl -H "X-Forwarded-Access-Token: $USER_B_TOKEN" \
     http://localhost:8000/api/unity-catalog/catalogs | jq .
```

**Expected Outcome**: Different users see different catalogs based on Unity Catalog permissions.

**Success Criteria**:
- ✅ User A sees catalogs they have access to
- ✅ User B sees different/fewer catalogs
- ✅ No user sees data they don't have permissions for
- ✅ Permissions enforced by Databricks platform (not application logic)

### 5.3 Test Lakebase Data Isolation

```bash
# User A saves preference
curl -X POST \
     -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"preference_key": "theme", "preference_value": "dark"}' \
     http://localhost:8000/api/preferences

# User B tries to read preferences
curl -H "X-Forwarded-Access-Token: $USER_B_TOKEN" \
     http://localhost:8000/api/preferences | jq .
```

**Expected Outcome**: User B's response is empty array `[]` (cannot see User A's data).

**Success Criteria**:
- ✅ User A can save preferences
- ✅ User B cannot see User A's preferences
- ✅ user_id filtering enforced in database queries

---

## Phase 6: Error Handling Validation (5 minutes)

### 6.1 Test Invalid Token

```bash
# Test with malformed token
curl -H "X-Forwarded-Access-Token: invalid-token-12345" \
     http://localhost:8000/api/user/me
```

**Expected Response**:
```json
{
  "error_code": "AUTH_INVALID",
  "message": "The provided access token is invalid or malformed.",
  "detail": "Token validation failed"
}
```

**Success Criteria**:
- ✅ HTTP 401 status
- ✅ error_code is "AUTH_INVALID"
- ✅ Helpful error message

### 6.2 Test Empty Token

```bash
# Test with empty token header
curl -H "X-Forwarded-Access-Token: " \
     http://localhost:8000/api/user/me
```

**Expected Response**: Same as missing token (AUTH_MISSING).

**Success Criteria**:
- ✅ HTTP 401 status
- ✅ error_code is "AUTH_MISSING"
- ✅ Treats empty token same as missing token

### 6.3 Monitor Logs for Authentication Events

```bash
# Check logs for authentication events
tail -100 nohup.out | jq 'select(.event | startswith("auth."))'
```

**Expected Log Events**:
```json
{"event": "auth.token_extraction", "has_token": true, "endpoint": "/api/user/me"}
{"event": "auth.mode", "mode": "obo", "auth_type": "pat"}
{"event": "auth.user_id_extracted", "user_id": "your-email@example.com"}
```

**Success Criteria**:
- ✅ Log events show "mode": "obo" only (never "service_principal")
- ✅ No "auth.fallback_triggered" events
- ✅ All authentication events have correlation IDs

---

## Success Checklist

### Authentication Behavior
- [ ] `/health` endpoint is public (no authentication required)
- [ ] `/metrics` endpoint requires authentication
- [ ] All other API endpoints require user token
- [ ] Missing token returns HTTP 401 with AUTH_MISSING
- [ ] Invalid token returns HTTP 401 with AUTH_INVALID
- [ ] No service principal fallback behavior

### Service Initialization
- [ ] UnityCatalogService requires user_token (raises ValueError if missing)
- [ ] ModelServingService requires user_token (raises ValueError if missing)
- [ ] UserService requires user_token (raises ValueError if missing)
- [ ] LakebaseService does NOT require user_token (hybrid approach)

### Permission Enforcement
- [ ] Different users see different Unity Catalog resources
- [ ] Lakebase queries enforce user_id filtering
- [ ] Users cannot access other users' data
- [ ] Unity Catalog permissions enforced by platform

### Observability
- [ ] Logs show "auth.mode": "obo" only
- [ ] No "auth.fallback_triggered" events in logs
- [ ] Correlation IDs present in all logs
- [ ] Metrics do not include "auth_fallback_total" counter

### Error Responses
- [ ] All 401 errors have structured format
- [ ] error_code field is present and correct
- [ ] message field is user-friendly
- [ ] detail field provides technical context

---

## Troubleshooting

### Issue: "Databricks CLI not found"
**Solution**: Install Databricks CLI:
```bash
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
```

### Issue: "Token authentication failed"
**Solution**: Re-authenticate:
```bash
databricks auth login --host https://your-workspace.cloud.databricks.com
```

### Issue: "Cannot connect to localhost:8000"
**Solution**: Verify development server is running:
```bash
ps aux | grep uvicorn
# If not running: ./watch.sh
```

### Issue: "Still seeing service principal fallback in logs"
**Solution**: Verify implementation removed fallback logic:
```bash
# Search for removed patterns
grep -r "_create_service_principal_config" server/services/
# Should return no results
```

---

## Next Steps

After completing this quickstart:
1. ✅ All success criteria met → Ready for deployment
2. ⚠️ Issues found → Review implementation against contracts
3. 📝 Update documentation based on testing discoveries
4. 🚀 Deploy to dev environment and repeat validation

**Estimated Total Time**: 30-45 minutes for complete validation.

