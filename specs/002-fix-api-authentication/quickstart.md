# Quickstart: OBO Authentication Validation

**Date**: 2025-10-09  
**Feature**: Fix API Authentication and Implement On-Behalf-Of User (OBO)  
**Purpose**: End-to-end validation scenarios for authentication implementation

---

## Prerequisites

### Environment Setup
```bash
# 1. Navigate to repository root
cd /Users/pulkit.chadha/Documents/Projects/databricks-app-template

# 2. Ensure environment variables are configured
# For Databricks Apps deployment:
#   - X-Forwarded-Access-Token header provided by platform automatically
#   - DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET set by platform
#
# For local development:
cat > .env.local << 'EOF'
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_CLIENT_ID=your_service_principal_client_id
DATABRICKS_CLIENT_SECRET=your_service_principal_client_secret
DATABRICKS_USER_TOKEN=your_personal_access_token  # Optional: for local OBO testing
EOF

# 3. Install dependencies
uv sync
cd client && bun install && cd ..

# 4. Run database migrations
uv run alembic upgrade head

# 5. Start the application
./watch.sh
```

### Test Users Setup (for multi-user testing)
- **User A**: Admin user with full Unity Catalog access
- **User B**: Restricted user with limited catalog access
- Both users should have different PAT tokens or be accessed via different browser sessions

---

## Validation Scenarios

### Scenario 1: Basic OBO Authentication - User Information Endpoint

**Objective**: Verify that `/api/user/me` endpoint successfully uses OBO token to return authenticated user information.

**Steps**:
```bash
# 1. In Databricks Apps deployment
# Request includes X-Forwarded-Access-Token header automatically

# Test with curl (simulate platform header)
curl -X GET http://localhost:8000/api/user/me \
  -H "X-Forwarded-Access-Token: ${DATABRICKS_USER_TOKEN}" \
  -H "Content-Type: application/json"

# Expected response:
# {
#   "user_id": "1234567890abcdef",
#   "email": "user@example.com",
#   "username": "user@example.com",
#   "display_name": "Example User",
#   "is_authenticated": true,
#   "auth_method": "obo"
# }
```

**Success Criteria**:
- ✅ Response returns 200 OK
- ✅ Response contains valid user_id, email, username
- ✅ `auth_method` field shows "obo"
- ✅ No SDK authentication error in logs
- ✅ Logs show: `auth_type="pat"` in structured output

**Failure Indicators**:
- ❌ Error: "more than one authorization method configured: oauth and pat"
- ❌ Response returns service principal user instead of actual user
- ❌ Response returns 401 Unauthorized

**Log Validation**:
```bash
# Check logs for authentication details
./dba_logz.py | grep -A 5 "user_token"

# Expected log entry:
# {
#   "timestamp": "2025-10-09T10:00:00Z",
#   "level": "INFO",
#   "message": "User authenticated",
#   "user_id": "1234567890abcdef",
#   "auth_method": "obo",
#   "token_present": true,
#   "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
# }
```

---

### Scenario 2: Unity Catalog Permission Isolation

**Objective**: Verify that different users see only catalogs they have permissions for.

**Steps**:
```bash
# Test with User A (admin - has access to all catalogs)
curl -X GET http://localhost:8000/api/unity-catalog/catalogs \
  -H "X-Forwarded-Access-Token: ${USER_A_TOKEN}" \
  -H "Content-Type: application/json"

# Expected: Returns all catalogs (main, dev, prod, etc.)
# {
#   "catalogs": [
#     {"name": "main", "owner": "admin@example.com", ...},
#     {"name": "dev", "owner": "admin@example.com", ...},
#     {"name": "prod", "owner": "admin@example.com", ...}
#   ],
#   "total_count": 3
# }

# Test with User B (restricted - has access to dev only)
curl -X GET http://localhost:8000/api/unity-catalog/catalogs \
  -H "X-Forwarded-Access-Token: ${USER_B_TOKEN}" \
  -H "Content-Type: application/json"

# Expected: Returns only dev catalog
# {
#   "catalogs": [
#     {"name": "dev", "owner": "user@example.com", ...}
#   ],
#   "total_count": 1
# }
```

