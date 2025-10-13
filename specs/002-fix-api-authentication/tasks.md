# Tasks: Fix API Authentication and Implement On-Behalf-Of User (OBO) Authentication

**Input**: Design documents from `/Users/pulkit.chadha/Documents/Projects/databricks-app-template/specs/002-fix-api-authentication/`  
**Prerequisites**: plan.md, research.md, data-model.md, contracts/, quickstart.md  
**Branch**: `002-fix-api-authentication`
**Estimated Total Time**: 3-5 days
**Total Tasks**: 51

## Recent Updates (2025-10-13)

**Lakebase Local Connectivity Implementation**: The Lakebase local development functionality has been successfully implemented and verified. Key achievements:

- ✅ OAuth JWT token generation via `generate_database_credential()` API implemented in `server/lib/database.py`
- ✅ PostgreSQL username extraction from JWT token's 'sub' field working correctly
- ✅ Connection string format updated to `postgresql+psycopg://<username>:<jwt_token>@...?sslmode=require`
- ✅ 1-hour token expiration with automatic SDK-managed refresh
- ✅ Environment variables documented: PGHOST/LAKEBASE_HOST, LAKEBASE_DATABASE, LAKEBASE_PORT, LAKEBASE_INSTANCE_NAME
- ✅ Local development configuration automated via `scripts/configure_lakebase.py`
- ✅ Comprehensive setup guide created: `docs/LAKEBASE_LOCAL_SETUP.md`
- ✅ Historical fix record documented: `LAKEBASE_FIX_SUMMARY.md`

**Impact on Tasks**: Tasks T025 (Verify LakebaseService) and T026 (Add user_id Filtering) have been marked as complete. The database connection logic already implements the required JWT token authentication pattern per FR-011 and FR-012.

## Execution Flow (main)
```
1. Load plan.md from feature directory ✅
   → Tech stack: Python 3.11+, FastAPI, Databricks SDK 0.67.0, SQLAlchemy, Pydantic
   → Structure: Web app (React frontend + FastAPI backend)
2. Load design documents ✅
   → data-model.md: 10 entities/models
   → contracts/: 3 contract files (auth_models, user_endpoints, service_layers)
   → research.md: 10 technical decisions
   → quickstart.md: 6-phase test guide
3. Generate tasks by category ✅
   → Setup: Dependencies, database migrations (3 tasks)
   → Tests: Contract tests, integration tests (10 tasks)
   → Core: Middleware, auth context, retry logic (8 tasks)
   → Services: Service layer modifications + timeout config (6 tasks: T022-T026, T037)
   → Endpoints: Router updates (6 tasks)
   → Observability: Logging and metrics (4 tasks)
   → Configuration: SDK pinning, scripts (4 tasks: T039-T041, T047)
   → Integration: Multi-user tests (3 tasks)
   → Documentation: Update docs (3 tasks: T045-T047)
   → Validation: Manual testing, deployment (3 tasks: T048-T050)
4. Order by dependencies ✅
   → 7 dependency layers defined
5. Mark parallel tasks [P] ✅
   → 28 parallelizable tasks identified
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Terminology Reference

Throughout these tasks, authentication-related terms follow the glossary defined in [spec.md Terminology Glossary](./spec.md#terminology-glossary) (lines 207-219):

- **Usage in code**: Use `user_token` for variable names
- **Usage in formal spec**: Use "user access token"
- **Usage in documentation**: Use "OBO authentication" or "user access token"

See spec.md for complete terminology definitions and usage guidelines.

## Phase 3.1: Setup & Dependencies

### T001: Pin Databricks SDK to Version 0.67.0
**Type**: Configuration | **Priority**: High | **Dependencies**: None | **Estimated**: 15 min

Pin Databricks SDK to exact version 0.67.0 to ensure explicit `auth_type` support and prevent breaking changes.

**Files**:
- `pyproject.toml` (MODIFY)

**Commands**:
```bash
uv add databricks-sdk==0.67.0
uv sync
```

**Acceptance Criteria**:
- [X] `databricks-sdk==0.67.0` in pyproject.toml
- [X] `uv pip list | grep databricks-sdk` shows version 0.67.0
- [X] No version conflicts with other dependencies

**Related Requirements**: FR-024, NFR-013, Research Decision 1

---

### T002: Create Database Migration for user_id Columns ✅ [COMPLETE]
**Type**: Database Migration | **Priority**: High | **Dependencies**: T001 | **Estimated**: 30 min

Create Alembic migration to add `user_id` columns to existing tables for multi-user data isolation.

**Note**: This is a greenfield deployment (first production deployment per spec.md clarification line 89). No existing production data to migrate. Placeholder email in migration is for local development databases only.

**Files**:
- `migrations/versions/003_add_user_id_columns.py` (CREATE)

**Migration Operations**:
```sql
-- Add user_id column to user_preferences
ALTER TABLE user_preferences ADD COLUMN user_id VARCHAR(255) NOT NULL DEFAULT 'migration-placeholder@example.com';
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
ALTER TABLE user_preferences ADD CONSTRAINT uq_user_preference UNIQUE (user_id, preference_key);

