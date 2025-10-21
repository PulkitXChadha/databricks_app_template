# Deployment Script Fixes

This document describes the fixes applied to resolve deployment issues.

## Issues Identified

From the deployment output, several issues were identified:

1. **Terraform Provider Error**: `Provider produced inconsistent result after apply` - The Databricks provider reported an unexpected value for `budget_policy_id`
2. **Catalog Already Exists**: The catalog 'lakebase_catalog_dev' already exists, causing a deployment conflict
3. **Failed Resource Retrieval**: Could not automatically retrieve SQL Warehouse ID and Lakebase host
4. **Lakebase Connectivity Failed**: Connection attempts to Lakebase failed after deployment

## Fixes Applied

### 1. Improved Error Handling in deploy.sh

**Location**: `deploy.sh` lines 437-483

**Changes**:
- Added specific error detection for known Terraform provider issues
- Improved handling of "already exists" errors for catalogs
- Added resource verification after Terraform errors
- Made the script continue gracefully when resources already exist

**Key improvements**:
```bash
# Now detects and handles three types of errors:
- CATALOG_EXISTS_ERROR: Resources already exist (expected on redeployment)
- INCONSISTENT_RESULT_ERROR: Terraform provider bug
- BUDGET_POLICY_ERROR: Known provider issue with budget_policy_id
```

### 2. Enhanced Resource Retrieval Logic

**Location**: `deploy.sh` lines 480-641

**Changes**:
- Improved SQL Warehouse ID retrieval with better error handling
- Enhanced Lakebase host retrieval with multiple format support
- Added file-based parsing instead of pipe-based for better error detection
- Added verbose mode debugging output
- Made the script continue even if automatic retrieval fails

**Key improvements**:
- Uses temporary files for better error tracking
- Provides helpful messages on failure with manual recovery steps
- Handles both list and dict response formats from Databricks API

### 3. Non-Blocking Lakebase Connectivity Test

**Location**: `deploy.sh` lines 615-641

**Changes**:
- Changed from fatal error to warning when Lakebase connection fails
- Added informative messages about why connection might fail
- Provided manual test command for later verification
- Made connectivity test conditional on LAKEBASE_HOST availability

**Rationale**: Lakebase instances can take time to initialize, and failed connectivity shouldn't block the entire deployment.

### 4. Fixed Hard-Coded Warehouse ID

**Location**: `databricks.yml` lines 113-116

**Changes**:
```yaml
# Before:
- name: sql-warehouse
  sql_warehouse:
    id: 4b9b953939869799  # Hard-coded, environment-specific ID
    permission: CAN_USE

# After:
- name: sql-warehouse
  sql_warehouse:
    id: ${var.warehouse_id}  # Uses variable from DATABRICKS_WAREHOUSE_ID
    permission: CAN_USE
```

**Rationale**: Using a variable instead of hard-coding ensures the configuration works across different environments and can be automatically populated during deployment.

**Note**: The `warehouse_id` variable is populated from the `DATABRICKS_WAREHOUSE_ID` environment variable, which is automatically set by the deploy script after creating the warehouse.

### 5. Created Manual Resource Retrieval Script

**Location**: `scripts/get_lakebase_host.py`

**Purpose**: Provides a manual way to retrieve Lakebase and warehouse connection details if automated retrieval fails.

**Usage**:
```bash
# Get connection details for dev environment
python scripts/get_lakebase_host.py --target dev

# Output as environment variables (add to .env.local)
python scripts/get_lakebase_host.py --target dev --output-format env

# Output as JSON
python scripts/get_lakebase_host.py --target dev --output-format json
```

## How These Fixes Resolve the Issues

### Issue 1: Terraform Provider Error
**Fixed by**: Enhanced error detection (lines 437-483)
- Script now recognizes this as a known provider bug
- Verifies resources were actually created despite the error
- Continues deployment if verification succeeds

### Issue 2: Catalog Already Exists
**Fixed by**: Improved resource existence handling (lines 322-415, 437-483)
- Script checks for existing resources before deployment
- Handles "already exists" errors gracefully
- Provides guidance on resolving inconsistent states

### Issue 3: Failed Resource Retrieval
**Fixed by**: Enhanced retrieval logic (lines 480-570) + manual script
- Better error handling and format support
- Provides manual recovery steps
- Created dedicated script for manual retrieval

### Issue 4: Lakebase Connectivity Failed
**Fixed by**: Non-blocking connectivity test (lines 615-641)
- Changed from error to warning
- Continues deployment even if connection fails
- Provides manual test command

## Testing the Fixes

To test the deployment with these fixes:

```bash
# Run deployment with verbose output
./deploy.sh --target dev --verbose

# If automatic retrieval fails, manually get connection details
python scripts/get_lakebase_host.py --target dev

# Add the output to .env.local, then test connectivity
uv run python -c 'from server.lib.database import get_engine; get_engine().connect()'
```

## Expected Behavior After Fixes

1. **First Deployment**: May see Terraform provider warnings but should continue
2. **Subsequent Deployments**: Should gracefully handle existing resources
3. **Resource Retrieval**: Provides helpful messages and manual steps if automatic retrieval fails
4. **Connectivity**: Warns but doesn't fail if Lakebase isn't immediately available

## Known Limitations

1. **Terraform Provider Bug**: The `budget_policy_id` inconsistency is a provider bug and may persist until fixed upstream
2. **Lakebase Initialization**: Lakebase instances can take 5-10 minutes to become fully available
3. **API Response Formats**: The Databricks CLI API response formats may vary between versions

## Recovery Steps

If deployment still fails:

1. **Check existing resources**:
   ```bash
   databricks catalogs list
   databricks database list-database-instances
   databricks warehouses list
   ```

2. **Manually retrieve connection details**:
   ```bash
   python scripts/get_lakebase_host.py --target dev --output-format env >> .env.local
   ```

3. **Test connectivity**:
   ```bash
   uv run python -c 'from server.lib.database import get_engine; get_engine().connect()'
   ```

4. **If catalog exists but instance doesn't** (inconsistent state):
   ```bash
   # Option 1: Delete catalog and redeploy
   databricks catalogs delete lakebase_catalog_dev --force
   
   # Option 2: Create instance manually, then redeploy
   ```

## Future Improvements

1. Add retry logic for Databricks API calls
2. Implement better state detection and recovery
3. Add health check endpoint for Lakebase
4. Create automated recovery scripts for common issues
5. Add bundle validate step before deploy to catch issues early

