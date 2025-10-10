# Research: Authentication Implementation Patterns

**Feature**: Fix API Authentication and Implement On-Behalf-Of User (OBO) Authentication  
**Date**: 2025-10-10  
**Status**: Complete

## Executive Summary

This research document captures the technical decisions and architectural patterns required to implement dual authentication (OBO for user operations, service principal for system operations) in a Databricks Apps environment. All technical unknowns have been resolved through the clarification process documented in the feature specification.

---

## 1. Databricks SDK Authentication Configuration

### Decision: Use Explicit `auth_type` Parameter

**Chosen Approach**: Configure Databricks SDK clients with explicit `auth_type` parameter to prevent multi-method detection errors.

**Rationale**:
- The error "more than one authorization method configured: oauth and pat" occurs when the SDK auto-detects multiple authentication methods from environment variables
- Databricks Apps platform automatically sets OAuth environment variables (`DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`)
- User access tokens are provided separately via `X-Forwarded-Access-Token` header
- SDK version 0.67.0+ supports explicit `auth_type` parameter to disambiguate

**Implementation Pattern**:
```python
# Pattern A: On-Behalf-Of-User Authentication
from databricks.sdk import WorkspaceClient

client = WorkspaceClient(
    host=workspace_url,
    token=user_access_token,  # From X-Forwarded-Access-Token header
    auth_type="pat"  # Explicit PAT authentication
)

# Pattern B: Service Principal Authentication
client = WorkspaceClient(
    host=workspace_url,
    client_id=os.environ["DATABRICKS_CLIENT_ID"],
    client_secret=os.environ["DATABRICKS_CLIENT_SECRET"],
    auth_type="oauth-m2m"  # Explicit OAuth M2M
)
```

**Alternatives Considered**:
- **Clear OAuth environment variables**: Rejected - would break other platform integrations
- **Use only service principal**: Rejected - violates user-level permission enforcement (FR-008)
- **Custom authentication wrapper**: Rejected - adds unnecessary complexity when SDK supports explicit config

**SDK Version Requirements**:
- **Minimum**: 0.67.0 (introduced explicit `auth_type` support)
- **Pinned**: 0.67.0 (prevent breaking changes per NFR-013)
- **Update mechanism**: Use `uv` to pin exact version in `pyproject.toml`

**References**:
- Databricks SDK Python documentation: https://databricks-sdk-py.readthedocs.io/
- Feature spec clarification (Session 2025-10-10): SDK version and auth_type parameter
- Constitution Principle VII: Development Tooling Standards (uv for package management)

---

## 2. Token Extraction and Propagation

### Decision: Extract Fresh Tokens Per Request via Middleware

**Chosen Approach**: FastAPI middleware extracts `X-Forwarded-Access-Token` header on every request and stores in request state.

**Rationale**:
- Databricks Apps platform provides user tokens via standard header
- Tokens can expire and be refreshed by platform automatically
- Per-request extraction ensures immediate token revocation takes effect (NFR-005)
- Request state provides clean dependency injection pattern to service layers
- No caching reduces security exposure and complexity

**Implementation Pattern**:
```python
# Middleware in server/lib/auth.py
@app.middleware("http")
async def extract_user_token(request: Request, call_next):
    user_token = request.headers.get("X-Forwarded-Access-Token")
    request.state.user_token = user_token
    request.state.has_user_token = user_token is not None
    
    # Log token presence (not token value)
    logger.info("auth.token_extraction", {
        "has_token": request.state.has_user_token,
        "request_id": request.state.request_id
    })
    
    return await call_next(request)

# Dependency injection in routers
def get_user_token(request: Request) -> Optional[str]:
    return getattr(request.state, "user_token", None)

# Usage in endpoints
@router.get("/api/user/me")
async def get_user_info(user_token: Optional[str] = Depends(get_user_token)):
    service = UserService(user_token=user_token)
    return await service.get_user_info()
```