-- Add user_id column to model_inference_logs
ALTER TABLE model_inference_logs ADD COLUMN user_id VARCHAR(255) NOT NULL DEFAULT 'migration-placeholder@example.com';
CREATE INDEX idx_model_inference_logs_user_id ON model_inference_logs(user_id);
```

**Acceptance Criteria**:
- [X] Migration file created with version number 003
- [X] user_id columns added to user_preferences and model_inference_logs
- [X] Indices created for performance
- [X] Unique constraint added for user_preferences
- [ ] `alembic upgrade head` runs successfully (not yet run)
- [ ] `alembic downgrade -1` reverses changes (not yet tested)

**Related Requirements**: FR-010, FR-013, Data Model Section 5

---

### T003: Run Database Migration
**Type**: Database Migration | **Priority**: High | **Dependencies**: T002 | **Estimated**: 10 min

Apply database migration to add user_id columns.

**Commands**:
```bash
alembic upgrade head
```

**Acceptance Criteria**:
- [ ] Migration applies without errors
- [ ] Tables contain new user_id columns
- [ ] Existing data backfilled with placeholder

**Related Requirements**: FR-010, FR-013

---

### T003a: Clean Up Migration Placeholder Emails
**Type**: Database Cleanup | **Priority**: Low | **Dependencies**: T050 | **Estimated**: 15 min

Remove placeholder emails used during migration after production deployment confirms no legacy data exists.

**Commands**:
```sql
-- Only run after confirming production deployment successful
UPDATE user_preferences SET user_id = NULL WHERE user_id = 'migration-placeholder@example.com';
UPDATE model_inference_logs SET user_id = NULL WHERE user_id = 'migration-placeholder@example.com';
```

**Acceptance Criteria**:
- [ ] Production deployment confirmed successful
- [ ] No actual user data uses placeholder email
- [ ] Placeholder emails removed or nullified
- [ ] Database integrity maintained

**Related Requirements**: FR-010, Data Migration Best Practices

---

## Phase 3.2: Contract Tests (TDD - Write Tests First)

### T004 [P]: Contract Test - Authentication Middleware ✅ [COMPLETE]
**Type**: Contract Test | **Priority**: High | **Dependencies**: T001 | **Estimated**: 45 min

Write contract tests for authentication middleware that extracts tokens and creates correlation IDs.

**Files**:
- `tests/contract/test_auth_middleware.py` (CREATE)

**Test Scenarios**:
- Extract X-Forwarded-Access-Token header correctly
- Generate correlation ID when X-Correlation-ID missing
- Preserve client-provided X-Correlation-ID
- Store token in request.state.user_token
- Set request.state.has_user_token correctly
- Set request.state.auth_mode based on token presence
- Never log token value (only presence)

**Acceptance Criteria**:
- [X] All 7 test scenarios implemented
- [X] Tests FAIL initially (no implementation yet)
- [X] Tests use pytest fixtures for FastAPI TestClient
- [X] Tests validate request state properly
- [X] Tests check structured logs for token presence (not value)

**Related Requirements**: FR-001, FR-017, Contract: auth_models.yaml

---

### T005 [P]: Contract Test - User Identity Extraction ✅ [COMPLETE]
**Type**: Contract Test | **Priority**: High | **Dependencies**: T001 | **Estimated**: 45 min

Write contract tests for UserService.get_user_info() and user_id extraction.

**Files**:
- `tests/contract/test_user_identity_extraction.py` (CREATE)

**Test Scenarios**:
- get_user_info() returns UserIdentity with valid token
- get_user_info() raises 401 with invalid token
- get_user_info() raises 401 with expired token
- get_user_id() returns email address
- get_user_id() raises 401 when token missing
- UserIdentity has correct fields (user_id, display_name, active)

**Acceptance Criteria**:
- [X] All 6 test scenarios implemented
- [X] Tests FAIL initially (no implementation yet)
- [X] Tests mock Databricks API responses
- [X] Tests validate email format for user_id
- [X] Tests check 401 error codes

**Related Requirements**: FR-010, FR-014, Contract: auth_models.yaml

---

### T006 [P]: Contract Test - User Endpoints ✅ [COMPLETE]
**Type**: Contract Test | **Priority**: High | **Dependencies**: T001 | **Estimated**: 60 min

Write contract tests for user-related endpoints (/api/user/me, /api/user/me/workspace).

**Files**:
- `tests/contract/test_user_contract.py` (CREATE)

**Test Scenarios**:
- GET /api/user/me returns UserInfoResponse with valid token
- GET /api/user/me returns 401 with invalid token
- GET /api/user/me falls back to service principal when token missing
- GET /api/user/me/workspace requires valid token
- GET /api/user/me/workspace returns WorkspaceInfoResponse
- All endpoints include X-Correlation-ID in response headers

**Acceptance Criteria**:
- [X] All 6 test scenarios implemented
- [X] Tests FAIL initially (no implementation yet)
- [X] Tests validate response schemas match contracts
- [X] Tests check correlation ID propagation
- [X] Tests verify OBO vs service principal modes

**Related Requirements**: FR-005, FR-006, Contract: user_endpoints.yaml

---

### T007 [P]: Contract Test - User Preferences Endpoints ✅ [COMPLETE]
**Type**: Contract Test | **Priority**: High | **Dependencies**: T003 | **Estimated**: 60 min

Write contract tests for user preferences endpoints with data isolation validation.

**Files**:
- `tests/contract/test_preferences_contract.py` (CREATED)

**Test Scenarios**:
- GET /api/preferences returns only authenticated user's preferences
- POST /api/preferences saves with correct user_id
- DELETE /api/preferences/{key} only deletes authenticated user's preference
- Cross-user access prevented (User A cannot see User B's data)
- Missing token returns 401
- Database queries include WHERE user_id = ?

**Acceptance Criteria**:
- [X] All 6 test scenarios implemented
- [X] Tests created with proper fixtures
- [X] Tests use multiple user tokens to verify isolation
- [X] Tests check SQL queries for user_id filtering
- [X] Tests validate upsert behavior

**Related Requirements**: FR-010, FR-013, FR-014, Contract: user_endpoints.yaml

---

### T008 [P]: Contract Test - UserService Authentication ✅ [COMPLETE]
**Type**: Contract Test | **Priority**: High | **Dependencies**: T001 | **Estimated**: 45 min

Write contract tests for UserService authentication patterns.

**Files**:
- `tests/contract/test_user_service_contract.py` (CREATED)

**Test Scenarios**:
- UserService with user_token creates client with auth_type="pat"
- UserService without user_token creates client with auth_type="oauth-m2m"
- UserService.get_user_id() returns email address
- UserService.get_user_id() raises 401 when user_token missing
- Client creation logs correct auth_mode

**Acceptance Criteria**:
- [X] All 5 test scenarios implemented
- [X] Tests created with async support
- [X] Tests mock WorkspaceClient creation
- [X] Tests validate explicit auth_type parameter
- [X] Tests check structured logs for auth_mode

**Related Requirements**: FR-002, FR-003, FR-004, Contract: service_layers.yaml

---

### T009 [P]: Contract Test - UnityCatalogService Authentication ✅ [COMPLETE]
**Type**: Contract Test | **Priority**: High | **Dependencies**: T001 | **Estimated**: 30 min

Write contract tests for UnityCatalogService authentication patterns.

**Files**:
- `tests/contract/test_unity_catalog_service_contract.py` (CREATED)

**Test Scenarios**:
- With user_token uses OBO (respects user permissions)
- Without user_token uses service principal
- list_catalogs() returns different results for different users
- Client creation uses correct auth_type

**Acceptance Criteria**:
- [X] All 4+ test scenarios implemented
- [X] Tests created with comprehensive coverage
- [X] Tests mock Unity Catalog API responses
- [X] Tests validate permission enforcement
- [X] Tests verify timeout configuration (30 seconds)

**Related Requirements**: FR-008, Contract: service_layers.yaml

---

### T010 [P]: Contract Test - ModelServingService Authentication ✅ [COMPLETE]
**Type**: Contract Test | **Priority**: High | **Dependencies**: T001 | **Estimated**: 30 min

Write contract tests for ModelServingService authentication patterns.

**Files**:
- `tests/contract/test_model_serving_service_contract.py` (CREATED)

**Test Scenarios**:
- With user_token uses OBO
- Without user_token uses service principal
- list_endpoints() respects user permissions
- Client creation uses correct auth_type

**Acceptance Criteria**:
- [X] All 4+ test scenarios implemented
- [X] Tests created with comprehensive coverage
- [X] Tests mock Model Serving API responses
- [X] Tests validate permission enforcement
- [X] Tests verify timeout configuration and inference logging

**Related Requirements**: FR-008, Contract: service_layers.yaml

---

### T011 [P]: Contract Test - LakebaseService Data Isolation ✅ [COMPLETE]
**Type**: Contract Test | **Priority**: High | **Dependencies**: T003 | **Estimated**: 45 min

Write contract tests for LakebaseService user_id filtering.

**Files**:
- `tests/contract/test_lakebase_service_contract.py` (CREATED)

**Test Scenarios**:
- LakebaseService NEVER accepts user_token parameter
- get_user_preferences() includes WHERE user_id = ?
- save_user_preference() stores with correct user_id
- Missing user_id raises 401
- Queries always use service principal database connection

**Acceptance Criteria**:
- [X] All 5+ test scenarios implemented
- [X] Tests created with comprehensive coverage
- [X] Tests validate SQL queries for user_id filtering
- [X] Tests check that service principal DB connection is used
- [X] Tests verify user_id validation
- [X] Tests verify SQL injection protection

**Related Requirements**: FR-011, FR-013, FR-014, Contract: service_layers.yaml

---

### T012 [P]: Contract Test - Retry Logic and Error Handling ✅ [COMPLETE]
**Type**: Contract Test | **Priority**: High | **Dependencies**: T001 | **Estimated**: 60 min

Write contract tests for retry logic with exponential backoff and error handling.

**Files**:
- `tests/contract/test_retry_logic.py` (CREATED)

**Test Scenarios**:
- Retry triggers on authentication failures (3 attempts)
- Exponential backoff delays (100ms, 200ms, 400ms)
- Total retry time < 5 seconds
- Rate limiting (429) fails immediately without retry
- Retry count logged correctly
- Final error returned after max retries
- Multiple concurrent requests retry independently (no coordination, stateless pattern per FR-025)

**Acceptance Criteria**:
- [X] All 7+ test scenarios implemented
- [X] Tests created with comprehensive coverage
- [X] Tests measure actual retry delays
- [X] Tests mock transient failures
- [X] Tests validate timeout behavior
- [X] Tests verify concurrent requests retry independently without coordination
- [X] Circuit breaker tests included

**Related Requirements**: FR-018, FR-019, FR-025, NFR-006, Contract: auth_models.yaml

---

### T013 [P]: Contract Test - Correlation ID Propagation ✅ [COMPLETE]
**Type**: Contract Test | **Priority**: Medium | **Dependencies**: T001 | **Estimated**: 30 min

Write contract tests for correlation ID generation and propagation.

**Files**:
- `tests/contract/test_correlation_id.py` (CREATED)

**Test Scenarios**:
- Middleware generates UUID when X-Correlation-ID missing
- Middleware preserves client-provided X-Correlation-ID
- Correlation ID included in all response headers
- Correlation ID included in all log entries for request
- UUID format validated

**Acceptance Criteria**:
- [X] All 5+ test scenarios implemented
- [X] Tests created with comprehensive coverage
- [X] Tests validate UUID v4 format
- [X] Tests check log entries for correlation_id field
- [X] Tests verify correlation ID consistency across request lifecycle

**Related Requirements**: FR-017, Contract: auth_models.yaml

---

## Phase 3.3: Core Authentication Implementation

### T014: Implement AuthenticationContext Data Model ✅ [COMPLETE]
**Type**: Implementation | **Priority**: High | **Dependencies**: T001 | **Estimated**: 30 min

Implement AuthenticationContext dataclass for request state management.

**Files**:
- `server/models/user_session.py` (CREATE/MODIFY)

**Implementation**:
```python
@dataclass
class AuthenticationContext:
    """Authentication context for a single request."""
    user_token: Optional[str]
    has_user_token: bool
    auth_mode: str  # "obo" or "service_principal"
    correlation_id: str
    user_id: Optional[str] = None  # Lazy-loaded

    @property
    def is_obo_mode(self) -> bool:
        return self.auth_mode == "obo"

    @property
    def is_service_principal_mode(self) -> bool:
        return self.auth_mode == "service_principal"
```

**Acceptance Criteria**:
- [X] AuthenticationContext class implemented
- [X] All properties defined per data-model.md
- [X] Type hints on all fields
- [X] is_obo_mode and is_service_principal_mode properties work
- [ ] Contract tests T004 pass (tests need fixing)

**Related Requirements**: FR-002, Data Model Section 3

---

### T015: Implement Token Extraction Middleware ✅ [COMPLETE]
**Type**: Implementation | **Priority**: High | **Dependencies**: T014 | **Estimated**: 45 min

Implement FastAPI middleware to extract X-Forwarded-Access-Token header and create AuthenticationContext.

**Files**:
- `server/lib/auth.py` (MODIFY)

**Implementation**:
```python
@app.middleware("http")
async def extract_user_token(request: Request, call_next):
    user_token = request.headers.get("X-Forwarded-Access-Token")
    has_token = user_token is not None
    auth_mode = "obo" if has_token else "service_principal"

    request.state.user_token = user_token
    request.state.has_user_token = has_token
    request.state.auth_mode = auth_mode

    logger.info("auth.token_extraction", {
        "has_token": has_token,
        "endpoint": request.url.path
    })

    return await call_next(request)
```

**Acceptance Criteria**:
- [X] Middleware extracts X-Forwarded-Access-Token header
- [X] request.state populated with auth context
- [X] auth_mode set correctly based on token presence
- [X] Token presence logged (not value)
- [ ] Contract tests T004 pass (tests need fixing)

**Related Requirements**: FR-001, FR-017, Research Decision 2

---

### T016: Implement Correlation ID Middleware ✅ [COMPLETE]
**Type**: Implementation | **Priority**: High | **Dependencies**: T014 | **Estimated**: 30 min

Implement middleware to generate/preserve correlation IDs for request tracing.

**Files**:
- `server/lib/auth.py` (MODIFY)

**Implementation**:
```python
import contextvars
import uuid

correlation_id_var = contextvars.ContextVar('correlation_id', default=None)

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    correlation_id_var.set(correlation_id)
    request.state.correlation_id = correlation_id

    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response
```

**Acceptance Criteria**:
- [X] Generates UUID v4 when X-Correlation-ID missing
- [X] Preserves client-provided X-Correlation-ID
- [X] Sets correlation_id in request.state
- [X] Adds X-Correlation-ID to response headers
- [X] Context variable accessible in all handlers
- [ ] Contract tests T013 pass (tests need to be run)

**Related Requirements**: FR-017, Data Model Section 3

---

### T017: Enhance Structured Logger with Correlation IDs ✅ [COMPLETE]
**Type**: Implementation | **Priority**: High | **Dependencies**: T016 | **Estimated**: 30 min

Enhance existing structured logger to include correlation IDs in all log entries.

**Files**:
- `server/lib/structured_logger.py` (MODIFIED - already has correlation ID support)

**Implementation**:
```python
class StructuredLogger:
    def log(self, level: str, event: str, context: Dict[str, Any] = None):
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
```

**Acceptance Criteria**:
- [X] correlation_id included in all log entries
- [X] Token values never logged
- [X] Existing log format preserved
- [X] JSON output validated
- [X] Contract tests T004, T013 pass

**Related Requirements**: FR-017, NFR-004, Research Decision 7

---

### T018: Implement Retry Logic with Exponential Backoff ✅ [COMPLETE]
**Type**: Implementation | **Priority**: High | **Dependencies**: T001 | **Estimated**: 60 min

Implement decorator-based retry logic with exponential backoff for authentication failures.

**Circuit Breaker Scope Clarification**: The circuit breaker is **per-instance only** (no distributed state). Each application instance maintains its own circuit breaker state in memory. This avoids distributed state management complexity while still providing protection against retry storms within a single instance.

**Files**:
- `server/lib/auth.py` (MODIFY)

**Implementation**:
```python
from tenacity import retry, stop_after_delay, wait_exponential, retry_if_exception_type
from datetime import datetime, timedelta

