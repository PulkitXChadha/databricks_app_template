# Integration Testing Quickstart Guide

**Feature**: 005-write-integration-test  
**Date**: October 18, 2025  
**Audience**: Developers, QA Engineers, CI/CD Maintainers

## Overview

This guide provides practical instructions for running integration tests, generating coverage reports, and interpreting results. Integration tests validate end-to-end API workflows across Lakebase, Unity Catalog, and Model Serving services.

---

## Prerequisites

### 1. Install Dependencies

```bash
# Ensure you're in the project root
cd /Users/pulkit.chadha/Documents/Projects/databricks-app-template

# Install dev dependencies (includes pytest, pytest-asyncio, pytest-cov)
uv sync --dev

# Verify pytest and pytest-cov are installed
pytest --version
pytest --cov --help
```

### 2. Configure Test Environment

```bash
# Copy environment template (if not already done)
cp .env.example .env.local

# Set required environment variables for Lakebase (test database)
export PGHOST="your-lakebase-host.cloud.databricks.com"
export LAKEBASE_DATABASE="test_database"
export PGUSER="your-service-principal"
export PGPASSWORD="your-database-token"
export PGPORT="443"
export PGSSLMODE="require"

# Set Databricks workspace URL
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
```

### 3. Optional: Configure Multi-User Testing

For tests that require multiple user accounts (multi-user isolation tests):

```bash
# Configure Databricks CLI profiles for User A and User B
databricks auth login --profile user-a --host https://your-workspace.cloud.databricks.com
databricks auth login --profile user-b --host https://your-workspace.cloud.databricks.com

# Verify profiles are configured
databricks auth profiles
```

---

## Running Integration Tests

### Quick Start: Run All Integration Tests

```bash
# Run all integration tests with coverage
pytest tests/integration/ --cov=server/routers --cov=server/services --cov-report=term --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

### Run Specific Test Files

```bash
# Test Lakebase endpoints only
pytest tests/integration/test_lakebase_full_flow.py -v

# Test Unity Catalog endpoints only
pytest tests/integration/test_unity_catalog_full_flow.py -v

# Test Model Serving endpoints only
pytest tests/integration/test_model_serving_full_flow.py -v

# Test cross-service workflows
pytest tests/integration/test_cross_service_workflows.py -v
```

### Run Specific Test Classes or Functions

```bash
# Run specific test class
pytest tests/integration/test_lakebase_full_flow.py::TestLakebasePreferencesCRUD -v

# Run specific test function
pytest tests/integration/test_lakebase_full_flow.py::TestLakebasePreferencesCRUD::test_create_preference -v

# Run tests matching a keyword
pytest tests/integration/ -k "preference" -v
pytest tests/integration/ -k "isolation" -v
```

### Run Tests by Marker

```bash
# Run only integration tests (skip contract and unit tests)
pytest -m integration -v

# Run only slow tests
pytest -m slow -v

# Run all tests except slow ones
pytest -m "not slow" -v
```

---

## Coverage Reporting

### Generate Coverage Reports

```bash
# Terminal report (quick overview)
pytest tests/integration/ --cov=server/routers --cov=server/services --cov-report=term

# HTML report (detailed, interactive)
pytest tests/integration/ --cov=server/routers --cov=server/services --cov-report=html
open htmlcov/index.html

# XML report (for CI/CD)
pytest tests/integration/ --cov=server/routers --cov=server/services --cov-report=xml

# All reports at once
pytest tests/integration/ --cov=server/routers --cov=server/services --cov-report=term --cov-report=html --cov-report=xml
```

### Interpret Coverage Reports

#### Terminal Report Example

```
---------- coverage: platform darwin, python 3.11.5 -----------
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
server/routers/lakebase.py                 45      3    93%
server/routers/model_serving.py            78      5    94%
server/routers/unity_catalog.py            65      4    94%
server/routers/user.py                     23      1    96%
server/services/lakebase_service.py        52      4    92%
server/services/model_serving_service.py   89      7    92%
server/services/schema_detection_service.py 67      5    93%
server/services/unity_catalog_service.py   74      6    92%
server/services/user_service.py            34      2    94%
-----------------------------------------------------------
TOTAL                                     527     37    93%
```

**Interpretation:**
- **Stmts**: Total statements (lines of code)
- **Miss**: Statements not executed by tests
- **Cover**: Coverage percentage (Stmts - Miss) / Stmts * 100
- **Target**: 90% minimum (SC-001 requirement)

#### HTML Report Navigation

1. Open `htmlcov/index.html` in browser
2. Click on any module name (e.g., `server/routers/lakebase.py`)
3. **Green lines**: Executed by tests (covered)
4. **Red lines**: Not executed by tests (missing coverage)
5. **Yellow lines**: Partially covered (branch not taken)
6. Identify red/yellow lines → write tests to cover them

---

## Fail on Low Coverage

```bash
# Fail if coverage is below 90% (CI/CD gate)
pytest tests/integration/ --cov=server/routers --cov=server/services --cov-fail-under=90

