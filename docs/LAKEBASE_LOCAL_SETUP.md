# Lakebase Local Development Setup

This guide explains how to configure Lakebase (PostgreSQL) for local development of the Databricks App Template.

## Problem

When running the app locally, you might encounter this error:

```json
{
    "detail": {
        "error_code": "LAKEBASE_NOT_CONFIGURED",
        "message": "User preferences are not available. Lakebase database is not configured for this deployment.",
        "technical_details": {
            "error_type": "ConfigurationError",
            "suggestion": "Configure Lakebase resource in databricks.yml or set PGHOST and LAKEBASE_DATABASE environment variables."
        }
    }
}
```

## Solution

Lakebase requires specific configuration in your `.env.local` file to work in local development.

### Prerequisites

1. **Deployed Lakebase Instance**: You must have deployed the Databricks bundle with Lakebase resources:
   ```bash
   databricks bundle deploy --target dev
   ```

2. **Authenticated**: You must be authenticated to Databricks:
   ```bash
   databricks auth login
   ```

### Quick Setup

Run the automated configuration script:

```bash
# Configure Lakebase automatically
uv run python scripts/configure_lakebase.py

# Or check current status
uv run python scripts/configure_lakebase.py --check-only
```

### Manual Setup

If you prefer to configure manually:

#### Step 1: Get Lakebase Instance Details

```bash
# List your Lakebase instances
databricks bundle summary --target dev
```

Look for the database instance name (e.g., `databricks-app-lakebase-dev`).

#### Step 2: Get Connection Details

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
instance_name = "databricks-app-lakebase-dev"

instances = list(w.database.list_database_instances())
for instance in instances:
    if instance.name == instance_name:
        print(f"Host: instance-{instance.uid}.database.cloud.databricks.com")
        print(f"Port: 5432")
        print(f"Instance Name: {instance.name}")
```

#### Step 3: Update .env.local

Add these lines to your `.env.local` file:

```bash
# Lakebase Configuration
PGHOST=instance-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX.database.cloud.databricks.com
LAKEBASE_HOST=instance-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX.database.cloud.databricks.com
LAKEBASE_PORT=5432
LAKEBASE_DATABASE=app_database
LAKEBASE_INSTANCE_NAME=databricks-app-lakebase-dev
```

Replace the `XXXX` values with your actual instance UID.

## Authentication

### OAuth Token Auto-Refresh

The app uses Databricks SDK to automatically generate and refresh OAuth tokens for Lakebase access:

1. **Token Generation**: When a database connection is needed, the SDK calls `generate_database_credential()` to get a fresh OAuth token
2. **Token Lifetime**: Tokens expire after 1 hour
3. **Auto-Refresh**: The SDK handles token refresh automatically - no manual intervention needed
4. **Username Extraction**: The username is extracted from the JWT token's `sub` field (your email)

### How It Works

```python
# server/lib/database.py

# 1. Generate OAuth token for the Lakebase instance
cred = workspace_client.database.generate_database_credential(
    request_id=str(uuid.uuid4()),
    instance_names=[instance_name]
)

# 2. Extract username from JWT token's 'sub' field
username = extract_username_from_token(cred.token)  # e.g., "user@example.com"

# 3. Connect using extracted username and token
connection_params = {
    "user": username,
    "password": cred.token
}
```

## Database Migrations

After configuring Lakebase, run migrations to create tables:

```bash
# Run all pending migrations
alembic upgrade head

# Check current migration version
alembic current

# View migration history
alembic history
```

## Verification

### Test Database Connection

```bash
uv run python << 'EOF'
from server.lib.database import test_connection

if test_connection():
    print("✅ Lakebase connection successful!")
else:
    print("❌ Lakebase connection failed")
EOF
```

### Check Database Tables

```bash
uv run python << 'EOF'
import os
from pathlib import Path

# Load .env.local
if Path('.env.local').exists():
    with open('.env.local') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                if key and value:
                    os.environ[key] = value

from server.lib.database import create_lakebase_engine
from sqlalchemy import inspect

engine = create_lakebase_engine()
inspector = inspect(engine)
tables = inspector.get_table_names()

print("Database tables:")
for table in tables:
    print(f"  ✅ {table}")

engine.dispose()
EOF
```

### Start the App

```bash
# Start development servers
./watch.sh

# Visit the app
open http://localhost:5173/
```

## Troubleshooting

### Error: "role 'token' does not exist"

**Cause**: Old code was using literal "token" as username instead of extracting from JWT.

**Solution**: This has been fixed in the codebase. The username is now extracted from the JWT token's `sub` field.

### Error: "connection refused" or "connection timeout"

**Causes**:
1. Lakebase instance not deployed
2. Instance still starting up (takes 2-3 minutes after deployment)
3. Incorrect host in `.env.local`

**Solutions**:
```bash
# Check instance status
databricks bundle summary --target dev

# Verify host is correct
echo $PGHOST

# Wait and retry if instance is starting
```

### Error: "Failed to generate Lakebase database credential"

**Causes**:
1. Not authenticated to Databricks
2. Insufficient permissions
3. Instance name incorrect

**Solutions**:
```bash
# Re-authenticate
databricks auth login

# Verify instance name
databricks bundle summary --target dev | grep "database_instances"

# Check permissions (must have CAN_USE on Lakebase instance)
```

### Error: "No module named 'databricks'"

**Cause**: Dependencies not installed

**Solution**:
```bash
# Sync dependencies
uv sync
```

## Technical Details

### JWT Token Structure

The OAuth token is a JWT (JSON Web Token) with this structure:

```json
{
  "sub": "user@example.com",    // Username (extracted for PostgreSQL auth)
  "aud": "workspace_id",          // Workspace ID
  "exp": 1234567890,              // Expiration timestamp (1 hour)
  "iat": 1234567000               // Issued at timestamp
}
```

### Connection Flow

```
┌─────────────────┐
│   Application   │
└────────┬────────┘
         │
         │ 1. Request database connection
         ▼
┌─────────────────┐
│  Database.py    │
└────────┬────────┘
         │
         │ 2. Generate OAuth token
         ▼
┌─────────────────┐
│ Databricks SDK  │
│ .database.      │
│ generate_       │
│ database_       │
│ credential()    │
└────────┬────────┘
         │
         │ 3. Return JWT token
         ▼
┌─────────────────┐
│ Extract username│
│ from token sub  │
└────────┬────────┘
         │
         │ 4. Connect with username + token
         ▼
┌─────────────────┐
│ Lakebase        │
│ PostgreSQL      │
└─────────────────┘
```

### File Changes

The following files were updated to support username extraction:

1. **`server/lib/database.py`**:
   - Added `_extract_username_from_token()` function
   - Updated event listener to extract username from JWT
   - Added imports for `base64` and `json`

2. **`migrations/env.py`**:
   - Same changes as database.py for migration support

## Security Notes

1. **Never commit `.env.local`**: It contains sensitive connection information
2. **Tokens auto-expire**: OAuth tokens expire after 1 hour for security
3. **User-level access**: Tokens are per-user and respect Unity Catalog permissions
4. **SSL required**: All Lakebase connections use SSL (`sslmode=require`)

## Additional Resources

- [Databricks Apps Documentation](https://docs.databricks.com/dev-tools/databricks-apps/)
- [Lakebase Documentation](https://docs.databricks.com/lakehouse-architecture/lakebase/)
- [Unity Catalog Documentation](https://docs.databricks.com/data-governance/unity-catalog/)
- [Local Development Guide](./LOCAL_DEVELOPMENT.md)

