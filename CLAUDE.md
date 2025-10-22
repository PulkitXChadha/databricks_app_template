# Databricks App Template Development Guide

## Project Memory

This is a modern full-stack application template for Databricks Apps, featuring FastAPI backend with React TypeScript frontend and modern development tooling.

## Tech Stack

**Backend:**
- Python with `uv` for package management
- FastAPI for API framework
- Databricks SDK for workspace integration
- OpenAPI automatic client generation

**Frontend:**
- TypeScript with React
- Vite for fast development and hot reloading
- Design Bricks components (migrating from shadcn/ui) for Databricks look-and-feel
- shadcn/ui components with Tailwind CSS (being phased out)
- React Query for API state management
- Bun for package management
- Recharts for metrics visualization and charting (feature 006-app-metrics)

**Databricks Integrations:**
- Unity Catalog for lakehouse data access with fine-grained permissions
- Lakebase (Databricks-hosted Postgres) for transactional data
- Model Serving endpoints for ML inference
- Asset Bundles for reproducible deployments
- **OBO-Only Authentication**: All Databricks API operations use On-Behalf-Of user authentication

### 🚨 IMPORTANT: OBO-Only Authentication Architecture 🚨

**Authentication Pattern (as of 003-obo-only-support)**:
- **Databricks APIs**: All operations require user access token (OBO-only pattern)
- **Lakebase**: Uses application-level credentials with user_id filtering (hybrid approach)
- **No service principal fallback** for Databricks API operations

**Key Principles**:
1. All Databricks API services (`UnityCatalogService`, `ModelServingService`, `UserService`) require `user_token` parameter
2. `/health` endpoint is public (no authentication required)
3. `/metrics` endpoint requires user authentication
4. User identity extraction via `get_user_token()` dependency (raises 401 if missing)
5. LakebaseService uses service principal credentials + user_id filtering

**Error Handling**:
- Missing token → HTTP 401 with `AUTH_MISSING` error code
- Invalid token → HTTP 401 with `AUTH_INVALID` error code  
- Expired token → HTTP 401 with `AUTH_EXPIRED` error code
- All errors include correlation_id for tracing

**Local Development**:
- Use Databricks CLI for token generation: `databricks auth token`
- Set token in request header: `X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN`
- Test script: `scripts/get_user_token.py`

**Documentation**:
- See `docs/OBO_AUTHENTICATION.md` for detailed authentication guide
- See `specs/003-obo-only-support/` for implementation details

## Metrics System (Feature 006-app-metrics)

**Purpose**: Comprehensive application usage and performance metrics collection with admin-only dashboard.

### Architecture Overview

**Three-table hybrid retention strategy**:
- **Raw metrics** (7-day retention): `performance_metrics`, `usage_events`
- **Aggregated metrics** (90-day retention): `aggregated_metrics`
- **Automatic routing**: Queries <7 days use raw tables, 8-90 days use aggregated table

### Key Components

**Backend Services**:
- `server/services/admin_service.py` - Workspace admin privilege checking with 5-minute cache
- `server/services/metrics_service.py` - Metrics collection, retrieval, and query routing
- `server/lib/metrics_middleware.py` - Automatic performance metric collection (all API requests)
- `server/routers/metrics.py` - Admin-only metrics API endpoints
- `scripts/aggregate_metrics.py` - Daily aggregation job (2 AM UTC, Databricks workflow)

**Frontend Components**:
- `client/src/services/usageTracker.ts` - Usage event batching (10s OR 20 events)
- `client/src/components/MetricsDashboard.tsx` - Admin dashboard with time range selector
- `client/src/components/PerformanceChart.tsx` - Response time trends (Recharts)
- `client/src/components/EndpointBreakdownTable.tsx` - Per-endpoint performance table

### Admin Access Control

**Workspace admin check** (FR-011):
- Uses Databricks Workspace API: `WorkspaceClient.current_user.me()`
- Checks group membership: configurable via `ADMIN_GROUPS` env var
- Default groups: "admins", "workspace_admins", "administrators" (case-insensitive)
- Caching: 5-minute TTL to reduce API calls
- Error handling: Returns 503 Service Unavailable if API check fails (fail-secure)