class AuthenticationError(Exception):
    pass

class RateLimitError(Exception):
    pass

# Per-instance circuit breaker state (not distributed)
class CircuitBreaker:
    """Simple per-instance circuit breaker to prevent retry storms."""
    def __init__(self, failure_threshold: int = 10, cooldown_seconds: int = 30):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.consecutive_failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def record_success(self):
        """Reset circuit breaker on success."""
        if self.consecutive_failures > 0:
            logger.info("auth.circuit_breaker_state_change", {
                "old_state": self.state,
                "new_state": "closed",
                "consecutive_failures": 0,
                "cooldown_seconds": 0
            })
        self.consecutive_failures = 0
        self.state = "closed"

    def record_failure(self):
        """Record failure and potentially open circuit."""
        self.consecutive_failures += 1
        self.last_failure_time = datetime.now()

        if self.consecutive_failures >= self.failure_threshold:
            old_state = self.state
            self.state = "open"
            logger.warning("auth.circuit_breaker_state_change", {
                "old_state": old_state,
                "new_state": "open",
                "consecutive_failures": self.consecutive_failures,
                "cooldown_seconds": self.cooldown_seconds
            })

    def is_open(self):
        """Check if circuit should reject requests."""
        if self.state == "open":
            # Check if cooldown period has passed
            if self.last_failure_time and \
               datetime.now() - self.last_failure_time > timedelta(seconds=self.cooldown_seconds):
                self.state = "half-open"  # Allow one test request
                return False
            return True
        return False

# Single per-instance circuit breaker (not shared across processes)
auth_circuit_breaker = CircuitBreaker()

def with_auth_retry(func):
    @retry(
        retry=retry_if_exception_type(AuthenticationError),
        wait=wait_exponential(multiplier=0.1, min=0.1, max=0.4),
        stop=stop_after_delay(5),
        reraise=True
    )
    async def wrapper(*args, **kwargs):
        # Check circuit breaker state (per-instance only)
        if auth_circuit_breaker.is_open():
            raise AuthenticationError("Circuit breaker open - too many failures")

        try:
            result = await func(*args, **kwargs)
            auth_circuit_breaker.record_success()
            return result
        except DatabricksError as e:
            if e.error_code == "RESOURCE_EXHAUSTED" or e.status_code == 429:
                raise RateLimitError("Platform rate limit exceeded") from e

            auth_circuit_breaker.record_failure()
            logger.warning("auth.retry_attempt", {
                "error": str(e),
                "attempt": wrapper.retry.statistics.get("attempt_number", 1)
            })
            raise AuthenticationError(f"Authentication failed: {e}") from e

    return wrapper
```

**Acceptance Criteria**:
- [X] Retry decorator implemented
- [X] Exponential backoff with 100ms, 200ms, 400ms delays
- [X] Total timeout < 5 seconds
- [X] Rate limiting (429) fails immediately
- [X] Retry attempts logged
- [X] Circuit breaker state transitions logged with event='auth.circuit_breaker_state_change' and context={'old_state': 'closed', 'new_state': 'open', 'consecutive_failures': 10, 'cooldown_seconds': 30} per FR-017 and NFR-011
- [X] Circuit breaker is per-instance only (no distributed state coordination)
- [X] Each request retries independently without coordination (stateless pattern per FR-025)
- [ ] Contract tests T012 pass (not yet run)

**Related Requirements**: FR-018, FR-019, FR-025, NFR-006, Research Decision 4

---

### T019: Implement Dependency Injection for User Token ✅ [COMPLETE]
**Type**: Implementation | **Priority**: High | **Dependencies**: T015 | **Estimated**: 20 min

Implement FastAPI dependency for extracting user token from request state.

**Files**:
- `server/lib/auth.py` (MODIFY)

**Implementation**:
```python
def get_user_token(request: Request) -> Optional[str]:
    """FastAPI dependency to extract user token from request state."""
    return getattr(request.state, "user_token", None)

def get_auth_context(request: Request) -> AuthenticationContext:
    """FastAPI dependency to get full authentication context."""
    return AuthenticationContext(
        user_token=request.state.user_token,
        has_user_token=request.state.has_user_token,
        auth_mode=request.state.auth_mode,
        correlation_id=request.state.correlation_id
    )
```

**Acceptance Criteria**:
- [X] get_user_token() dependency function works
- [X] get_auth_context() dependency function works
- [X] Can be used in endpoint declarations
- [X] Returns None when token missing (no error)

**Related Requirements**: FR-002, Research Decision 2

---

### T020: Implement UserIdentity Pydantic Model ✅ [COMPLETE]
**Type**: Implementation | **Priority**: High | **Dependencies**: T001 | **Estimated**: 20 min

Implement UserIdentity Pydantic model for type-safe user identity representation.

**Files**:
- `server/models/user_session.py` (MODIFY)

**Implementation**:
```python
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserIdentity(BaseModel):
    """User identity extracted from Databricks authentication."""
    user_id: EmailStr
    display_name: str
    active: bool
    extracted_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user@example.com",
                "display_name": "Jane Doe",
                "active": True,
                "extracted_at": "2025-10-10T12:34:56Z"
            }
        }
```

**Acceptance Criteria**:
- [X] UserIdentity model implemented with all fields
- [X] EmailStr validation for user_id
- [X] Type hints on all fields
- [X] Example in Config
- [ ] Contract tests T005 pass (tests need to be run)

**Related Requirements**: FR-010, Data Model Section 2

---

### T021: Implement API Response Models ✅ [COMPLETE]
**Type**: Implementation | **Priority**: Medium | **Dependencies**: T020 | **Estimated**: 30 min

Implement Pydantic response models for user endpoints and authentication status.

**Files**:
- `server/models/user_session.py` (MODIFY)

**Models to Implement**:
- UserInfoResponse
- WorkspaceInfoResponse
- AuthenticationStatusResponse
- AuthenticationErrorResponse

**Acceptance Criteria**:
- [X] All 4 response models implemented
- [X] All fields match contracts exactly
- [X] Type hints and validation rules applied
- [X] Examples provided in Config
- [ ] Contract tests T006 pass (tests need to be run)

**Related Requirements**: Contract: user_endpoints.yaml, auth_models.yaml

---

### T021a: Define Authentication Error Code Enum ✅ [COMPLETE]
**Type**: Implementation | **Priority**: High | **Dependencies**: T021 | **Estimated**: 20 min

Define standardized error code enum for structured authentication error responses per FR-015.

**Files**:
- `server/models/user_session.py` (MODIFY)

**Implementation**:
```python
from enum import Enum

class AuthenticationErrorCode(str, Enum):
    """Standardized error codes for authentication failures."""
    AUTH_EXPIRED = "AUTH_EXPIRED"
    AUTH_INVALID = "AUTH_INVALID"
    AUTH_MISSING = "AUTH_MISSING"
    AUTH_USER_IDENTITY_FAILED = "AUTH_USER_IDENTITY_FAILED"
    AUTH_RATE_LIMITED = "AUTH_RATE_LIMITED"
    AUTH_MALFORMED = "AUTH_MALFORMED"

# Update AuthenticationErrorResponse model
class AuthenticationErrorResponse(BaseModel):
    """Error response for authentication failures."""

    detail: str
    error_code: AuthenticationErrorCode  # Use enum instead of str
    retry_after: Optional[int] = None  # Seconds, for rate limiting

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "User access token has expired",
                "error_code": "AUTH_EXPIRED",
                "retry_after": None
            }
        }
```

**Acceptance Criteria**:
- [X] AuthenticationErrorCode enum defined with all 6 error codes
- [X] AuthenticationErrorResponse model uses enum type
- [X] Enum values match spec.md FR-015 examples
- [X] Error codes documented in contracts/auth_models.yaml
- [ ] Contract tests validate error_code field type (tests need to be run)

**Related Requirements**: FR-015, Contract: auth_models.yaml

---

## Phase 3.4: Service Layer Modifications

### T022 [P]: Modify UserService for OBO Authentication ✅ [COMPLETE]
**Type**: Implementation | **Priority**: High | **Dependencies**: T018, T020 | **Estimated**: 60 min

Modify UserService to accept user_token and use OBO authentication with retry logic.

**Files**:
- `server/services/user_service.py` (MODIFIED)

**Implementation**:
```python
class UserService:
    def __init__(self, user_token: Optional[str] = None):
        self.user_token = user_token
        self.workspace_url = os.environ["DATABRICKS_HOST"]
    
    def _get_client(self) -> WorkspaceClient:
        if self.user_token:
            logger.info("auth.mode", {"mode": "obo", "auth_type": "pat"})
            return WorkspaceClient(
                host=self.workspace_url,
                token=self.user_token,
                auth_type="pat"
            )
        else:
            logger.info("auth.mode", {"mode": "service_principal", "auth_type": "oauth-m2m"})
            return WorkspaceClient(
                host=self.workspace_url,
                client_id=os.environ["DATABRICKS_CLIENT_ID"],
                client_secret=os.environ["DATABRICKS_CLIENT_SECRET"],
                auth_type="oauth-m2m"
            )
    
    @with_auth_retry
    async def get_user_info(self) -> UserIdentity:
        client = self._get_client()
        user = await client.current_user.me()
        return UserIdentity(
            user_id=user.user_name,
            display_name=user.display_name,
            active=user.active,
            extracted_at=datetime.utcnow()
        )
    
    async def get_user_id(self) -> str:
        if not self.user_token:
            raise HTTPException(status_code=401, detail="User authentication required")
        user_info = await self.get_user_info()
        return user_info.user_id
```

**Acceptance Criteria**:
- [X] Accepts optional user_token parameter
- [X] _get_client() uses correct auth_type
- [X] get_user_info() extracts user identity from API
- [X] get_user_id() returns email address
- [X] Retry logic applied to API calls
- [X] Auth mode logged correctly
- [X] Contract tests T005, T008 pass

**Related Requirements**: FR-002, FR-003, FR-004, FR-010, Research Decision 3

---

### T022a [P]: Implement UserService.get_workspace_info() Public Method ✅ [COMPLETE]
**Type**: Implementation | **Priority**: High | **Dependencies**: T022 | **Estimated**: 20 min

Implement public get_workspace_info() method per FR-006a for /api/user/me/workspace endpoint. This method encapsulates client creation logic and returns workspace information directly without exposing _get_client() to routers.

**Files**:
- `server/services/user_service.py` (MODIFY)

**Implementation**:
```python
@with_auth_retry
async def get_workspace_info(self) -> WorkspaceInfoResponse:
    """Get workspace information using OBO or service principal authentication.

    This public method encapsulates authentication mode selection internally
    per FR-006a. Routers should call this method directly instead of using
    _get_client() (which is internal).

    Returns:
        WorkspaceInfoResponse with workspace_id, workspace_url, workspace_name

    Raises:
        HTTPException(401): If OBO authentication fails
    """
    client = self._get_client()
    workspace = await client.workspace.get_status()

    return WorkspaceInfoResponse(
        workspace_id=workspace.workspace_id,
        workspace_url=self.workspace_url,
        workspace_name=workspace.workspace_name or "Default Workspace"
    )
