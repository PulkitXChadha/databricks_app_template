
# Quickstart: Databricks App Template with Service Integrations

**Feature**: Databricks service integrations (Unity Catalog, Lakebase, Model Serving)  
**Date**: October 5, 2025  
**Status**: Implementation Complete

## Overview

This quickstart guide walks you through setting up and testing the Databricks App Template with integrated Unity Catalog queries, Lakebase user preferences, and Model Serving inference capabilities.

---

## Prerequisites

### Required

- **Python 3.11+** with `uv` package manager
- **Node.js 18.0+** with `bun` package manager
- **Databricks workspace** with:
  - Unity Catalog enabled
  - Lakebase provisioned
  - SQL Warehouse running
  - Model Serving endpoint deployed (optional for full testing)
- **Databricks CLI** installed and configured
- **Access tokens** for workspace and Lakebase

### Optional

- **Git** for version control
- **VS Code** or Cursor for development

---

## Setup

### 1. Install Dependencies

#### Backend (Python)

```bash
# Install Python dependencies with uv
uv sync

# Verify installation
uv run python --version  # Should be 3.11+
```

#### Frontend (TypeScript/React)

```bash
# Navigate to client directory
cd client

# Install dependencies with bun
bun install

# Verify installation
bun --version  # Should be 1.0+

# Return to project root
cd ..
```

### 2. Configure Environment Variables

Create a `.env.local` file in the project root:

```bash
# Copy example (if exists) or create new file
touch .env.local
```

Add the following environment variables:

```bash
# Databricks Workspace Configuration
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com

# Unity Catalog Configuration (will be auto-populated after deployment)
DATABRICKS_WAREHOUSE_ID=  # Leave empty, will be set after Step 3
DATABRICKS_CATALOG=main
DATABRICKS_SCHEMA=samples

# Lakebase Configuration (will be auto-populated after deployment)
LAKEBASE_HOST=  # Leave empty, will be set after Step 3
LAKEBASE_PORT=5432
LAKEBASE_DATABASE=app_database
LAKEBASE_INSTANCE_NAME=  # Leave empty, will be set after Step 3 (e.g., databricks-app-lakebase-dev)

# Model Serving Configuration
MODEL_SERVING_ENDPOINT=your-endpoint-name  # e.g., sentiment-analysis
MODEL_SERVING_TIMEOUT=30

# Observability Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
```

**Note**: The `DATABRICKS_WAREHOUSE_ID` and `LAKEBASE_HOST` values will be automatically generated when you deploy the Databricks Asset Bundle in Step 3. Authentication is handled via OAuth through the Databricks CLI.

### 3. Deploy Databricks Resources (SQL Warehouse + Lakebase)

Before running database migrations, you need to provision the Lakebase database and SQL Warehouse using Databricks Asset Bundles.

#### Validate Bundle Configuration

First, verify your `databricks.yml` configuration is valid:

```bash
# Validate bundle configuration
databricks bundle validate --target dev

# Expected output:
# ✓ Configuration valid
```

If validation fails, check the error messages and ensure:
- The Databricks CLI is authenticated via OAuth (`databricks auth login`)
- Environment variable `DATABRICKS_HOST` is set in `.env.local` (if needed)
- The bundle syntax is correct (YAML formatting)

#### Deploy to Development Environment

Deploy the bundle to provision Lakebase and SQL Warehouse resources:

```bash
# Deploy to dev environment
databricks bundle deploy --target dev

# This will create:
# 1. SQL Warehouse: databricks-app-warehouse-dev
# 2. Lakebase Instance: databricks-app-lakebase-dev
# 3. Lakebase Catalog: lakebase_catalog_dev
```

**Expected Output:**
```
Starting bundle deployment...

Creating SQL Warehouse: databricks-app-warehouse-dev
  ✓ Warehouse created (ID: abc123def456)
  ✓ Starting warehouse...
  ✓ Warehouse running

Creating Lakebase Database Instance: databricks-app-lakebase-dev
  ✓ Instance provisioned (Host: xyz789.cloud.databricks.com)
  ✓ Instance ready

Creating Lakebase Database Catalog: lakebase_catalog_dev
  ✓ Catalog registered in Unity Catalog
  ✓ Database app_database created

Deployment completed successfully!
```