**Success Criteria**:
- ✅ User A sees all catalogs (main, dev, prod)
- ✅ User B sees only dev catalog
- ✅ Different responses for different users (permission isolation verified)
- ✅ No SDK authentication errors
- ✅ Logs show different user_id for each request

**Failure Indicators**:
- ❌ Both users see same catalogs (permission isolation failed)
- ❌ Service principal user shown instead of actual user
- ❌ Authorization errors in logs

**Log Validation**:
```bash
# Check that different user_ids are logged
./dba_logz.py | grep "catalog_access" | jq '.user_id'

# Expected: Two different user_ids
```

---

### Scenario 3: Model Serving Endpoint Access with OBO

**Objective**: Verify that model serving endpoint listing uses user credentials and respects permissions.

**Steps**:
```bash
# Test listing model endpoints
curl -X GET http://localhost:8000/api/model-serving/endpoints \
  -H "X-Forwarded-Access-Token: ${DATABRICKS_USER_TOKEN}" \
  -H "Content-Type: application/json"

# Expected response:
# {
#   "endpoints": [
#     {
#       "name": "llama-2-70b-chat",
#       "state": "READY",
#       "creator": "user@example.com",
#       ...
#     }
#   ],
#   "total_count": 1,
#   "limit": 50,
#   "offset": 0
# }
```

**Success Criteria**:
- ✅ Response returns 200 OK
- ✅ Only endpoints the user has access to are returned
- ✅ No SDK authentication errors
- ✅ Logs show `auth_type="pat"` for model serving API calls

**Failure Indicators**:
- ❌ Error: "more than one authorization method configured"
- ❌ Returns all endpoints regardless of user permissions
- ❌ Response returns 403 Forbidden (service principal vs. user auth confusion)

---

### Scenario 4: Lakebase Service Principal Authentication

**Objective**: Verify that Lakebase connections use service principal (NOT OBO token) and user_id filtering works.

**Steps**:
```bash
# Test user preferences endpoint (Lakebase operation)
curl -X GET http://localhost:8000/api/preferences \
  -H "X-Forwarded-Access-Token: ${USER_A_TOKEN}" \
  -H "Content-Type: application/json"

# Expected: Returns preferences for User A only
# {
#   "preferences": [
#     {"key": "theme", "value": "dark", "user_id": "user_a_id"}
#   ]
# }

# Test with User B
curl -X GET http://localhost:8000/api/preferences \
  -H "X-Forwarded-Access-Token: ${USER_B_TOKEN}" \
  -H "Content-Type: application/json"

# Expected: Returns preferences for User B only (different data)
# {
#   "preferences": [
#     {"key": "theme", "value": "light", "user_id": "user_b_id"}
#   ]
# }

# Verify preferences are isolated
curl -X POST http://localhost:8000/api/preferences \
  -H "X-Forwarded-Access-Token: ${USER_A_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"key": "language", "value": "en"}'

# User B should NOT see User A's new preference
curl -X GET http://localhost:8000/api/preferences \
  -H "X-Forwarded-Access-Token: ${USER_B_TOKEN}" \
  -H "Content-Type: application/json"

# Expected: User B's response does NOT include language preference
```

**Success Criteria**:
- ✅ User A and User B see different preferences (data isolation)
- ✅ Database connection uses service principal (check logs)
- ✅ All queries include WHERE user_id = ? clause (check SQL logs)
- ✅ No user OBO token passed to Lakebase connection
- ✅ user_id field present in all database records

**Failure Indicators**:
- ❌ User A sees User B's preferences (data isolation failed)
- ❌ Database connection attempts to use OBO token
- ❌ Missing user_id in database queries

**Log Validation**:
```bash
# Check database connection logs
./dba_logz.py | grep "database_connection" | jq '.'

# Expected log entry:
# {
#   "message": "Database connection established",
#   "auth_method": "service_principal",
#   "connection_type": "lakebase",
#   "user_id": "1234567890abcdef"  # User context for filtering, not DB auth
# }
```

---

### Scenario 5: Local Development Fallback (No OBO Token)

**Objective**: Verify that application works in local development without X-Forwarded-Access-Token header.

