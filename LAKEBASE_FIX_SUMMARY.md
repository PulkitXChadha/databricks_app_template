# Lakebase Local Development Fix Summary

## Problem

When running the Databricks App Template locally at `http://localhost:5173/`, the application was returning this error:

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

## Root Cause

Two issues were identified:

### 1. Missing Environment Variables

The `.env.local` file lacked the required Lakebase configuration variables:
- `PGHOST` - Lakebase instance hostname
- `LAKEBASE_HOST` - Same as PGHOST (for compatibility)
- `LAKEBASE_PORT` - Database port (5432)
- `LAKEBASE_DATABASE` - Database name (app_database)
- `LAKEBASE_INSTANCE_NAME` - Logical instance name from bundle

### 2. Incorrect PostgreSQL Username

The code in `server/lib/database.py` was using the literal string `"token"` as the PostgreSQL username, which caused this error:

```
role "token" does not exist
```

The actual username needs to be extracted from the OAuth JWT token's `sub` field (the user's email).

## Solution

### Part 1: Configure Environment Variables

1. **Retrieved Lakebase instance details** from the deployed bundle using Databricks SDK:
   ```python
   from databricks.sdk import WorkspaceClient
   
   w = WorkspaceClient()
   instances = list(w.database.list_database_instances())
   ```

2. **Added configuration to `.env.local`**:
   ```bash
   PGHOST=instance-0fac1568-f318-4b0d-9110-cd868b343908.database.cloud.databricks.com
   LAKEBASE_HOST=instance-0fac1568-f318-4b0d-9110-cd868b343908.database.cloud.databricks.com
   LAKEBASE_PORT=5432
   LAKEBASE_DATABASE=app_database
   LAKEBASE_INSTANCE_NAME=databricks-app-lakebase-dev
   ```

### Part 2: Fix Username Extraction

Updated `server/lib/database.py` to extract the username from the JWT token:

```python
def _extract_username_from_token(token: str) -> str:
    """Extract username from JWT token's 'sub' field."""
    try:
        # JWT format: header.payload.signature
        parts = token.split('.')
        if len(parts) < 2:
            raise ValueError("Invalid JWT format")
        
        # Decode payload (add padding if needed)
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        payload_data = json.loads(decoded)
        
        # Extract subject (username/email)
        username = payload_data.get('sub')
        if not username:
            raise ValueError("No 'sub' field in JWT token")
        
        return username
    except Exception as e:
        raise Exception(f"Failed to extract username from token: {e}")
```

Then updated the connection event listener:

```python
@event.listens_for(engine, "do_connect")
def provide_token(dialect, conn_rec, cargs, cparams):
    # ... generate token ...
    
    # Extract username from token and set credentials
    if token_to_use:
        username = _extract_username_from_token(token_to_use)
        cparams["user"] = username  # e.g., "pulkit.chadha@databricks.com"
        cparams["password"] = token_to_use
```

The same fix was applied to `migrations/env.py` for Alembic migrations.

## Files Changed

1. **`.env.local`** - Added Lakebase configuration variables
2. **`server/lib/database.py`** - Added username extraction logic
3. **`migrations/env.py`** - Added username extraction logic
4. **`scripts/configure_lakebase.py`** - Created automated setup script (new)
5. **`docs/LAKEBASE_LOCAL_SETUP.md`** - Created comprehensive guide (new)

## Verification

### Database Connection Test

```bash
$ uv run python << 'EOF'
from server.lib.database import create_lakebase_engine
from sqlalchemy import text

engine = create_lakebase_engine()
with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print("✅ Connection successful!")
engine.dispose()
EOF

✅ Connection successful!
```

### Database Tables

```bash
$ uv run python -c "from server.lib.database import create_lakebase_engine; from sqlalchemy import inspect; engine = create_lakebase_engine(); print([t for t in inspect(engine).get_table_names()]); engine.dispose()"

['alembic_version', 'user_preferences', 'model_inference_logs']
```

### Application Startup

```bash
$ uv run python -c "from server.app import app; from server.lib.database import is_lakebase_configured; print(f'Lakebase configured: {is_lakebase_configured()}')"

Lakebase configured: True
```

## How OAuth Token Authentication Works

### Token Generation Flow

```
1. Application needs database connection
   ↓
2. Call workspace_client.database.generate_database_credential()
   ↓
3. Databricks returns JWT token (valid for 1 hour)
   ↓
4. Extract username from token.sub field
   ↓
5. Connect to PostgreSQL:
   - username: user@example.com (from token.sub)
   - password: eyJraWQiOiJ... (the JWT token)
   ↓
6. Lakebase validates token and grants access
```

### Token Structure

The JWT token contains:

```json
{
  "sub": "pulkit.chadha@databricks.com",  // Username for PostgreSQL
  "aud": "1444828305810485",               // Workspace ID
  "exp": 1697211541,                        // Expiration (1 hour)
  "iat": 1697207941                         // Issued at
}
```

### Auto-Refresh

- Tokens automatically expire after 1 hour
- The SDK handles token refresh transparently
- New tokens are generated for each connection
- No manual intervention required

## Benefits

1. **Local Development Works**: Developers can now run the app locally with full Lakebase access
2. **Secure Authentication**: Uses OAuth tokens with automatic expiration
3. **User-Level Access**: Each developer's database access respects their Unity Catalog permissions
4. **Auto-Refresh**: Tokens refresh automatically every hour
5. **Easy Setup**: Configuration script automates the setup process

## Usage

### Quick Start

```bash
# 1. Configure Lakebase (one-time setup)
uv run python scripts/configure_lakebase.py

# 2. Run migrations (one-time setup)
alembic upgrade head

# 3. Start the app
./watch.sh

# 4. Visit the app
open http://localhost:5173/
```

### Check Configuration Status

```bash
# Check if Lakebase is configured
uv run python scripts/configure_lakebase.py --check-only
```

## Troubleshooting

See the comprehensive troubleshooting guide in [`docs/LAKEBASE_LOCAL_SETUP.md`](./docs/LAKEBASE_LOCAL_SETUP.md).

## Future Improvements

1. **Automatic Token Refresh UI**: Display token expiration time in the app
2. **Health Check Endpoint**: Add `/api/health/database` endpoint
3. **Connection Pooling Metrics**: Monitor connection pool usage
4. **Setup Wizard**: Interactive CLI wizard for first-time setup

## Related Documentation

- [`docs/LAKEBASE_LOCAL_SETUP.md`](./docs/LAKEBASE_LOCAL_SETUP.md) - Comprehensive setup guide
- [`docs/LOCAL_DEVELOPMENT.md`](./docs/LOCAL_DEVELOPMENT.md) - General local development guide
- [`docs/OBO_AUTHENTICATION.md`](./docs/OBO_AUTHENTICATION.md) - On-behalf-of-user authentication
- [`server/lib/database.py`](./server/lib/database.py) - Database connection implementation