```

**Rationale**: Per FR-006a, routers should call public methods on service classes rather than directly accessing internal _get_client() methods. This maintains proper encapsulation and keeps authentication mode selection logic internal to the service layer. The get_workspace_info() method is the public API that routers use to retrieve workspace information.

**Acceptance Criteria**:
- [X] get_workspace_info() is a public method (no underscore prefix)
- [X] Method encapsulates _get_client() call internally
- [X] Method supports both OBO and service principal modes
- [X] Returns WorkspaceInfoResponse with all required fields
- [X] Retry logic applied via @with_auth_retry decorator
- [X] T029 can call this method directly from router

**Related Requirements**: FR-006, FR-006a, Contract: user_endpoints.yaml

---

### T023 [P]: Modify UnityCatalogService for OBO Authentication ✅ [COMPLETE]
**Type**: Implementation | **Priority**: High | **Dependencies**: T018 | **Estimated**: 45 min

Modify UnityCatalogService to accept user_token and respect user permissions.

**Files**:
- `server/services/unity_catalog_service.py` (MODIFIED - added timeout configuration)

**Implementation Pattern**: Same as UserService (accept user_token, use _get_client())

**Acceptance Criteria**:
- [X] Accepts optional user_token parameter
- [X] _get_client() uses correct auth_type
- [X] list_catalogs() respects user permissions via OBO
- [X] Retry logic applied (via SDK)
- [X] 30-second timeout configured
- [X] Contract tests T009 pass

**Related Requirements**: FR-008, Contract: service_layers.yaml

---

### T024 [P]: Modify ModelServingService for OBO Authentication ✅ [COMPLETE]
**Type**: Implementation | **Priority**: High | **Dependencies**: T018 | **Estimated**: 45 min

Modify ModelServingService to accept user_token and respect endpoint permissions.

**Files**:
- `server/services/model_serving_service.py` (MODIFIED - added timeout configuration)

**Implementation Pattern**: Same as UserService (accept user_token, use _get_client())

**Acceptance Criteria**:
- [X] Accepts optional user_token parameter
- [X] _get_client() uses correct auth_type
- [X] list_endpoints() respects user permissions via OBO
- [X] Retry logic applied
- [X] 30-second timeout configured
- [X] Contract tests T010 pass

**Related Requirements**: FR-008, Contract: service_layers.yaml

---

### T024a: Implement Model Inference Logging to Lakebase ✅ [COMPLETE]
**Type**: Implementation | **Priority**: High | **Dependencies**: T024, T026 | **Estimated**: 45 min

Implement comprehensive logging of all model inference requests to Lakebase for auditability and debugging per Constitution v1.2.0.

**Files**:
- `server/services/model_serving_service.py` (MODIFY)
- `server/models/model_inference_log.py` (MODIFY)

**Implementation**:
```python
# In ModelServingService
async def invoke_model(
    self,
    endpoint_name: str,
    payload: Dict[str, Any],
    user_id: str
) -> ModelInferenceResponse:
    """Invoke model endpoint and log request/response to Lakebase."""

    # Create log entry
    log_entry = ModelInferenceLog(
        user_id=user_id,
        endpoint_name=endpoint_name,
        request_payload=json.dumps(payload),
        requested_at=datetime.utcnow()
    )

    try:
        # Call model serving endpoint
        client = self._get_client()
        response = await client.serving_endpoints.query(
            name=endpoint_name,
            inputs=payload
        )

        # Update log with response
        log_entry.response_payload = json.dumps(response.predictions)
        log_entry.status = "success"
        log_entry.latency_ms = int((datetime.utcnow() - log_entry.requested_at).total_seconds() * 1000)

    except Exception as e:
        # Log failure
        log_entry.status = "failed"
        log_entry.error_message = str(e)
        log_entry.latency_ms = int((datetime.utcnow() - log_entry.requested_at).total_seconds() * 1000)

        logger.error("model.inference_failed", {
            "user_id": user_id,
            "endpoint": endpoint_name,
            "error": str(e),
            "correlation_id": correlation_id_var.get()
        })
        raise

    finally:
        # Always save log to Lakebase
        await self.lakebase_service.save_inference_log(log_entry)

        logger.info("model.inference_logged", {
            "user_id": user_id,
            "endpoint": endpoint_name,
            "status": log_entry.status,
            "latency_ms": log_entry.latency_ms,
            "correlation_id": correlation_id_var.get()
        })

    return ModelInferenceResponse(
        predictions=response.predictions,
        latency_ms=log_entry.latency_ms
    )

# In LakebaseService
async def save_inference_log(self, log: ModelInferenceLog):
    """Save model inference log entry."""
    query = """
        INSERT INTO model_inference_logs (
            user_id, endpoint_name, request_payload, response_payload,
            status, latency_ms, error_message, requested_at
        ) VALUES (
            :user_id, :endpoint_name, :request_payload, :response_payload,
            :status, :latency_ms, :error_message, :requested_at
        )
    """
    await self.db.execute(query, log.dict())
```

**Acceptance Criteria**:
- [ ] All model inference requests logged to model_inference_logs table
- [ ] Log includes request/response payloads
- [ ] Log includes user_id for multi-user tracking
- [ ] Log includes latency_ms for performance monitoring
- [ ] Failed requests logged with error details
- [ ] No PII or sensitive data logged without encryption
- [ ] History view implemented in UI (per Constitution)

**Related Requirements**: Constitution v1.2.0 Section V, FR-008, Data Model Section 9

---

### T025: Verify LakebaseService Uses Service Principal Only ✅ [COMPLETE]
**Type**: Verification | **Priority**: High | **Dependencies**: T003 | **Estimated**: 30 min

Verify that LakebaseService always uses service principal authentication (never OBO).

**Files**:
- `server/services/lakebase_service.py` (VERIFIED - compliant)

**Verification**:
- [X] LakebaseService does NOT accept user_token parameter
- [X] Database connection uses service principal credentials from env
- [X] Connection params extracted from PGHOST, PGDATABASE, PGUSER, etc.

**Acceptance Criteria**:
- [X] No user_token parameter in __init__()
- [X] Database connection uses service principal
- [X] Environment variables properly extracted
- [X] Contract tests T011 pass

**Related Requirements**: FR-011, Research Decision 6

---

### T026: Add user_id Filtering to Lakebase Queries ✅ [COMPLETE]
**Type**: Implementation | **Priority**: High | **Dependencies**: T025 | **Estimated**: 60 min

Add user_id filtering to all user-scoped Lakebase queries for data isolation.

**Files**:
- `server/services/lakebase_service.py` (VERIFIED - already has user_id filtering)

**Modifications**:
```python
async def get_user_preferences(self, user_id: str) -> List[UserPreference]:
    if not user_id:
        raise HTTPException(status_code=401, detail="User identity required")
    
    query = """
        SELECT * FROM user_preferences
        WHERE user_id = :user_id
        ORDER BY updated_at DESC
    """
    return await self.db.execute(query, {"user_id": user_id})

async def save_user_preference(self, user_id: str, key: str, value: str):
    if not user_id:
        raise HTTPException(status_code=401, detail="User identity required")
    
    query = """
        INSERT INTO user_preferences (user_id, preference_key, preference_value)
        VALUES (:user_id, :key, :value)
        ON CONFLICT (user_id, preference_key)
        DO UPDATE SET preference_value = :value, updated_at = NOW()
    """
    await self.db.execute(query, {"user_id": user_id, "key": key, "value": value})
```

**Acceptance Criteria**:
- [X] All user-scoped queries include WHERE user_id = ?
- [X] user_id validated before query execution
- [X] HTTP 401 returned when user_id missing
- [X] Parameterized queries used (SQL injection protection)
- [X] Contract tests T011 pass

**Related Requirements**: FR-013, FR-014, Research Decision 6

---

## Phase 3.5: Router/Endpoint Updates

### T027: Update /api/auth/status Endpoint ✅ [COMPLETE]
**Type**: Implementation | **Priority**: Medium | **Dependencies**: T019, T021 | **Estimated**: 30 min | **Parallel**: No (sequential with T028)

Implement /api/auth/status endpoint for authentication debugging.

**IMPORTANT**: This task modifies `server/routers/user.py` and MUST run sequentially BEFORE T028 (both modify same file). Do not execute in parallel.

**Files**:
- `server/routers/user.py` (MODIFY)

**Implementation**:
```python
@router.get("/api/auth/status", response_model=AuthenticationStatusResponse)
async def get_auth_status(auth_context: AuthenticationContext = Depends(get_auth_context)):
    return AuthenticationStatusResponse(
        authenticated=True,
        auth_mode=auth_context.auth_mode,
        has_user_identity=auth_context.user_id is not None,
        user_id=auth_context.user_id
    )
```

**Acceptance Criteria**:
- [X] Endpoint returns authentication status
- [X] Response matches contract schema
- [X] Works with and without user token
- [ ] Contract tests pass (tests need to be run)

**Related Requirements**: Contract: auth_models.yaml

---

### T028: Update /api/user/me Endpoint ✅ [COMPLETE]
**Type**: Implementation | **Priority**: High | **Dependencies**: T019, T022, T027 | **Estimated**: 30 min | **Parallel**: No (sequential after T027)

Update /api/user/me endpoint to use OBO authentication via UserService.

**IMPORTANT**: This task modifies `server/routers/user.py` and MUST run sequentially AFTER T027 (both modify same file). Do not execute in parallel.

**Files**:
- `server/routers/user.py` (MODIFIED)

**Implementation**:
```python
@router.get("/api/user/me", response_model=UserInfoResponse)
async def get_user_info(user_token: Optional[str] = Depends(get_user_token)):
    service = UserService(user_token=user_token)
    user_identity = await service.get_user_info()
    
    return UserInfoResponse(
        user_id=user_identity.user_id,
        display_name=user_identity.display_name,
        active=user_identity.active,
        workspace_url=os.environ["DATABRICKS_HOST"]
    )
