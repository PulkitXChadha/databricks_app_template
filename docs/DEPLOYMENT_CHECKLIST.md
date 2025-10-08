# Deployment Checklist: Databricks App Template

**Version**: 1.0.0  
**Last Updated**: October 8, 2025  
**Status**: Complete Guide for Dev & Prod Deployments

---

## Overview

This checklist guides you through deploying the Databricks App Template to both development and production environments. Follow each section in order to ensure a successful deployment.

**Deployment Modes:**
- 🧪 **Development** (`--target dev`) - Testing and iteration
- 🚀 **Production** (`--target prod`) - Live application

---

## 📋 Phase 1: Pre-Deployment Preparation

### 1.1 System Dependencies ✅

Verify all required tools are installed:

- [ ] **Git** - Version control
  ```bash
  git --version  # Any recent version
  ```

- [ ] **uv** - Python package manager
  ```bash
  uv --version  # Should be installed via Homebrew/Cargo
  ```

- [ ] **bun** - JavaScript package manager
  ```bash
  bun --version  # Should be 1.0+
  ```

- [ ] **Node.js** - Runtime for Playwright (optional)
  ```bash
  node --version  # Should be 18.0+
  ```

- [ ] **Databricks CLI** - Managed by uv
  ```bash
  databricks --version  # Auto-installed with uv sync
  ```

- [ ] **Python 3.11+** - Managed by uv
  ```bash
  uv run python --version  # Should be 3.11+
  ```

**Quick Setup (if missing tools):**
```bash
./setup.sh  # Interactive setup script handles all dependencies
```

---

### 1.2 Databricks Workspace Requirements ✅

Verify your Databricks workspace has the necessary features enabled:

- [ ] **Unity Catalog** enabled in workspace
  ```bash
  databricks catalogs list  # Should return catalog list
  ```

- [ ] **Lakebase** available in workspace
  - Check Databricks Console → Data → Lakebase
  - Verify you have permissions to create database instances

- [ ] **SQL Warehouses** - Can create/manage warehouses
  ```bash
  databricks warehouses list  # Check access
  ```

- [ ] **Model Serving** (optional but recommended)
  - Check Databricks Console → Serving
  - Verify you have endpoint creation permissions

- [ ] **Apps Platform** enabled
  ```bash
  databricks apps list  # Should work without error
  ```

---

### 1.3 Authentication & Credentials ✅

Authenticate with Databricks:

- [ ] **OAuth Authentication** via Databricks CLI
  ```bash
  databricks auth login --host https://your-workspace.cloud.databricks.com
  ```

- [ ] **Verify Authentication**
  ```bash
  databricks auth env  # Should show active authentication
  databricks current-user me  # Should return your user info
  ```

- [ ] **Check Permissions**
  - Can create SQL Warehouses
  - Can create Lakebase instances
  - Can deploy Databricks Apps
  - Can access Unity Catalog

**Troubleshooting:**
```bash
# Re-authenticate if needed
databricks auth login --force-persistent
```

---

### 1.4 Repository Setup ✅

Prepare your codebase:

- [ ] **Clone/Pull Latest Code**
  ```bash
  git pull origin main  # Or your deployment branch
  git status  # Ensure clean working directory
  ```

- [ ] **Install Python Dependencies**
  ```bash
  uv sync  # Installs all Python packages from pyproject.toml
  ```

- [ ] **Install Frontend Dependencies**
  ```bash
  cd client
  bun install
  cd ..
  ```

- [ ] **Verify Installation**
  ```bash
  uv run python -c "import fastapi; import sqlalchemy; print('OK')"
  cd client && bun run build && cd ..  # Test build
  ```

---

## 📋 Phase 2: Environment Configuration

### 2.1 Environment Variables (.env.local) ✅

Create or update `.env.local` in project root:

- [ ] **Create file from template**
  ```bash
  touch .env.local  # Or copy from .env.local.example
  ```

- [ ] **Set Databricks Workspace Configuration**
  ```bash
  DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
  ```

- [ ] **Set Unity Catalog Configuration** (will update after deployment)
  ```bash
  DATABRICKS_WAREHOUSE_ID=  # Leave empty, will be set in Phase 3
  DATABRICKS_CATALOG=main
  DATABRICKS_SCHEMA=samples  # For dev; use 'default' for prod
  ```