**Usage**:
```python
from server.lib.auth import get_admin_user

@router.get("/admin-only-endpoint")
async def admin_endpoint(admin_user = Depends(get_admin_user)):
    # admin_user = {"user_id": "email", "email": "email"}
    # Non-admins receive 403 Forbidden
    pass
```

### Metrics Collection Patterns

**Automatic Performance Metrics** (FR-001):
- Middleware captures ALL API requests automatically
- Excludes health check endpoints: `/health`, `/ready`, `/ping`, `/internal/*`, `/admin/system/*`
- Records: endpoint, method, status_code, response_time_ms, user_id, error_type
- **Lakebase Configuration Check**: MUST check `is_lakebase_configured()` before attempting database operations
- **Graceful degradation**: Collection failures never impact API responses
- **Local Development**: Metrics collection automatically skipped if Lakebase not configured (debug log only)

**Manual Usage Events**:
```typescript
import { usageTracker } from './services/usageTracker';

// Track user action
usageTracker.track({
  event_type: 'button_click',
  page_name: '/metrics',
  element_id: 'refresh-button',
  success: true,
  metadata: { custom: 'data' }
});

// Automatic batching (10 seconds OR 20 events)
// Automatic flush on page unload via navigator.sendBeacon
```

### Query Routing Logic

**Time-based routing**:
- Last 7 days (0-7 days ago): Query `performance_metrics` and `usage_events` tables ONLY
- 8-90 days ago: Query `aggregated_metrics` table ONLY with pre-computed percentiles
- Boundary handling: Split queries at 7-day cutoff, merge results in application layer

**Implementation**:
```python
def get_performance_metrics(time_range: str):
    start_time, end_time = parse_time_range(time_range)
    if (datetime.utcnow() - start_time).days <= 7:
        return _query_raw_performance_metrics()  # High granularity
    else:
        return _query_aggregated_performance_metrics()  # Pre-computed
```

### Data Lifecycle Management

**Daily Aggregation Job** (2 AM UTC):
1. Aggregate 7-day-old raw metrics into hourly buckets
2. Pre-compute percentiles (p50, p95, p99) using PostgreSQL `percentile_cont`
3. Delete processed raw records (atomic transaction)
4. Cleanup 90-day-old aggregated records
5. Monitor database size (alert if >1M records)

**Idempotency**: Check-before-insert pattern prevents duplicate aggregations on retry

**Job Configuration** (in `databricks.yml`):
```yaml
resources:
  jobs:
    metrics_aggregation_job:
      schedule:
        quartz_cron_expression: "0 0 2 * * ?"
        timezone_id: "UTC"
      python_wheel_task:
        entry_point: "aggregate_metrics"  # From pyproject.toml [project.scripts]
```

### Database Schema

**PerformanceMetric** (raw, 7-day retention):
- Indexed: timestamp, endpoint, user_id
- Captures: response_time_ms, status_code, method, error_type

**UsageEvent** (raw, 7-day retention):
- Indexed: timestamp, event_type, user_id
- Captures: page_name, element_id, success, metadata (JSON)

**AggregatedMetric** (pre-computed, 90-day retention):
- Indexed: time_bucket, metric_type, endpoint_path, event_type
- Stores: aggregated_values (JSON with avg, min, max, p50, p95, p99), sample_count

### API Endpoints

**Admin-Only Endpoints**:
- `GET /api/v1/metrics/performance?time_range=24h&endpoint=/api/v1/lakebase/sources`
- `GET /api/v1/metrics/usage?time_range=7d&event_type=button_click`
- `GET /api/v1/metrics/time-series?time_range=30d&metric_type=both`

**Authenticated (Not Admin)**:
- `POST /api/v1/metrics/usage-events` - Submit batch events (max 1000 per batch)
- `GET /api/v1/metrics/usage/count?time_range=24h` - Get user's event count for data loss validation

### Terminology Standards

**Consistent usage required across codebase**:
- **performance metrics** (lowercase): API request timing data - `PerformanceMetric` model
- **usage events** (lowercase): User interaction data - `UsageEvent` model
- **aggregated metrics** (lowercase): Pre-computed summaries - `AggregatedMetric` model
- **metrics collection**: Overall system combining both performance and usage
- **raw metrics**: Data in 7-day retention tables
- **Naming convention**: lowercase for concepts, PascalCase for models, snake_case for tables