# Output if coverage < 90%:
# FAILED: Coverage is below 90% (current: 87%)
```

---

## Test Modes: Mock vs. Live

### Mock Mode (Default)

All external Databricks APIs are mocked. **Use this for:**
- Local development without Databricks workspace
- CI/CD pipelines (fast, no credentials required)
- Unit-like integration tests (test logic, not external APIs)

```bash
# Default mode (no environment variable needed)
pytest tests/integration/ -v
```

### Live Mode (Optional)

Tests call real Databricks workspace APIs. **Use this for:**
- End-to-end validation before production deployment
- Smoke testing after deployment
- Verifying permission enforcement with real user accounts

```bash
# Enable live mode
export TEST_MODE=live

# Run integration tests against real workspace
pytest tests/integration/ -v

# Disable live mode (back to mock)
unset TEST_MODE
```

**Requirements for Live Mode:**
- Valid Databricks CLI profiles configured
- Network access to Databricks workspace
- Test user accounts with appropriate permissions
- Longer test execution time (1-3 minutes vs. 10-30 seconds)

---

## Parallel Execution (Optional)

Speed up test suite by running tests in parallel:

```bash
# Enable parallel execution (requires pytest-xdist)
pytest tests/integration/ -n auto --cov=server/routers --cov=server/services --cov-report=html

# -n auto: Use all available CPU cores
# -n 4: Use exactly 4 workers
```

**Note:** Parallel execution may cause database contention. Ensure tests are properly isolated.

---

## Debugging Failed Tests

### Verbose Output

```bash
# Show detailed test execution (-v)
pytest tests/integration/test_lakebase_full_flow.py -v

# Show extra verbose output (-vv)
pytest tests/integration/test_lakebase_full_flow.py -vv

# Show print statements (-s)
pytest tests/integration/test_lakebase_full_flow.py -v -s
```

### Stop on First Failure

```bash
# Stop after first failure (-x)
pytest tests/integration/ -x

# Stop after 3 failures (--maxfail=3)
pytest tests/integration/ --maxfail=3
```

### Run Last Failed Tests

```bash
# Re-run only tests that failed last time
pytest --lf

# Re-run failed tests first, then remaining tests
pytest --ff
```

### Show Full Traceback

```bash
# Show full traceback on failures
pytest tests/integration/ --tb=long

# Show short traceback (default)
pytest tests/integration/ --tb=short

# Show no traceback (only summary)
pytest tests/integration/ --tb=no
```

### Debug with PDB

```bash
# Drop into debugger on failure
pytest tests/integration/ --pdb

# Drop into debugger at start of each test
pytest tests/integration/ --trace
```

---

## CI/CD Integration

### GitHub Actions Workflow Example

```yaml
name: Integration Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      
      - name: Install dependencies
        run: |
          uv sync --dev
      
      - name: Run integration tests with coverage
        env:
          PGHOST: ${{ secrets.LAKEBASE_HOST }}
          LAKEBASE_DATABASE: ${{ secrets.LAKEBASE_DATABASE }}
          PGUSER: ${{ secrets.LAKEBASE_USER }}
          PGPASSWORD: ${{ secrets.LAKEBASE_PASSWORD }}
          PGPORT: "443"
          PGSSLMODE: "require"
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
        run: |
          pytest tests/integration/ \
            --cov=server/routers \
            --cov=server/services \
            --cov-report=xml \
            --cov-report=term \
            --cov-fail-under=90 \
            --maxfail=5
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          flags: integration
          name: integration-tests
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'server'"

**Solution:** Ensure project root is in PYTHONPATH

```bash
# Run pytest from project root
cd /Users/pulkit.chadha/Documents/Projects/databricks-app-template
pytest tests/integration/ -v

# Or add project root to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/Users/pulkit.chadha/Documents/Projects/databricks-app-template"
```

### Issue: "Database connection failed"

**Solution:** Verify Lakebase environment variables