- [ ] **Set Lakebase Configuration** (will update after deployment)
  ```bash
  LAKEBASE_HOST=  # Leave empty, will be set in Phase 3
  LAKEBASE_PORT=5432
  LAKEBASE_DATABASE=app_database
  LAKEBASE_INSTANCE_NAME=  # Leave empty, will be set in Phase 3
  ```

- [ ] **Set Model Serving Configuration** (optional)
  ```bash
  MODEL_SERVING_ENDPOINT=your-endpoint-name  # Or leave empty
  MODEL_SERVING_TIMEOUT=30
  ```

- [ ] **Set Observability Configuration**
  ```bash
  LOG_LEVEL=INFO
  LOG_FORMAT=json
  ```

- [ ] **Set App Configuration**
  ```bash
  DATABRICKS_APP_NAME=databricks-app-template-dev  # Or -prod
  DBA_SOURCE_CODE_PATH=/Workspace/Users/your.email@company.com/databricks-app-template
  DATABRICKS_AUTH_TYPE=databricks-cli  # OAuth via CLI
  ```

**Security Note:** Never commit `.env.local` to version control!

---

### 2.2 Databricks Bundle Configuration (databricks.yml) ✅

Verify bundle configuration is correct:

- [ ] **Review Bundle Variables**
  - Edit `databricks.yml` if needed
  - Check `warehouse_cluster_size` (default: 2X-Small)
  - Check `lakebase_capacity` (default: CU_1)
  - Verify catalog/schema names match your workspace

- [ ] **Validate Bundle Syntax**
  ```bash
  databricks bundle validate --target dev
  ```
  - Should return: ✓ Configuration valid
  - Fix any YAML syntax errors

- [ ] **Review Dev vs Prod Differences**
  - Dev: Resource names suffixed with `-dev`
  - Prod: No suffix (production names)
  - Prod: Different permissions (admins: CAN_MANAGE, users: CAN_USE)
  - Prod: Different auto-stop times, serverless settings

---

## 📋 Phase 3: Resource Provisioning

### 3.1 Deploy Databricks Asset Bundle ✅

Deploy infrastructure resources to Databricks:

**For Development Environment:**

- [ ] **Deploy Bundle to Dev**
  ```bash
  databricks bundle deploy --target dev
  ```
  Expected: 5-10 minutes for initial provisioning

- [ ] **Verify Resources Created**
  ```bash
  databricks bundle summary --target dev
  ```
  Should show:
  - SQL Warehouse: `databricks-app-warehouse-dev`
  - Lakebase Instance: `databricks-app-lakebase-dev`
  - Lakebase Catalog: `lakebase_catalog_dev`
  - App: `databricks-app-template-dev`

- [ ] **Retrieve Auto-Generated Values**
  ```bash
  # SQL Warehouse ID
  databricks warehouses list | grep "databricks-app-warehouse-dev"
  
  # Lakebase Host (check Databricks Console → Catalog → lakebase_catalog_dev)
  # Or from bundle output during deployment
  ```

- [ ] **Update .env.local with Generated Values**
  ```bash
  # Update these lines in .env.local:
  DATABRICKS_WAREHOUSE_ID=abc123def456  # From warehouses list
  LAKEBASE_HOST=xyz789.cloud.databricks.com  # From catalog details
  LAKEBASE_INSTANCE_NAME=databricks-app-lakebase-dev  # Logical bundle name
  ```

**For Production Environment (later):**

Same steps, but use `--target prod` and different resource names.

---

### 3.2 Wait for Resources to be Ready ✅

Ensure all resources are in READY state:

- [ ] **Check SQL Warehouse Status**
  ```bash
  databricks warehouses get <warehouse-id>
  ```
  Expected: `state: RUNNING`

- [ ] **Check Lakebase Instance Status**
  - Visit Databricks Console → Data → Lakebase
  - Instance should show: Status = READY
  - Wait 2-3 minutes for DNS propagation if just created

- [ ] **Test Lakebase Connectivity**
  ```bash
  # This will fail if Lakebase isn't ready
  uv run python -c "from server.lib.database import get_engine; get_engine().connect()"
  ```

---

## 📋 Phase 4: Database Setup

### 4.1 Run Database Migrations ✅

Create necessary Lakebase tables:

- [ ] **Verify Alembic Configuration**
  ```bash
  cat alembic.ini  # Check configuration
  ls migrations/versions/  # Check migration files exist
  ```

- [ ] **Run Migrations**
  ```bash
  alembic upgrade head
  ```
  Expected output:
  ```
  INFO  [alembic.runtime.migration] Running upgrade  -> 001_create_user_preferences
  INFO  [alembic.runtime.migration] Running upgrade 001_create_user_preferences -> 002_create_model_inference_logs
  ```

- [ ] **Verify Current Migration**
  ```bash
  alembic current
  ```
  Should show: `002_create_model_inference_logs (head)`

- [ ] **Verify Tables Created**
  ```bash
  uv run python -c "
  from server.lib.database import get_engine
  from sqlalchemy import inspect
  engine = get_engine()
  inspector = inspect(engine)
  tables = inspector.get_table_names()
  print('Tables:', tables)
  assert 'user_preferences' in tables
  assert 'model_inference_logs' in tables
  print('✅ All tables exist')
  "
  ```

---

### 4.2 Create Sample Data (Optional) ✅

Populate Unity Catalog and Lakebase with test data:

- [ ] **Create Unity Catalog Sample Data**
  ```bash
  uv run python scripts/setup_sample_data.py unity-catalog --rows 100
  ```
  Creates: `main.samples.demo_data` table

- [ ] **Create Lakebase Sample Data**
  ```bash
  uv run python scripts/setup_sample_data.py lakebase --num-records 5
  ```
  Creates: Sample user preferences

- [ ] **Create All Sample Data**
  ```bash
  uv run python scripts/setup_sample_data.py create-all
  ```

- [ ] **Verify Sample Data**
  ```bash
  # Unity Catalog
  databricks sql-queries --warehouse-id <id> --query "SELECT COUNT(*) FROM main.samples.demo_data"
  
  # Lakebase
  uv run python -c "
  from server.lib.database import get_session
  from server.models.user_preference import UserPreference
  with get_session() as session:
      count = session.query(UserPreference).count()
      print(f'Sample preferences: {count}')
  "
  ```

---

## 📋 Phase 5: Local Testing (Pre-Deployment)

### 5.1 Start Local Development Servers ✅

Test the app locally before deploying:

- [ ] **Start Watch Script**
  ```bash
  ./watch.sh
  ```
  This starts both frontend (port 5173) and backend (port 8000)

- [ ] **Verify Servers Running**
  ```bash
  # Backend
  curl http://localhost:8000/health
  
  # Frontend
  curl http://localhost:5173
  ```

- [ ] **Check Logs**
  ```bash
  tail -f /tmp/databricks-app-watch.log
  ```

---

### 5.2 Test Core Functionality ✅

Verify all integrations work locally:

- [ ] **Test Health Endpoint**
  ```bash
  uv run python dba_client.py /health --app_url http://localhost:8000
  ```
  Expected: `{"status": "healthy"}`

- [ ] **Test User Endpoint**
  ```bash
  uv run python dba_client.py /api/user/me --app_url http://localhost:8000
  ```
  Expected: User profile with email

- [ ] **Test Unity Catalog**
  ```bash
  curl "http://localhost:8000/api/unity-catalog/tables?catalog=main&schema=samples&limit=10"
  ```
  Expected: Table data with pagination

- [ ] **Test Lakebase Preferences**
  ```bash
  # List preferences
  curl http://localhost:8000/api/preferences
  
  # Create preference
  curl -X POST http://localhost:8000/api/preferences \
    -H "Content-Type: application/json" \
    -d '{"preference_key": "theme", "preference_value": {"mode": "dark"}}'
  ```

- [ ] **Test Model Serving** (if endpoint configured)
  ```bash
  # List endpoints
  curl http://localhost:8000/api/model-serving/endpoints
  
  # Invoke model (if endpoint exists)
  curl -X POST http://localhost:8000/api/model-serving/invoke \
    -H "Content-Type: application/json" \
    -d '{"endpoint_name": "your-endpoint", "inputs": {"text": "test"}}'
  ```

- [ ] **Test Frontend UI**
  - Visit http://localhost:5173
  - Navigate through all tabs:
    - Welcome page loads
    - Unity Catalog tab works
    - Model Serving tab works
    - Preferences tab works

---

### 5.3 Run Integration Tests ✅

Execute automated test suites:

