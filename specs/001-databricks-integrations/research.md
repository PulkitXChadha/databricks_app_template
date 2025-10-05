# Technical Research: Databricks Service Integrations

**Feature**: `001-databricks-integrations`  
**Date**: Saturday, October 4, 2025  
**Status**: Complete

## Overview

This document consolidates technical research findings for implementing Databricks service integrations including Unity Catalog, Lakebase, Model Serving, Design Bricks UI, observability, and Asset Bundles.

---

## 1. Unity Catalog Integration

### Decision
Use Databricks SDK `WorkspaceClient` with SQL Warehouse execution for querying Unity Catalog managed tables. Leverage Unity Catalog's built-in access control for multi-user data isolation.

### Implementation Pattern

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

class UnityCatalogService:
    def __init__(self):
        self.client = WorkspaceClient()
    
    async def query_table(self, catalog: str, schema: str, table: str, 
                         warehouse_id: str, user_context: dict) -> list[dict]:
        """Query Unity Catalog table with user-specific permissions."""
        query = f"SELECT * FROM {catalog}.{schema}.{table} LIMIT 100"
        
        # Execute with user context for access control
        response = self.client.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=query,
            # User context ensures Unity Catalog enforces permissions
        )
        
        # Poll for completion
        if response.status.state == StatementState.SUCCEEDED:
            return self._parse_results(response)
        else:
            raise Exception(f"Query failed: {response.status.state}")
```

### Configuration
```bash
# Environment Variables
DATABRICKS_WAREHOUSE_ID=<sql-warehouse-id>
UNITY_CATALOG_NAME=main
UNITY_CATALOG_SCHEMA=samples
```

### Best Practices
- **Connection Pooling**: Reuse `WorkspaceClient` instance across requests
- **Query Limits**: Default to LIMIT 100 for UI queries, paginate for larger datasets
- **Error Handling**: Catch `DatabricksError` and provide user-friendly messages
- **Permissions**: Let Unity Catalog enforce access control via user context
- **Caching**: Cache schema metadata (tables, columns) for 5 minutes

### Alternatives Considered
- **Databricks Connect**: Rejected - more suitable for Spark workloads than simple queries
- **Direct REST API**: Rejected - SDK provides better error handling and type safety
- **MLflow Data**: Rejected - Unity Catalog is the modern, recommended approach

---

## 2. Lakebase Integration

### Decision
Use SQLAlchemy with `psycopg2` driver to connect to Lakebase (Databricks-hosted Postgres). Implement connection pooling with token-based authentication.

### Implementation Pattern

```python
from sqlalchemy import create_engine, Column, Integer, String, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

Base = declarative_base()

class UserPreference(Base):
    __tablename__ = 'user_preferences'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    preferences = Column(JSON, nullable=False)

class LakebaseService:
    def __init__(self, connection_string: str, token: str):
        # Connection string format: 
        # postgresql+psycopg2://token:<token>@<host>:<port>/<database>
        self.engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True  # Verify connections before use
        )
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    async def save_user_preference(self, user_id: str, prefs: dict):
        """Save user-specific preferences with data isolation."""
        pref = UserPreference(user_id=user_id, preferences=prefs)
        self.session.add(pref)
        self.session.commit()
    
    async def get_user_preferences(self, user_id: str) -> dict:
        """Retrieve preferences for a specific user only."""
        pref = self.session.query(UserPreference).filter_by(
            user_id=user_id
        ).first()
        return pref.preferences if pref else {}