**Steps**:
```bash
# Unset user token to simulate local development
unset DATABRICKS_USER_TOKEN

# Test endpoint without token header
curl -X GET http://localhost:8000/api/user/me \
  -H "Content-Type: application/json"

# Expected response (service principal fallback):
# {
#   "user_id": "service_principal_id",
#   "username": "service_principal@databricks.com",
#   "is_authenticated": true,
#   "auth_method": "service_principal"
# }
```

**Success Criteria**:
- ✅ Response returns 200 OK (no 401 error)
- ✅ `auth_method` field shows "service_principal"
- ✅ Logs clearly indicate fallback mode
- ✅ Application remains functional for development

**Failure Indicators**:
- ❌ Response returns 401 Unauthorized
- ❌ SDK authentication errors
- ❌ Application crashes or hangs

**Log Validation**:
```bash
# Check fallback logs
./dba_logz.py | grep "auth_fallback" | jq '.'

# Expected log entry:
# {
#   "level": "WARNING",
#   "message": "No user token found, using service principal",
#   "auth_method": "service_principal",
#   "environment": "local_development"
# }
```

---

### Scenario 6: Authentication Retry with Exponential Backoff

**Objective**: Verify that transient authentication failures trigger retry with exponential backoff.

**Steps**:
```bash
# This scenario requires simulating transient failures
# Can be tested with mock responses or network disruption

# Monitor logs during authentication attempts
./dba_logz.py | grep "auth_retry" | jq '.'

# Expected log sequence (if retry occurs):
# {
#   "level": "WARNING",
#   "message": "Authentication failed, retrying",
#   "attempt": 1,
#   "delay_ms": 100,
#   "correlation_id": "..."
# }
# {
#   "level": "WARNING",
#   "message": "Authentication failed, retrying",
#   "attempt": 2,
#   "delay_ms": 200,
#   "correlation_id": "..."
# }
# {
#   "level": "INFO",
#   "message": "Authentication succeeded",
#   "attempt": 3,
#   "total_duration_ms": 450,
#   "correlation_id": "..."
# }
```

**Success Criteria**:
- ✅ Retry attempts logged with attempt number and delay
- ✅ Exponential backoff delays: 100ms, 200ms, 400ms
- ✅ Total timeout does not exceed 5 seconds
- ✅ Successful recovery after transient failure
- ✅ HTTP 429 (rate limit) triggers immediate failure without retries

**Failure Indicators**:
- ❌ No retry attempts on transient failures
- ❌ Linear backoff instead of exponential
- ❌ Timeout exceeds 5 seconds
- ❌ Retry occurs on HTTP 429 (should fail immediately)

---

### Scenario 7: Multi-Tab User Session (Stateless Auth)

**Objective**: Verify that multiple browser tabs work independently with stateless authentication.

**Steps**:
1. Open the app in Browser Tab 1, authenticate as User A
2. Open the app in Browser Tab 2, authenticate as User A (same user)
3. In Tab 1, list Unity Catalog catalogs
4. In Tab 2, list Model Serving endpoints
5. Close Tab 1
6. In Tab 2, list Unity Catalog catalogs again

**Success Criteria**:
- ✅ Tab 2 continues to work after Tab 1 is closed (stateless)
- ✅ Both tabs operate independently
- ✅ No shared state or token caching between tabs
- ✅ Each request extracts token fresh from headers

**Failure Indicators**:
- ❌ Tab 2 fails after Tab 1 is closed (state sharing)
- ❌ Authentication errors when multiple tabs open
- ❌ Token caching causes stale data

---

### Scenario 8: Token Expiration and Platform Refresh

**Objective**: Verify that the platform's token refresh is transparent to the application.

**Note**: This scenario validates stateless authentication from a token lifecycle perspective, complementing Scenario 7's multi-tab validation. Both scenarios confirm no token caching (NFR-005) but focus on different aspects: Scenario 7 tests spatial independence (multiple tabs), while Scenario 8 tests temporal independence (token refresh over time).