**Alternatives Considered**:
- **Cache tokens in memory**: Rejected - security risk, delayed revocation (violates NFR-005)
- **Store tokens in session storage**: Rejected - same security concerns plus added complexity
- **Pass tokens via custom headers**: Rejected - platform already provides standard header

**Performance Considerations**:
- Header extraction adds <1ms per request (negligible)
- Eliminates cache invalidation logic complexity
- NFR-001 requirement: Total auth overhead must be <10ms (easily achievable)

**References**:
- Feature spec FR-001, FR-002, NFR-005
- FastAPI middleware documentation: https://fastapi.tiangolo.com/tutorial/middleware/
- Databricks Apps Cookbook - OBO Authentication: https://apps-cookbook.dev/docs/streamlit/authentication/users_obo

---

## 3. User Identity Extraction

### Decision: Call UserService.get_user_info() with User Token

**Chosen Approach**: Extract user email address by calling Databricks API `current_user.me()` with user access token, retrieve `userName` field.

**Rationale**:
- Databricks platform provides authoritative user identity via API
- JWT token parsing would require cryptographic verification and key management
- API call is already authenticated - no additional validation needed
- `userName` field contains email address suitable for database user_id
- Aligns with platform security model (trust platform-provided identity)

**Implementation Pattern**:
```python
# In UserService (server/services/user_service.py)
class UserService:
    def __init__(self, user_token: Optional[str] = None):
        self.user_token = user_token
    
    async def get_user_info(self) -> UserInfo:
        """Get authenticated user's information from Databricks."""
        if not self.user_token:
            # Fallback to service principal for system operations
            client = self._get_service_principal_client()
        else:
            # OBO authentication for user operations
            client = WorkspaceClient(
                host=self.workspace_url,
                token=self.user_token,
                auth_type="pat"
            )
        
        try:
            user = client.current_user.me()
            return UserInfo(
                user_id=user.user_name,  # Email address
                display_name=user.display_name,
                active=user.active
            )
        except Exception as e:
            logger.error("auth.user_info_failed", {
                "error": str(e),
                "has_token": self.user_token is not None
            })
            raise HTTPException(status_code=401, detail="Failed to extract user identity")
    
    async def get_user_id(self) -> str:
        """Extract user_id for database operations. Returns email address."""
        user_info = await self.get_user_info()
        return user_info.user_id
```

**Alternatives Considered**:
- **Parse JWT token manually**: Rejected - requires key management, token validation, more complex
- **Extract from custom header**: Rejected - platform doesn't provide user_id in headers
- **Use service principal identity**: Rejected - violates multi-user isolation (Constitution Principle IX)

**Error Handling**:
- API call failure returns HTTP 401 per FR-014
- Malformed response logged and returns 401
- Retry logic handled separately (see section 4)

**References**:
- Feature spec FR-010, FR-014
- Databricks SDK `WorkspaceClient.current_user.me()` documentation
- Constitution Principle IX: Multi-User Data Isolation

---

## 4. Retry Logic and Error Handling

### Decision: Exponential Backoff with 5-Second Total Timeout

**Chosen Approach**: Implement decorator-based retry logic with exponential backoff (100ms, 200ms, 400ms delays) for authentication failures.

**Rationale**:
- Handles transient errors (network hiccups, token refresh timing)
- Exponential backoff prevents thundering herd
- 5-second total timeout prevents request hangs (NFR-006)
- Treats all token errors (expired, invalid, malformed) identically per FR-018
- Immediate failure on HTTP 429 respects platform rate limits (FR-019)

**Token Error Type Handling**: The Databricks SDK does not distinguish between expired, malformed, and cryptographically invalid tokens at the exception level - all authentication failures raise `DatabricksError` with authentication-related error codes. The retry decorator catches all `DatabricksError` exceptions and applies the same retry logic regardless of the underlying token error type. This unified handling is intentional per spec.md Edge Cases section (line 125) and simplifies the implementation while providing consistent user experience for all authentication failures.

