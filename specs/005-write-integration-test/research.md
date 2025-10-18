# Research: Integration Testing Patterns for Databricks Apps

**Feature**: 005-write-integration-test  
**Date**: October 18, 2025  
**Research Phase**: Phase 0 - Resolving Technical Unknowns

## Overview

This document resolves all NEEDS CLARIFICATION items from the Technical Context in plan.md. Research findings are organized by decision area with rationale and alternatives considered.

---

## 1. Mock Strategy

### Decision: Hybrid Mocking with Mock-by-Default, Live-Optional Pattern

**Chosen Approach:**
- **Default Mode (CI/CD)**: Mock all external Databricks APIs using `unittest.mock.patch`
- **Optional Live Mode**: Environment variable `TEST_MODE=live` enables real Databricks workspace calls
- **Mocking Targets**:
  - `WorkspaceClient` and subclients (`current_user`, `serving_endpoints`, `tables`)
  - Databricks SDK authentication flows
  - Unity Catalog API responses
  - Model Serving endpoint responses
  - Lakebase database connections (use in-memory SQLite for fast tests)

**Rationale:**
- CI/CD pipelines must run without external dependencies (fast, deterministic, no credentials)
- Developers need ability to test against real workspace for end-to-end validation
- Existing tests already use this pattern (`tests/contract/test_user_contract.py` patches WorkspaceClient)
- Mock-by-default ensures tests are fast (5-minute suite requirement)

**Implementation Pattern:**
```python
# Existing pattern from tests/contract/test_user_contract.py
with patch('server.routers.user.UserService') as MockService:
    mock_service = Mock()
    mock_service.get_user_info = AsyncMock(return_value=user_identity)
    MockService.return_value = mock_service
    # Test with mocked service
```

**Alternatives Considered:**
1. **All Live Tests**: Rejected - requires credentials in CI/CD, slow, flaky
2. **All Mocked Tests**: Rejected - misses real integration issues, no end-to-end validation
3. **Separate Mock and Live Test Suites**: Rejected - increases maintenance burden, duplication

---

## 2. Fixture Organization

### Decision: Three-Tier Fixture Architecture (Shared, Scoped, Isolated)

**Chosen Approach:**

**Tier 1: Shared Fixtures (tests/conftest.py - Session Scope)**
- `app`: FastAPI application instance
- `client`: TestClient for HTTP requests
- `get_test_user_token_fixture`: Real user tokens from Databricks CLI (when available)
- `mock_env`: Environment variables for Lakebase
- `reset_circuit_breaker`: Auth circuit breaker reset (autouse)

**Tier 2: Service-Specific Fixtures (tests/integration/conftest.py - Session/Module Scope)**
- `user_a_token_real`: Real token for User A (session-scoped, from CLI)
- `user_b_token_real`: Real token for User B (session-scoped, from CLI)
- Mock Databricks clients configured per service

**Tier 3: Test-Specific Fixtures (Per test file - Function Scope)**
- `mock_user_a`, `mock_user_b`: Mock user objects for isolation tests
- `setup_and_teardown`: Database cleanup (autouse per test class)
- Service-specific data fixtures (preferences, inference logs, etc.)

**Rationale:**
- Session-scoped fixtures amortize expensive operations (CLI token fetch, app initialization)
- Function-scoped fixtures ensure test isolation (database cleanup, per-test data)
- Existing pattern from `tests/integration/conftest.py` already implements this
- Three-tier structure balances performance (reuse) and isolation (cleanup)

**Example from Existing Code:**
```python
# tests/integration/conftest.py - Session scope for expensive operations
@pytest.fixture(scope="session")
def user_a_token_real():
    """Real user token for User A from Databricks CLI."""
    token = get_test_user_token("default")
    return token

# tests/integration/test_multi_user_isolation.py - Function scope with cleanup
@pytest.fixture(autouse=True)
def setup_and_teardown(self):
    """Clean up test data before and after each test."""
    session: Session = next(get_db_session())
    try:
        # Clean up before test
        session.query(UserPreference).filter(...).delete()
        session.commit()
        yield
    finally:
        # Clean up after test
        session.query(UserPreference).filter(...).delete()
        session.commit()
        session.close()
```