### Lakebase Configuration

**Local Development Setup**:
Metrics collection requires Lakebase to be configured. Add these to `.env.local`:

```bash
# Lakebase Configuration (required for metrics collection)
PGHOST=instance-xxxxx.database.cloud.databricks.com
LAKEBASE_DATABASE=app_database
LAKEBASE_INSTANCE_NAME=databricks-app-lakebase-dev
LAKEBASE_PORT=443  # Optional, defaults to 5432
```

**Graceful Degradation**:
- If Lakebase is not configured, metrics collection is automatically skipped
- Application continues to work normally without metrics
- Debug logs: `"Skipping performance metric collection - Lakebase not configured"`
- Same pattern used by Model Serving for inference logging

**Configuration Check Pattern**:
```python
from server.lib.database import is_lakebase_configured

# ALWAYS check before database operations
if not is_lakebase_configured():
    logger.debug("Skipping operation - Lakebase not configured")
    return
```

### Troubleshooting

**Dashboard shows "No data available"**:
1. Check if Lakebase is configured: `python -c "from server.lib.database import is_lakebase_configured; print(is_lakebase_configured())"`
2. Verify environment variables: `PGHOST`, `LAKEBASE_DATABASE`, `LAKEBASE_INSTANCE_NAME`
3. Check middleware registration in `server/app.py`
4. Query raw tables directly: `SELECT COUNT(*) FROM performance_metrics;`

**Metrics show 0 for Unique Users / Active Users / Usage data**:
1. **Frontend Authentication Issue**: Check if frontend has valid token in built JavaScript
   - Frontend builds bake in `VITE_DATABRICKS_USER_TOKEN` at build time
   - After token refresh, MUST rebuild frontend: `cd client && bun run build`
   - Copy new build to production: `cp -r client/build/* build/`
   - Reload browser to pick up new build (Cmd+R or Ctrl+R)
2. **Timezone Mismatch Bug**: Database has timezone-aware timestamps but code uses naive datetimes
   - Symptom: `"can't compare offset-naive and offset-aware datetimes"` warning in logs
   - Fix: Use `datetime.now(timezone.utc)` instead of `datetime.utcnow()` everywhere
   - ALWAYS use timezone-aware datetimes when working with Lakebase/Postgres
3. **Verify events are being sent**: Check browser console for `[UsageTracker]` debug messages
4. **Test backend manually**: Submit test event with curl to verify API works
5. **Query database directly**: Check if events exist: `SELECT COUNT(*) FROM usage_events;`

**"Database instance is not found" errors**:
1. Verify `LAKEBASE_INSTANCE_NAME` matches your databricks.yml resource name
2. Check `PGHOST` is correct Lakebase instance hostname
3. Ensure you have access to the Lakebase instance in Databricks workspace
4. Restart development server after adding environment variables

**Admin check always fails (403)**:
1. Verify user is workspace admin in Databricks
2. Check `ADMIN_GROUPS` env var matches actual group names
3. Review admin service logs: `python dba_logz.py | grep "Admin check"`
4. Test Databricks API manually: `databricks auth token` then `curl https://workspace/api/2.0/preview/scim/v2/Me`

**Aggregation job not running**:
1. Check Databricks jobs list: `databricks jobs list | grep metrics`
2. Verify job schedule in `databricks.yml`
3. Test manually: `uv run aggregate-metrics`
4. Review job run logs in Databricks workspace

**High dashboard load time (>10s)**:
1. Check aggregation job is running (reduces raw table size)
2. Verify indexes exist on timestamp columns
3. Consider adding LIMIT to initial dashboard load
4. Review query execution plans for optimization

### Performance Considerations

**Success Criteria**:
- Middleware overhead: <5ms per request (SC-002)
- Dashboard load time: <3 seconds (SC-001)
- 30-day query time: <5 seconds (SC-006)
- Collection rate: 100% of API requests (SC-004)
- Update latency: <60 seconds for raw data visibility (SC-003)