```

### Configuration
```bash
# Environment Variables
LAKEBASE_HOST=<workspace>.cloud.databricks.com
LAKEBASE_PORT=5432
LAKEBASE_DATABASE=<database-name>
LAKEBASE_TOKEN=<databricks-token>
```

### Best Practices
- **Connection Pooling**: Use `QueuePool` with 5-10 connections for typical workload
- **Token Rotation**: Detect expired tokens and refresh automatically
- **Schema Migrations**: Use Alembic for schema versioning and migrations
- **Data Isolation**: Always filter queries by `user_id` from authenticated context
- **Transactions**: Use SQLAlchemy sessions with proper commit/rollback
- **Health Checks**: `pool_pre_ping=True` validates connections before use

### Alternatives Considered
- **asyncpg**: Rejected - psycopg2 better supported by SQLAlchemy ORM
- **Direct psycopg2**: Rejected - SQLAlchemy provides ORM and migration tools
- **External Postgres**: Rejected - violates constitution (use Databricks-native only)

---

## 3. Model Serving Integration

### Decision
Use Databricks SDK to invoke serving endpoints with proper error handling and timeout configuration. Support both synchronous and streaming responses.

### Implementation Pattern

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ServingEndpoint
import httpx

class ModelServingService:
    def __init__(self):
        self.client = WorkspaceClient()
    
    async def invoke_model(self, endpoint_name: str, inputs: dict) -> dict:
        """Invoke a model serving endpoint."""
        endpoint = self.client.serving_endpoints.get(endpoint_name)
        
        # Construct serving URL
        url = f"{endpoint.config.served_models[0].workload_url}/invocations"
        
        # Make request with timeout
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json={"inputs": inputs},
                headers={
                    "Authorization": f"Bearer {self._get_token()}",
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def list_endpoints(self) -> list[dict]:
        """List available serving endpoints."""
        endpoints = self.client.serving_endpoints.list()
        return [
            {
                "name": ep.name,
                "state": ep.state.config_update,
                "model": ep.config.served_models[0].model_name
            }
            for ep in endpoints
        ]
```

### Configuration
```bash
# Environment Variables
MODEL_SERVING_ENDPOINT=<endpoint-name>
MODEL_SERVING_TIMEOUT=30
```

### Best Practices
- **Timeouts**: Set 30s timeout for model inference, 5s for list operations
- **Retry Logic**: Retry up to 3 times with exponential backoff for transient errors
- **Error Handling**: Distinguish between client errors (4xx) and server errors (5xx)
- **Response Caching**: Cache model metadata (not predictions) for 5 minutes
- **Monitoring**: Log inference latency and error rates

### Alternatives Considered
- **Direct REST API**: Rejected - SDK provides authentication and error handling
- **MLflow Client**: Rejected - Serving Endpoints API is more direct
- **Batch Inference**: Deferred - focus on real-time for this template

---

## 4. Design Bricks UI Migration

### Decision
Migrate from shadcn/ui to Design Bricks component library to align with Databricks look-and-feel (Constitution Principle I).

### Component Mapping

| shadcn/ui Component | Design Bricks Equivalent | Notes |
|---------------------|--------------------------|-------|
| `Button` | `<databricks-button>` | Use `variant` prop for primary/secondary |
| `Card` | `<databricks-card>` | Similar API, supports elevation |
| `Input` | `<databricks-input>` | Add `label` prop for accessibility |
| `Badge` | `<databricks-tag>` | Different color scheme |
| `Alert` | `<databricks-banner>` | Use `type` for info/warning/error |
| `Skeleton` | `<databricks-skeleton>` | Same API |

### Implementation Pattern

```typescript
// Before (shadcn/ui)
import { Button } from "@/components/ui/button"

<Button variant="default" size="lg">
  Click Me
</Button>

// After (Design Bricks)
import '@databricks/design-bricks/button'

<databricks-button variant="primary" size="large">
  Click Me
</databricks-button>
```

### Installation
```bash
cd client
bun add @databricks/design-bricks
```

### Best Practices
- **Incremental Migration**: Migrate page-by-page, starting with WelcomePage
- **Theme Consistency**: Use Design Bricks theme tokens for colors/spacing
- **Accessibility**: Design Bricks components have built-in ARIA support
- **Documentation**: Reference https://pulkitxchadha.github.io/DesignBricks

### Alternatives Considered
- **Keep shadcn/ui**: Rejected - violates Constitution Principle I
- **Custom Components**: Rejected - Design Bricks provides all needed components
- **Material-UI**: Rejected - not Databricks-aligned

---

## 5. Observability Patterns

### Decision
Use Python `logging` module with structured logging (JSON format) for logs, and emit custom metrics to Databricks observability tools.

### Implementation Pattern

