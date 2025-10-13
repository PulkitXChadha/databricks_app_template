# Local Development Guide

This guide covers local development setup and testing for the Databricks App Template, including On-Behalf-Of-User (OBO) authentication testing.

## Prerequisites

- Python 3.11+ (managed by uv)
- Node.js 18+
- Databricks CLI authenticated (`databricks auth login`)
- Service principal credentials (for local testing)

## Environment Setup

### 1. Required Environment Variables

Create a `.env.local` file in the repository root:

```bash
# Databricks workspace
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com

# Service principal (for local dev)
DATABRICKS_CLIENT_ID=your-service-principal-client-id
DATABRICKS_CLIENT_SECRET=your-service-principal-client-secret

# SQL Warehouse (for Unity Catalog queries)
DATABRICKS_WAREHOUSE_ID=your-warehouse-id

# Optional: Unity Catalog defaults
DATABRICKS_CATALOG=main
DATABRICKS_SCHEMA=samples
```

**Note**: Lakebase (database) environment variables are automatically set by Databricks Apps platform. For local development without Lakebase, database-dependent features will be skipped.

### 2. Install Dependencies

```bash
# Install Python dependencies
uv sync

# Install frontend dependencies
cd client && bun install && cd ..
```

### 3. Start Development Server

```bash
# Start both backend and frontend with hot reloading
./watch.sh

# Or start separately:
# Terminal 1 - Backend
uv run uvicorn server.app:app --reload --port 8000

# Terminal 2 - Frontend
cd client && bun run dev
```

## Authentication Modes

The application supports two authentication modes:

### Mode 1: Service Principal (Automatic Fallback)

When no user token is provided, the application automatically falls back to service principal authentication. This is useful for:
- Health checks
- System operations
- Local development without user context

**Test it**:
```bash
# No authentication header = service principal mode
curl http://localhost:8000/api/health
curl http://localhost:8000/api/auth/status | jq .
# Returns: {"authenticated": true, "auth_mode": "service_principal", ...}
```

### Mode 2: On-Behalf-Of-User (OBO) Authentication

When a user token is provided via `X-Forwarded-Access-Token` header, the application uses OBO authentication to respect user-level permissions.

## Testing OBO Authentication Locally

### Step 1: Get Your User Access Token

```bash
# Fetch your user access token from Databricks CLI
export DATABRICKS_USER_TOKEN=$(databricks auth token)

# Verify token is set
echo ${DATABRICKS_USER_TOKEN:0:20}...
# Should output: eyJhbGciOiJSUzI1NiIs...
```

### Step 2: Test User Identity Endpoint

```bash
# Call /api/user/me with your user token
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

### Step 3: Test Workspace Information

```bash
# Get workspace details
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

### Step 4: Test Unity Catalog Permissions

```bash
# List catalogs (respects your permissions)
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
     http://localhost:8000/api/unity-catalog/catalogs | jq .

# List schemas in a catalog
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
     http://localhost:8000/api/unity-catalog/catalogs/main/schemas | jq .

# List tables in a schema
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
     http://localhost:8000/api/unity-catalog/catalogs/main/schemas/default/tables | jq .
```

**Note**: You'll only see resources you have permission to access. Different users will see different results.

### Step 5: Test Model Serving Endpoints

```bash
# List model serving endpoints (respects your permissions)
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
     http://localhost:8000/api/model-serving/endpoints | jq .
```

## Multi-User Testing

To test data isolation between users, you need tokens from two different Databricks users:

### Option 1: Named Profiles (Recommended)

```bash
# Authenticate User A
databricks auth login --profile user-a --host https://your-workspace.cloud.databricks.com
export DATABRICKS_USER_A_TOKEN=$(databricks auth token --profile user-a)

# Authenticate User B
databricks auth login --profile user-b --host https://your-workspace.cloud.databricks.com
export DATABRICKS_USER_B_TOKEN=$(databricks auth token --profile user-b)

# Test User A
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_A_TOKEN" \
     http://localhost:8000/api/user/me | jq '.user_id'

# Test User B
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_B_TOKEN" \
     http://localhost:8000/api/user/me | jq '.user_id'
```

