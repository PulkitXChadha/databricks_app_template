# Technical Research: OBO Authentication Implementation

**Date**: 2025-10-09  
**Feature**: Fix API Authentication and Implement On-Behalf-Of User (OBO)  
**Status**: Complete

---

## Research Areas

### 1. Databricks SDK Authentication Configuration

**Decision**: Use explicit `auth_type` parameter when creating WorkspaceClient instances

**Rationale**:
- Databricks SDK performs automatic authentication detection by scanning environment variables, config files, and parameters
- When multiple authentication methods are available (e.g., OAuth env vars + token parameter), SDK raises error: "more than one authorization method configured: oauth and pat"
- Explicit `auth_type` parameter overrides auto-detection and prevents conflicts
- Two auth_type values needed:
  - `auth_type="pat"` for user token-based authentication (OBO pattern)
  - `auth_type="oauth-m2m"` for service principal OAuth (system operations)

**Implementation Pattern**:
```python
# OBO pattern - user token from header
user_client = WorkspaceClient(
    host=os.getenv("DATABRICKS_HOST"),
    token=user_token,
    auth_type="pat"  # Explicit PAT mode
)

# Service principal pattern - OAuth credentials from env
service_client = WorkspaceClient(
    host=os.getenv("DATABRICKS_HOST"),
    client_id=os.getenv("DATABRICKS_CLIENT_ID"),
    client_secret=os.getenv("DATABRICKS_CLIENT_SECRET"),
    auth_type="oauth-m2m"  # Explicit OAuth machine-to-machine
)
```

**References**:
- Databricks SDK documentation: Authentication configuration
- Error logs from deployed app: "more than one authorization method configured: oauth and pat"
- Databricks Apps Cookbook: https://apps-cookbook.dev/docs/streamlit/authentication/users_obo

**Alternatives Considered**:
- Unsetting environment variables: Rejected - fragile, affects global state, not thread-safe
- Using separate processes: Rejected - adds complexity, resource overhead
- Token-only approach without OAuth env vars: Rejected - service principal needed for Lakebase

---

### 2. FastAPI Dependency Injection for User Context

**Decision**: Use FastAPI dependency functions to extract and inject user tokens into service layer

**Rationale**:
- FastAPI's dependency injection system provides clean, testable way to pass request context
- Dependencies can access Request object to extract headers
- Type hints ensure compile-time validation of auth parameters
- Enables easy mocking in tests (override dependencies)
- Centralizes auth logic in one place (DRY principle)

**Implementation Pattern**:
```python
# In server/lib/auth.py
async def get_user_token(request: Request) -> str | None:
    """Extract user access token from X-Forwarded-Access-Token header."""
    token = request.headers.get("X-Forwarded-Access-Token")
    return token

# In routers
@router.get("/api/user/me")
async def get_current_user(user_token: str | None = Depends(get_user_token)):
    service = UserService(user_token=user_token)
    return await service.get_current_user()
```

**References**:
- FastAPI documentation: Dependencies with yield
- FastAPI documentation: Using the Request directly
- Existing codebase: `server/app.py` middleware pattern for correlation IDs

**Alternatives Considered**:
- Middleware-based injection: Rejected - harder to test, global state issues
- Request context vars: Rejected - implicit dependencies, harder to trace
- Manual header extraction in each endpoint: Rejected - violates DRY, error-prone

---

### 3. Exponential Backoff Retry Logic

**Decision**: Implement retry decorator with exponential backoff for authentication failures

**Rationale**:
- Transient network issues and token refresh timing can cause temporary auth failures
- Exponential backoff (100ms, 200ms, 400ms) gives platform time to resolve transient issues
- 5-second total timeout prevents request hanging indefinitely
- Structured logging at each retry attempt enables debugging
- Rate limit detection (HTTP 429) short-circuits retry to respect platform limits