**Optimization strategies**:
- Connection pooling: min=5, max=20 connections
- Async writes: Metrics recorded asynchronously
- Batch inserts: Usage events submitted in batches
- Pre-computed percentiles: Calculated during aggregation for historical data
- Indexed queries: All time-range queries use indexed timestamp columns

### Testing

**TDD Workflow** (Principle XII):
1. **RED Phase**: Write failing tests (contract + integration + unit)
2. **GREEN Phase**: Implement minimal code to pass tests
3. **REFACTOR Phase**: Improve code quality while keeping tests GREEN

**Test organization**:
- `tests/contract/test_metrics_api.py` - API endpoint contract tests
- `tests/integration/test_metrics_collection.py` - Middleware collection tests
- `tests/integration/test_metrics_aggregation.py` - Aggregation job tests
- `tests/unit/test_admin_service.py` - Admin privilege checking tests
- `tests/unit/test_metrics_service.py` - Service layer unit tests

**Run tests**: `pytest tests/ -v --cov`

## Development Workflow

### Package Management
- Use `uv add/remove` for Python dependencies, not manual edits to pyproject.toml
- Use `bun add/remove` for frontend dependencies, not manual package.json edits
- Always check if dependencies exist in the project before adding new ones

### Development Commands
- `./setup.sh` - Interactive environment setup and dependency installation
- `./watch.sh` - Start development servers with hot reloading (frontend:5173, backend:8000)
- `./fix.sh` - Format code (ruff for Python, prettier for TypeScript)
- `./deploy.sh` - Deploy to Databricks Apps

### 🚨 IMPORTANT: NEVER RUN THE SERVER MANUALLY 🚨

**ALWAYS use the watch script with nohup and logging:**

```bash
# Start development servers (REQUIRED COMMAND)
nohup ./watch.sh > /tmp/databricks-app-watch.log 2>&1 &

# Or for production mode
nohup ./watch.sh --prod > /tmp/databricks-app-watch.log 2>&1 &
```

**NEVER run uvicorn or the server directly!** Always use `./watch.sh` as it:
- Configures environment variables properly
- Starts both frontend and backend correctly
- Generates TypeScript client automatically
- Handles authentication setup
- Provides proper logging and error handling

### 🛑 HOW TO KILL THE DEVELOPMENT SERVERS

**To kill the development servers, use ONE of these methods:**

```bash
# Method 1: Using the PID file (preferred)
kill $(cat /tmp/databricks-app-watch.pid)

# Method 2: Kill by process name
pkill -f watch.sh

# Method 3: If you know the watch script PID directly
kill [PID]
```

**How it works (Updated Cleanup System):**
- **Recursive Process Tree Killing**: The cleanup function kills each tracked process (frontend, backend, watcher) and ALL their descendant processes recursively
- **Final Port Cleanup**: After process tree cleanup, any remaining processes on ports 5173 and 8000 are force-killed as a final safety measure
- **Complete Port Liberation**: Both ports 5173 (frontend) and 8000 (backend) are guaranteed to be freed
- **Handles Complex Process Chains**: Works with npm → bun → node process hierarchies that can't be killed with simple parent-child relationships

**Technical Details:**
- Uses `kill_tree()` function that recursively finds and kills all child processes
- Tracks specific PIDs: Frontend (shell wrapper), Backend (uvicorn), Watcher (watchmedo)  
- Final cleanup: `lsof -ti:5173 | xargs kill` and `lsof -ti:8000 | xargs kill`
- **Test Result**: Killing the watch script completely frees both ports with zero orphaned processes

### 🚨 PYTHON EXECUTION RULE 🚨

**NEVER run `python` directly - ALWAYS use `uv run`:**

```bash
# ✅ CORRECT - Always use uv run
uv run python script.py
uv run uvicorn server.app:app
uv run scripts/make_fastapi_client.py

# ❌ WRONG - Never use python directly
python script.py
uvicorn server.app:app
python scripts/make_fastapi_client.py
```

### 🚨 TIMEZONE HANDLING RULE 🚨

**ALWAYS use timezone-aware datetimes when working with databases:**