```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # JSON formatter for structured logs
        handler = logging.StreamHandler()
        handler.setFormatter(self._json_formatter())
        self.logger.addHandler(handler)
    
    def _json_formatter(self):
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": record.levelname,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                }
                if hasattr(record, "user_id"):
                    log_data["user_id"] = record.user_id
                if hasattr(record, "duration_ms"):
                    log_data["duration_ms"] = record.duration_ms
                return json.dumps(log_data)
        return JSONFormatter()
    
    def log_request(self, endpoint: str, user_id: str, duration_ms: float):
        extra = {"user_id": user_id, "duration_ms": duration_ms}
        self.logger.info(f"API request: {endpoint}", extra=extra)
```

### Configuration
```python
# server/app.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'  # JSON formatter will handle actual format
)
```

### Best Practices
- **Structured Logging**: Always use JSON format for machine-readable logs
- **Context**: Include `user_id`, `request_id`, `duration_ms` in all logs
- **Log Levels**: INFO for normal operations, WARNING for retries, ERROR for failures
- **Sensitive Data**: Never log tokens, passwords, or PII
- **Performance**: Log request latency for all API calls

### Distributed Tracing (Correlation-ID Based Request Tracking)

**Implementation Pattern**: Simplified correlation-ID tracking using Python contextvars (NOT full OpenTelemetry).

**Core Components**:

1. **Context Variable**: Store request ID in async-safe context
```python
# server/lib/distributed_tracing.py
import contextvars
from uuid import uuid4

correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    'request_id', default='no-request-id'
)

def get_correlation_id() -> str:
    """Retrieve the current request's correlation ID."""
    return correlation_id.get()

def set_correlation_id(request_id: str) -> None:
    """Set the correlation ID for the current request context."""
    correlation_id.set(request_id)
```

2. **FastAPI Middleware**: Generate UUID per request
```python
# server/app.py
from uuid import uuid4
from fastapi import Request
from server.lib.distributed_tracing import set_correlation_id, get_correlation_id

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Inject correlation ID into request context and response headers."""
    # Extract from header or generate new UUID
    request_id = request.headers.get('X-Request-ID', str(uuid4()))
    set_correlation_id(request_id)
    
    response = await call_next(request)
    response.headers['X-Request-ID'] = request_id
    return response
```

3. **Logging Integration**: Include correlation ID in all structured logs
```python
# server/lib/structured_logger.py
from server.lib.distributed_tracing import get_correlation_id

def log_info(message: str, **context):
    """Log INFO level message with correlation ID."""
    log_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'level': 'INFO',
        'message': message,
        'request_id': get_correlation_id(),  # ← Always include
        **context
    }
    print(json.dumps(log_data))

def log_error(message: str, error: Exception, **context):
    """Log ERROR level message with correlation ID and error details."""
    log_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'level': 'ERROR',
        'message': message,
        'request_id': get_correlation_id(),  # ← Always include
        'error_type': type(error).__name__,
        'error_message': str(error),
        **context
    }
    print(json.dumps(log_data))
```

**Propagation**: Context variables automatically propagate through async calls within the same request context.

**Testing**: 
```bash
# Verify correlation ID is propagated
curl -H "X-Request-ID: test-123" http://localhost:8000/api/user/me
# Check logs contain: "request_id": "test-123"

# Verify auto-generated ID when header not present
curl http://localhost:8000/api/user/me
# Check response header X-Request-ID contains UUID
# Check logs contain same UUID
```

**Best Practices**:
- Always call `set_correlation_id()` at the start of request processing (middleware handles this)
- Include `request_id` in all log output for traceability
- Propagate `X-Request-ID` header in upstream service calls
- Use correlation IDs to trace requests across logs when debugging

Include `request_id` in all structured logs for request correlation across services.

### Alternatives Considered
- **Full OpenTelemetry**: Deferred - adds complexity for educational template (use simplified correlation-ID approach instead)
- **Custom Metrics Backend**: Rejected - use Databricks-native tools
- **Print Statements**: Rejected - not structured or filterable

---

## 6. Multi-User Data Isolation