**Implementation Pattern**:
```python
import asyncio
from functools import wraps

async def retry_with_backoff(func, max_attempts=3, base_delay=0.1, max_timeout=5.0):
    """Retry with exponential backoff for transient auth failures."""
    start_time = time.time()
    
    for attempt in range(1, max_attempts + 1):
        try:
            return await func()
        except HTTPStatusError as e:
            # Detect rate limiting - fail immediately
            if e.response.status_code == 429:
                raise
            
            # Check total timeout
            elapsed = time.time() - start_time
            if elapsed >= max_timeout:
                raise
            
            # Calculate delay with exponential backoff
            delay = base_delay * (2 ** (attempt - 1))
            if attempt < max_attempts:
                await asyncio.sleep(delay)
            else:
                raise
```

**References**:
- FR-018: Exponential backoff requirement (3 attempts: 100ms, 200ms, 400ms)
- NFR-006: 5-second total timeout requirement
- FR-019: HTTP 429 rate limit immediate failure requirement
- AWS Architecture Blog: Exponential Backoff and Jitter

**Alternatives Considered**:
- Linear backoff: Rejected - doesn't give enough time for platform recovery
- Jitter addition: Deferred - not needed for small user scale (<50 concurrent)
- Circuit breaker pattern: Deferred - overkill for authentication (better for downstream services)

---

### 4. Lakebase Service Principal Authentication

**Decision**: Maintain exclusive service principal authentication for all Lakebase operations

**Rationale**:
- Platform limitation: Lakebase PostgreSQL roles are created based on service principal client ID only
- No mechanism exists for per-user database authentication at PostgreSQL level
- `PGUSER` environment variable contains service principal client ID + role name
- Application-level user_id filtering provides data isolation (PostgreSQL level isolation not possible)

**Implementation Pattern**:
```python
# In server/lib/database.py
def get_lakebase_connection():
    """Create Lakebase connection using service principal credentials only."""
    # Service principal OAuth token generated via Databricks SDK
    from databricks.sdk import WorkspaceClient
    
    service_client = WorkspaceClient(
        host=os.getenv("DATABRICKS_HOST"),
        client_id=os.getenv("DATABRICKS_CLIENT_ID"),
        client_secret=os.getenv("DATABRICKS_CLIENT_SECRET"),
        auth_type="oauth-m2m"
    )
    
    token = service_client.generate_database_credential()
    
    # Connection uses platform-provided PGHOST, PGDATABASE, PGUSER
    engine = create_engine(
        f"postgresql://{os.getenv('PGUSER')}:{token}@{os.getenv('PGHOST')}:{os.getenv('PGPORT')}/{os.getenv('PGDATABASE')}",
        connect_args={"sslmode": os.getenv("PGSSLMODE", "require")}
    )
    return engine

# In services - always filter by user_id
async def get_user_preferences(user_id: str):
    """Get preferences for specific user - user_id from OBO token."""
    query = select(UserPreference).where(UserPreference.user_id == user_id)
    result = await session.execute(query)
    return result.scalars().all()
```

**References**:
- Databricks Lakebase documentation: https://docs.databricks.com/aws/en/dev-tools/databricks-apps/lakebase
- Clarification from spec: "Connection to lakebase from the App is only supported with service principles"
- FR-011: LakebaseService MUST use service principal credentials exclusively
- FR-013: System MUST filter all user-scoped database queries by user_id

**Alternatives Considered**:
- Per-user database connections: Rejected - platform does not support
- Row-level security policies in PostgreSQL: Rejected - requires per-user roles (not available)
- Separate databases per user: Rejected - not scalable, not supported by platform

---

### 5. User Identity Extraction from OBO Token

**Decision**: Extract user_id from Databricks WorkspaceClient.current_user.me() API call

**Rationale**:
- Platform-native way to get authenticated user identity
- Token validation happens automatically via SDK
- Returns structured user object with user_id, email, username
- More secure than parsing JWT client-side (prevents token forgery)
- Single source of truth for user identity