**Deployment Time**: Expect 5-10 minutes for initial provisioning.

#### Retrieve Auto-Generated Configuration

After deployment, retrieve the auto-generated resource IDs:

```bash
# List deployed resources
databricks bundle resources list --target dev

# Example output:
# Resource Type          Resource Name                    ID/URL
# warehouses            sql_warehouse_dev                 abc123def456
# database_instances    lakebase_dev                      xyz789.cloud.databricks.com
# database_catalogs     lakebase_catalog_dev              lakebase_catalog_dev
# apps                  databricks_app                    databricks-app-template-dev
```

#### Update Environment Variables

Update your `.env.local` with the auto-generated values:

```bash
# Update DATABRICKS_WAREHOUSE_ID (from warehouses resource)
DATABRICKS_WAREHOUSE_ID=abc123def456

# Update LAKEBASE_HOST (from database_instances resource)
LAKEBASE_HOST=xyz789.cloud.databricks.com

# Update LAKEBASE_INSTANCE_NAME (logical bundle name, NOT the UUID from host)
LAKEBASE_INSTANCE_NAME=databricks-app-lakebase-dev  # For dev target
# For prod target, use: databricks-app-lakebase
```

**Tip**: You can also find these values in the Databricks Console:
- **Warehouse ID**: SQL → Warehouses → databricks-app-warehouse-dev → Copy ID from URL
- **Lakebase Host**: Catalog → lakebase_catalog_dev → Connection Details
- **Lakebase Instance Name**: Use the logical name from your bundle (e.g., `databricks-app-lakebase-dev`), NOT the UUID from the host



#### Troubleshooting Deployment

**EC-005: Bundle Validation Failure**

If validation fails:
1. Check YAML syntax in `databricks.yml`
2. Verify OAuth authentication is active:
   ```bash
   databricks auth env
   ```
3. Run with verbose output:
   ```bash
   databricks bundle validate -t dev --debug
   ```

**Resource Creation Timeout**

If deployment times out (>15 minutes):
1. Check Databricks Console for resource status
2. Verify your workspace has capacity for new resources
3. Check account permissions for Lakebase and SQL Warehouses

**Lakebase Connection Failure**