```bash
# Check environment variables are set
echo $PGHOST
echo $LAKEBASE_DATABASE

# Test database connection manually
psql "host=$PGHOST dbname=$LAKEBASE_DATABASE user=$PGUSER password=$PGPASSWORD port=$PGPORT sslmode=$PGSSLMODE"
```

### Issue: "Databricks CLI not found" (for live mode)

**Solution:** Install Databricks CLI

```bash
# Install Databricks CLI
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh

# Verify installation
databricks --version

# Authenticate
databricks auth login --host https://your-workspace.cloud.databricks.com
```

### Issue: "Tests are slow (> 5 minutes)"

**Diagnosis:**

```bash
# Identify slow tests with --durations flag
pytest tests/integration/ --durations=10
```

**Solutions:**
1. Enable parallel execution: `pytest -n auto`
2. Use session-scoped fixtures (already implemented)
3. Mock expensive operations (Unity Catalog queries, model inference)
4. Review database cleanup efficiency (ensure indexed user_id filtering)

### Issue: "Coverage report missing files"

**Solution:** Ensure coverage paths match source structure

```bash
# Verify source paths
ls -la server/routers/
ls -la server/services/

# Run coverage with correct paths
pytest tests/integration/ --cov=server/routers --cov=server/services --cov-report=html
```

---

## Best Practices

### 1. Run Tests Before Committing

```bash
# Quick pre-commit check
pytest tests/integration/ --maxfail=3 -x
```

### 2. Generate Coverage Reports Regularly

```bash
# Weekly coverage review
pytest tests/integration/ --cov=server/routers --cov=server/services --cov-report=html
open htmlcov/index.html
# Review red/yellow lines, add tests for uncovered paths
```

### 3. Keep Tests Fast

- Use mock mode by default (save live mode for final validation)
- Session-scope expensive fixtures (tokens, metadata)
- Function-scope isolated data (preferences, logs)
- Avoid unnecessary database queries

### 4. Maintain Test Independence

- Each test should pass when run alone
- No shared mutable state between tests
- Cleanup test data in `autouse` fixtures
- Use unique user IDs for test data

### 5. Write Clear Test Names

```python
# Good: Descriptive, explains what is being tested
def test_user_a_cannot_see_user_b_preferences():
    pass

# Bad: Vague, unclear purpose
def test_preferences():
    pass
```

---

## Quick Reference Commands

```bash
# Most common commands

# 1. Run all integration tests with coverage
pytest tests/integration/ --cov=server/routers --cov=server/services --cov-report=html

# 2. Run specific test file
pytest tests/integration/test_lakebase_full_flow.py -v

# 3. Run with coverage threshold (CI/CD)
pytest tests/integration/ --cov=server/routers --cov=server/services --cov-fail-under=90

# 4. Debug failed test
pytest tests/integration/test_lakebase_full_flow.py::test_create_preference -vv -s --pdb

# 5. Run last failed tests
pytest --lf -v

# 6. Show slowest tests
pytest tests/integration/ --durations=10

# 7. Run in parallel
pytest tests/integration/ -n auto

# 8. Live mode (real Databricks APIs)
TEST_MODE=live pytest tests/integration/ -v
```

---

## Next Steps

1. **Review existing tests**: Read `tests/integration/test_multi_user_isolation.py` for patterns
2. **Check coverage**: Run tests with `--cov-report=html`, identify gaps
3. **Add missing tests**: Use user stories in `spec.md` as test scenarios
4. **Run in CI/CD**: Integrate coverage reporting into deployment pipeline
5. **Monitor coverage**: Track coverage trends over time, maintain 90%+ target

---

## Additional Resources

- **Feature Specification**: [spec.md](./spec.md) - User stories and acceptance criteria
- **Implementation Plan**: [plan.md](./plan.md) - Technical approach and architecture
- **Research Findings**: [research.md](./research.md) - Testing patterns and best practices
- **Coverage Contracts**: [contracts/coverage-targets.yaml](./contracts/coverage-targets.yaml) - Coverage requirements
- **pytest Documentation**: https://docs.pytest.org/
- **pytest-cov Documentation**: https://pytest-cov.readthedocs.io/
- **Constitution (Principle XII - TDD)**: `.specify/memory/constitution.md`

---

## Support

For questions or issues:
1. Check this quickstart guide
2. Review research findings in `research.md`
3. Consult existing integration tests in `tests/integration/`
4. Refer to Constitution Principle XII (TDD requirements)
5. Ask team lead or submit GitHub issue

**Happy Testing! 🎯**

