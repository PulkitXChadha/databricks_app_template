# Research: OBO-Only Authentication Implementation

**Feature**: Remove Service Principal Fallback - OBO-Only Authentication  
**Date**: 2025-10-14  
**Status**: Complete

## Executive Summary

This research document captures the technical decisions required to remove service principal authentication fallback and implement OBO-only authentication for Databricks API operations. All technical unknowns were resolved through the clarification process documented in the feature specification (Session 2025-10-14).

---

## 1. Authentication Architecture Simplification

### Decision: Remove Service Principal Fallback for Databricks APIs

**Chosen Approach**: Remove all automatic fallback to service principal authentication when user tokens are missing. Require user_token parameter in all Databricks API service initializations.

**Rationale**:
- User explicitly requested removal of fallback ("no need for backward compatibility")
- Eliminates privilege escalation risk where app could bypass user permissions
- Simplifies authentication code path (single pattern vs. dual pattern)
- Strengthens audit trails (all operations tied to actual users)
- Aligns with zero-trust security model

**Implementation Pattern**:
```python
# BEFORE (002-fix-api-authentication pattern):
class UnityCatalogService:
    def __init__(self, user_token: Optional[str] = None):
        self.user_token = user_token
    
    def _get_client(self) -> WorkspaceClient:
        if self.user_token:
            # OBO authentication
            return WorkspaceClient(host=..., token=self.user_token, auth_type="pat")
        else:
            # Automatic fallback to service principal
            return WorkspaceClient(
                host=...,
                client_id=...,
                client_secret=...,
                auth_type="oauth-m2m"
            )

# AFTER (003-obo-only-support pattern):
class UnityCatalogService:
    def __init__(self, user_token: str):  # Required, not Optional
        if not user_token:
            raise ValueError("user_token is required for UnityCatalogService")
        self.user_token = user_token
    
    def _get_client(self) -> WorkspaceClient:
        # ONLY OBO authentication - no fallback
        return WorkspaceClient(
            host=self.workspace_url,
            token=self.user_token,
            auth_type="pat"
        )
```

**Alternatives Considered**:
- **Keep fallback with warnings**: Rejected - defeats security purpose, maintains complexity
- **Configuration flag to enable/disable**: Rejected - adds configuration burden without value
- **Gradual migration**: Rejected - user explicitly stated no backward compatibility needed

**Breaking Changes**:
- Services cannot be initialized without user_token
- Requests without X-Forwarded-Access-Token header will fail (except /health)
- Local development requires Databricks CLI authentication

**References**:
- Feature spec FR-001, FR-002, FR-003
- Clarification Session 2025-10-14: No backward compatibility required
- Constitution Principle IX: Multi-User Data Isolation (strengthened)

---

## 2. Health Check and Metrics Endpoints Authentication

### Decision: Conditional Authentication Pattern

**Chosen Approach**: `/health` endpoint is public (no authentication), `/metrics` endpoint requires user authentication.

**Rationale**:
- Monitoring infrastructure needs unauthenticated health checks for uptime detection
- Kubernetes liveness/readiness probes don't have user credentials
- Metrics contain potentially sensitive operational data (request rates, error rates, user counts)
- Separate authentication requirements allows proper security boundaries