- [ ] **Multi-User Isolation Test**
  ```bash
  uv run pytest tests/integration/test_multi_user_isolation.py -v
  ```

- [ ] **Observability Test**
  ```bash
  uv run pytest tests/integration/test_observability.py -v
  ```

- [ ] **Pagination Performance Test**
  ```bash
  uv run pytest tests/integration/test_pagination_performance.py -v
  ```

- [ ] **Accessibility Compliance Test**
  ```bash
  uv run pytest tests/integration/test_accessibility_compliance.py -v
  ```

- [ ] **Model Input Validation Test**
  ```bash
  uv run pytest tests/integration/test_model_input_validation.py -v
  ```

- [ ] **All Tests Pass**
  ```bash
  uv run pytest tests/integration/ -v
  ```

---

### 5.4 Verify Structured Logging ✅

Test correlation ID propagation:

- [ ] **Test with Custom Request ID**
  ```bash
  curl -H "X-Request-ID: test-trace-123" http://localhost:8000/health
  ```

- [ ] **Check Logs for Correlation ID**
  - Look for `test-trace-123` in terminal output
  - Verify JSON structured format
  - Verify correlation ID preserved in response header

---

## 📋 Phase 6: Build & Deployment

### 6.1 Pre-Deployment Validation ✅

Final checks before deploying:

- [ ] **Stop Local Servers**
  ```bash
  pkill -f watch.sh
  rm -f /tmp/databricks-app-watch.pid
  ```

- [ ] **Code Quality Checks**
  ```bash
  ./fix.sh  # Format Python and TypeScript code
  ```

- [ ] **Type Checking** (if using mypy)
  ```bash
  uv run mypy server/ --strict --show-error-codes
  ```

- [ ] **Linter Checks** (if using ruff)
  ```bash
  uv run ruff check server/
  ```

- [ ] **Build Frontend**
  ```bash
  cd client
  bun run build
  cd ..
  ```
  Expected: Build completes without errors

- [ ] **Generate Requirements**
  ```bash
  uv run python scripts/generate_semver_requirements.py
  cat requirements.txt  # Verify no editable installs
  ```

---

### 6.2 Deploy to Databricks Apps ✅

Deploy the application:

**For Development Environment:**

- [ ] **Deploy App**
  ```bash
  ./deploy.sh --verbose --create
  ```
  - `--create`: Creates app if it doesn't exist
  - `--verbose`: Shows detailed deployment logs

- [ ] **Monitor Deployment**
  - Watch for successful completion message
  - Note the app URL from output
  - Deployment time: 2-5 minutes typically

- [ ] **Check App Status**
  ```bash
  ./app_status.sh --verbose
  ```
  Expected: App state = RUNNING

**For Production Environment (after dev is verified):**

Same steps, but:
- Update `.env.local` with production values
- Use `DATABRICKS_APP_NAME=databricks-app-template` (no -dev suffix)
- Deploy bundle with `--target prod`
- Run migrations against production Lakebase

---

## 📋 Phase 7: Post-Deployment Verification

### 7.1 Check Deployment Status ✅

Verify app deployed successfully:

- [ ] **List Apps**
  ```bash
  databricks apps list
  ```
  Should show your app in the list

- [ ] **Get App Details**
  ```bash
  databricks apps get databricks-app-template-dev --output json
  ```
  Expected: `status: RUNNING`, `url: https://...`

- [ ] **Check Workspace Files**
  ```bash
  ./app_status.sh --verbose
  ```
  Verify all files synced correctly

---

### 7.2 Test Deployed Application ✅

Test the live deployed app:

- [ ] **Access App URL**
  - Visit app URL from deployment output
  - Should load welcome page
  - Verify Databricks authentication works

- [ ] **Test API Endpoints**
  ```bash
  # Auto-detects deployed app URL
  uv run python dba_client.py /health
  uv run python dba_client.py /api/user/me
  uv run python dba_client.py /api/preferences
  ```

- [ ] **Test All Tabs in UI**
  - Unity Catalog queries work
  - Preferences CRUD operations work
  - Model Serving invocations work (if configured)

- [ ] **Check Application Logs**
  - Visit `<app-url>/logz` in browser
  - Verify structured logging visible
  - Check for any errors

- [ ] **Stream Logs for Debugging**
  ```bash
  uv run python dba_logz.py --duration -1  # Stream continuously
  ```