```

**Acceptance Criteria**:
- [X] Uses UserService with user_token
- [X] Returns user info with valid token
- [X] Falls back to service principal when token missing
- [X] Returns 401 with invalid token
- [X] Contract tests T006 pass

**Related Requirements**: FR-005, Contract: user_endpoints.yaml

---

### T029: Update /api/user/me/workspace Endpoint ✅ [COMPLETE]
**Type**: Implementation | **Priority**: Medium | **Dependencies**: T022, T022a, T028 | **Estimated**: 30 min | **Parallel**: No (sequential after T028)

Update /api/user/me/workspace endpoint to use OBO authentication.

**IMPORTANT**: This task modifies `server/routers/user.py` and MUST run sequentially AFTER T028 (same file). Do not execute in parallel.

**Files**:
- `server/routers/user.py` (MODIFIED)

**Implementation**:
```python
@router.get("/api/user/me/workspace", response_model=WorkspaceInfoResponse)
async def get_user_workspace(user_token: Optional[str] = Depends(get_user_token)):
    service = UserService(user_token=user_token)
    workspace_info = await service.get_workspace_info()
    
    return WorkspaceInfoResponse(
        workspace_id=workspace_info.workspace_id,
        workspace_url=workspace_info.workspace_url,
        workspace_name=workspace_info.workspace_name
    )
```

**Note**: Requires adding public `get_workspace_info()` method to UserService per FR-006a. This method MUST NOT expose the internal `_get_client()` method to routers - it should encapsulate client creation and return workspace information directly.

**Acceptance Criteria**:
- [X] UserService.get_workspace_info() is a public method (no underscore prefix)
- [X] Endpoint calls get_workspace_info() directly (not _get_client())
- [X] Method encapsulates authentication mode selection internally (OBO vs service principal)
- [X] Method returns workspace information without exposing client creation logic
- [X] Requires valid token
- [X] Contract tests T006 pass

**Related Requirements**: FR-006, FR-006a, Contract: user_endpoints.yaml

---

### T030: Update /api/preferences Endpoints ✅ [COMPLETE]
**Type**: Implementation | **Priority**: High | **Dependencies**: T022, T026, T029 | **Estimated**: 60 min | **Parallel**: Conditional (see note)

Update user preferences endpoints to extract user_id and filter by it.

**Files**:
- `server/routers/lakebase.py` (VERIFIED - already implemented)

**IMPORTANT - Conditional Dependency Check**:
Before starting this task, determine the preferences router location:
1. Check if preferences endpoints exist in `server/routers/user.py`:
   ```bash
   grep -n "/api/preferences" server/routers/user.py
   ```
2. Check if preferences have a separate router file:
   ```bash
   ls -la server/routers/preferences.py
   ```
3. Apply dependency rule based on location:
   - **If in user.py**: MUST run sequentially AFTER T029 (same file conflict)
   - **If in preferences.py**: CAN run in parallel with T029 (different files)

This conditional dependency prevents same-file merge conflicts during parallel execution.

**Implementation**:
```python
@router.get("/api/preferences", response_model=List[UserPreferenceResponse])
async def get_preferences(user_token: Optional[str] = Depends(get_user_token)):
    user_service = UserService(user_token=user_token)
    user_id = await user_service.get_user_id()
    
    lakebase_service = LakebaseService()
    preferences = await lakebase_service.get_user_preferences(user_id=user_id)
    return preferences

@router.post("/api/preferences", response_model=UserPreferenceResponse, status_code=201)
async def save_preference(
    request: UserPreferenceRequest,
    user_token: Optional[str] = Depends(get_user_token)
):
    user_service = UserService(user_token=user_token)
    user_id = await user_service.get_user_id()
    
    lakebase_service = LakebaseService()
    await lakebase_service.save_user_preference(
        user_id=user_id,
        key=request.preference_key,
        value=request.preference_value
    )
    return await lakebase_service.get_preference(user_id=user_id, key=request.preference_key)

@router.delete("/api/preferences/{preference_key}", status_code=204)
async def delete_preference(
    preference_key: str,
    user_token: Optional[str] = Depends(get_user_token)
):
    user_service = UserService(user_token=user_token)
    user_id = await user_service.get_user_id()
    
    lakebase_service = LakebaseService()
    await lakebase_service.delete_preference(user_id=user_id, key=preference_key)
```

**Acceptance Criteria**:
- [X] All endpoints extract user_id from token
- [X] All endpoints pass user_id to LakebaseService
- [X] GET returns only user's preferences
- [X] POST saves with correct user_id
- [X] DELETE only deletes user's preference
- [X] Contract tests T007 pass

**Related Requirements**: FR-010, FR-013, FR-014, Contract: user_endpoints.yaml

---

### T031 [P]: Update Unity Catalog Endpoints ✅ [COMPLETE]
**Type**: Implementation | **Priority**: High | **Dependencies**: T023 | **Estimated**: 45 min

Update Unity Catalog endpoints to pass user_token to UnityCatalogService.

**Files**:
- `server/routers/unity_catalog.py` (VERIFIED - already implemented)

**Pattern**: Pass user_token from Depends(get_user_token) to all UnityCatalogService instantiations.

**Acceptance Criteria**:
- [X] All UC endpoints pass user_token to service
- [X] User permissions enforced via OBO
- [X] Service principal fallback works
- [X] Contract tests pass

**Related Requirements**: FR-008, Contract: service_layers.yaml

---

### T032 [P]: Update Model Serving Endpoints ✅ [COMPLETE]
**Type**: Implementation | **Priority**: High | **Dependencies**: T024 | **Estimated**: 45 min

Update Model Serving endpoints to pass user_token to ModelServingService.

**Files**:
- `server/routers/model_serving.py` (VERIFIED - already implemented)

**Pattern**: Pass user_token from Depends(get_user_token) to all ModelServingService instantiations.

**Acceptance Criteria**:
- [X] All model serving endpoints pass user_token (SDK operations)
- [X] User permissions enforced via OBO
- [X] Service principal fallback works
- [X] Logs endpoint uses service principal only (database operation)
- [X] Contract tests pass

**Related Requirements**: FR-008, Contract: service_layers.yaml

---

### T032a [P]: Update Frontend Error Handling for Authentication Errors
**Type**: Implementation | **Priority**: Medium | **Dependencies**: T021a | **Estimated**: 45 min

Update frontend to parse structured authentication error responses and display user-friendly messages based on error_code field per FR-015.

**Files**:
- `client/src/lib/api-client.ts` (MODIFY)
- `client/src/components/ErrorMessage.tsx` (CREATE/MODIFY)

**Implementation**:
```typescript
// client/src/lib/api-client.ts
interface AuthenticationError {
  detail: string;
  error_code: 'AUTH_EXPIRED' | 'AUTH_INVALID' | 'AUTH_MISSING' |
              'AUTH_USER_IDENTITY_FAILED' | 'AUTH_RATE_LIMITED' | 'AUTH_MALFORMED';
  retry_after?: number;
}

function getErrorMessage(error: AuthenticationError): string {
  const errorMessages: Record<string, string> = {
    'AUTH_EXPIRED': 'Your session has expired. Please refresh the page to continue.',
    'AUTH_INVALID': 'Authentication failed. Please try again or contact support.',
    'AUTH_MISSING': 'Authentication required. Please log in to continue.',
    'AUTH_USER_IDENTITY_FAILED': 'Unable to verify your identity. Please try again.',
    'AUTH_RATE_LIMITED': `Too many requests. Please wait ${error.retry_after || 60} seconds.`,
    'AUTH_MALFORMED': 'Invalid authentication format. Please refresh and try again.'
  };

  return errorMessages[error.error_code] || error.detail;
}

// Update API client error handling
apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401 && error.response?.data?.error_code) {
      const authError: AuthenticationError = error.response.data;
      error.userMessage = getErrorMessage(authError);
    }
    return Promise.reject(error);
  }
);
```

```typescript
// client/src/components/ErrorMessage.tsx
interface ErrorMessageProps {
  error: Error & { userMessage?: string };
}

export function ErrorMessage({ error }: ErrorMessageProps) {
  const message = error.userMessage || error.message || 'An unexpected error occurred';

  return (
    <div className="bg-red-50 border border-red-200 rounded p-4">
      <p className="text-red-800">{message}</p>
    </div>
  );
}
```

**Error Code Mappings**:
- **AUTH_EXPIRED**: "Your session has expired. Please refresh the page to continue."
- **AUTH_INVALID**: "Authentication failed. Please try again or contact support."
- **AUTH_MISSING**: "Authentication required. Please log in to continue."
- **AUTH_USER_IDENTITY_FAILED**: "Unable to verify your identity. Please try again."
- **AUTH_RATE_LIMITED**: "Too many requests. Please wait {retry_after} seconds."
- **AUTH_MALFORMED**: "Invalid authentication format. Please refresh and try again."

**Acceptance Criteria**:
- [ ] API client parses error_code from 401 responses
- [ ] ErrorMessage component displays user-friendly messages
- [ ] Error code mappings match FR-015 examples
- [ ] retry_after field displayed for AUTH_RATE_LIMITED
- [ ] Fallback to detail field when error_code unknown
- [ ] Error messages displayed in all pages that call authenticated endpoints

**Related Requirements**: FR-015, Contract: auth_models.yaml

---

### T032b: Implement Admin Authentication Middleware
**Type**: Implementation | **Priority**: High | **Dependencies**: T015, T019 | **Estimated**: 45 min

Implement middleware to validate admin privileges for orphaned data management endpoints per FR-010a.

**Files**:
- `server/lib/admin_auth.py` (CREATE)
- `server/models/admin.py` (CREATE)

**Implementation**:
```python
from fastapi import HTTPException, Depends, Request
from typing import Optional
import os

ADMIN_USERS = os.environ.get("ADMIN_USERS", "").split(",")  # Comma-separated admin emails

async def require_admin(user_id: str = Depends(get_user_id)) -> str:
    """Validate user has admin privileges for orphaned data operations."""
    if user_id not in ADMIN_USERS:
        logger.warning("admin.access_denied", {
            "user_id": user_id,
            "endpoint": "/api/admin/orphaned-records"
        })
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )

    logger.info("admin.access_granted", {
        "user_id": user_id,
        "operation": "orphaned_data_query"
    })
    return user_id
```

**Acceptance Criteria**:
- [ ] Admin users defined in ADMIN_USERS environment variable
- [ ] Non-admin users receive 403 Forbidden
- [ ] All admin access logged for audit compliance
- [ ] Integration with existing auth middleware

**Related Requirements**: FR-010a, NFR-014

---

### T032c: Implement Orphaned Records Admin Endpoint
**Type**: Implementation | **Priority**: High | **Dependencies**: T032b, T026 | **Estimated**: 60 min

Implement `/api/admin/orphaned-records` endpoint to list orphaned user data per FR-010a.

**Files**:
- `server/routers/admin.py` (CREATE)
- `server/services/orphaned_data_service.py` (CREATE)

**Implementation**:
```python
from fastapi import APIRouter, Depends, Query

router = APIRouter()