**Alternatives Considered:**
1. **Flat Fixture Structure**: Rejected - leads to fixture pollution, unclear dependencies
2. **Per-File Fixtures Only**: Rejected - duplication across test files, slow test suite
3. **All Session-Scoped**: Rejected - breaks test isolation, causes cross-test contamination

---

## 3. Async Testing Patterns

### Decision: pytest-asyncio with Auto Mode for Service Layer Tests

**Chosen Approach:**
- Use `@pytest.mark.asyncio` decorator for async test functions
- pytest-asyncio auto mode enabled in `pyproject.toml` (already configured: `asyncio_mode = "auto"`)
- Service layer tests use `AsyncMock` for async methods
- Router tests use synchronous `TestClient` (FastAPI handles async internally)

**Rationale:**
- FastAPI routers are async but TestClient handles them synchronously
- Service layer methods are truly async and need async test execution
- Auto mode reduces boilerplate (no need to mark every async test)
- Existing contract tests already use this pattern

**Implementation Pattern:**
```python
# Service layer async test (existing pattern from tests/contract/test_user_service_contract.py)
@pytest.mark.asyncio
async def test_get_user_info_extracts_identity_from_api(self):
    """Test get_user_info() extracts UserIdentity from Databricks API."""
    with patch('server.services.user_service.WorkspaceClient') as mock_workspace_client:
        mock_client = MagicMock()
        mock_client.current_user.me = MagicMock(return_value=mock_user_data)
        mock_workspace_client.return_value = mock_client
        
        service = UserService(user_token=user_token)
        user_identity = await service.get_user_info()  # Async call
        
        assert isinstance(user_identity, UserIdentity)
```

```python
# Router test (synchronous - FastAPI handles async)
def test_get_user_me_returns_user_info_with_valid_token(self, client):
    """Test that GET /api/user/me returns UserInfoResponse."""
    with patch('server.routers.user.UserService') as MockService:
        mock_service = Mock()
        mock_service.get_user_info = AsyncMock(return_value=user_identity)
        MockService.return_value = mock_service

        response = client.get("/api/user/me", headers={"X-Forwarded-Access-Token": "valid-token"})
        
        assert response.status_code == 200
```

**Alternatives Considered:**
1. **Synchronous Only**: Rejected - can't test async service methods properly
2. **asyncio.run() Manual**: Rejected - pytest-asyncio is already installed and configured
3. **All Async Tests**: Rejected - router tests don't need async, adds complexity

---

## 4. Database Isolation Strategy

### Decision: Real Database with Per-Test Cleanup via Fixtures

**Chosen Approach:**
- Use configured Lakebase (Postgres) connection for integration tests
- **Per-test cleanup**: `autouse` fixtures delete test data before and after each test
- **User isolation**: Test data filtered by user_id (test-user-a@example.com, test-user-b@example.com)
- **Transactional cleanup**: SQLAlchemy sessions with explicit commit/rollback
- **Optional SQLite**: For fast local testing without Lakebase, use in-memory SQLite

**Rationale:**
- Integration tests should use real database to catch SQL errors, constraint violations
- Per-test cleanup ensures test isolation without transaction rollback (which hides commit issues)
- Existing pattern from `tests/integration/test_multi_user_isolation.py` proves this works
- User-scoped filtering matches production data isolation pattern

**Implementation Pattern:**
```python
# Existing pattern from tests/integration/test_multi_user_isolation.py
@pytest.fixture(autouse=True)
def setup_and_teardown(self):
    """Clean up test data before and after each test."""
    session: Session = next(get_db_session())
    try:
        # Clean up any existing test data
        session.query(UserPreference).filter(
            UserPreference.user_id.in_(["user-a@company.com", "user-b@company.com"])
        ).delete(synchronize_session=False)
        session.commit()
        yield  # Run test
    finally:
        # Clean up after test
        session.query(UserPreference).filter(
            UserPreference.user_id.in_(["user-a@company.com", "user-b@company.com"])
        ).delete(synchronize_session=False)
        session.commit()
        session.close()
```