```python
# ✅ CORRECT - Timezone-aware datetime
from datetime import datetime, timezone
now = datetime.now(timezone.utc)
start_time = now - timedelta(hours=24)

# ❌ WRONG - Naive datetime (will fail with Postgres timestamp comparisons)
now = datetime.utcnow()  # Deprecated and timezone-naive
start_time = now - timedelta(hours=24)
```

**Why this matters:**
- Lakebase/Postgres stores timestamps as `TIMESTAMP WITH TIME ZONE` (timezone-aware)
- Comparing naive datetimes with timezone-aware timestamps raises: `"can't compare offset-naive and offset-aware datetimes"`
- `datetime.utcnow()` is deprecated in Python 3.12+ and returns naive datetimes
- `datetime.now(timezone.utc)` returns timezone-aware datetimes and is the modern standard

**Rule applies to:**
- All datetime queries against Lakebase/Postgres
- Any datetime filtering in SQLAlchemy queries
- Time range parsing for metrics and reporting
- Scheduled job timestamps

### 🚨 DATABRICKS CLI EXECUTION RULE 🚨

**The Databricks CLI is installed globally and run directly:**

```bash
# ✅ CORRECT - Use databricks CLI directly
databricks current-user me
databricks apps list
databricks workspace list /

# With environment variables when needed:
source .env.local && export DATABRICKS_HOST && export DATABRICKS_TOKEN && databricks current-user me
```

**Installation:**
- The CLI is installed globally during setup via ./setup.sh
- Uses official installation methods (brew on macOS, official installer on Linux)
- Always available in the PATH after installation

**🚨 DATABRICKS APPS COMPATIBILITY 🚨**

If the user runs into issues with the Databricks CLI not recognizing `apps` commands (e.g., "Error: unknown command 'apps'"), they need to upgrade to CLI version 0.265.0+:

```bash
# Check current version
databricks --version

# If version is < 0.265.0, offer to upgrade
# ONLY upgrade if user explicitly confirms - very important!
brew upgrade databricks
```

**When to upgrade:**
- User gets "unknown command 'apps'" errors
- CLI version shows < 0.265.0
- User explicitly requests CLI upgrade

**IMPORTANT**: Always ask for user confirmation before upgrading, as this affects their global CLI installation.

### Claude Natural Language Commands
Claude understands natural language commands for common development tasks:

**Development Lifecycle:**
- "start the devserver" → Runs `./watch.sh` in background with logging
- "kill the devserver" → Stops all background development processes
- "fix the code" → Runs `./fix.sh` to format Python and TypeScript code
- "deploy the app" → Runs `./deploy.sh` to deploy to Databricks Apps

**Development Tasks:**
- "add a new API endpoint" → Creates FastAPI routes with proper patterns
- "create a new React component" → Builds UI components using shadcn/ui
- "debug this error" → Analyzes logs and fixes issues
- "install [package]" → Adds dependencies using uv (Python) or bun (frontend)
- "generate the TypeScript client" → Regenerates API client from OpenAPI spec
- "open the UI in playwright" → Opens the frontend app in Playwright browser for testing
- "open app" → Gets app URL from `./app_status.sh` and opens it with `open {url}`

### Implementation Validation Workflow
**During implementation, ALWAYS:**
1. **Start development server first**: `nohup ./watch.sh > /tmp/databricks-app-watch.log 2>&1 &`
2. **Open app with Playwright** to see current state before changes
3. **After each implementation step:**
   - Check logs: `tail -f /tmp/databricks-app-watch.log`
   - Use Playwright to verify UI changes are working
   - Take snapshots to confirm features render correctly
   - Test user interactions and API calls
4. **🚨 CRITICAL: FastAPI Endpoint Verification**
   - **IMPORTANT: After adding ANY new FastAPI endpoint, MUST curl the endpoint to verify it works**
   - **NEVER move on to the next step until the endpoint is verified with curl**
   - **Example verification commands:**
     ```bash
     # Test GET endpoint
     curl -s http://localhost:8000/api/new-endpoint | jq
     
     # Test POST endpoint
     curl -X POST -H "Content-Type: application/json" -d '{"key":"value"}' http://localhost:8000/api/new-endpoint | jq
     ```
   - **Show the curl response to confirm the endpoint works correctly**
   - **If the endpoint fails, debug and fix it before proceeding**