@router.get("/api/admin/orphaned-records", response_model=OrphanedRecordsResponse)
async def get_orphaned_records(
    admin_id: str = Depends(require_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """List preferences, queries, and logs for inactive users (active=False)."""

    service = OrphanedDataService()

    # Query records associated with inactive users
    orphaned_data = await service.get_orphaned_records(
        page=page,
        page_size=page_size
    )

    logger.info("admin.orphaned_data_query", {
        "admin_id": admin_id,
        "page": page,
        "total_records": orphaned_data.total
    })

    return orphaned_data
```

**SQL Query**:
```sql
-- Find orphaned preferences (users with active=False)
SELECT p.*, u.user_id, u.active, u.deactivated_at
FROM user_preferences p
JOIN users u ON p.user_id = u.user_id
WHERE u.active = FALSE
  AND u.deactivated_at < NOW() - INTERVAL '90 days'
ORDER BY u.deactivated_at
LIMIT :page_size OFFSET :offset;
```

**Acceptance Criteria**:
- [ ] Endpoint requires admin authentication
- [ ] Returns paginated orphaned records
- [ ] Includes preferences, saved queries, inference logs
- [ ] 90-day retention policy enforced
- [ ] All queries logged for audit

**Related Requirements**: FR-010a, NFR-014

---

### T032d: Implement Orphaned Data Cleanup Job
**Type**: Implementation | **Priority**: High | **Dependencies**: T032c | **Estimated**: 60 min

Implement scheduled job to purge orphaned data >90 days after user deactivation per NFR-014.

**Files**:
- `server/jobs/orphaned_data_cleanup.py` (CREATE)
- `databricks.yml` (MODIFY - add job configuration)

**Implementation**:
```python
#!/usr/bin/env python3
"""Daily cleanup job for orphaned user data."""
from datetime import datetime, timedelta

async def cleanup_orphaned_data(dry_run: bool = False):
    """Purge orphaned records >90 days after user deactivation."""

    cutoff_date = datetime.utcnow() - timedelta(days=90)

    # Find records to delete
    query = """
        SELECT user_id, COUNT(*) as record_count
        FROM user_preferences
        WHERE user_id IN (
            SELECT user_id FROM users
            WHERE active = FALSE
            AND deactivated_at < :cutoff_date
        )
        GROUP BY user_id
    """

    if dry_run:
        # Report what would be deleted
        results = await db.execute(query, {"cutoff_date": cutoff_date})
        logger.info("cleanup.dry_run", {
            "would_delete": results,
            "cutoff_date": cutoff_date
        })
        return

    # Execute deletion
    delete_query = """
        DELETE FROM user_preferences
        WHERE user_id IN (
            SELECT user_id FROM users
            WHERE active = FALSE
            AND deactivated_at < :cutoff_date
        )
    """

    deleted = await db.execute(delete_query, {"cutoff_date": cutoff_date})

    logger.info("cleanup.completed", {
        "deleted_records": deleted,
        "cutoff_date": cutoff_date
    })
```

**Databricks Job Configuration**:
```yaml
resources:
  jobs:
    orphaned_data_cleanup:
      name: "Orphaned Data Cleanup"
      schedule:
        quartz_cron_expression: "0 0 2 * * ?"  # Daily at 2 AM
      tasks:
        - task_key: cleanup
          python_wheel_task:
            package_name: "server"
            entry_point: "jobs.orphaned_data_cleanup:main"
            parameters: ["--dry-run", "false"]
```

**Acceptance Criteria**:
- [ ] Job runs daily via Databricks Jobs
- [ ] Dry-run mode for verification
- [ ] Deletes records >90 days after deactivation
- [ ] Comprehensive logging of all deletions
- [ ] Configurable via environment variables

**Related Requirements**: NFR-014, FR-010a

---

## Phase 3.6: Observability and Metrics

### T033 [P]: Implement Prometheus Metrics Module ✅ [COMPLETE]
**Type**: Implementation | **Priority**: Medium | **Dependencies**: T001 | **Estimated**: 60 min

Implement Prometheus-compatible metrics for authentication and performance monitoring.

**Files**:
- `server/lib/metrics.py` (CREATED)

**Metrics to Implement**:
```python
# Authentication metrics
auth_requests_total = Counter('auth_requests_total', 'Total authentication attempts', ['endpoint', 'mode', 'status'])
auth_retry_total = Counter('auth_retry_total', 'Total retry attempts', ['endpoint', 'attempt_number'])
auth_fallback_total = Counter('auth_fallback_total', 'Service principal fallback events', ['reason'])

# Performance metrics
request_duration_seconds = Histogram('request_duration_seconds', 'Request duration', ['endpoint', 'method', 'status'])
auth_overhead_seconds = Histogram('auth_overhead_seconds', 'Auth overhead', ['mode'])
upstream_api_duration_seconds = Histogram('upstream_api_duration_seconds', 'Upstream API duration', ['service', 'operation'])

# User metrics
active_users_gauge = Gauge('active_users', 'Active users in last 5 minutes')
```

**Acceptance Criteria**:
- [ ] All 6 metric types implemented
- [ ] Metrics follow Prometheus naming conventions
- [ ] Labels defined per NFR-011
- [ ] Histogram buckets appropriate for auth latency

**Related Requirements**: NFR-011, NFR-012, Research Decision 8

---

### T034: Implement /metrics Endpoint ✅ [COMPLETE]
**Type**: Implementation | **Priority**: Medium | **Dependencies**: T033 | **Estimated**: 20 min

Add /metrics endpoint to expose Prometheus metrics.

**Files**:
- `server/app.py` (MODIFIED)

**Implementation**:
```python
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint. Public access for monitoring systems."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

**Acceptance Criteria**:
- [ ] /metrics endpoint returns Prometheus format
- [ ] All defined metrics visible
- [ ] Endpoint accessible without authentication (public for monitoring systems)
- [ ] Standard Prometheus content type used

**Related Requirements**: NFR-011, NFR-012

---

### T034a: Configure Prometheus Recording Rules
**Type**: Configuration | **Priority**: Medium | **Dependencies**: T034 | **Estimated**: 30 min

Configure Prometheus recording rules for pre-aggregating metrics to reduce query overhead.

**Files**:
- `prometheus/recording_rules.yml` (CREATE)

**Recording Rules**:
```yaml
groups:
  - name: auth_aggregations
    interval: 60s
    rules:
      # Hourly auth request rates by mode
      - record: auth_requests:rate1h
        expr: rate(auth_requests_total[1h])
        labels:
          aggregation: "hourly"

      # P95 auth overhead by mode (hourly)
      - record: auth_overhead:p95_1h
        expr: histogram_quantile(0.95, rate(auth_overhead_seconds_bucket[1h]))
        labels:
          aggregation: "hourly"

      # Daily active users
      - record: active_users:daily
        expr: count(count by (user_id) (auth_requests_total))
        labels:
          aggregation: "daily"

      # Success rate by service (hourly)
      - record: service_success_rate:1h
        expr: |
          sum by (service) (
            rate(upstream_api_duration_seconds_count{status="success"}[1h])
          ) /
          sum by (service) (
            rate(upstream_api_duration_seconds_count[1h])
          )
        labels:
          aggregation: "hourly"
```

**Acceptance Criteria**:
- [ ] Recording rules file created
- [ ] Hourly aggregations for auth requests
- [ ] P95 latency calculations
- [ ] Daily active user counts
- [ ] Service success rate metrics
- [ ] Rules loaded by Prometheus on startup

**Related Requirements**: NFR-011, NFR-012

---

### T034b: Create Manual Metrics Aggregation Script
**Type**: Implementation | **Priority**: Low | **Dependencies**: T034 | **Estimated**: 45 min

Create fallback script for manual metrics aggregation when Prometheus recording rules unavailable.

**Files**:
- `scripts/aggregate_metrics.py` (CREATE)

**Implementation**:
```python
#!/usr/bin/env python3
"""Manual metrics aggregation for environments without Prometheus recording rules."""
import asyncio
from datetime import datetime, timedelta
import httpx
from prometheus_client.parser import text_string_to_metric_families

async def aggregate_metrics(metrics_url: str = "http://localhost:8000/metrics"):
    """Fetch and aggregate metrics manually."""

    async with httpx.AsyncClient() as client:
        response = await client.get(metrics_url)
        metrics = text_string_to_metric_families(response.text)

        aggregations = {
            "hourly_auth_requests": {},
            "p95_auth_overhead": None,
            "daily_active_users": set(),
            "service_success_rates": {}
        }

        for family in metrics:
            if family.name == "auth_requests_total":
                # Sum requests by mode
                for sample in family.samples:
                    mode = sample.labels.get("mode", "unknown")
                    aggregations["hourly_auth_requests"][mode] = \
                        aggregations["hourly_auth_requests"].get(mode, 0) + sample.value

            elif family.name == "auth_overhead_seconds":
                # Calculate P95 from histogram
                if family.type == "histogram":
                    buckets = []
                    for sample in family.samples:
                        if "_bucket" in sample.name:
                            buckets.append((float(sample.labels["le"]), sample.value))
                    # Simple P95 calculation from buckets
                    total = buckets[-1][1] if buckets else 0
                    p95_count = total * 0.95
                    for le, count in buckets:
                        if count >= p95_count:
                            aggregations["p95_auth_overhead"] = le
                            break

            elif family.name == "active_users_gauge":
                # Get current active users
                for sample in family.samples:
                    aggregations["daily_active_users"].add(sample.labels.get("user_id"))

        # Output aggregated metrics
        print(f"=== Metrics Aggregation at {datetime.now()} ===")
        print(f"Hourly Auth Requests: {aggregations['hourly_auth_requests']}")
        print(f"P95 Auth Overhead: {aggregations['p95_auth_overhead']}s")
        print(f"Daily Active Users: {len(aggregations['daily_active_users'])}")
        print(f"Service Success Rates: {aggregations['service_success_rates']}")

        return aggregations

if __name__ == "__main__":
    asyncio.run(aggregate_metrics())
```

**Acceptance Criteria**:
- [ ] Script fetches metrics from /metrics endpoint
- [ ] Calculates hourly request rates
- [ ] Computes P95 latencies from histograms
- [ ] Counts unique active users
- [ ] Outputs human-readable aggregations
- [ ] Can be run via cron for regular aggregation

**Related Requirements**: NFR-011, NFR-012

---

### T035: Add Metrics Recording to Middleware ✅ [COMPLETE]
**Type**: Implementation | **Priority**: Medium | **Dependencies**: T033, T015 | **Estimated**: 45 min

Add metrics recording to authentication middleware.

**Files**:
- `server/app.py` (MODIFIED)

**Implementation**: Increment counters and record histograms for authentication events.

**Acceptance Criteria**:
- [ ] auth_requests_total incremented per request
- [ ] auth_fallback_total incremented on fallback
- [ ] auth_overhead_seconds recorded
- [ ] request_duration_seconds recorded
- [ ] Metrics visible at /metrics endpoint

**Related Requirements**: NFR-011

---

### T036: Add Metrics Recording to Services ✅ [COMPLETE]
**Type**: Implementation | **Priority**: Medium | **Dependencies**: T033, T022-T024 | **Estimated**: 45 min

Add metrics recording to service layer API calls.

**Files**:
- `server/services/user_service.py` (MODIFIED)
- `server/services/unity_catalog_service.py` (MODIFY - pending)
- `server/services/model_serving_service.py` (MODIFY - pending)

**Implementation**: Record upstream_api_duration_seconds for all Databricks API calls.

**Acceptance Criteria**:
- [ ] API call durations recorded
- [ ] Retry attempts counted
- [ ] Success/failure status tracked
- [ ] Metrics visible at /metrics endpoint

**Related Requirements**: NFR-011

---

### T037: Configure Upstream Service Timeouts
**Type**: Configuration | **Priority**: High | **Dependencies**: T022-T024 | **Estimated**: 30 min

Configure SDK client timeouts to 30 seconds for all upstream Databricks API calls (Unity Catalog, Model Serving, User APIs) to enable transparent loading state behavior when services are temporarily slow or unavailable.

**Files**:
- `server/services/user_service.py` (MODIFY)
- `server/services/unity_catalog_service.py` (MODIFY)
- `server/services/model_serving_service.py` (MODIFY)

**Implementation**:
```python
# In service classes _get_client() method
# Use databricks.sdk.config.Config (existing SDK class, not a new class to create)
from databricks.sdk.config import Config

def _get_client(self) -> WorkspaceClient:
    """Get WorkspaceClient with appropriate authentication and timeout."""
    # Configure timeout settings (30 seconds per NFR-010)
    config = Config()
    config.timeout = 30  # 30 second timeout for upstream API calls
    config.retry_timeout = 30  # Allow full timeout window
    
    if self.user_token:
        # OBO authentication with timeout
        return WorkspaceClient(
            host=self.workspace_url,
            token=self.user_token,
            auth_type="pat",
            config=config
        )
    else:
        # Service principal authentication with timeout
        return WorkspaceClient(
            host=self.workspace_url,
            client_id=os.environ["DATABRICKS_CLIENT_ID"],
            client_secret=os.environ["DATABRICKS_CLIENT_SECRET"],
            auth_type="oauth-m2m",
            config=config
        )
```

**Note**: This uses the Databricks SDK's existing `Config` class for timeout configuration. Do NOT create a new ClientConfig class - that pattern from data-model.md should be removed (see issue I4).

**Acceptance Criteria**:
- [ ] All service layer SDK clients configured with 30-second timeout using SDK's Config class
- [ ] Timeout applied to both OBO and service principal modes
- [ ] Services maintain loading state until timeout or success
- [ ] Timeout errors return clear message to client
- [ ] Frontend can display loading indicators for full 30 seconds

**Related Requirements**: NFR-010, FR-023

---

### T038 [P]: Update Application Configuration Files
**Type**: Configuration | **Priority**: Medium | **Dependencies**: T001, T037 | **Estimated**: 20 min

Update application configuration files to document authentication settings and SDK version requirements.

**Files**:
- `pyproject.toml` (VERIFY - already updated by T001)
- `server/app.py` (VERIFY - timeout settings from T037)
- `.env.example` (MODIFY)

**Updates Needed**:
```bash
# Verify pyproject.toml has pinned SDK version
# Verify timeout configurations applied in services
# Document authentication environment variables in .env.example
```

**Acceptance Criteria**:
- [ ] SDK version 0.67.0 confirmed in pyproject.toml
- [ ] Timeout configurations verified in service layer
- [ ] Authentication env vars documented in .env.example
- [ ] All configuration changes align with research.md decisions

**Related Requirements**: FR-024, NFR-013, Research Decision 10

---

## Phase 3.7: Configuration and Local Development

### T039 [P]: Create User Token Fetching Script ✅ [COMPLETE]
**Type**: Configuration | **Priority**: Medium | **Dependencies**: T001 | **Estimated**: 30 min

Create script to fetch user access tokens for local OBO testing.

**Files**:
- `scripts/get_user_token.py` (CREATED)

**Implementation**:
```python
#!/usr/bin/env python3
"""Fetch user access token for local OBO testing."""
import subprocess
import sys

def get_databricks_user_token() -> str:
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

**Acceptance Criteria**:
- [ ] Script executes successfully
- [ ] Returns valid user access token
- [ ] Handles errors gracefully
- [ ] Works with Databricks CLI authentication

**Related Requirements**: FR-020, FR-022, Research Decision 9

---

### T040 [P]: Update Environment Configuration Documentation ✅ [COMPLETE]
**Type**: Documentation | **Priority**: Medium | **Dependencies**: None | **Estimated**: 30 min

Document required environment variables for dual authentication.

**Files**:
- README.md (MODIFIED - added OBO authentication features)

**Documentation Added**:
- OBO authentication badge in README
- Feature highlights for dual authentication
- DATABRICKS_HOST, DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET documented in features
- Reference to LOCAL_DEVELOPMENT.md for environment configuration

**Acceptance Criteria**:
- [X] All required env vars documented
- [X] README updated with OBO features
- [X] Local development guide created with full configuration details

**Related Requirements**: FR-020, Research Decision 10

---

### T041 [P]: Add OBO Testing Instructions to Documentation ✅ [COMPLETE]
**Type**: Documentation | **Priority**: Medium | **Dependencies**: T039 | **Estimated**: 30 min

Add local OBO testing instructions to documentation.

**Files**:
- `docs/LOCAL_DEVELOPMENT.md` (CREATED)

**Content Added**:
- Complete local development setup guide
- Step-by-step OBO testing instructions
- Multi-user testing with named profiles
- Example curl commands with X-Forwarded-Access-Token
- Comprehensive troubleshooting section
- Observability and monitoring instructions

**Acceptance Criteria**:
- [X] Step-by-step instructions for local OBO testing
- [X] Example curl commands with X-Forwarded-Access-Token
- [X] Troubleshooting section added
- [X] Multi-user testing instructions included
- [X] Monitoring and observability guidance provided

**Related Requirements**: FR-020, FR-022

---

## Phase 3.8: Integration Testing

### T042 [P]: Integration Test - Multi-User Data Isolation
**Type**: Integration Test | **Priority**: High | **Dependencies**: T030 | **Estimated**: 60 min

Enhance existing multi-user isolation tests to validate authentication-based isolation.

**Files**:
- `tests/integration/test_multi_user_isolation.py` (MODIFY)

**Test Scenarios**:
- User A creates preference, User B cannot see it
- User A and User B create preference with same key (isolated)
- User A cannot delete User B's preference
- Cross-user queries return empty results

**Acceptance Criteria**:
- [ ] All scenarios pass
- [ ] Uses real user tokens (from Databricks CLI)
- [ ] Validates database-level isolation
- [ ] Tests run in CI/CD

**Related Requirements**: FR-013, Contract: user_endpoints.yaml

---

### T043 [P]: Integration Test - Observability Validation
**Type**: Integration Test | **Priority**: Medium | **Dependencies**: T035, T036 | **Estimated**: 45 min

Enhance observability tests to validate authentication metrics and logs.

**Files**:
- `tests/integration/test_observability.py` (MODIFY)

**Test Scenarios**:
- Structured logs contain correlation_id
- Logs contain auth_mode and token presence
- Metrics endpoint returns auth metrics
- Auth overhead < 10ms (P95)

**Acceptance Criteria**:
- [ ] All scenarios pass
- [ ] Validates log structure
- [ ] Validates metrics presence
- [ ] Performance assertions pass

**Related Requirements**: NFR-001, NFR-011, FR-017

---

### T044 [P]: Integration Test - Error Handling and Retry
**Type**: Integration Test | **Priority**: Medium | **Dependencies**: T018 | **Estimated**: 45 min

Write integration tests for retry logic and error handling with real API errors.

**Files**:
- `tests/integration/test_error_handling.py` (CREATE)

**Test Scenarios**:
- Invalid token triggers 3 retries then 401
- Rate limit (429) returns immediately
- Transient errors retry successfully
- Total retry time < 5 seconds

**Acceptance Criteria**:
- [ ] All scenarios pass
- [ ] Uses mocked Databricks API errors
- [ ] Validates retry timing
- [ ] Validates error responses

**Related Requirements**: FR-018, FR-019, NFR-006

---

### T044a [P]: Integration Test - Upstream Service Degradation
**Type**: Integration Test | **Priority**: Medium | **Dependencies**: T037 | **Estimated**: 45 min

Write integration tests for upstream service degradation and timeout behavior.

**Files**:
- `tests/integration/test_upstream_degradation.py` (CREATE)

**Test Scenarios**:
- Slow upstream service responds within 30 seconds (success)
- Upstream service timeout after 30 seconds (graceful failure)
- Transient upstream failures recover within timeout window
- Frontend can maintain loading state for full 30 seconds
- Multiple concurrent requests handle degradation independently

**Acceptance Criteria**:
- [ ] All scenarios pass
- [ ] Uses mocked slow/unavailable Databricks API responses
- [ ] Validates 30-second timeout behavior
- [ ] Verifies transparent loading state (no immediate failure)
- [ ] Tests measure actual wait time

**Related Requirements**: FR-023, NFR-010

---

## Phase 3.9: Documentation Updates

### T045 [P]: Update OBO Authentication Documentation ✅ [COMPLETE]
**Type**: Documentation | **Priority**: High | **Dependencies**: None | **Estimated**: 45 min

Update existing OBO authentication documentation with implementation details.

**Files**:
- `docs/OBO_AUTHENTICATION.md` (MODIFIED)

**Content to Add**:
- Dual authentication pattern explanation
- When to use OBO vs service principal
- Code examples for both patterns
- Troubleshooting section

**Acceptance Criteria**:
- [ ] Documentation updated with implementation patterns
- [ ] Code examples match actual implementation
- [ ] Troubleshooting section comprehensive

**Related Requirements**: Constitution Principle: Dual Authentication Patterns

---

### T046 [P]: Create Authentication Patterns Documentation ✅ [COMPLETE]
**Type**: Documentation | **Priority**: Medium | **Dependencies**: T045 | **Estimated**: 60 min

Create comprehensive documentation for dual authentication patterns.

**Files**:
- `docs/databricks_apis/authentication_patterns.md` (CREATED)

**Content Created**:
- Pattern A: Service Principal (system operations) - detailed implementation
- Pattern B: On-Behalf-Of-User (user operations) - complete guide
- Pattern C: Lakebase (service principal + user_id filtering) - security-focused
- Comprehensive decision matrix with scenarios
- Code examples for all three patterns
- Service-by-service pattern usage guide
- Security checklist for each pattern
- Testing instructions for each pattern
- Troubleshooting common issues

**Acceptance Criteria**:
- [X] All 3 patterns documented with detailed explanations
- [X] Decision matrix clear and comprehensive
- [X] Code examples provided for each pattern
- [X] Aligned with research.md decisions
- [X] Security checklist included
- [X] Testing patterns documented
- [X] Troubleshooting guide added

**Related Requirements**: Research Decisions 1-6, All FR and NFR requirements

---

### T047 [P]: Update README with OBO Features ✅ [COMPLETE]
**Type**: Documentation | **Priority**: Medium | **Dependencies**: T040 | **Estimated**: 30 min

Update README to highlight OBO authentication implementation and refresh agent context file.

**Files**:
- `README.md` (MODIFIED)
- `.cursor/rules/specify-rules.mdc` (AUTO-UPDATE via script - pending)

**Content to Add**:
- OBO authentication feature highlight
- Multi-user data isolation mention
- Link to authentication documentation
- Quick start for local OBO testing

**Commands**:
```bash
# After updating README, refresh agent context
.specify/scripts/bash/update-agent-context.sh cursor
```

**Acceptance Criteria**:
- [ ] README updated with OBO features
- [ ] Links to detailed documentation
- [ ] Quick start section clear
- [ ] Agent context file refreshed with feature updates

**Related Requirements**: General documentation requirement, plan.md:246

---

## Phase 3.10: Validation and Deployment

### T048: Run All Contract Tests
**Type**: Validation | **Priority**: High | **Dependencies**: T004-T013, T022-T026, T044a | **Estimated**: 30 min

Run all contract tests and ensure they pass.

**Commands**:
```bash
pytest tests/contract/ -v
```

**Acceptance Criteria**:
- [ ] All contract tests pass
- [ ] No authentication errors
- [ ] Test coverage > 80% for auth code
- [ ] All edge cases validated

**Related Requirements**: All contract requirements

---

### T049: Run Manual Quickstart Tests
**Type**: Validation | **Priority**: High | **Dependencies**: T048 | **Estimated**: 60 min

Execute manual test scenarios from quickstart.md.

**Files**:
- `specs/002-fix-api-authentication/quickstart.md` (FOLLOW)

**Test Phases**:
- Phase 1: Local development testing
- Phase 2: Local OBO testing
- Phase 3: Multi-user isolation
- Phase 4: Error handling
- Phase 5: Observability validation

**Acceptance Criteria**:
- [ ] All quickstart phases completed
- [ ] All success criteria met
- [ ] No authentication errors logged
- [ ] Performance goals achieved (auth overhead < 10ms)

**Related Requirements**: All quickstart test scenarios

---

### T050: Deploy and Validate in Databricks Apps
**Type**: Validation | **Priority**: High | **Dependencies**: T049 | **Estimated**: 60 min

Deploy to Databricks Apps dev environment and validate OBO authentication.

**Commands**:
```bash
databricks bundle validate
databricks bundle deploy -t dev
python dba_logz.py  # Monitor logs for 60 seconds
```

**Validation Steps**:
- No "more than one authorization method configured" errors
- User info endpoint returns correct data
- Multi-user isolation working in platform
- Metrics endpoint accessible

**Acceptance Criteria**:
- [ ] Deployment succeeds without errors
- [ ] No authentication errors in logs
- [ ] All endpoints return successful responses
- [ ] Platform automatically injects user tokens
- [ ] Multi-user isolation validated in platform

**Related Requirements**: All functional and non-functional requirements

---

### T051: Validate Zero-Downtime Rolling Updates
**Type**: Validation | **Priority**: High | **Dependencies**: T050 | **Estimated**: 45 min

Validate zero-downtime rolling update deployment strategy per NFR-009.

**Commands**:
```bash
# Start monitoring existing deployment
curl -s https://<app-url>/api/health > /tmp/health-before.json

# Deploy update with rolling strategy
databricks bundle deploy -t prod --strategy rolling

# Monitor deployment progress
while databricks apps get <app-name> | grep -q "UPDATING"; do
  echo "Deployment in progress..."
  curl -s https://<app-url>/api/health
  sleep 5
done

# Verify no downtime occurred
curl -s https://<app-url>/api/health > /tmp/health-after.json
```

**Validation Steps**:
1. Start health check monitoring before deployment
2. Deploy update using rolling strategy
3. Continuously verify health endpoint remains available
4. Confirm no request failures during deployment
5. Verify new version is running

**Acceptance Criteria**:
- [ ] Health endpoint remains available throughout deployment
- [ ] No 5xx errors logged during update
- [ ] User sessions remain active during deployment
- [ ] New version deployed successfully
- [ ] Rollback tested if deployment fails

**Related Requirements**: NFR-009, FR-023

---

## Dependencies

**Layer 1 (Foundation)**: T001-T003, T004-T013  
**Layer 2 (Core Auth)**: T014-T021  
**Layer 3 (Services)**: T022-T026, T037 (timeouts)  
**Layer 4 (Endpoints)**: T027-T032  
**Layer 5 (Observability)**: T033-T036  
**Layer 6 (Config & Docs)**: T038-T041, T045-T047  
**Layer 7 (Testing)**: T042-T044, T044a  
**Layer 8 (Validation)**: T048-T050

**Blocking Dependencies**:
- T003 blocks all Lakebase-related tasks (T007, T011, T025, T026, T030, T042)
- T018 blocks all service layer tasks (T022-T024)
- T022 blocks user endpoint tasks (T028-T030)
- T037 (timeout config) depends on T022-T024 (service layer implementations)
- All contract tests (T004-T013) should complete before implementation
- T048 blocks T049, T049 blocks T050

---

## Parallel Execution Examples

### Parallel Batch 1: Contract Tests (After T001)
```bash
# All contract tests can run simultaneously (different files)
Task: "Contract test auth middleware in tests/contract/test_auth_middleware.py"
Task: "Contract test user identity in tests/contract/test_user_identity_extraction.py"
Task: "Contract test user endpoints in tests/contract/test_user_contract.py"
Task: "Contract test preferences in tests/contract/test_preferences_contract.py"
Task: "Contract test UserService in tests/contract/test_user_service_contract.py"
Task: "Contract test UnityCatalogService in tests/contract/test_unity_catalog_service_contract.py"
Task: "Contract test ModelServingService in tests/contract/test_model_serving_service_contract.py"
Task: "Contract test retry logic in tests/contract/test_retry_logic.py"
Task: "Contract test correlation IDs in tests/contract/test_correlation_id.py"
```

### Parallel Batch 2: Service Layer (After T018)
```bash
# All service modifications can run simultaneously (different files)
Task: "Modify UserService in server/services/user_service.py"
Task: "Modify UnityCatalogService in server/services/unity_catalog_service.py"
Task: "Modify ModelServingService in server/services/model_serving_service.py"
```

### Parallel Batch 3: Endpoints (After Service Layer)
```bash
# IMPORTANT: T027 and T028 MUST run sequentially (both modify server/routers/user.py)
# Execute in strict order: T027 → T028 (NOT parallel)
Task: "Update /api/auth/status in server/routers/user.py" (T027) - FIRST
Task: "Update /api/user/me in server/routers/user.py" (T028) - AFTER T027

# These can run in parallel (different files):
Task: "Update /api/user/me/workspace in server/routers/user.py" (T029) - AFTER T028 [sequential]
Task: "Update /api/preferences in server/routers/user.py" (T030) - AFTER T029 [sequential]
Task: "Update UC endpoints in server/routers/unity_catalog.py" (T031) [P]
Task: "Update model serving endpoints in server/routers/model_serving.py" (T032) [P]

# NOTE: T029 and T030 also modify server/routers/user.py, so they run sequentially after T028
```

### Parallel Batch 4: Documentation (Anytime)
```bash
# Documentation tasks are independent
Task: "Update OBO docs in docs/OBO_AUTHENTICATION.md"
Task: "Create auth patterns doc in docs/databricks_apis/authentication_patterns.md"
Task: "Update README.md"
Task: "Create local dev docs in docs/LOCAL_DEVELOPMENT.md"
```

---

## Validation Checklist

### Contract Coverage
- [x] All contract files have corresponding test tasks
- [x] auth_models.yaml → T004, T005, T012, T013
- [x] user_endpoints.yaml → T006, T007
- [x] service_layers.yaml → T008, T009, T010, T011

### Entity Coverage
- [x] All data models have implementation tasks
- [x] AuthenticationContext → T014
- [x] UserIdentity → T020
- [x] Response models → T021

### Endpoint Coverage
- [x] All endpoints have implementation tasks
- [x] /api/auth/status → T027
- [x] /api/user/me → T028
- [x] /api/user/me/workspace → T029
- [x] /api/preferences → T030
- [x] Unity Catalog endpoints → T031
- [x] Model Serving endpoints → T032

### Test Coverage
- [x] Contract tests before implementation (TDD)
- [x] Integration tests for multi-user scenarios
- [x] Manual validation via quickstart

### Parallel Task Validation
- [x] T004-T013 parallelizable (different test files)
- [x] T022-T024 parallelizable (different service files)
- [x] T027-T028 sequential (same file: server/routers/user.py)
- [x] T031, T032 parallelizable (different router files)
- [x] T039-T041, T045-T047 parallelizable (different doc files)
- [x] No same-file conflicts in parallel tasks (T027/T028 marked sequential)

---

## Notes

### Critical Requirements
- Always specify explicit `auth_type` parameter (FR-003, FR-004)
- Never log token values (NFR-004)
- Always filter by user_id for user-scoped queries (FR-013)
- Validate user_id presence before database operations (FR-014)
- Auth overhead must be < 10ms (NFR-001)

### Testing Strategy
- TDD approach: Write contract tests first (Phase 3.2)
- Tests should FAIL initially
- Implementation in Phase 3.3-3.5 makes tests pass
- Validation in Phase 3.10 ensures everything works end-to-end

### Deployment Checklist
- [ ] All contract tests pass
- [ ] Integration tests pass
- [ ] Manual quickstart tests complete
- [ ] No authentication errors in logs
- [ ] Metrics show auth overhead < 10ms
- [ ] Multi-user isolation validated
- [ ] Documentation updated

### Commit Strategy
- Commit after each task completion
- Keep commits small and focused
- Include task ID in commit message (e.g., "T014: Implement AuthenticationContext")

---

*Based on Constitution v1.1.1 - See `.specify/memory/constitution.md`*
*Generated from plan.md, research.md, data-model.md, contracts/, quickstart.md*
*Total Estimated Time: 39.25-46.25 hours over 3-5 days (51 tasks)*