**Implementation Pattern**:
```python
async def get_user_identity(user_token: str) -> dict:
    """Extract user identity from OBO token via Databricks API."""
    client = WorkspaceClient(
        host=os.getenv("DATABRICKS_HOST"),
        token=user_token,
        auth_type="pat"
    )
    
    user_info = client.current_user.me()
    
    return {
        "user_id": user_info.id,
        "email": user_info.emails[0].value if user_info.emails else None,
        "username": user_info.user_name,
        "display_name": user_info.display_name
    }
```

**References**:
- Databricks SDK: WorkspaceClient.current_user.me() API
- FR-001: Extract user access tokens from X-Forwarded-Access-Token header
- FR-010: Store user_id with all user-specific database records
- Constitution Principle IX: User identity extracted from Databricks authentication context

**Alternatives Considered**:
- JWT decoding client-side: Rejected - requires secret key, security risk
- Trusting client-provided user_id: Rejected - major security vulnerability
- Header-based user identity: Rejected - headers can be spoofed

---

### 6. Multi-User Data Isolation Patterns

**Decision**: Implement application-level user_id filtering with mandatory WHERE clauses

**Rationale**:
- Database-level isolation not available (single service principal role)
- Application-level filtering provides security if implemented correctly
- Query builder patterns (SQLAlchemy) make filtering consistent
- Schema includes user_id column on all user-scoped tables
- Validation layer rejects queries missing user_id for user-scoped operations

**Implementation Pattern**:
```python
# Schema: All user-scoped tables have user_id column
class UserPreference(Base):
    __tablename__ = "user_preferences"
    
    id = Column(UUID, primary_key=True)
    user_id = Column(String, nullable=False, index=True)  # Indexed for performance
    key = Column(String, nullable=False)
    value = Column(JSON, nullable=False)
    
    __table_args__ = (
        Index("ix_user_preferences_user_id_key", "user_id", "key", unique=True),
    )

# Service layer: Always require user_id
class UserPreferenceService:
    def __init__(self, user_id: str):
        if not user_id:
            raise ValueError("user_id is required for user preference operations")
        self.user_id = user_id
    
    async def get_preferences(self):
        """Get preferences - automatically filtered by user_id."""
        query = select(UserPreference).where(UserPreference.user_id == self.user_id)
        result = await session.execute(query)
        return result.scalars().all()
    
    async def set_preference(self, key: str, value: dict):
        """Set preference - automatically includes user_id."""
        pref = UserPreference(
            id=uuid4(),
            user_id=self.user_id,  # Always set from authenticated context
            key=key,
            value=value
        )
        session.add(pref)
        await session.commit()
```

**References**:
- FR-013: System MUST filter all user-scoped database queries by user_id
- FR-014: System MUST validate that user_id is present before executing operations
- Constitution Principle IX: Lakebase queries filtered by user_id in WHERE clauses
- Success Metric #7: Data isolation verified with user_id filtering

**Alternatives Considered**:
- PostgreSQL Row-Level Security (RLS): Rejected - requires per-user database roles (not available)
- Stored procedures with built-in filtering: Rejected - adds complexity, harder to maintain
- View-based filtering: Rejected - still requires application to enforce user context

---

### 7. SDK Version Pinning and Dependency Management

**Decision**: Pin exact Databricks SDK version (0.59.0) in requirements.txt

**Rationale**:
- SDK authentication behavior changed between versions (auth_type parameter introduced in 0.33.0+)
- Breaking changes in SDK could break authentication without warning
- Exact version pinning (not ranges like >=0.59.0) ensures consistent behavior
- Minimum version 0.33.0 required for explicit auth_type parameter support
- Version 0.59.0 confirmed to support both auth_type="pat" and auth_type="oauth-m2m"

**Implementation Pattern**:
```python
# requirements.txt
databricks-sdk==0.59.0  # Exact version, not >=0.59.0 or ~=0.59.0
```