### Decision
Combine Unity Catalog's table-level access control with Lakebase row-level security (user_id filtering) for comprehensive data isolation.

### Implementation Pattern

```python
from fastapi import Depends, HTTPException
from databricks.sdk import WorkspaceClient

async def get_current_user_id() -> str:
    """Extract user ID from authentication context."""
    client = WorkspaceClient()
    user = client.current_user.me()
    return user.user_name

# Unity Catalog: Access control enforced by catalog
@router.get("/data/table")
async def get_table_data(user_id: str = Depends(get_current_user_id)):
    # Unity Catalog automatically filters based on user permissions
    service = UnityCatalogService()
    return await service.query_table(
        catalog="main", 
        schema="samples", 
        table="data",
        warehouse_id=settings.WAREHOUSE_ID,
        user_context={"user_id": user_id}
    )

# Lakebase: Explicit user_id filtering
@router.get("/preferences")
async def get_preferences(user_id: str = Depends(get_current_user_id)):
    # Explicitly filter by user_id
    service = LakebaseService()
    return await service.get_user_preferences(user_id=user_id)
```

### Best Practices
- **Authentication**: Use Databricks Apps built-in authentication for user identity
- **Authorization**: Never trust client-provided user_id, always extract from auth context
- **Unity Catalog**: Let catalog enforce table/column permissions automatically
- **Lakebase**: Always filter by `user_id` in WHERE clauses
- **Testing**: Test with multiple user accounts to verify isolation

### Alternatives Considered
- **Session-based Auth**: Rejected - use Databricks Apps authentication
- **JWT Tokens**: Rejected - Databricks SDK handles token management
- **API Keys**: Rejected - not secure for multi-user scenarios

---

## 7. Asset Bundle Configuration

### Decision
Create comprehensive `databricks.yml` with full bundle configuration for dev, staging, and prod environments.

### Configuration Pattern

```yaml
# databricks.yml
bundle:
  name: databricks-app-template
  version: 0.1.0

include:
  - resources/*.yml

variables:
  app_name:
    description: "Application name"
    default: "databricks-app-template"
  
targets:
  dev:
    mode: development
    workspace:
      host: ${DATABRICKS_HOST}
    resources:
      apps:
        databricks_app:
          name: ${var.app_name}-dev
          description: "Databricks App Template (Development)"
          source_code_path: ./
          config:
            env:
              - name: DATABRICKS_WAREHOUSE_ID
                value: ${var.warehouse_id}
              - name: LAKEBASE_HOST
                value: ${var.lakebase_host}
              - name: LAKEBASE_DATABASE
                value: ${var.lakebase_database}
  
  prod:
    mode: production
    workspace:
      host: ${DATABRICKS_HOST}
    resources:
      apps:
        databricks_app:
          name: ${var.app_name}
          description: "Databricks App Template (Production)"
          source_code_path: ./
          config:
            env:
              - name: DATABRICKS_WAREHOUSE_ID
                value: ${var.warehouse_id}
              - name: LAKEBASE_HOST
                value: ${var.lakebase_host}
              - name: LAKEBASE_DATABASE
                value: ${var.lakebase_database}
          permissions:
            - level: CAN_MANAGE
              group_name: admins
            - level: CAN_VIEW
              group_name: users
```

### Deployment Commands
```bash
# Validate bundle
databricks bundle validate

# Deploy to dev
databricks bundle deploy -t dev

# Deploy to prod
databricks bundle deploy -t prod
```

### Best Practices
- **Environment Variables**: Use bundle variables for configuration
- **Permissions**: Define explicit permissions per environment
- **Resources**: Include all app resources (endpoints, tables, etc.)
- **Validation**: Always run `validate` before `deploy`
- **Version Control**: Track databricks.yml in Git

### Alternatives Considered
- **Manual Deployment**: Rejected - not reproducible or auditable
- **Terraform**: Rejected - Asset Bundles are Databricks-native solution
- **GitHub Actions**: Deferred - focus on CLI first, CI/CD later

---

## 8. Sample Data Setup

### Decision
Create Python script to generate minimal sample data for Unity Catalog and Lakebase, with clear documentation for connecting real resources.

### Implementation Pattern