**Implementation Pattern**:
```python
# In server/lib/auth.py
from tenacity import (
    retry, 
    stop_after_delay, 
    wait_exponential,
    retry_if_exception_type,
    RetryError
)

class AuthenticationError(Exception):
    """Base exception for authentication failures."""
    pass

class RateLimitError(Exception):
    """Platform rate limit exceeded - do not retry."""
    pass

def with_auth_retry(func):
    """Decorator for authentication retry logic with exponential backoff."""
    
    @retry(
        retry=retry_if_exception_type(AuthenticationError),
        wait=wait_exponential(multiplier=0.1, min=0.1, max=0.4),  # 100ms, 200ms, 400ms
        stop=stop_after_delay(5),  # 5 second total timeout
        reraise=True
    )
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except DatabricksError as e:
            # Detect rate limiting
            if e.error_code == "RESOURCE_EXHAUSTED" or e.status_code == 429:
                logger.error("auth.rate_limit", {"error": str(e)})
                raise RateLimitError("Platform rate limit exceeded") from e
            
            # Retry authentication errors
            logger.warning("auth.retry_attempt", {
                "error": str(e),
                "attempt": wrapper.retry.statistics.get("attempt_number", 1)
            })
            raise AuthenticationError(f"Authentication failed: {e}") from e
    
    return wrapper

# Usage in services
@with_auth_retry
async def _make_databricks_api_call(self, client: WorkspaceClient):
    """Make authenticated API call with automatic retry."""
    return client.current_user.me()
```

**Alternatives Considered**:
- **No retries**: Rejected - user experience degraded by transient failures
- **Fixed delay retry**: Rejected - doesn't adapt to increasing load
- **Longer timeouts**: Rejected - violates NFR-006 (5-second limit)
- **Differentiate token error types**: Rejected - clarification confirmed identical handling (FR-018)

**Stateless Pattern**:
- Each request retries independently (no coordination per FR-025)
- Multiple parallel requests may each perform 3 retries
- Acceptable for small scale (<50 concurrent users per NFR-009)

**Monitoring**:
- Log each retry attempt with attempt number
- Expose retry rate metrics per NFR-011
- Track success/failure after retries

**References**:
- Feature spec FR-018, FR-019, FR-025, NFR-006, NFR-009
- Tenacity library documentation: https://tenacity.readthedocs.io/
- Databricks platform rate limiting behavior

---

## 5. Service Principal vs. OBO Pattern Separation

### Decision: Dual Authentication Pattern with Explicit Mode Selection

**Chosen Approach**: Services accept optional `user_token` parameter; presence determines authentication mode.

**Rationale**:
- Clear separation of concerns (system vs. user operations)
- Single responsibility: each service method knows its auth requirements
- Automatic fallback when header missing (FR-016, FR-020)
- Aligns with Constitution Principle: Dual Authentication Patterns

**Implementation Pattern**:
```python
# Base pattern in all service classes
class BaseService:
    def __init__(self, user_token: Optional[str] = None):
        self.user_token = user_token
        self.workspace_url = os.environ["DATABRICKS_HOST"]
    
    def _get_client(self) -> WorkspaceClient:
        """Get WorkspaceClient with appropriate authentication."""
        if self.user_token:
            # Pattern B: On-Behalf-Of-User Authentication
            logger.info("auth.mode", {"mode": "obo", "auth_type": "pat"})
            return WorkspaceClient(
                host=self.workspace_url,
                token=self.user_token,
                auth_type="pat"
            )
        else:
            # Pattern A: Service Principal Authentication (automatic fallback)
            logger.info("auth.mode", {"mode": "service_principal", "auth_type": "oauth-m2m"})
            return WorkspaceClient(
                host=self.workspace_url,
                client_id=os.environ["DATABRICKS_CLIENT_ID"],
                client_secret=os.environ["DATABRICKS_CLIENT_SECRET"],
                auth_type="oauth-m2m"
            )

# Lakebase-specific: ALWAYS use service principal
class LakebaseService:
    def __init__(self):
        # NEVER accept user_token - Lakebase doesn't support OBO
        self.connection_params = self._get_connection_params_from_env()
    
    def _get_connection_params_from_env(self) -> dict:
        """Extract Lakebase connection params from platform environment."""
        return {
            "host": os.environ["PGHOST"],
            "database": os.environ["PGDATABASE"],
            "user": os.environ["PGUSER"],  # Service principal client ID
            "port": os.environ["PGPORT"],
            "sslmode": os.environ["PGSSLMODE"]
        }
```