**Steps**:
```bash
# 1. Make initial request with valid token
curl -X GET http://localhost:8000/api/user/me \
  -H "X-Forwarded-Access-Token: ${VALID_TOKEN}" \
  -H "Content-Type: application/json"

# Expected: Success

# 2. Wait for token to approach expiration (platform will refresh)
# Platform automatically updates X-Forwarded-Access-Token header

# 3. Make another request (platform provides refreshed token)
curl -X GET http://localhost:8000/api/user/me \
  -H "X-Forwarded-Access-Token: ${REFRESHED_TOKEN}" \
  -H "Content-Type: application/json"

# Expected: Success with no application-level token management
```

**Success Criteria**:
- ✅ Application accepts both old and new tokens seamlessly
- ✅ No token caching in application (fresh extraction each request)
- ✅ Platform handles refresh transparently
- ✅ No user-visible errors during token refresh

**Failure Indicators**:
- ❌ Application caches old token, rejects new token
- ❌ Authentication errors during token refresh window
- ❌ Application attempts to manage token lifecycle

---

### Scenario 9: Rate Limiting Compliance (HTTP 429)

**Objective**: Verify that the application respects platform rate limits and fails immediately on HTTP 429.

**Steps**:
```bash
# Simulate rate limit response (requires mock or actual rate limiting)
# Make rapid requests to trigger rate limiting

# Monitor logs for rate limit handling
./dba_logz.py | grep "rate_limit" | jq '.'

# Expected log entry:
# {
#   "level": "ERROR",
#   "message": "Rate limit exceeded, failing request",
#   "status_code": 429,
#   "retry_attempts": 0,
#   "correlation_id": "..."
# }
```

**Success Criteria**:
- ✅ HTTP 429 response triggers immediate failure (no retries)
- ✅ Error logged with status_code=429
- ✅ Client receives HTTP 429 response
- ✅ No exponential backoff retry on rate limit

**Failure Indicators**:
- ❌ Retry attempts on HTTP 429 (violates platform limits)
- ❌ Infinite retry loop
- ❌ Rate limit not detected

---

### Scenario 10: Concurrent Request Retry Independence

**Objective**: Verify that concurrent API requests from the same user each retry independently without coordination.

**Steps**:
```bash
# Make 5 concurrent requests from same user
for i in {1..5}; do
  curl -X GET http://localhost:8000/api/unity-catalog/catalogs \
    -H "X-Forwarded-Access-Token: ${DATABRICKS_USER_TOKEN}" \
    -H "X-Correlation-ID: $(uuidgen)" \
    -H "Content-Type: application/json" &
done
wait

# Check logs to see if requests were handled independently
./dba_logz.py | grep "correlation_id" | jq -c '{correlation_id, message, attempt}' | tail -20

# If auth temporarily fails, check retry patterns
./dba_logz.py | grep "auth_retry" | jq -c '{correlation_id, attempt, delay_ms}'
```

**Expected Behavior**:
```json
// Request 1 succeeds immediately
{"correlation_id": "550e8400-e29b-41d4-a716-446655440001", "message": "Auth succeeded", "attempt": 1}

// Request 2 retries independently
{"correlation_id": "550e8400-e29b-41d4-a716-446655440002", "message": "Auth failed, retrying", "attempt": 1}
{"correlation_id": "550e8400-e29b-41d4-a716-446655440002", "message": "Auth succeeded", "attempt": 2}

// Request 3 succeeds immediately (while Request 2 was retrying)
{"correlation_id": "550e8400-e29b-41d4-a716-446655440003", "message": "Auth succeeded", "attempt": 1}
```

**Success Criteria**:
- ✅ Each request has unique correlation_id
- ✅ If retries occur, each request retries independently (different correlation_ids in logs)
- ✅ No shared retry state or coordination between requests
- ✅ Some requests may succeed while others retry (stateless pattern)
- ✅ Total retry count can be N requests × 3 attempts (independent retries)
- ✅ Each request respects 5s timeout independently

**Failure Indicators**:
- ❌ Retry coordination or shared state between requests
- ❌ All requests wait for first request's retry to complete
- ❌ Requests share retry counters or backoff timers
- ❌ Second request doesn't start until first completes