**References**:
- FR-024: Use pinned exact SDK version with auth_type parameter support
- NFR-013: Pin to exact version in requirements.txt to prevent breaking changes
- Databricks SDK changelog: auth_type parameter added in 0.33.0
- Verified in pyproject.toml: databricks-sdk version 0.59.0

**Alternatives Considered**:
- Version ranges (>=0.59.0, <1.0.0): Rejected - allows breaking changes
- Semantic versioning (~=0.59.0): Rejected - allows patch updates that might break
- Latest version always: Rejected - unpredictable breaking changes

---

### 8. Comprehensive Observability Metrics

**Decision**: Expose Prometheus-compatible metrics for authentication operations

**Rationale**:
- NFR-011 requires comprehensive metrics (auth success/failure, retry rates, latencies, per-user counts)
- NFR-012 requires Prometheus/Datadog/CloudWatch compatibility
- Standard metrics format enables integration with existing observability platforms
- P95/P99 latency tracking essential for performance monitoring and SLA compliance
- Per-user metrics enable usage tracking and anomaly detection

**Metrics to Expose**:

| Metric Name | Type | Description | Labels |
|-------------|------|-------------|--------|
| `auth_success_total` | Counter | Successful authentications | endpoint, auth_method |
| `auth_failure_total` | Counter | Failed authentications | endpoint, auth_method, reason |
| `auth_retry_total` | Counter | Retry attempts | endpoint, attempt_number |
| `auth_token_extraction_seconds` | Histogram | Token extraction time | endpoint |
| `auth_request_duration_seconds` | Histogram | Request duration with P95/P99 | endpoint, auth_method |
| `auth_requests_by_user` | Counter | Requests per user | user_id, endpoint |
| `upstream_service_available` | Gauge | Service availability (0 or 1) | service_name |

**Implementation Pattern**:
```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
auth_success = Counter('auth_success_total', 'Successful authentications', ['endpoint', 'auth_method'])
auth_failure = Counter('auth_failure_total', 'Failed authentications', ['endpoint', 'auth_method', 'reason'])
auth_duration = Histogram('auth_request_duration_seconds', 'Request duration', ['endpoint', 'auth_method'])

# Use in code
with auth_duration.labels(endpoint='/api/user/me', auth_method='obo').time():
    result = await authenticate_user(token)
    auth_success.labels(endpoint='/api/user/me', auth_method='obo').inc()
```

**Metrics Endpoint**:
- Expose at `/metrics` endpoint (standard Prometheus format)
- Compatible with Prometheus, Datadog, CloudWatch (via exporters)
- No custom instrumentation required at deployment time

**References**:
- NFR-011: Expose comprehensive operational metrics
- NFR-012: Prometheus/Datadog/CloudWatch compatibility required
- Success Metric #6: Observability validated with metrics queryable in standard platforms

**Alternatives Considered**:
- Custom metrics format: Rejected - requires custom tooling, reduces compatibility
- Application-level logging only: Rejected - harder to aggregate and query
- OpenTelemetry full tracing: Deferred - Constitution specifies simpler correlation-ID based approach

---

### 9. Stateless Retry Pattern for Concurrent Requests

**Decision**: Each request implements retry logic independently without coordination

**Rationale**:
- Stateless pattern aligns with no-token-caching requirement (NFR-005)
- Simpler implementation - no shared state or locking needed
- Thread-safe by design - each request is independent
- Each request can fail/retry independently based on its specific circumstances
- Trade-off: N concurrent requests × 3 retries = potentially 3N backend calls
- Acceptable at scale (<50 concurrent users, <1000 req/min per NFR-009)
- Multi-tab support: Each tab's requests retry independently (Scenario 7)