---

### 7.3 Verify Multi-User Isolation ✅

Test data isolation between users:

- [ ] **Test with User A**
  - Create preference: `theme = dark`
  - Note user_id in logs

- [ ] **Test with User B** (different account)
  - Create preference: `theme = light`
  - Verify User A's preference NOT visible
  - Verify User B sees only their own data

- [ ] **Confirm Isolation**
  - Each user sees only their own preferences
  - No cross-user data leakage

---

### 7.4 Performance Verification ✅

Verify performance meets requirements:

- [ ] **Single User Response Times**
  - Unity Catalog queries: < 500ms (for ≤100 rows)
  - Preferences operations: < 300ms
  - Model inference: < 2s

- [ ] **Concurrent User Testing**
  ```bash
  # Simulate 10 concurrent users
  # (Create a load testing script or use existing tools)
  ```

- [ ] **Connection Pool Health**
  - Check no connection pool exhaustion errors
  - Monitor active vs idle connections

---

## 📋 Phase 8: Production Deployment

### 8.1 Pre-Production Checklist ✅

Before deploying to production:

- [ ] **Dev Deployment Successful**
  - All dev tests passed
  - No critical issues found
  - Users tested dev environment

- [ ] **Review Production Configuration**
  - Different resource names (no `-dev` suffix)
  - Production capacity settings
  - Production permissions (admins: CAN_MANAGE, users: CAN_USE)
  - Production schema (`default` vs `samples`)

- [ ] **Backup Existing Production** (if applicable)
  - Export current production data
  - Document current configuration
  - Plan rollback procedure

- [ ] **Communication Plan**
  - Notify stakeholders of deployment
  - Document expected downtime (if any)
  - Prepare rollback plan

---

### 8.2 Production Deployment Steps ✅

Deploy to production environment:

- [ ] **Validate Production Bundle**
  ```bash
  databricks bundle validate --target prod
  ```

- [ ] **Deploy Production Bundle**
  ```bash
  databricks bundle deploy --target prod
  ```
  This provisions:
  - SQL Warehouse: `databricks-app-warehouse`
  - Lakebase: `databricks-app-lakebase`
  - App: `databricks-app-template`

- [ ] **Update Production .env.local**
  ```bash
  # Create .env.production with prod values
  DATABRICKS_WAREHOUSE_ID=<prod-warehouse-id>
  LAKEBASE_HOST=<prod-lakebase-host>
  LAKEBASE_INSTANCE_NAME=databricks-app-lakebase  # No -dev suffix
  DATABRICKS_SCHEMA=default  # Prod uses default schema
  DATABRICKS_APP_NAME=databricks-app-template
  ```

- [ ] **Run Production Migrations**
  ```bash
  source .env.production  # Load production env vars
  alembic upgrade head
  ```

- [ ] **Deploy Production App**
  ```bash
  ./deploy.sh --verbose
  ```

- [ ] **Verify Production Deployment**
  ```bash
  databricks apps list | grep databricks-app-template
  ./app_status.sh --verbose
  ```

---

### 8.3 Production Validation ✅

Verify production deployment:

- [ ] **Test with Admin Account**
  - Should have CAN_MANAGE permissions
  - Can access all features

- [ ] **Test with Regular User Account**
  - Should have CAN_USE permissions
  - Cannot modify app settings
  - Can use app features

- [ ] **Verify Data Isolation**
  - Production data separate from dev
  - No dev data visible in prod
  - User data properly isolated

- [ ] **Monitor Production Logs**
  ```bash
  uv run python dba_logz.py --duration -1
  ```
  - Watch for errors
  - Verify expected traffic
  - Check performance metrics

- [ ] **Load Testing** (optional)
  - Simulate expected production load
  - Verify performance under load
  - Check resource utilization

---

## 📋 Phase 9: Monitoring & Maintenance

### 9.1 Ongoing Monitoring ✅

Set up continuous monitoring:

- [ ] **Regular Health Checks**
  ```bash
  # Add to cron or monitoring tool
  */5 * * * * curl https://your-app-url/health
  ```

- [ ] **Log Monitoring**
  - Set up alerts for ERROR level logs
  - Monitor correlation ID patterns
  - Track performance metrics

- [ ] **Resource Monitoring**
  - SQL Warehouse utilization
  - Lakebase connection pool usage
  - Model Serving endpoint health