**Log Validation**:
```bash
# Verify independent retry behavior
./dba_logz.py | grep "auth" | jq '{correlation_id, message, attempt, timestamp}' > auth_logs.json

# Check for overlapping timestamps (parallel execution)
# Expected: Some requests should have overlapping timestamps, indicating parallel processing

# Count unique correlation IDs
./dba_logz.py | grep "auth" | jq -r '.correlation_id' | sort | uniq | wc -l
# Expected: 5 (one per concurrent request)
```

**Rationale**:
- FR-025 requires independent retry logic per request
- NFR-005 requires no token caching (enables stateless pattern)
- Validates that multi-tab scenarios (Scenario 7) work correctly
- Ensures thread-safe authentication without locks or shared state

---

## Automated Test Suite

### Contract Tests (TDD - Run BEFORE Implementation)
```bash
# Contract tests validate API endpoints match OpenAPI contracts
# These tests MUST fail initially (no implementation yet)

cd /Users/pulkit.chadha/Documents/Projects/databricks-app-template

# Run contract tests
uv run pytest tests/contract/test_user_contract.py -v
uv run pytest tests/contract/test_model_serving_contract.py -v
uv run pytest tests/contract/test_unity_catalog_contract.py -v

# Expected: All tests FAIL (implementation not done yet)
# After implementation: All tests PASS
```

### Integration Tests (Multi-User Isolation)
```bash
# Run multi-user isolation tests
uv run pytest tests/integration/test_multi_user_isolation.py -v

# Test coverage:
# - Two users with different permissions
# - Verify data isolation in Lakebase
# - Verify Unity Catalog permission enforcement
# - Verify audit logs show correct user_id
```

### Unit Tests (Auth Utilities)
```bash
# Run auth utility unit tests
uv run pytest tests/unit/test_auth.py -v

# Test coverage:
# - Token extraction from headers (present, absent, malformed)
# - Exponential backoff logic (delays, timeout)
# - User_id validation in service constructors
# - SDK auth_type configuration
```

---

## Deployment Validation

### Post-Deployment Checklist (Databricks Apps)
```bash
# 1. Deploy to Databricks Apps
databricks bundle validate
databricks bundle deploy --target prod

# 2. Monitor logs for 60 seconds
./dba_logz.py --duration 60

# Expected logs:
# - Uvicorn startup messages
# - No Python exceptions
# - No "more than one authorization method configured" errors

# 3. Test core endpoints
./dba_client.py test-user-me
./dba_client.py test-unity-catalog
./dba_client.py test-model-serving

# Expected: All endpoints return 200 OK

# 4. Verify observability metrics
# Check metrics endpoint or monitoring dashboard
curl http://localhost:8000/metrics

# Expected metrics:
# - auth_success_total (counter)
# - auth_failure_total (counter)
# - auth_retry_total (counter)
# - auth_latency_ms (histogram with P95, P99)
# - per_user_request_count (counter with user_id label)
```

---

## Success Validation Summary

✅ **Feature is successfully implemented when ALL scenarios pass:**

1. ✅ Scenario 1: User information endpoint returns authenticated user (not service principal)
2. ✅ Scenario 2: Unity Catalog shows different data for different users
3. ✅ Scenario 3: Model serving endpoints respect user permissions
4. ✅ Scenario 4: Lakebase uses service principal but filters by user_id
5. ✅ Scenario 5: Local development works without OBO token
6. ✅ Scenario 6: Authentication retries with exponential backoff
7. ✅ Scenario 7: Multi-tab sessions work independently (stateless)
8. ✅ Scenario 8: Token refresh is transparent
9. ✅ Scenario 9: Rate limiting compliance (HTTP 429 immediate failure)
10. ✅ Scenario 10: Concurrent requests retry independently (no coordination)

✅ **All contract tests pass** (after implementation)
✅ **All integration tests pass** (multi-user isolation verified)
✅ **All unit tests pass** (auth utilities validated)
✅ **Deployment validation passes** (no errors in logs, metrics healthy)
✅ **Zero authentication errors** in Databricks Apps logs

---

**Next Steps**: Proceed to Phase 2 (/tasks command) to generate implementation tasks from this design.