**Implementation Pattern**:
```python
# Each request has independent retry logic
async def handle_request(user_token: str, correlation_id: str):
    """Each request retries independently - no coordination."""
    for attempt in range(1, 4):  # 3 attempts
        try:
            # Each request creates its own client
            client = WorkspaceClient(token=user_token, auth_type="pat")
            result = await client.current_user.me()
            
            # Log success with correlation_id
            logger.info("Auth succeeded", 
                       correlation_id=correlation_id, 
                       attempt=attempt)
            return result
            
        except AuthError as e:
            # Each request logs its own retry
            logger.warning("Auth failed, retrying",
                          correlation_id=correlation_id,
                          attempt=attempt)
            if attempt < 3:
                await asyncio.sleep(0.1 * (2 ** (attempt - 1)))
            else:
                raise
```

**Concurrency Behavior**:
- Request A (correlation_id=123) and Request B (correlation_id=456) arrive simultaneously
- Both requests retry independently if auth fails
- Request A might succeed on attempt 1 while Request B retries 3 times
- No coordination, no shared retry state, no locks
- Each request respects 5s total timeout independently

**References**:
- FR-025: Implement retry logic independently per request
- NFR-005: No token caching (enables stateless pattern)
- Clarification from spec: "Each request retries independently (no coordination, potentially N×3 retries to backend)"
- Scenario 7 (quickstart.md): Multi-tab sessions work independently

**Alternatives Considered**:
- Coordinated retry with shared state: Rejected - violates stateless requirement, adds complexity
- Circuit breaker pattern: Deferred - better suited for upstream service failures (FR-023)
- Request deduplication: Rejected - each request is unique, deduplication inappropriate

---

## Technology Stack Validation

### Confirmed Technologies
| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| Python | 3.11+ | Backend language | ✅ Confirmed in pyproject.toml |
| FastAPI | 0.104+ | Web framework | ✅ Confirmed in dependencies |
| Databricks SDK | 0.59.0 | API client | ✅ Confirmed in dependencies |
| SQLAlchemy | 2.0+ | Database ORM | ✅ Confirmed in dependencies |
| Psycopg | 3.1+ | PostgreSQL driver | ✅ Confirmed in dependencies |
| TypeScript | 5.2+ | Frontend type safety | ✅ Confirmed in client/package.json |
| React | 18.3 | Frontend UI framework | ✅ Confirmed in client/package.json |
| pytest | 7.4+ | Python testing | ✅ Confirmed in dev dependencies |
| httpx | 0.25+ | HTTP client for tests | ✅ Confirmed in dev dependencies |

### Authentication Flow Technologies
| Component | Technology | Purpose |
|-----------|------------|---------|
| Token Extraction | FastAPI Request headers | Extract X-Forwarded-Access-Token |
| Dependency Injection | FastAPI Depends() | Pass user context to services |
| User Identity | Databricks SDK current_user.me() | Get authenticated user info |
| Service Principal | Databricks SDK OAuth M2M | System-level operations |
| Database Auth | Databricks SDK generate_database_credential() | Lakebase token generation |
| Retry Logic | asyncio + exponential backoff | Handle transient auth failures |
| Logging | Existing structured_logger.py | Auth activity audit trail |

---

## Integration Patterns

### Pattern 1: Middleware → Dependency → Service
```
1. Middleware (correlation_id) - existing
2. Dependency (get_user_token) - NEW
3. Router (endpoint) - MODIFIED (add Depends)
4. Service (operations) - MODIFIED (add user_token param)
5. Databricks SDK (API calls) - NEW (explicit auth_type)
```

### Pattern 2: OBO Token Lifecycle
```
1. Platform provides token in X-Forwarded-Access-Token header
2. FastAPI dependency extracts token (no caching, fresh every request)
3. Router passes token to service layer
4. Service creates WorkspaceClient with token + auth_type="pat"
5. SDK validates token and makes API calls
6. No token storage or persistence (stateless)
```

### Pattern 3: Dual Authentication
```
User Operations (OBO):
  Request → Token Extraction → UserService(token) → WorkspaceClient(token, auth_type="pat") → API

System Operations (Service Principal):
  Request → LakebaseService() → WorkspaceClient(client_id, client_secret, auth_type="oauth-m2m") → Database Token
```