**Implementation Pattern**:
```python
# In server/app.py

# Public health endpoint (no auth dependency)
@app.get("/health")
async def health():
    """Public health check for monitoring infrastructure."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Authenticated metrics endpoint
@app.get("/metrics")
async def metrics(user_token: str = Depends(get_user_token)):
    """Prometheus metrics endpoint - requires authentication."""
    if not user_token:
        raise HTTPException(
            status_code=401,
            detail={"error_code": "AUTH_MISSING", "message": "Authentication required for metrics"}
        )
    
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

**Alternatives Considered**:
- **Both public**: Rejected - metrics expose sensitive operational data
- **Both authenticated**: Rejected - breaks monitoring infrastructure integration
- **API key for health checks**: Rejected - adds complexity without security benefit
- **mTLS for health checks**: Rejected - overengineered for template application

**Monitoring Infrastructure Impact**:
- Health checks work without configuration (monitoring-friendly)
- Metrics access requires authenticated users (security-conscious)
- Developers can view metrics during authenticated sessions
- Production monitoring can use service accounts with user tokens

**References**:
- Feature spec FR-008
- Clarification Session 2025-10-14: Conditional authentication pattern
- Industry best practices for health check endpoints

---

## 3. LakebaseService Authentication Strategy

### Decision: Maintain Hybrid Approach (Application-Level Credentials + User_ID Filtering)

**Chosen Approach**: LakebaseService continues using application-level database credentials with user_id filtering in queries. Does NOT require user_token parameter.

**Rationale**:
- Lakebase OAuth JWT tokens use service principal credentials (not OBO)
- Database connection pooling incompatible with per-user credentials
- User_id filtering provides data isolation at application level
- No breaking changes to existing database access patterns
- Maintains single connection pool for performance

**Implementation Pattern**:
```python
# LakebaseService - NO CHANGES from 002 pattern
class LakebaseService:
    def __init__(self):
        # NO user_token parameter - uses application-level credentials
        self.connection_params = self._get_connection_params_from_env()
    
    async def get_user_preferences(self, user_id: str) -> List[UserPreference]:
        """Get preferences with user_id filtering."""
        if not user_id:
            raise HTTPException(status_code=401, detail="User identity required")
        
        # Application-level database connection with user_id filtering
        query = """
            SELECT * FROM user_preferences
            WHERE user_id = :user_id  -- Enforces data isolation
        """
        return await self.db.execute(query, {"user_id": user_id})
```

**Router Pattern** (how to use with user identity):
```python
@router.get("/api/preferences")
async def get_preferences(user_token: str = Depends(get_user_token)):
    # Extract user_id using UserService (requires OBO token)
    user_service = UserService(user_token=user_token)
    user_id = await user_service.get_user_id()  # Requires authentication
    
    # Database operations use application-level credentials
    lakebase_service = LakebaseService()  # No user_token needed
    return await lakebase_service.get_user_preferences(user_id=user_id)
```

**Alternatives Considered**:
- **Per-user database credentials**: Rejected - connection pool can't support, token expiration complexity
- **Remove Lakebase entirely**: Rejected - breaking change, loses persistent storage
- **Require user_token in LakebaseService**: Rejected - doesn't use it for connection (confusing API)

**Security Guarantees**:
- All user-scoped queries MUST include `WHERE user_id = ?`
- user_id extraction requires valid user_token (UserService OBO)
- No direct user input for user_id (extracted from authentication context)
- Application-level credentials have minimal database permissions

**References**:
- Feature spec FR-002 (clarified: LakebaseService exception)
- Clarification Session 2025-10-14: Hybrid approach for database
- Constitution Principle IX: Multi-User Data Isolation

---

## 4. Background Jobs and Scheduled Tasks

### Decision: No Background Jobs Exist - Edge Case is Theoretical

**Chosen Approach**: Document that application has no background jobs, scheduled tasks, or automated processes. All operations are user-initiated.

**Rationale**:
- Current codebase analysis shows no cron jobs, scheduled tasks, or background workers
- All API endpoints are request-response (synchronous user-initiated)
- No async job queues or task schedulers configured
- Edge case mentioned in spec is theoretical concern, not actual requirement

**Implementation Impact**:
- No code changes needed (nothing to remove)
- Documentation should clarify scope: user-initiated operations only
- Future background jobs would need different authentication strategy (out of scope)

**If Background Jobs Were Added** (future consideration):
```python
# NOT IMPLEMENTED - for reference only
# Option 1: Pre-authorized operations (admin-initiated)
async def scheduled_cleanup_job():
    # Would need to use an admin user's token or separate auth mechanism
    pass