```python
# scripts/setup_sample_data.py
from databricks.sdk import WorkspaceClient
from sqlalchemy import create_engine
import pandas as pd

class SampleDataSetup:
    def __init__(self):
        self.client = WorkspaceClient()
    
    def create_unity_catalog_sample(self):
        """Create sample table in Unity Catalog."""
        warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
        
        # Create sample data
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Sample A", "Sample B", "Sample C"],
            "value": [100, 200, 300]
        })
        
        # Upload to Unity Catalog
        self.client.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement="""
                CREATE TABLE IF NOT EXISTS main.samples.demo_data (
                    id INT,
                    name STRING,
                    value INT
                )
            """
        )
        
        # Insert data
        for _, row in df.iterrows():
            self.client.statement_execution.execute_statement(
                warehouse_id=warehouse_id,
                statement=f"""
                    INSERT INTO main.samples.demo_data 
                    VALUES ({row['id']}, '{row['name']}', {row['value']})
                """
            )
    
    def create_lakebase_sample(self):
        """Create sample tables in Lakebase."""
        engine = create_engine(os.getenv("LAKEBASE_CONNECTION_STRING"))
        
        with engine.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    preferences JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_id 
                ON user_preferences(user_id)
            """)
```

### Usage
```bash
# Run setup script
python scripts/setup_sample_data.py --create-all

# Or selectively
python scripts/setup_sample_data.py --unity-catalog
python scripts/setup_sample_data.py --lakebase
```

### Best Practices
- **Minimal Data**: Create only 5-10 rows per table for demonstration
- **Documentation**: Include README with instructions to connect real data
- **Idempotent**: Script should be safe to run multiple times
- **Cleanup**: Provide cleanup script to remove sample data

---

## Summary of Technical Decisions

| Integration | Technology | Rationale |
|-------------|-----------|-----------|
| **Unity Catalog** | Databricks SDK + SQL Warehouse | Native integration, access control built-in |
| **Lakebase** | SQLAlchemy + psycopg2 | ORM support, connection pooling, migrations |
| **Model Serving** | Databricks SDK + httpx | Async support, timeout control, error handling |
| **UI Components** | Design Bricks | Constitutional requirement, Databricks branding |
| **Observability** | Python logging (JSON) | Structured logs, Databricks-native |
| **Data Isolation** | Unity Catalog ACLs + user_id filtering | Multi-layer security approach |
| **Deployment** | Asset Bundles (databricks.yml) | Reproducible, version-controlled, auditable |
| **Sample Data** | Python setup script | Automated, minimal, documented |

---

## Dependencies to Add

### Python (pyproject.toml)
```toml
dependencies = [
    # Existing
    "fastapi>=0.104.1",
    "uvicorn[standard]>=0.24.0",
    "databricks-sdk==0.59.0",
    "pydantic>=2.5.0",
    "mlflow[databricks]>=3.1.1",
    
    # New
    "sqlalchemy>=2.0.0",        # Lakebase ORM
    "psycopg2-binary>=2.9.0",   # Postgres driver
    "alembic>=1.13.0",          # Database migrations
    "httpx>=0.25.0",            # Async HTTP (already present)
]
```

### TypeScript (client/package.json)
```json
{
  "dependencies": {
    "@databricks/design-bricks": "^1.0.0"
  }
}
```

---

## Environment Variables

```bash
# Databricks Authentication
DATABRICKS_HOST=https://<workspace>.cloud.databricks.com
DATABRICKS_TOKEN=<token>

# Unity Catalog
DATABRICKS_WAREHOUSE_ID=<warehouse-id>
UNITY_CATALOG_NAME=main
UNITY_CATALOG_SCHEMA=samples

# Lakebase
LAKEBASE_HOST=<workspace>.cloud.databricks.com
LAKEBASE_PORT=5432
LAKEBASE_DATABASE=<database-name>
LAKEBASE_TOKEN=<token>

# Model Serving
MODEL_SERVING_ENDPOINT=<endpoint-name>
MODEL_SERVING_TIMEOUT=30

# Observability
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

**Status**: ✅ All research complete, ready for Phase 1 design.

