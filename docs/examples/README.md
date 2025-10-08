# Authorization Examples

This directory contains practical examples demonstrating user authorization in Databricks Apps.

## Files

### `authorization_examples.py`
Complete Python examples showing:
- App authorization with service principal
- User authorization with access tokens
- Combined authorization patterns
- FastAPI integration examples
- WorkspaceClient examples

## Quick Example

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

# App Authorization (Service Principal)
app_client = WorkspaceClient()  # Uses env credentials

# User Authorization (User Token)
user_cfg = Config(
    host=os.getenv('DATABRICKS_HOST'),
    token=user_access_token  # From x-forwarded-access-token header
)
user_client = WorkspaceClient(config=user_cfg)
```

## Running Examples

These examples are meant to be **reference material** - copy patterns into your own code.

To run the script (requires Databricks workspace connection):

```bash
# Set environment variables
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
export DATABRICKS_HTTP_PATH="/sql/1.0/warehouses/your-warehouse-id"

# Run
python authorization_examples.py
```

## See Also

- `../USER_AUTHORIZATION.md` - Full documentation
- `../USER_AUTHORIZATION_QUICKSTART.md` - Quick start guide
- `../../server/services/unity_catalog_service.py` - Production implementation