**Usage Patterns**:
```python
# User-scoped endpoint (uses OBO)
@router.get("/api/unity-catalog/catalogs")
async def list_catalogs(user_token: Optional[str] = Depends(get_user_token)):
    service = UnityCatalogService(user_token=user_token)
    return await service.list_catalogs()  # Uses user's permissions

# System endpoint (uses service principal)
@router.get("/api/health")
async def health_check():
    service = UnityCatalogService()  # No user_token
    return await service.get_workspace_info()  # Uses app permissions

# Lakebase endpoint (service principal + user_id filtering)
@router.get("/api/preferences")
async def get_preferences(user_token: Optional[str] = Depends(get_user_token)):
    # Extract user_id for filtering
    user_service = UserService(user_token=user_token)
    user_id = await user_service.get_user_id()  # Requires OBO token
    
    # Database operations use service principal
    lakebase_service = LakebaseService()
    return await lakebase_service.get_user_preferences(user_id=user_id)
```

**Alternatives Considered**:
- **Separate service classes**: Rejected - code duplication, harder to maintain
- **Configuration flag**: Rejected - implicit behavior, harder to trace
- **Always require user_token**: Rejected - breaks health checks and system operations

**Fallback Behavior**:
- Missing `X-Forwarded-Access-Token` → automatic service principal mode (FR-016)
- Log fallback events for observability (FR-021)
- Works in local development without Databricks Apps (FR-020)

**References**:
- Feature spec FR-002, FR-004, FR-011, FR-016, FR-020, FR-021
- Constitution Principle: Dual Authentication Patterns
- Existing codebase: `server/services/` pattern

---

## 6. Lakebase Data Isolation Pattern

### Decision: Application-Level Filtering with user_id

**Chosen Approach**: All user-scoped Lakebase queries include `WHERE user_id = ?` clauses; validate user_id presence before query execution.

**Rationale**:
- Lakebase PostgreSQL roles are service principal-only (platform limitation per FR-011)
- Database-level row-level security not available
- Application-level filtering is only option for multi-user isolation
- Aligns with Constitution Principle IX: Multi-User Data Isolation

**Implementation Pattern**:
```python
# In LakebaseService (server/services/lakebase_service.py)
class LakebaseService:
    async def get_user_preferences(self, user_id: str) -> List[UserPreference]:
        """Get preferences for specific user. MUST filter by user_id."""
        if not user_id:
            # Fail fast if user_id missing (FR-014)
            raise HTTPException(
                status_code=401,
                detail="User identity required for data access"
            )
        
        query = """
            SELECT preference_key, preference_value, created_at, updated_at
            FROM user_preferences
            WHERE user_id = :user_id
            ORDER BY updated_at DESC
        """
        
        result = await self.db.execute(query, {"user_id": user_id})
        return [UserPreference(**row) for row in result]
    
    async def save_user_preference(self, user_id: str, key: str, value: str):
        """Save preference for specific user. MUST include user_id."""
        if not user_id:
            raise HTTPException(status_code=401, detail="User identity required")
        
        query = """
            INSERT INTO user_preferences (user_id, preference_key, preference_value)
            VALUES (:user_id, :key, :value)
            ON CONFLICT (user_id, preference_key)
            DO UPDATE SET preference_value = :value, updated_at = NOW()
        """
        
        await self.db.execute(query, {
            "user_id": user_id,
            "key": key,
            "value": value
        })
        
        # Audit log with user_id
        logger.info("lakebase.preference_saved", {
            "user_id": user_id,
            "key": key
        })
```

