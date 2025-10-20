# Deployment Checklist: App Usage and Performance Metrics

**Feature**: 006-app-metrics  
**Purpose**: Pre-deployment and post-deployment validation gates per Constitution Principle XII

## Pre-Deployment Gates

All items MUST pass before deploying to any environment.

### 1. Test Suite Execution ✅

- [ ] Run full test suite: `pytest tests/ -v`
  - **Expected**: ALL tests pass (contract + integration + unit)
  - **Action on failure**: Fix failing tests before deployment

### 2. Bundle Validation ✅

- [ ] Run bundle validation: `databricks bundle validate`
  - **Expected**: Exit code 0 (no validation errors)
  - **Action on failure**: Fix databricks.yml configuration errors

### 3. Code Quality ✅

- [ ] Run linter: `ruff check server/ --fix`
  - **Expected**: 0 errors (warnings acceptable)
  - **Action on failure**: Fix linter errors

- [ ] Run frontend linter: `cd client && bun run lint`
  - **Expected**: 0 errors (warnings acceptable)
  - **Action on failure**: Fix linter errors

### 4. Type Checking ✅

- [ ] Run frontend type checking: `cd client && bun run tsc --noEmit`
  - **Expected**: No type errors
  - **Action on failure**: Fix TypeScript errors

- [ ] Run backend type checking: `cd server && ruff check --select=F821`
  - **Expected**: No undefined name errors
  - **Action on failure**: Fix Python type errors

### 5. Smoke Testing ✅

- [ ] Start local development server: `./watch.sh`
  - **Expected**: Backend and frontend start without errors

- [ ] Test metrics API endpoints with curl:
  ```bash
  # Test admin access (requires valid token)
  curl -H "X-Forwarded-Access-Token: $TOKEN" http://localhost:8000/api/v1/metrics/performance
  
  # Test non-admin returns 403
  curl -H "X-Forwarded-Access-Token: $NON_ADMIN_TOKEN" http://localhost:8000/api/v1/metrics/performance
  ```
  - **Expected**: Admin gets 200, non-admin gets 403

### 6. Aggregation Script Testing ✅

- [ ] Run aggregation script manually: `uv run aggregate-metrics`
  - **Expected**: Script completes successfully with log output
  - **Action on failure**: Debug aggregation logic

### 7. Documentation Review ✅

- [ ] Review CLAUDE.md updates for accuracy
  - **Expected**: Metrics system patterns documented
  - **Action on failure**: Update documentation

---

## Post-Deployment Validation

Run these checks immediately after deploying to any environment.

### 1. Log Monitoring (60 seconds) 📊

- [ ] Run log monitor: `python dba_logz.py` for 60 seconds
  - **Expected**: Uvicorn startup messages, no Python exceptions
  - **Look for**: `INFO: Application startup complete`
  - **Action on failure**: Check logs for exceptions, redeploy if needed

### 2. Application Health Check 🏥

- [ ] Access deployed application URL
  - **Expected**: Application loads without errors

- [ ] Navigate to Metrics dashboard as admin
  - **Expected**: Dashboard displays (may show "No data available" if fresh deployment)

### 3. API Endpoint Testing 🔌

- [ ] Test core metrics endpoints with `dba_client.py`
  ```bash
  python dba_client.py --endpoint /api/v1/metrics/performance
  ```
  - **Expected**: 200 response for admin, 403 for non-admin

### 4. Metrics Collection Verification 📈

- [ ] Make 5-10 API requests to various endpoints
- [ ] Query metrics API after 60 seconds
  - **Expected**: Metric records created in database
  - **Action on failure**: Check middleware registration, database connection

### 5. Database Verification 💾

- [ ] Connect to Lakebase and verify tables exist:
  ```sql
  SELECT COUNT(*) FROM performance_metrics;
  SELECT COUNT(*) FROM usage_events;
  SELECT COUNT(*) FROM aggregated_metrics;
  ```
  - **Expected**: Tables exist (counts may be 0 for fresh deployment)

### 6. Scheduled Job Verification ⏰

- [ ] Check Databricks workspace jobs list
  - **Expected**: `metrics_aggregation_job` appears in jobs list
  - **Schedule**: Daily at 2 AM UTC
  - **Action on failure**: Verify databricks.yml job configuration

---

## Rollback Criteria 🚨

Immediately rollback if any of these occur:

1. **Test suite failure rate >5%** in post-deployment smoke tests
2. **Application fails to start** (uvicorn startup errors)
3. **Database migration fails** (Alembic errors)
4. **Metrics collection blocks user requests** (requests hang or timeout)
5. **Admin check always fails** (all users denied access)

---

## Deployment Success Criteria ✅

- [ ] All pre-deployment gates passed
- [ ] All post-deployment validations passed
- [ ] No CRITICAL or ERROR logs in first 60 seconds
- [ ] Metrics dashboard accessible to admin users
- [ ] Metrics collection creating database records

---

## Notes

- **First deployment**: Expect "No data available" in dashboard until metrics accumulate
- **Admin access**: Requires Databricks workspace admin privileges (configurable via `ADMIN_GROUPS` env var)
- **Aggregation job**: First run scheduled for 2 AM UTC next day; test manually if needed
- **Performance**: Monitor P95 latency remains <185ms (baseline 180ms + 5ms overhead)

**Last Updated**: 2025-10-19  
**Owner**: Development Team