# Option 2: User-scoped background jobs
async def process_user_request(user_id: str, user_token: str):
    # Job would need to store user_token securely (token expiration concerns)
    pass
```

**Documentation Note**:
Add to docs/OBO_AUTHENTICATION.md:
> **Background Jobs**: This application has no background jobs, scheduled tasks, or automated processes. All operations are user-initiated through authenticated API requests. If background job functionality is added in the future, it would require a separate authentication strategy beyond the scope of OBO-only authentication.

**References**:
- Feature spec Edge Cases section
- Clarification Session 2025-10-14: No background jobs exist
- Codebase analysis: No task schedulers found

---

## 5. Testing Strategy for Multi-User Permission Scenarios

### Decision: Mixed Testing Approach (Unit Mocks, Integration Real Tokens)

**Chosen Approach**: Unit tests use mock/fake tokens, integration tests use real user tokens from multiple test accounts with different permission levels.

**Rationale**:
- Unit tests need speed and isolation (mock tokens sufficient)
- Integration tests need to validate actual Databricks permission enforcement
- Multiple test users enable verification of permission boundaries
- Real tokens test token extraction, validation, and API integration

**Implementation Pattern**:

**A. Unit Tests (with mocks)**:
```python
# tests/unit/test_unity_catalog_service.py
@pytest.fixture
def mock_user_token():
    """Mock user token for unit testing."""
    return "mock-token-12345"

def test_service_requires_token(mock_user_token):
    """Verify service initialization requires token."""
    # Should succeed with token
    service = UnityCatalogService(user_token=mock_user_token)
    assert service.user_token == mock_user_token
    
    # Should fail without token
    with pytest.raises(ValueError, match="user_token is required"):
        UnityCatalogService(user_token=None)

@patch('databricks.sdk.WorkspaceClient')
def test_list_catalogs(mock_client, mock_user_token):
    """Test catalog listing with mocked SDK."""
    service = UnityCatalogService(user_token=mock_user_token)
    # Mock SDK responses
    mock_client.return_value.catalogs.list.return_value = [...]
    
    catalogs = await service.list_catalogs()
    assert len(catalogs) > 0
```

**B. Integration Tests (with real tokens)**:
```python
# tests/integration/test_obo_multi_user.py
import subprocess