**Verify Data Isolation**: User A and User B should see different catalogs/endpoints based on their permissions.

### Option 2: Re-authenticate (If Profiles Not Supported)

```bash
# Authenticate as User A
databricks auth login --host https://your-workspace.cloud.databricks.com
export DATABRICKS_USER_A_TOKEN=$(databricks auth token)

# Save User A's preferences
curl -X POST \
     -H "X-Forwarded-Access-Token: $DATABRICKS_USER_A_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"preference_key": "theme", "preference_value": "dark"}' \
     http://localhost:8000/api/preferences

# Re-authenticate as User B
databricks auth login --host https://your-workspace.cloud.databricks.com  # Login as different user
export DATABRICKS_USER_B_TOKEN=$(databricks auth token)

# Verify User B cannot see User A's preferences
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_B_TOKEN" \
     http://localhost:8000/api/preferences | jq .
# Should return empty array []
```

## Monitoring Logs

### View Structured Logs

```bash
# View all logs
tail -f nohup.out

# View only authentication events
tail -f nohup.out | grep -E "(auth\.|ERROR)"

# View authentication events in JSON format
tail -f nohup.out | jq 'select(.event | startswith("auth."))'
```

### Expected Log Events

- `auth.token_extraction` - Token extracted from header
- `auth.mode` - Authentication mode selected (OBO or service principal)
- `auth.user_id_extracted` - User identity retrieved
- `auth.fallback_triggered` - Service principal fallback activated
- `auth.retry_attempt` - Authentication retry triggered
- `auth.failed` - Authentication failure after retries

## Testing Error Scenarios

### Invalid Token

```bash
# Use invalid token (should return 401 after retries)
curl -H "X-Forwarded-Access-Token: invalid-token-12345" \
     http://localhost:8000/api/user/me
```

**Expected**: HTTP 401 with error message after 3 retry attempts (~700ms total)

### Missing Token (Service Principal Fallback)

```bash
# No token = automatic service principal fallback
curl http://localhost:8000/api/user/me
```

**Expected**: Returns service principal's user info (fallback mode)

### Missing User Identity for Database Operations

```bash
# Try to access user preferences without token (should return 401)
curl http://localhost:8000/api/preferences
```

**Expected**: HTTP 401 "User authentication required"

## Observability

### View Metrics

```bash
# View Prometheus metrics
curl http://localhost:8000/metrics | grep auth_

# View authentication request counts
curl http://localhost:8000/metrics | grep "auth_requests_total"

# View authentication overhead (should be < 10ms)
curl http://localhost:8000/metrics | grep "auth_overhead_seconds"
```

### View Authentication Status

```bash
# Check current authentication status
curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
     http://localhost:8000/api/auth/status | jq .
```

## Troubleshooting

### Issue: "more than one authorization method configured"

**Cause**: SDK detecting multiple authentication methods (OAuth + PAT)

**Solution**: Verify all WorkspaceClient creations use explicit `auth_type` parameter:
- `auth_type="pat"` for OBO (user token)
- `auth_type="oauth-m2m"` for service principal

### Issue: 401 errors even with valid token

**Cause**: Token extraction may be failing

**Solution**: Check logs for token extraction:
```bash
grep "auth.token_extraction" nohup.out | tail -5
```

### Issue: Users seeing other users' data

**Cause**: Missing `WHERE user_id = ?` in database queries

**Solution**: Verify all user-scoped queries in `server/services/lakebase_service.py` include user_id filtering

### Issue: Slow authentication (> 10ms overhead)

**Cause**: Blocking operations in auth flow

**Solution**: Check metrics and optimize:
```bash
curl http://localhost:8000/metrics | grep "auth_overhead_seconds_bucket"
```

## Running Tests

This project uses pytest with performance optimizations for fast test execution.

### Quick Test Commands