If Lakebase connection fails:
1. Verify `LAKEBASE_HOST` is correct (no https:// prefix)
2. Check firewall rules allow port 5432
3. Ensure OAuth authentication has Lakebase access permissions
4. Wait 2-3 minutes after deployment for DNS propagation

### 4. Run Database Migrations

Create the necessary Lakebase tables:

```bash
# Run Alembic migrations to create user_preferences and model_inference_logs tables
alembic upgrade head

# Verify migrations
alembic current  # Should show: 002_create_model_inference_logs
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001_create_user_preferences
INFO  [alembic.runtime.migration] Running upgrade 001_create_user_preferences -> 002_create_model_inference_logs
```

### 5. Create Sample Data (Optional)

Populate Unity Catalog and Lakebase with sample data for testing:

```bash
# Create all sample data (Unity Catalog + Lakebase)
uv run python scripts/setup_sample_data.py create-all

# Or create selectively:
uv run python scripts/setup_sample_data.py unity-catalog --rows 50
uv run python scripts/setup_sample_data.py lakebase --num-records 3
```

**Sample Data Created:**
- Unity Catalog: `main.samples.demo_data` table with 100 rows
- Lakebase: 5 sample user preferences for testing

### 6. Start Development Server

#### Understanding Development Modes

This template supports multiple development and deployment modes:

| Mode | Script | Purpose | Environment |
|------|--------|---------|-------------|
| **Local Development** | `./watch.sh` | Daily development with hot reload | Local machine, connects to Databricks services |
| **Local Container Testing** | `./run_app_local.sh` | Debug deployment issues | Local container simulating Databricks Apps |
| **Production Deployment** | `./deploy.sh` | Deploy to Databricks Apps | Databricks workspace |

**For this quickstart, we'll use Local Development mode** (`./watch.sh`):
- ✅ Runs FastAPI server locally on your machine
- ✅ Runs Vite dev server locally for frontend hot reload  
- ✅ Authenticates via Databricks CLI (OAuth)
- ✅ Connects to remote Databricks services (Unity Catalog, Lakebase, Model Serving)
- ✅ Best for rapid development and testing
- ❌ Does NOT require deploying to Databricks Apps first

**Important**: `./watch.sh` runs your app **locally** and connects to **remote** Databricks services. You don't need to deploy the app to Databricks to use it during development!

#### Start Local Development Servers

```bash
# Start watch script (runs both servers with hot reload)
./watch.sh

# Or start separately:

# Terminal 1: Backend
uv run uvicorn server.app:app --reload --port 8000

# Terminal 2: Frontend
cd client && bun run dev
```

**Expected Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.

VITE v5.0.8  ready in 423 ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

### 7. Verify Local Development

#### Check Logs

**Note**: The `/logz/batch` endpoint is provided by the Databricks Apps platform and is only available when:
- Running with `databricks apps run-local`
- Deployed to Databricks Apps

For local development with `./watch.sh`, logs are displayed directly in your terminal where the FastAPI server is running.

To test the log client against a local server:
```bash
# This will attempt to fetch from /logz/batch endpoint
# (Only works if running via databricks apps run-local)
uv run python dba_logz.py --app_url http://localhost:8000

# For deployed apps, auto-detect the URL:
uv run python dba_logz.py

# Stream logs continuously from deployed app:
uv run python dba_logz.py --duration -1
```

#### Test Endpoints

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test user endpoint
curl http://localhost:8000/api/user/me

# Test Unity Catalog endpoint
curl http://localhost:8000/api/unity-catalog/tables?catalog=main&schema=samples

# Test Lakebase preferences endpoint
curl http://localhost:8000/api/preferences

# Test Model Serving endpoints list
curl http://localhost:8000/api/model-serving/endpoints
```

#### Using the API Client

For testing with authentication:
```bash
# Test local endpoints (no authentication required)
uv run python dba_client.py /health --app_url http://localhost:8000
uv run python dba_client.py /api/user/me --app_url http://localhost:8000

# Test deployed app endpoints (auto-detected URL with OAuth)
uv run python dba_client.py /api/user/me
uv run python dba_client.py /api/preferences
```

#### Verify OpenAPI Docs

Visit http://localhost:8000/docs to see all available endpoints with interactive testing.

#### Development URLs Reference

When running locally with `./watch.sh`:
- **Frontend (React/Vite)**: http://localhost:5173/
- **Backend (FastAPI)**: http://localhost:8000/
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

**Important**: Use `http://localhost:8000` when testing backend endpoints with `dba_client.py` or `dba_logz.py` scripts in local development mode.

---

## Testing User Stories

### Story 1: View Unity Catalog Data

**Objective**: Query and display data from Unity Catalog tables with pagination.

**Steps**:

1. Navigate to http://localhost:5173
2. Click on the "Unity Catalog" tab
3. Select catalog: `main`, schema: `samples`, table: `demo_data`
4. Click "Query Table"
5. Verify:
   - Data displays in table with column headers
   - Pagination controls appear (Previous/Next buttons)
   - Page size selector works (10, 25, 50, 100, 500 rows)
   - Response time < 500ms for 100 rows

**Success Criteria**:
- ✅ Table data loads successfully
- ✅ Pagination controls functional
- ✅ Column data types displayed
- ✅ NULL values shown with styling

### Story 2: Manage User Preferences (CRUD Operations)

**Objective**: Create, read, update, and delete user preferences in Lakebase.

**Steps**:

1. Navigate to "Preferences" tab
2. **Create**: 
   - Select preference key: `theme`
   - Enter JSON value: `{"mode": "dark", "accent_color": "blue"}`
   - Click "Create"
   - Verify success banner appears
3. **Read**: 
   - Refresh page
   - Verify preference appears in "Current Preferences" list
4. **Update**: 
   - Modify JSON value: `{"mode": "light", "accent_color": "green"}`
   - Click "Update"
   - Verify updated value in list
5. **Delete**: 
   - Click "Delete" button for the preference
   - Confirm deletion
   - Verify preference removed from list

**Success Criteria**:
- ✅ All CRUD operations complete successfully
- ✅ Data persists across page refreshes
- ✅ JSON validation prevents invalid input
- ✅ User sees only their own preferences (data isolation)

### Story 3: Invoke Model for Inference

**Objective**: Submit inputs to a Model Serving endpoint and display predictions.

**Steps**:

1. Navigate to "Model Serving" tab
2. Click "Refresh Endpoints" to load available endpoints
3. Select endpoint from dropdown (e.g., `sentiment-analysis`)
4. Verify endpoint state is "READY"
5. Enter input JSON:
   ```json
   {
     "text": "This product is amazing! Highly recommend."
   }
   ```
6. Set timeout: 30 seconds
7. Click "Invoke Model"
8. Wait for response (should be < 2s)
9. Verify:
   - Predictions display in formatted JSON
   - Execution time shown in milliseconds
   - Request ID logged for tracing

**Success Criteria**:
- ✅ Endpoint state validation works
- ✅ Inference completes successfully
- ✅ Predictions display correctly
- ✅ Error handling for timeouts/failures

### Story 4: Multi-User Data Isolation

**Objective**: Verify that users can only access their own preferences.

**Steps**:

1. **User A Session**:
   - Log in as User A (or use User A token)
   - Create preference: `theme = dark`
   - Note the user_id in logs

2. **User B Session**:
   - Log in as User B (different token)
   - Navigate to Preferences
   - Verify User A's preference is NOT visible
   - Create preference: `theme = light`

3. **Back to User A**:
   - Refresh preferences
   - Verify only User A's preference visible

**Success Criteria**:
- ✅ Each user sees only their own preferences
- ✅ Database queries filter by user_id
- ✅ No cross-user data leakage

### Story 5: Observability with Correlation IDs

**Objective**: Trace requests across services using correlation IDs.

**Steps**:

1. Make an API request with custom request ID:
   ```bash
   curl -H "X-Request-ID: test-trace-123" \
        http://localhost:8000/api/unity-catalog/tables
   ```

2. Check logs for correlation ID:
   ```bash
   # For local development, check terminal output where FastAPI is running
   # For deployed apps, use:
   uv run python dba_logz.py --search "test-trace-123"
   ```

3. Verify logs show:
   - Request received with correlation ID
   - All downstream operations tagged with same ID
   - Performance metrics (duration_ms)
   - Response returned with same ID

**Success Criteria**:
- ✅ Logs are structured JSON format
- ✅ Correlation IDs propagate through all operations
- ✅ X-Request-ID header preserved in response
- ✅ Performance metrics logged

### Story 6: Error Handling

**Objective**: Verify graceful error handling for all error codes (EC-001 through EC-005).

**Steps**:

1. **EC-001: Model Unavailable**:
   - Invoke model with endpoint that doesn't exist
   - Verify error message: "Model endpoint not found"
   - Verify retry_after field present

2. **EC-002: Database Unavailable**:
   - Stop Lakebase connection (or use invalid credentials)
   - Try to fetch preferences
   - Verify error message: "Database service temporarily unavailable"

3. **EC-003: Authentication Required**:
   - Make request without token
   - Verify 401 response with "AUTH_REQUIRED" error_code

4. **EC-004: Catalog Permission Denied**:
   - Query table user doesn't have access to
   - Verify error message: "You don't have access to this table"

5. **EC-005: Bundle Validation Failure**:
   - Run `databricks bundle validate` with invalid config
   - Fix errors and revalidate

**Success Criteria**:
- ✅ All error codes implemented
- ✅ User-friendly error messages shown
- ✅ Technical details logged (not exposed to users)
- ✅ Retry logic works for transient errors

### Story 7: Accessibility Compliance (WCAG 2.1 Level A)

**Objective**: Verify keyboard navigation and accessibility features.

**Steps**:

1. Navigate entire app using only keyboard:
   - Tab through all interactive elements
   - Press Enter to activate buttons
   - Press Escape to close modals

2. Check contrast ratios:
   - Use browser DevTools → Lighthouse → Accessibility
   - Verify contrast ratios meet WCAG standards:
     - Normal text: ≥4.5:1
     - Large text: ≥3:1

3. Verify alt text and labels:
   - All images have descriptive alt text
   - All form inputs have labels
   - ARIA attributes present where needed

**Success Criteria**:
- ✅ Full keyboard navigation works
- ✅ Contrast ratios meet standards
- ✅ Screen reader compatible
- ✅ No accessibility violations in Lighthouse

### Story 8: Pagination Performance (NFR-003)

**Objective**: Verify pagination performance meets <500ms target.

**Steps**:

1. Query Unity Catalog table with 100 rows
2. Measure response time (use browser DevTools Network tab)
3. Navigate through pages (offset: 0, 100, 200, ...)
4. Test with 10 concurrent users:
   ```bash
   # Use load testing script
   python dba_client.py --concurrent 10 --queries 50
   ```

5. Verify:
   - Single user response time < 500ms
   - 10 concurrent users: latency increase < 20%

**Success Criteria**:
- ✅ Response time < 500ms for ≤100 rows
- ✅ Pagination doesn't significantly degrade performance
- ✅ Connection pooling handles concurrent requests

### Story 9: Deploy to Production

**Objective**: Deploy app to production environment using Asset Bundles.

**Steps**:

1. **Validate Production Configuration**:
   ```bash
   # Validate bundle for production target
   databricks bundle validate --target prod
   ```
   - Should pass with no errors
   - Verify production-specific settings (permissions, capacity, etc.)

2. **Review Resource Configuration**:
   - Production SQL Warehouse: `databricks-app-warehouse` (not `-dev` suffix)
   - Production Lakebase: `databricks-app-lakebase`
   - Production catalog: `lakebase_catalog`
   - Verify capacity settings appropriate for production load

3. **Deploy to Prod**:
   ```bash
   # Deploy production environment
   databricks bundle deploy --target prod
   ```
   - Creates production SQL Warehouse and Lakebase instance
   - Deploys app with production configuration
   - Sets up permissions (admins: CAN_MANAGE, users: CAN_VIEW)

4. **Update Production Environment Variables**:
   - Create `.env.production` with production values:
     ```bash
     DATABRICKS_WAREHOUSE_ID=<prod-warehouse-id>
     LAKEBASE_HOST=<prod-lakebase-host>
     DATABRICKS_SCHEMA=default  # Note: prod uses 'default' schema
     ```

5. **Run Production Migrations**:
   ```bash
   # Use production environment variables
   source .env.production
   alembic upgrade head
   ```

6. **Test Production Deployment**:
   - Access app URL from bundle output
   - Test with non-admin account to verify CAN_VIEW permissions
   - Verify data isolation between dev and prod

7. **Debug Deployment Issues (if needed)**:
   - If deployment fails, use local container testing:
     ```bash
     ./run_app_local.sh --verbose
     ```
   - This simulates the Databricks Apps environment locally
   - Helps identify issues with `app.yaml`, dependencies, or environment variables
   - Check deployment logs at app URL + `/logz` in browser

**Success Criteria**:
- ✅ Bundle validation passes for prod target
- ✅ Production resources provisioned successfully
- ✅ Prod deployment successful with correct permissions
- ✅ Permissions enforced correctly (admin vs user access)
- ✅ Data isolated from dev environment

---

## Troubleshooting

### Development vs Deployment Issues

**When to use each debugging approach:**

1. **Local Development Issues** (`./watch.sh` not working):
   - Check authentication: `databricks auth env`
   - Verify environment variables in `.env.local`
   - Check connection to Databricks services (Unity Catalog, Lakebase)
   - Review logs in terminal output (where FastAPI is running)
   - Test endpoints: `uv run python dba_client.py /health --app_url http://localhost:8000`

2. **Deployment Issues** (app fails after `./deploy.sh`):
   - Use `./run_app_local.sh` to simulate Databricks Apps environment
   - Check app status: `databricks apps list`
   - Visit app URL + `/logz` in browser for deployment logs
   - Use log client: `uv run python dba_logz.py` (auto-detects deployed app)
   - Verify workspace files synced correctly
   - Check `app.yaml` configuration

3. **Production Runtime Issues** (deployed app misbehaving):
   - Check app logs at `<app-url>/logz` (requires browser OAuth)
   - Use log client: `uv run python dba_logz.py --duration -1` (stream logs)
   - Use `./app_status.sh --verbose` to check status
   - Review environment variables in Databricks Apps settings
   - Check resource permissions (catalogs, warehouses, endpoints)

### EC-001: Model Endpoint Unavailable

**Symptoms**: Inference requests fail with "MODEL_UNAVAILABLE" error

**Solutions**:
1. Check endpoint state:
   ```bash
   curl http://localhost:8000/api/model-serving/endpoints
   ```
2. Verify endpoint is in READY state
3. Check MODEL_SERVING_ENDPOINT environment variable
4. Verify Databricks token has model serving permissions

### EC-002: Lakebase Connection Failure

**Symptoms**: Preference operations fail with "DATABASE_UNAVAILABLE" error

**Solutions**:
1. Verify Lakebase configuration in `.env.local`:
   - LAKEBASE_HOST
   - LAKEBASE_DATABASE
2. Ensure OAuth authentication is active:
   ```bash
   databricks auth env
   ```
3. Test connection:
   ```bash
   uv run python -c "from server.lib.database import get_engine; get_engine().connect()"
   ```
4. Check connection pool exhaustion (max 10 connections)
5. Run migrations if tables don't exist:
   ```bash
   alembic upgrade head
   ```

### EC-003: Authentication Failure

**Symptoms**: API requests return 401 "AUTH_REQUIRED" error

**Solutions**:
1. Re-authenticate with Databricks CLI using OAuth:
   ```bash
   databricks auth login --host https://your-workspace.cloud.databricks.com
   ```
2. Verify OAuth authentication is active:
   ```bash
   databricks auth env
   ```
3. Ensure your OAuth credentials have required permissions:
   - Unity Catalog access
   - Lakebase access
   - Model Serving access
4. Check if authentication has expired and re-login if needed

### EC-004: Unity Catalog Permission Denied

**Symptoms**: Query fails with "CATALOG_PERMISSION_DENIED" error

**Solutions**:
1. Check table grants:
   ```sql
   SHOW GRANTS ON TABLE main.samples.demo_data;
   ```
2. Grant SELECT permission:
   ```sql
   GRANT SELECT ON TABLE main.samples.demo_data TO `user@company.com`;
   ```
3. Verify user has access to catalog and schema
4. Use table owner account for testing

### EC-005: Bundle Validation Failure

**Symptoms**: `databricks bundle validate` returns errors

**Solutions**:
1. Check `databricks.yml` syntax (YAML format)
2. Verify all required environment variables set
3. Validate variable references (${VAR_NAME})
4. Check permissions section format
5. Run with verbose output:
   ```bash
   databricks bundle validate --debug
   ```

### Performance Issues

**Symptoms**: Slow API response times, timeouts

**Solutions**:
1. Check SQL Warehouse state (should be RUNNING)
2. Verify query has appropriate LIMIT clause
3. Monitor connection pool usage:
   ```python
   from server.lib.database import get_engine
   engine = get_engine()
   print(f"Pool size: {engine.pool.size()}")
   print(f"Checked out: {engine.pool.checkedout()}")
   ```
4. Increase timeout for large queries
5. Add indexes on frequently queried columns

### Frontend Build Issues

**Symptoms**: Client build fails, missing dependencies

**Solutions**:
1. Clear node_modules and reinstall:
   ```bash
   cd client
   rm -rf node_modules bun.lock
   bun install
   ```
2. Verify bun version:
   ```bash
   bun --version  # Should be 1.0+
   ```
3. Check for TypeScript errors:
   ```bash
   bun run build
   ```

---

## Additional Resources

### Documentation

- [Unity Catalog API Reference](../docs/databricks_apis/workspace_apis.md)
- [Model Serving Integration Guide](../docs/databricks_apis/model_serving.md)
- [Data Model](./data-model.md)
- [API Contracts](./contracts/)

### Support

- **GitHub Issues**: Report bugs and feature requests
- **Databricks Community**: Ask questions in forums
- **Documentation**: [docs.databricks.com](https://docs.databricks.com)

---

## Next Steps

After completing the quickstart:

1. **Customize**: Adapt the template for your use case
2. **Add Models**: Register and deploy your ML models
3. **Extend UI**: Add custom components with Design Bricks
4. **Monitor**: Set up alerts and dashboards for observability
5. **Scale**: Configure auto-scaling for SQL Warehouses and Model Serving

---

**Last Updated**: October 5, 2025  
**Version**: 1.0.0