5. **Install Playwright if needed**: `claude mcp add playwright npx '@playwright/mcp@latest'`
6. **Iterative validation**: Test each feature before moving to next step

**This ensures every implementation step is validated and working before proceeding.**

### Development Server
- **ALWAYS** run `./watch.sh` with nohup in background and log to file for debugging
- Watch script automatically runs in background and logs to `/tmp/databricks-app-watch.log`
- Frontend runs on http://localhost:5173
- Backend runs on http://localhost:8000
- API docs available at http://localhost:8000/docs
- Supports hot reloading for both frontend and backend
- Automatically generates TypeScript client from FastAPI OpenAPI spec
- **Check logs**: `tail -f /tmp/databricks-app-watch.log`
- **Stop processes**: `pkill -f "watch.sh"` or check PID file

### Code Quality
- Use `./fix.sh` for code formatting before commits
- Python: ruff for formatting and linting, ty for type checking
- TypeScript: prettier for formatting, ESLint for linting
- Type checking with TypeScript and ty (Python)

### API Development
- FastAPI automatically generates OpenAPI spec
- TypeScript client is auto-generated from OpenAPI spec
- Test endpoints with curl or FastAPI docs
- Check server logs after requests
- Verify response includes expected fields

### Databricks API Integration
- **ALWAYS** reference `docs/databricks_apis/` documentation when implementing Databricks features
- Use `docs/databricks_apis/databricks_sdk.md` for workspace, cluster, and SQL operations
- Use `docs/databricks_apis/mlflow_genai.md` for AI agent and LLM functionality
- Use `docs/databricks_apis/model_serving.md` for model serving endpoints and inference
- Use `docs/databricks_apis/workspace_apis.md` for file operations and directory management
- Follow the documented patterns and examples for proper API usage
- Check official documentation links in each API guide for latest updates

### Service Integration Patterns

**Unity Catalog Integration** (`server/services/unity_catalog_service.py`):
- Use `WorkspaceClient` with SQL Warehouse execution for queries
- Leverage Unity Catalog's built-in access control for permissions
- Query pattern: `SELECT * FROM {catalog}.{schema}.{table} LIMIT 100`
- Connection pooling: Reuse `WorkspaceClient` instance across requests
- See `specs/001-databricks-integrations/research.md` for detailed patterns

**Lakebase Integration** (`server/services/lakebase_service.py`):
- SQLAlchemy with `psycopg2` driver for Postgres connection
- Connection string: `postgresql+psycopg2://token:<token>@<host>:<port>/<database>`
- Connection pooling: QueuePool with 5-10 connections
- Always filter by `user_id` for data isolation
- **Configuration check**: ALWAYS call `is_lakebase_configured()` before database operations
- **Graceful degradation**: Skip operations with debug log if not configured
- Tables: `user_preferences`, `model_inference_logs`, `performance_metrics`, `usage_events`
- **Available in local development**: Lakebase CAN be connected from local environment with proper credentials

**Model Serving Integration** (`server/services/model_serving_service.py`):
- Use Databricks SDK to list and invoke serving endpoints
- Timeout: 30 seconds for inference requests
- Error handling: Retry up to 3 times with exponential backoff
- Log all inference requests to Lakebase for observability