**Security Requirements**:
- **ALL** user-scoped queries MUST filter by user_id (FR-013)
- Validate user_id presence before execution (FR-014)
- Return HTTP 401 when user_id missing or extraction fails
- Never trust client-provided user_id (Constitution Principle IX)

**Testing Strategy**:
- Multi-user isolation tests with different user accounts (test_multi_user_isolation.py)
- Verify user A cannot access user B's data
- Verify missing user_id returns 401
- Verify SQL injection protection via parameterized queries

**References**:
- Feature spec FR-010, FR-011, FR-013, FR-014
- Constitution Principle IX: Multi-User Data Isolation
- Databricks Lakebase documentation: https://docs.databricks.com/aws/en/dev-tools/databricks-apps/lakebase

---

## 7. Observability and Structured Logging

### Decision: JSON Structured Logs with Correlation IDs

**Chosen Approach**: Enhance existing `structured_logger.py` with authentication-specific fields; add correlation ID to all requests.

**Rationale**:
- Existing structured logging infrastructure in place
- Constitution Principle VIII: Observability First requires structured logs
- Correlation IDs enable request tracing across services
- JSON format enables automated log analysis and alerting
- Sensitive data protection (never log token values)

**Implementation Pattern**:
```python
# In server/lib/structured_logger.py (ENHANCE existing)
import contextvars
import uuid
from datetime import datetime
from typing import Any, Dict

# Context variable for correlation ID
correlation_id_var = contextvars.ContextVar('correlation_id', default=None)

class StructuredLogger:
    def log(self, level: str, event: str, context: Dict[str, Any] = None):
        """Log structured event with authentication context."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "event": event,
            "correlation_id": correlation_id_var.get(),
            **(context or {})
        }
        
        # Never log sensitive data
        if "token" in log_entry:
            del log_entry["token"]
        if "password" in log_entry:
            del log_entry["password"]
        
        print(json.dumps(log_entry))

# Middleware to set correlation ID (server/lib/auth.py)
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    # Accept client-provided correlation ID or generate new one
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    correlation_id_var.set(correlation_id)
    
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response
```

**Log Events for Authentication**:
```python
# Token extraction
logger.info("auth.token_extraction", {
    "has_token": bool(user_token),
    "endpoint": request.url.path
})

# Authentication mode selection
logger.info("auth.mode", {
    "mode": "obo" if user_token else "service_principal",
    "auth_type": "pat" if user_token else "oauth-m2m"
})

# Retry attempts
logger.warning("auth.retry_attempt", {
    "attempt": retry_count,
    "error_type": error.__class__.__name__,
    "endpoint": endpoint_name
})

# Fallback triggers
logger.info("auth.fallback_triggered", {
    "reason": "missing_token",
    "endpoint": request.url.path
})

# User identity extraction
logger.info("auth.user_id_extracted", {
    "user_id": user_id,  # Email is not PII in this context
    "method": "UserService.get_user_info"
})

# Authentication errors
logger.error("auth.failed", {
    "error_type": error.__class__.__name__,
    "error_message": str(error),
    "endpoint": request.url.path,
    "has_token": bool(user_token),
    "retry_count": retry_count
})
```

**Alternatives Considered**:
- **OpenTelemetry full tracing**: Rejected - overkill for template apps (Constitution uses simplified approach)
- **Plain text logs**: Rejected - violates Constitution Principle VIII
- **Custom log format**: Rejected - JSON is standard for automated analysis

**References**:
- Feature spec FR-017, NFR-011
- Constitution Principle VIII: Observability First
- Existing implementation: `server/lib/structured_logger.py`

---

## 8. Metrics and Monitoring

### Decision: Expose Prometheus-Compatible Metrics

**Chosen Approach**: Use Python `prometheus_client` library to expose authentication and performance metrics at `/metrics` endpoint.