- [ ] **Performance Metrics**
  - Response times
  - Error rates
  - User activity patterns

---

### 9.2 Maintenance Tasks ✅

Regular maintenance activities:

- [ ] **Weekly Tasks**
  - Review error logs
  - Check resource utilization
  - Verify all integrations healthy

- [ ] **Monthly Tasks**
  - Review and update dependencies
  - Analyze performance trends
  - Optimize slow queries
  - Review and clean up old data (if applicable)

- [ ] **Quarterly Tasks**
  - Security audit
  - Capacity planning review
  - Update documentation
  - Test disaster recovery procedures

---

## 📋 Troubleshooting Guide

### Common Issues & Solutions

#### Deployment Fails

**Issue**: `databricks bundle deploy` fails

**Solutions**:
1. Check bundle validation: `databricks bundle validate --target dev --debug`
2. Verify authentication: `databricks auth env`
3. Check workspace permissions
4. Review error message carefully

---

#### App Not Starting

**Issue**: App deployed but not accessible

**Solutions**:
1. Check logs: Visit `<app-url>/logz` in browser
2. Verify environment variables in app settings
3. Test locally: `./run_app_local.sh --verbose`
4. Check workspace files: `./app_status.sh --verbose`

---

#### Database Connection Errors

**Issue**: Cannot connect to Lakebase

**Solutions**:
1. Verify `LAKEBASE_INSTANCE_NAME` uses logical name (not UUID)
2. Check instance naming format (hyphens vs underscores)
3. Verify OAuth token generation: `databricks auth env`
4. Wait 2-3 minutes for DNS propagation after provisioning
5. Test connection: `uv run python -c "from server.lib.database import get_engine; get_engine().connect()"`

---

#### Model Serving Failures

**Issue**: Model inference requests fail

**Solutions**:
1. Check endpoint state: `curl http://localhost:8000/api/model-serving/endpoints`
2. Verify endpoint is in READY state
3. Check `MODEL_SERVING_ENDPOINT` environment variable
4. Verify permissions for model serving

---

#### Permission Denied Errors

**Issue**: Cannot access Unity Catalog tables

**Solutions**:
1. Check grants: `SHOW GRANTS ON TABLE main.samples.demo_data`
2. Grant permissions: `GRANT SELECT ON TABLE main.samples.demo_data TO \`user@company.com\``
3. Verify catalog/schema access
4. Use table owner account for testing

---

## 📋 Success Criteria

### Deployment Complete When:

- [ ] ✅ All bundle resources provisioned and RUNNING
- [ ] ✅ Database migrations completed successfully
- [ ] ✅ App accessible at public URL
- [ ] ✅ All API endpoints responding correctly
- [ ] ✅ UI loads and all tabs functional
- [ ] ✅ Multi-user isolation verified
- [ ] ✅ Structured logging with correlation IDs working
- [ ] ✅ Performance meets requirements (<500ms queries, <2s inference)
- [ ] ✅ Integration tests pass
- [ ] ✅ Production permissions configured correctly
- [ ] ✅ Monitoring and alerting set up

---

## 📚 Additional Resources

### Documentation
- [README.md](../README.md) - Project overview
- [Quickstart Guide](../specs/001-databricks-integrations/quickstart.md) - Detailed setup
- [Specification](../specs/001-databricks-integrations/spec.md) - Feature requirements
- [API Contracts](../specs/001-databricks-integrations/contracts/) - OpenAPI specs

### Scripts
- `./setup.sh` - Interactive environment setup
- `./watch.sh` - Start local dev servers
- `./deploy.sh` - Deploy to Databricks Apps
- `./app_status.sh` - Check deployment status
- `./run_app_local.sh` - Test locally in container
- `scripts/validate_deployment.sh` - Deployment validation

### Support
- **GitHub Issues**: Report bugs and feature requests
- **Databricks Documentation**: https://docs.databricks.com
- **Databricks Apps Guide**: https://docs.databricks.com/en/dev-tools/databricks-apps/

---

**🎉 Deployment Complete!**

Your Databricks App Template is now deployed and ready for use. Remember to:
- Monitor logs regularly
- Keep dependencies updated
- Review security best practices
- Test changes in dev before prod
- Document any custom modifications

---

**Last Updated**: October 8, 2025  
**Version**: 1.0.0