```bash
# Fast feedback during development (< 10 seconds)
# Runs contract tests in parallel, skipping slow tests
pytest tests/contract/ -n auto -m "not slow"

# Full test suite with parallel execution (< 2 minutes)
pytest -n auto

# Run specific test file
pytest tests/contract/test_user_service_contract.py -v

# Run tests by marker
pytest -m contract  # Only contract tests
pytest -m integration  # Only integration tests
pytest -m "not slow"  # Skip slow tests (35+ second timeouts)
```

### Test Organization

Tests are organized into categories with markers:

- **Contract Tests** (`-m contract`): Fast unit tests validating service contracts
- **Integration Tests** (`-m integration`): End-to-end tests with mocked dependencies
- **Slow Tests** (`-m slow`): Tests with deliberate delays (e.g., timeout testing)

### Performance Optimizations

The test suite includes several optimizations:

1. **Parallel Execution**: Uses `pytest-xdist` to run tests in parallel
   ```bash
   pytest -n auto  # Use all CPU cores
   pytest -n 4     # Use 4 workers
   ```

2. **Test Markers**: Skip slow tests during development
   ```bash
   pytest -m "not slow"  # Skip 35+ second timeout tests
   ```

3. **Shared Fixtures**: Reusable fixtures in `tests/conftest.py` reduce setup time

4. **TestClient**: Integration tests use FastAPI TestClient (no network calls)

5. **Timeout Protection**: Individual test timeout of 30s (configurable per test)

### Development Workflow

```bash
# 1. Fast feedback loop (run after each change)
pytest tests/contract/ -n auto -m "not slow" -x

# 2. Pre-commit validation (before committing)
pytest tests/contract/ tests/integration/ -n auto -m "not slow"

# 3. Full validation (before PR)
pytest -n auto -v

# 4. With coverage report
pytest --cov=server --cov-report=html -n auto
```

### Test Performance Tips

- **Parallel execution** provides 4-8x speedup on multi-core systems
- **Skipping slow tests** saves 70+ seconds per run
- **TestClient** is 10-100x faster than real HTTP requests
- **Shared fixtures** reduce mock setup time by 20-30%

### Debugging Test Failures

```bash
# Run with verbose output and stop on first failure
pytest -vv -x

# Show print statements and logs
pytest -s

# Run specific test with debugging
pytest tests/contract/test_user_service_contract.py::TestUserServiceAuthentication::test_obo_mode -vv -s

# Disable parallel execution for debugging
pytest tests/contract/ -v  # Without -n auto
```

### Contract Tests

```bash
# Run all contract tests (fast, parallelized)
pytest tests/contract/ -n auto

# Run specific service contract tests
pytest tests/contract/test_lakebase_service_contract.py -v
pytest tests/contract/test_unity_catalog_service_contract.py -v
pytest tests/contract/test_model_serving_service_contract.py -v
```

### Integration Tests

```bash
# Run all integration tests (skip slow ones for development)
pytest tests/integration/ -n auto -m "not slow"

# Run multi-user isolation tests
pytest tests/integration/test_multi_user_data_isolation.py -v

# Run observability tests
pytest tests/integration/test_observability.py -v

# Include slow tests (timeout scenarios)
pytest tests/integration/ -n auto  # Includes slow tests
```

### Continuous Integration

The CI pipeline runs tests with these optimizations enabled:

```bash
# CI command (runs all tests in parallel)
pytest -n auto --timeout=60 -v
```

## Next Steps

- Deploy to Databricks Apps: See [deployment documentation](../README.md#deployment)
- Review authentication patterns: See [authentication patterns documentation](./databricks_apis/authentication_patterns.md)
- Configure observability: See [OBO authentication documentation](./OBO_AUTHENTICATION.md)

## Additional Resources

- [Databricks Apps Documentation](https://docs.databricks.com/dev-tools/databricks-apps/)
- [Databricks CLI Documentation](https://docs.databricks.com/dev-tools/cli/)
- [Service Principal Authentication](https://docs.databricks.com/dev-tools/auth/oauth-m2m.html)
- [Unity Catalog](https://docs.databricks.com/data-governance/unity-catalog/)