def get_test_user_token(profile: str) -> str:
    """Get real user token from Databricks CLI."""
    result = subprocess.run(
        ["databricks", "auth", "token", "--profile", profile],
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip()

@pytest.fixture
def user_a_token():
    """Token for test user A (admin permissions)."""
    return get_test_user_token("test-user-a")

@pytest.fixture
def user_b_token():
    """Token for test user B (limited permissions)."""
    return get_test_user_token("test-user-b")

async def test_permission_isolation(user_a_token, user_b_token):
    """Verify users see different catalogs based on permissions."""
    # User A (admin) sees all catalogs
    service_a = UnityCatalogService(user_token=user_a_token)
    catalogs_a = await service_a.list_catalogs()
    
    # User B (limited) sees subset of catalogs
    service_b = UnityCatalogService(user_token=user_b_token)
    catalogs_b = await service_b.list_catalogs()
    
    # Verify permission enforcement
    assert len(catalogs_a) >= len(catalogs_b)
    assert all(c in catalogs_a for c in catalogs_b)
```

**C. Test User Setup**:
```bash
# Configure test users in Databricks CLI
databricks auth login --profile test-user-a --host https://workspace.cloud.databricks.com
databricks auth login --profile test-user-b --host https://workspace.cloud.databricks.com

# Verify tokens work
databricks auth token --profile test-user-a
databricks auth token --profile test-user-b
```

**Alternatives Considered**:
- **Only mock tokens**: Rejected - doesn't validate actual permission enforcement
- **Only real tokens**: Rejected - slow, requires Databricks workspace access
- **Single test user**: Rejected - can't verify permission boundaries
- **Service principal for integration tests**: Rejected - doesn't test OBO pattern

**Test Coverage Goals**:
- Unit tests: 100% code coverage with fast execution (<10s)
- Integration tests: Permission enforcement validation (<2min)
- Contract tests: API schema validation with mocks
- End-to-end tests: Full workflow with real tokens (manual via quickstart.md)

**References**:
- Feature spec FR-010
- Clarification Session 2025-10-14: Mixed testing approach
- Existing test structure in tests/ directory

---

## 6. Legacy Environment Variables Handling

### Decision: No Special Handling for DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET

**Chosen Approach**: Legacy service principal environment variables may remain in deployed environments but are simply not used. No validation, warnings, or error handling needed.

**Rationale**:
- Simplest implementation (no additional code)
- Deployments can keep existing secrets without breaking
- No confusing warnings or errors for operators
- Clean separation: variables exist but are ignored
- Gradual cleanup can happen at operator convenience

**Implementation Impact**:
```python
# BEFORE (002 pattern): Used service principal env vars
def _create_service_principal_config(self) -> Config:
    return Config(
        host=os.environ["DATABRICKS_HOST"],
        client_id=os.environ["DATABRICKS_CLIENT_ID"],  # ← No longer read
        client_secret=os.environ["DATABRICKS_CLIENT_SECRET"],  # ← No longer read
        auth_type="oauth-m2m"
    )

# AFTER (003 pattern): Method removed, env vars ignored
# No code references DATABRICKS_CLIENT_ID or DATABRICKS_CLIENT_SECRET
# Variables can remain in environment without effect
```

**Documentation Updates**:
```markdown
# docs/OBO_AUTHENTICATION.md

## Environment Variables

### Required
- `DATABRICKS_HOST`: Workspace URL (required for all operations)
- `DATABRICKS_WAREHOUSE_ID`: SQL Warehouse ID (required for Unity Catalog queries)

### Not Used (Legacy)
- `DATABRICKS_CLIENT_ID`: No longer used (previously for service principal auth)
- `DATABRICKS_CLIENT_SECRET`: No longer used (previously for service principal auth)

These legacy variables may remain in your environment but are not referenced by the application.
```

**Alternatives Considered**:
- **Fail startup if present**: Rejected - breaks existing deployments unnecessarily
- **Log warnings**: Rejected - confusing noise in logs
- **Deprecation period**: Rejected - user explicitly said no backward compatibility needed
- **Auto-cleanup**: Rejected - outside application's responsibility

**Migration Impact**:
- Zero-impact migration for deployments with these variables
- Documentation informs operators they can be removed
- No forced timeline for cleanup

**References**:
- Feature spec FR-009
- Clarification Session 2025-10-14: No special handling needed
- User requirement: "no need for backward compatibility"

---

## Summary of Technical Decisions

| Decision Area | Chosen Approach | Key Rationale | Implementation Impact |
|---------------|----------------|---------------|---------------------|
| Service Principal Fallback | Remove entirely for Databricks APIs | Security, simplicity, user requirement | Breaking change - requires user_token |
| Health/Metrics Endpoints | Conditional (health public, metrics auth) | Monitoring infrastructure + security | Split authentication requirements |
| Lakebase Authentication | Maintain hybrid approach | Connection pooling, existing pattern | No changes to database layer |
| Background Jobs | None exist (theoretical edge case) | Codebase analysis | Documentation only |
| Testing Strategy | Mixed (unit mocks, integration real) | Speed + permission validation | Update test fixtures |
| Legacy Environment Variables | No special handling (ignore) | Simplicity, smooth migration | Zero code changes needed |

All decisions align with OBO-only architecture and strengthen security posture. No unresolved technical unknowns remain.

---

**Status**: ✅ All technical decisions complete  
**Next Phase**: Design (data models, contracts, quickstart)