---

## Risk Mitigation

### Risk 1: Token Expiration Mid-Session
**Mitigation**: 
- No token caching (fresh extraction every request)
- Platform handles token refresh transparently
- Exponential backoff retry handles transient failures
- Multi-tab scenario: each tab operates independently (stateless auth)

### Risk 2: Service Principal Credentials Leak
**Mitigation**:
- Credentials only in environment variables (never in code)
- .env.local in .gitignore
- Databricks Apps platform manages secrets securely
- NFR-004: No credentials logged

### Risk 3: Cross-User Data Access
**Mitigation**:
- FR-014: Mandatory user_id validation before operations
- Service constructors require user_id parameter
- SQLAlchemy queries always include WHERE user_id clause
- Integration tests validate multi-user isolation (Success Metric #3)

### Risk 4: Rate Limiting During Retry
**Mitigation**:
- FR-019: Detect HTTP 429 and fail immediately (no further retries)
- Respect platform rate limits
- Structured logging tracks retry attempts for monitoring

### Risk 5: Local Development Without OBO Token
**Mitigation**:
- FR-016: Graceful fallback to service principal when token unavailable
- FR-021: Clear logging when using service principal in local mode
- FR-022: Environment variable-based local OBO testing

---

## Performance Considerations

### Authentication Overhead
- **Target**: <10ms per request (NFR-001)
- **Factors**: Header extraction (~1ms), token validation via API (~5-8ms)
- **Optimization**: No caching (security requirement), SDK client pooling

### Retry Overhead
- **Target**: 5s total timeout (NFR-006)
- **Worst Case**: 3 retries with 100ms, 200ms, 400ms delays = ~700ms overhead
- **Monitoring**: NFR-011 requires P95/P99 latency tracking

### Database Connection Pooling
- **Target**: <50 concurrent users (NFR-009)
- **Pattern**: Single service principal connection pool (SQLAlchemy)
- **Configuration**: Pool size tuned for concurrent query volume

---

## Testing Strategy

### Contract Testing (TDD Approach)
- Generate tests from OpenAPI specs
- Tests fail initially (no implementation)
- One test file per API contract: test_user_contract.py, test_model_serving_contract.py, test_unity_catalog_contract.py
- All contract tests must pass before deployment

### Integration Testing
- Multi-user isolation: Create 2 users, verify data separation
- Token expiration handling: Mock expired tokens, verify retry logic
- Rate limiting: Mock HTTP 429 responses, verify immediate failure
- Fallback behavior: Test without X-Forwarded-Access-Token header

### Unit Testing
- Token extraction from headers (present, absent, malformed)
- Exponential backoff logic (delays, total timeout)
- User_id validation in service constructors
- SDK auth_type configuration

---

## Documentation Updates Required

1. **docs/OBO_AUTHENTICATION.md**: Update with implementation details
   - Token extraction pattern
   - Dual authentication architecture diagram
   - Service layer modifications
   - Local development setup

2. **docs/databricks_apis/authentication_patterns.md**: Create or update
   - Pattern A: Service Principal (system operations)
   - Pattern B: On-Behalf-Of User (user operations)
   - Code examples for each pattern

3. **README.md**: Update development section
   - Environment variables for local OBO testing
   - How to test auth without Databricks Apps platform

---

## Research Completion Status

- [x] Databricks SDK authentication configuration patterns
- [x] FastAPI dependency injection for user context
- [x] Exponential backoff retry logic
- [x] Lakebase service principal authentication
- [x] User identity extraction from OBO token
- [x] Multi-user data isolation patterns
- [x] SDK version pinning and dependency management
- [x] Comprehensive observability metrics
- [x] Stateless retry pattern for concurrent requests
- [x] Technology stack validation
- [x] Integration patterns defined
- [x] Risk mitigation strategies
- [x] Performance considerations
- [x] Testing strategy
- [x] Documentation requirements

**Next Phase**: Design & Contracts (Phase 1)