**Alternatives Considered:**
1. **Transaction Rollback**: Rejected - hides commit issues, doesn't test real persistence
2. **In-Memory SQLite Only**: Rejected - misses Postgres-specific behavior (JSONB, indexes)
3. **Separate Test Database**: Rejected - adds configuration complexity, slower than cleanup
4. **Database Fixtures per Test**: Rejected - too slow, violates 5-minute suite requirement

---

## 5. CI/CD Integration Approach

### Decision: pytest-cov with Coverage Reporting and GitHub Actions Integration

**Chosen Approach:**
- **Add pytest-cov**: New dependency for coverage measurement
- **Coverage Command**: `pytest --cov=server/routers --cov=server/services --cov-report=term --cov-report=html --cov-report=xml`
- **Target Directories**: `server/routers/` and `server/services/` (90% line/branch coverage target)
- **Coverage Reports**:
  - Terminal report (for local development)
  - HTML report (for detailed analysis: `htmlcov/index.html`)
  - XML report (for CI/CD integration with coverage tools)
- **CI/CD Gate**: Test execution with coverage reporting in deployment pipeline
- **Failure Threshold**: Tests fail if coverage drops below 90% in routers/services

**Rationale:**
- pytest-cov is industry standard for Python coverage measurement
- Multiple report formats support both local development and CI/CD
- Scoped coverage (routers/services only) focuses on business logic, not test infrastructure
- HTML reports enable detailed coverage gap analysis
- XML format enables integration with GitHub Actions, Codecov, etc.

**Implementation Commands:**
```bash
# Install pytest-cov (add to pyproject.toml dev dependencies)
uv add --dev pytest-cov

# Run tests with coverage locally
pytest --cov=server/routers --cov=server/services --cov-report=term --cov-report=html

# CI/CD command (fail if coverage < 90%)
pytest --cov=server/routers --cov=server/services --cov-report=xml --cov-fail-under=90
```

**Configuration (add to pyproject.toml):**
```toml
[tool.coverage.run]
source = ["server/routers", "server/services"]
omit = ["*/tests/*", "*/__pycache__/*"]

[tool.coverage.report]
precision = 2
show_missing = true
skip_covered = false

[tool.coverage.html]
directory = "htmlcov"
```

**Alternatives Considered:**
1. **coverage.py Direct**: Rejected - pytest-cov integrates better with pytest workflow
2. **No Coverage Threshold**: Rejected - violates FR-019 (90% coverage requirement)
3. **100% Coverage Target**: Rejected - unrealistic, leads to testing trivial code
4. **Whole Codebase Coverage**: Rejected - tests/migrations/scripts don't need coverage

---

## 6. Test Data Management

### Decision: Hybrid Data Approach (Shared Read-Only + Per-Test Isolated)

**Chosen Approach:**

**Read-Only Reference Data (Session-Scoped Fixtures)**
- Mock catalog metadata (catalog names, schema names, table definitions)
- Mock user identities (user-a@company.com, user-b@company.com)
- Mock endpoint configurations (model serving endpoints, endpoint schemas)
- Loaded once per test session, never modified

**Isolated Per-Test Data (Function-Scoped with Cleanup)**
- User preferences (created/updated/deleted per test)
- Model inference logs (created per test, verified, deleted)
- Schema detection events (created per test)
- Created fresh for each test, cleaned up automatically

**Rationale:**
- Read-only data reuse speeds up test suite (avoid redundant setup)
- Per-test isolated data ensures test independence
- Matches production pattern (catalogs are read-only, preferences are user-scoped writes)
- Existing tests already follow this pattern (session-scoped tokens, function-scoped preferences)

**Implementation Pattern:**
```python
# Session-scoped read-only data
@pytest.fixture(scope="session")
def mock_catalog_metadata():
    """Mock Unity Catalog metadata (read-only, shared across tests)."""
    return {
        "catalogs": ["main", "samples"],
        "schemas": {"main": ["default", "sales"], "samples": ["tpch", "nyctaxi"]},
        "tables": {
            "main.default": ["customers", "orders"],
            "samples.tpch": ["nation", "region"]
        }
    }

# Function-scoped isolated data
@pytest.fixture
def user_a_preferences(setup_and_teardown):
    """Create isolated preferences for User A (cleaned up automatically)."""
    return {
        "user_id": "user-a@company.com",
        "preferences": []  # Empty, test will create
    }
```

