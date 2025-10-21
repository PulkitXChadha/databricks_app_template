# Quick Fix Guide for Deployment Issues

## Summary

The deployment script has been fixed to handle common issues:

✅ **Terraform provider errors** - Now handles inconsistent state gracefully  
✅ **Existing resources** - Reuses existing catalogs and instances  
✅ **Failed resource retrieval** - Provides manual recovery steps  
✅ **Lakebase connectivity** - Non-blocking with helpful guidance  
✅ **Hard-coded warehouse ID** - Now uses environment variable  

## Quick Start

### Option 1: Try deployment again (recommended)

```bash
./deploy.sh --target dev --verbose
```

The script now handles errors gracefully and will continue even if some steps fail.

### Option 2: If automatic resource retrieval fails

After running deployment, manually get connection details:

```bash
# Get connection details
python scripts/get_lakebase_host.py --target dev

# Or get as environment variables to add to .env.local
python scripts/get_lakebase_host.py --target dev --output-format env >> .env.local
```

### Option 3: Manual recovery

If you need to manually retrieve and set connection details:

1. **Get Lakebase host:**
   ```bash
   databricks database list-database-instances --output json
   ```
   Look for `databricks-app-lakebase-dev` and copy the `host` value.

2. **Get Warehouse ID:**
   ```bash
   databricks warehouses list --output json
   ```
   Look for `databricks-app-warehouse-dev` and copy the `id` value.

3. **Update .env.local:**
   ```bash
   # Add these lines to .env.local
   LAKEBASE_HOST=<host-from-step-1>
   PGHOST=<host-from-step-1>
   LAKEBASE_PORT=5432
   LAKEBASE_DATABASE=app_database
   LAKEBASE_INSTANCE_NAME=databricks-app-lakebase-dev
   DATABRICKS_WAREHOUSE_ID=<id-from-step-2>
   ```

4. **Test connectivity:**
   ```bash
   uv run python -c 'from server.lib.database import get_engine; get_engine().connect()'
   ```

## What Changed

### deploy.sh
- ✅ Better error handling for Terraform issues
- ✅ Improved resource retrieval with fallbacks
- ✅ Non-blocking Lakebase connectivity test
- ✅ Detailed error messages and recovery steps

### databricks.yml
- ✅ Removed hard-coded warehouse ID
- ✅ Now uses `${var.warehouse_id}` variable
- ✅ Properly references database instance

### New Helper Script
- ✅ `scripts/get_lakebase_host.py` - Manually retrieve connection details
- ✅ Supports multiple output formats (text, env, json)
- ✅ Works for both dev and prod environments

## Common Issues and Solutions

### Issue: "Catalog already exists"
**Solution**: This is now handled automatically. The script will reuse existing resources.

### Issue: "Provider produced inconsistent result"
**Solution**: This is a known Terraform provider bug. The script now verifies resources and continues.

### Issue: "Could not retrieve warehouse ID automatically"
**Solution**: 
```bash
python scripts/get_lakebase_host.py --target dev --output-format env >> .env.local
```

### Issue: "Could not connect to Lakebase"
**Solution**: This is normal during initial setup. Lakebase can take 5-10 minutes to initialize.
Test later with:
```bash
uv run python -c 'from server.lib.database import get_engine; get_engine().connect()'
```

### Issue: "DATABRICKS_WAREHOUSE_ID is not set"
**Solution**: Set it in .env.local using the helper script or manual steps above.

## Next Steps After Successful Deployment

1. **Verify resources:**
   ```bash
   databricks catalogs list
   databricks database list-database-instances
   databricks warehouses list
   ```

2. **Run migrations:**
   ```bash
   ./deploy.sh --target dev --bundle-only no --app-only no
   # Select yes for migrations
   ```

3. **Test locally:**
   ```bash
   ./watch.sh
   ```

4. **Deploy application:**
   ```bash
   ./deploy.sh --app-only --target dev
   ```

## Getting Help

- **Detailed fix documentation**: See `DEPLOYMENT_FIXES.md`
- **Check current resources**: Use the helper script or Databricks CLI
- **View logs**: `./view_logs.sh` (after app deployment)

## Validation

To verify everything is working:

```bash
# 1. Check environment variables
cat .env.local | grep -E "LAKEBASE_HOST|DATABRICKS_WAREHOUSE_ID"

# 2. Test database connection
uv run python -c 'from server.lib.database import get_engine; get_engine().connect()'

# 3. Verify migrations
uv run alembic current

# 4. Check app status (if deployed)
databricks apps list
```

## Important Notes

- ⚠️ Lakebase instances can take 5-10 minutes to become fully available
- ⚠️ The Terraform provider may report inconsistent states - this is a known issue
- ⚠️ Always use `--verbose` flag when troubleshooting
- ✅ The deployment script no longer exits on these common issues
- ✅ Manual recovery steps are now provided automatically