**Rationale**:
- NFR-011 requires comprehensive operational metrics
- NFR-012 requires standard observability platform compatibility
- Prometheus format is widely supported (Datadog, CloudWatch import)
- Existing FastAPI app can easily expose metrics endpoint

**Implementation Pattern**:
```python
# In server/lib/metrics.py (NEW)
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Authentication metrics
auth_requests_total = Counter(
    'auth_requests_total',
    'Total authentication attempts',
    ['endpoint', 'mode', 'status']
)

auth_retry_total = Counter(
    'auth_retry_total',
    'Total authentication retry attempts',
    ['endpoint', 'attempt_number']
)

auth_fallback_total = Counter(
    'auth_fallback_total',
    'Total service principal fallback events',
    ['reason']
)

# Performance metrics
request_duration_seconds = Histogram(
    'request_duration_seconds',
    'Request duration in seconds',
    ['endpoint', 'method', 'status'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0]
)

auth_overhead_seconds = Histogram(
    'auth_overhead_seconds',
    'Authentication overhead in seconds',
    ['mode'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1]
)

# User metrics
active_users_gauge = Gauge(
    'active_users',
    'Number of active users in last 5 minutes'
)

# Upstream service metrics
upstream_api_duration_seconds = Histogram(
    'upstream_api_duration_seconds',
    'Upstream API call duration',
    ['service', 'operation'],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0]
)

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

**Usage in Code**:
```python
# Increment counters
auth_requests_total.labels(
    endpoint="/api/user/me",
    mode="obo",
    status="success"
).inc()

# Record histograms
with request_duration_seconds.labels(
    endpoint=request.url.path,
    method=request.method,
    status=response.status_code
).time():
    response = await process_request(request)
```

**Metric Categories (per NFR-011)**:
- Authentication success/failure counts per endpoint
- Authentication retry rates
- Token extraction time
- Average and P95/P99 request latencies
- Per-user request counts
- Upstream service availability indicators

**Alternatives Considered**:
- **Custom metrics format**: Rejected - non-standard, harder to integrate
- **StatsD**: Rejected - less widely supported than Prometheus
- **Application Insights**: Rejected - vendor lock-in, not platform-agnostic

**References**:
- Feature spec NFR-011, NFR-012
- Constitution Principle VIII: Observability First
- Prometheus Python client: https://github.com/prometheus/client_python

---

## 9. Local Development and Testing

### Decision: Support Both Local and Platform Modes

**Chosen Approach**: Auto-detect environment and provide CLI tool for fetching real tokens in local development.

**Rationale**:
- FR-016 requires automatic fallback when platform header missing
- FR-020 requires local development support
- FR-022 requires real token testing capability
- Developers need to test OBO behavior before deployment

**Implementation Pattern**:

**A. Environment Detection**:
```python
# In server/lib/auth.py
def is_databricks_apps_environment() -> bool:
    """Detect if running in Databricks Apps platform."""
    return all([
        os.environ.get("DATABRICKS_CLIENT_ID"),
        os.environ.get("DATABRICKS_CLIENT_SECRET"),
        os.environ.get("PGHOST")  # Lakebase connection available
    ])

def should_use_obo(request: Request) -> bool:
    """Determine if OBO authentication should be used."""
    has_user_token = request.headers.get("X-Forwarded-Access-Token") is not None
    
    if not has_user_token:
        logger.info("auth.fallback_triggered", {
            "reason": "missing_token",
            "environment": "platform" if is_databricks_apps_environment() else "local"
        })
    
    return has_user_token
```

**B. Local Token Fetching** (for testing):
```python
# scripts/get_user_token.py (NEW)
"""
Fetch user access token for local OBO testing.

Usage:
    export DATABRICKS_USER_TOKEN=$(python scripts/get_user_token.py)
    
Then use in local testing:
    curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
         http://localhost:8000/api/user/me
"""

import subprocess
import sys