**Alternatives Considered:**
1. **All Isolated Data**: Rejected - too slow, redundant setup for read-only catalogs
2. **All Shared Data**: Rejected - test interference, cross-test contamination
3. **Database Seed Scripts**: Rejected - harder to maintain, doesn't match fixture pattern
4. **Factory Pattern (FactoryBoy)**: Rejected - adds dependency, overkill for simple models

---

## 7. Best Practices for pytest Integration Tests

### Research Findings from Existing Codebase

**Pattern 1: Test Organization by Service**
- One test file per service (test_lakebase_full_flow.py, test_unity_catalog_full_flow.py)
- Test classes group related scenarios (TestLakebasePreferences, TestLakebaseMulitUser)
- Matches project structure (routers/lakebase.py → tests/integration/test_lakebase_full_flow.py)

**Pattern 2: Clear Test Naming (Given-When-Then)**
- Existing test: `test_lakebase_preference_isolation`
- Docstrings document acceptance criteria from spec
- Assertion messages explain failures: `"User B should not see User A's preferences"`

**Pattern 3: Mock at Router/Service Boundary**
- Patch at import location: `patch('server.routers.user.UserService')`
- Mock service layer methods, test router responses
- Keep business logic real, mock external I/O only

**Pattern 4: Fixture Reuse Without Duplication**
- Base fixtures in `tests/conftest.py` (app, client, env)
- Integration-specific fixtures in `tests/integration/conftest.py` (real tokens)
- Test-specific fixtures in test files (mock users, cleanup)

**Pattern 5: Explicit Cleanup Over Implicit**
- `autouse=True` fixtures for cleanup (database, circuit breaker)
- Try-finally blocks ensure cleanup even on failure
- Delete by user_id filter, not DROP TABLE (preserves schema)

---

## 8. Technology Dependencies

### Existing Dependencies (Already Installed)
- pytest>=7.4.0 (test runner)
- pytest-asyncio>=0.21.0 (async test support)
- pytest-xdist>=3.5.0 (parallel execution - not used yet)
- pytest-timeout>=2.2.0 (timeout protection - not used yet)
- pytest-mock>=3.12.0 (cleaner mock syntax - not used yet)
- httpx>=0.25.0 (HTTP client, TestClient dependency)

### New Dependencies Required
- **pytest-cov**: Coverage measurement and reporting (MUST ADD)

### Optional Dependencies (Future Enhancements)
- pytest-xdist: Parallel test execution (enable with `-n auto` flag)
- pytest-timeout: Individual test timeouts (currently only 5-minute suite limit)
- pytest-mock: Cleaner mock syntax (currently using unittest.mock directly)

### Installation Command
```bash
# Add pytest-cov to dev dependencies
uv add --dev pytest-cov

# Sync dependencies
uv sync --dev
```

---

## Summary of Decisions

All NEEDS CLARIFICATION items have been resolved:

| Area | Decision | Status |
|------|----------|--------|
| Mock Strategy | Hybrid: Mock-by-default, live-optional with TEST_MODE=live | ✅ Resolved |
| Fixture Organization | Three-tier: Shared session → Service module → Test function | ✅ Resolved |
| Async Testing | pytest-asyncio auto mode, AsyncMock for services | ✅ Resolved |
| Database Isolation | Real DB with per-test cleanup via autouse fixtures | ✅ Resolved |
| CI/CD Integration | pytest-cov with 90% threshold, XML/HTML reports | ✅ Resolved |
| Test Data | Hybrid: Session-scoped read-only + function-scoped isolated | ✅ Resolved |

**Next Phase**: Phase 1 - Design data models, contracts, and quickstart guide.

---

## References

- Existing fixtures: `tests/conftest.py`, `tests/integration/conftest.py`
- Integration test examples: `tests/integration/test_multi_user_isolation.py`
- Contract test examples: `tests/contract/test_user_contract.py`
- pytest configuration: `pyproject.toml` [tool.pytest.ini_options]
- Constitution Principle XII (TDD): `.specify/memory/constitution.md`