**Schema Detection Service** (`server/services/schema_detection_service.py`):
- Automatic schema detection for model serving endpoints (feature 004-dynamic-endpoint-input-schema)
- Detects endpoint types: Foundation models (Claude, GPT, Llama), MLflow models, or Unknown
- Foundation models: Returns chat format example in <500ms (fast path)
- MLflow models: Queries Unity Catalog Model Registry with 5s timeout, generates example from schema
- Graceful fallback: Returns generic template on timeout/error (doesn't block user workflow)
- Browser session caching: Caches schemas in sessionStorage to avoid repeated API calls
- Multi-user isolation: All detection events logged to Lakebase with user_id filtering
- Correlation ID propagation: All events include correlation_id for end-to-end tracing
- Error handling: Handles 429 rate limits (exponential backoff), 403 permissions, timeouts
- See `specs/004-dynamic-endpoint-input-schema/` for complete specification

**Metrics Service** (`server/services/metrics_service.py`):
- Application usage and performance metrics collection (feature 006-app-metrics)
- Automatic performance metric collection via FastAPI middleware for all API requests
- Usage event tracking for user interactions (page views, clicks, feature usage)
- Hybrid retention: 7 days raw metrics, 90 days aggregated hourly summaries
- Admin-only dashboard for monitoring application health and user behavior
- Tables: `performance_metrics`, `usage_events`, `aggregated_metrics`
- Scheduled aggregation job runs daily at 2 AM to manage data lifecycle
- See `specs/006-app-metrics/` for complete specification

**Admin Service** (`server/services/admin_service.py`):
- Admin privilege verification using Databricks Workspace API
- Checks if user has workspace admin role for metrics dashboard access
- 5-minute caching to reduce API calls and improve resilience
- Fail-secure: Returns 503 if API check fails, 403 if not admin
- Used by metrics endpoints and other admin-only features

**Design Bricks UI Components**:
- Constitution requirement: ALL UI components must use Design Bricks
- Component source: https://pulkitxchadha.github.io/DesignBricks
- Installation: `cd client && bun add @databricks/design-bricks`
- Migration path: Replace shadcn/ui components incrementally
- See component mapping in `specs/001-databricks-integrations/research.md`

### Frontend Development
- **Primary**: Use Design Bricks components for Databricks look-and-feel (Constitution requirement)
- **Legacy**: shadcn/ui components (being migrated to Design Bricks)
- Follow React Query patterns for API calls
- Use TypeScript strictly - no `any` types
- Import from auto-generated client: `import { apiClient } from '@/fastapi_client'`
- Client uses Design Bricks components with proper TypeScript configuration
- Design Bricks installation: `cd client && bun add @databricks/design-bricks`
- shadcn components (legacy): npx shadcn@latest add <component-name>

**🚨 CRITICAL: Frontend Build and Token Management**:
- Environment variables (including `VITE_DATABRICKS_USER_TOKEN`) are baked into JavaScript bundle at build time
- After refreshing authentication token, MUST rebuild frontend: `cd client && bun run build`
- Production mode: Copy new build to backend: `cp -r client/build/* build/`
- Users MUST reload browser (Cmd+R or Ctrl+R) to pick up new build
- Development mode: Vite dev server picks up .env.local changes automatically (no rebuild needed)

### Testing Methodology
- Test API endpoints using FastAPI docs interface
- Use browser dev tools for frontend debugging
- Check network tab for API request/response inspection
- Verify console for any JavaScript errors

### Deployment
- Use `./deploy.sh` for Databricks Apps deployment
- Automatically builds frontend and generates requirements.txt
- Configures app.yaml with environment variables
- Verifies deployment through Databricks CLI

### 🚨 CRITICAL: Post-Deployment Monitoring Workflow 🚨

**ALWAYS follow this workflow after any deployment:**

1. **Immediately after deployment, MUST run log monitoring:**
   ```bash
   # Monitor deployment logs for 60 seconds to catch installation issues
   uv run python dba_logz.py <app-url> --duration 60
   
   # Or search specifically for uvicorn startup messages:
   uv run python dba_logz.py <app-url> --search "Application startup complete\|Uvicorn running" --duration 60
   ```

2. **Verify successful uvicorn startup:**
   - **REQUIRED**: Look for these specific uvicorn startup messages in logs:
     - `INFO: Application startup complete.`
     - `INFO: Uvicorn running`
   - **REQUIRED**: Look for any Python exceptions, import errors, or dependency issues in the logs
   - **If uvicorn startup messages not seen after reasonable time, run without search filter to see all logs and find errors:**
     ```bash
     # If no startup messages found, check all logs for errors
     uv run python dba_logz.py <app-url> --duration 30
     ```
   - **If ANY exceptions occur during installation or startup, MUST fix and redeploy**

3. **Exception handling protocol:**
   - **If Python exceptions found**: Analyze the error, fix the issue in code, and redeploy immediately
   - **If dependency issues found**: Update requirements, fix dependencies, and redeploy immediately
   - **If uvicorn fails to start**: Debug the FastAPI app, fix the issue, and redeploy immediately
   - **Never leave a deployment in a broken state**

4. **Deployment verification checklist:**
   - ✅ No Python exceptions during installation
   - ✅ All dependencies installed successfully  
   - ✅ Uvicorn server started and listening
   - ✅ FastAPI app accessible at the deployed URL
   - ✅ No critical errors in the log stream

5. **Test deployed endpoints with `dba_client.py`:**
   ```bash
   # Test core endpoints to verify app is functional
   uv run python dba_client.py <app-url> /health
   uv run python dba_client.py <app-url> /docs  
   uv run python dba_client.py <app-url> /api/user/me
   ```

**This monitoring workflow ensures deployments are successful and functional before moving on to other tasks.**

- **IMPORTANT**: Use `dba_logz.py` for real-time log streaming with search capabilities
- App logs are also available at: `https://<app-url>/logz` (visit in browser - requires OAuth authentication)

### Environment Configuration
- Use `.env.local` for local development configuration
- Set environment variables and Databricks credentials
- Never commit `.env.local` to version control
- Use `./setup.sh` to create and update environment configuration

### Debugging Tips
- Verify environment variables are set correctly
- Use FastAPI docs for API testing: http://localhost:8000/docs
- Check browser console for frontend errors
- Use React Query DevTools for API state inspection
- **Check watch logs**: `tail -f /tmp/databricks-app-watch.log` for all development server output
- **Check process status**: `ps aux | grep databricks-app` or check PID file at `/tmp/databricks-app-watch.pid`
- **Force stop**: `kill $(cat /tmp/databricks-app-watch.pid)` or `pkill -f watch.sh`

### Key Files
- `server/app.py` - FastAPI application entry point
- `server/routers/` - API endpoint routers
- `server/lib/metrics_middleware.py` - Automatic performance metrics collection middleware
- `client/src/App.tsx` - React application entry point
- `client/src/pages/` - React page components
- `client/src/services/usageTracker.ts` - Frontend usage event tracking with batching
- `scripts/make_fastapi_client.py` - TypeScript client generator
- `scripts/aggregate_metrics.py` - Daily metrics aggregation job (scheduled at 2 AM)
- `pyproject.toml` - Python dependencies and project configuration
- `client/package.json` - Frontend dependencies and scripts
- `claude_scripts/` - Test scripts created by Claude for testing functionality

### API Documentation
- `docs/databricks_apis/` - Comprehensive API documentation for Databricks integrations
- `docs/databricks_apis/databricks_sdk.md` - Databricks SDK usage patterns
- `docs/databricks_apis/mlflow_genai.md` - MLflow GenAI for AI agents
- `docs/databricks_apis/model_serving.md` - Model serving endpoints and inference
- `docs/databricks_apis/workspace_apis.md` - Workspace file operations

### Feature Specifications
- `specs/001-databricks-integrations/` - Service integrations feature documentation
- `specs/001-databricks-integrations/spec.md` - Feature requirements and user stories
- `specs/001-databricks-integrations/research.md` - Technical decisions and implementation patterns
- `specs/001-databricks-integrations/data-model.md` - Entity definitions and database schemas
- `specs/001-databricks-integrations/contracts/` - OpenAPI contract specifications
- `specs/001-databricks-integrations/quickstart.md` - Testing and verification guide
- `specs/006-app-metrics/` - App usage and performance metrics feature documentation
- `specs/006-app-metrics/spec.md` - Metrics collection requirements and admin dashboard
- `specs/006-app-metrics/research.md` - Metrics architecture and technology choices
- `specs/006-app-metrics/data-model.md` - Metrics entities and lifecycle management
- `specs/006-app-metrics/contracts/` - Metrics API contract specifications
- `specs/006-app-metrics/quickstart.md` - Implementation guide with TDD workflow

### Documentation Files
- `docs/product.md` - Product requirements document (created during /dba workflow)
- `docs/design.md` - Technical design document (created during /dba workflow)
- These files are generated through iterative collaboration with the user during the /dba command

### Common Issues
- If TypeScript client is not found, run the client generation script manually
- If hot reload not working, restart `./watch.sh`
- If dependencies missing, run `./setup.sh` to reinstall

Remember: This is a development template focused on rapid iteration and modern tooling.