def get_databricks_user_token() -> str:
    """Get user token via Databricks CLI."""
    try:
        result = subprocess.run(
            ["databricks", "auth", "token"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to fetch token: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: Databricks CLI not installed", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    print(get_databricks_user_token())
```

**C. Local Development Documentation**:
```markdown
# docs/LOCAL_DEVELOPMENT.md (UPDATE existing)

## Testing OBO Authentication Locally

1. Install Databricks CLI:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
   ```

2. Authenticate with your workspace:
   ```bash
   databricks auth login --host https://your-workspace.cloud.databricks.com
   ```

3. Fetch user token:
   ```bash
   export DATABRICKS_USER_TOKEN=$(python scripts/get_user_token.py)
   ```

4. Test endpoints with OBO:
   ```bash
   curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
        http://localhost:8000/api/user/me
   ```

5. Test fallback (without token):
   ```bash
   curl http://localhost:8000/api/health  # Uses service principal
   ```
```

**Testing Strategy**:
- Unit tests: Mock user_token parameter in services
- Integration tests: Use real tokens from Databricks CLI
- Contract tests: Validate both auth modes (with/without token)
- Local manual testing: Follow docs above

**Alternatives Considered**:
- **Mock tokens**: Rejected - doesn't test real authentication flow
- **Always require platform**: Rejected - makes local development harder
- **Manual token entry**: Rejected - CLI automation is cleaner

**References**:
- Feature spec FR-016, FR-020, FR-021, FR-022
- Databricks CLI documentation: https://docs.databricks.com/dev-tools/cli/

---

## 10. Dependency Management

### Decision: Pin Databricks SDK to Exact Version 0.67.0

**Chosen Approach**: Use `uv` to add pinned SDK version to `pyproject.toml`.

**Rationale**:
- NFR-013 requires exact version pinning
- SDK behavior changes could break authentication logic
- Version 0.67.0 confirmed to support explicit `auth_type` parameter
- `uv` is constitutional standard for Python package management

**Implementation**:
```bash
# Add pinned dependency
uv add databricks-sdk==0.67.0

# This updates pyproject.toml with:
# dependencies = [
#     "databricks-sdk==0.67.0",
#     ...
# ]
```

**Version Selection Rationale**:
- 0.67.0 is current stable version (as of 2025-10-10)
- Confirmed support for `auth_type="pat"` and `auth_type="oauth-m2m"`
- No known authentication-related bugs
- Future updates require explicit version bump and testing

**Update Policy**:
- SDK updates require explicit decision and testing
- Monitor Databricks SDK release notes for security patches
- Document version upgrade process in `docs/DEPENDENCY_UPDATES.md`

**References**:
- Feature spec FR-024, NFR-013
- Constitution Principle VII: Development Tooling Standards
- Databricks SDK releases: https://github.com/databricks/databricks-sdk-py/releases

---

## Summary of Technical Decisions

| Decision Area | Chosen Approach | Key Rationale |
|---------------|----------------|---------------|
| SDK Authentication | Explicit `auth_type` parameter | Prevents multi-method detection error |
| Token Extraction | Per-request middleware | Security, immediate revocation, simplicity |
| User Identity | API call to `current_user.me()` | Platform authoritative, no key management |
| Retry Logic | Exponential backoff, 5s timeout | Balance reliability and performance |
| Auth Pattern | Dual mode (OBO + service principal) | Constitutional requirement, clear separation |
| Lakebase Isolation | Application-level user_id filtering | Platform limitation, only viable option |
| Observability | JSON structured logs + Prometheus metrics | Constitutional requirement, industry standard |
| Local Development | Auto-fallback + CLI token fetching | Developer experience, testing capability |
| SDK Version | Pin to 0.67.0 | Stability, prevent breaking changes |

All decisions align with Constitutional principles and feature requirements. No complexity deviations required.

---

**Status**: ✅ All technical unknowns resolved  
**Next Phase**: Design (data models, contracts, quickstart)
