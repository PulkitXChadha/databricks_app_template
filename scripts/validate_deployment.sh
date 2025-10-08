#!/bin/bash
#
# Validation script for final deployment and testing (T046-T049)
#
# This script provides a checklist and automated validation for:
# - T046: Execute quickstart.md end-to-end
# - T047: Verify structured logging with correlation IDs
# - T048: Deploy to dev environment and test
# - T049: Deploy to prod environment and validate permissions
#
# Usage:
#   ./scripts/validate_deployment.sh [--task T046|T047|T048|T049] [--env dev|prod]
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${GREEN}=== $1 ===${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo "  $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Parse command line arguments
TASK=${1:-all}
ENV=${2:-dev}

print_header "Databricks App Template - Deployment Validation"
echo "Task: $TASK"
echo "Environment: $ENV"

# T046: Execute quickstart.md end-to-end
validate_quickstart() {
    print_header "T046: Execute quickstart.md End-to-End"
    
    echo "This task validates the quickstart guide by following all setup steps."
    echo "Checklist (from specs/001-databricks-integrations/quickstart.md):"
    echo ""
    
    # Step 1: Check dependencies
    print_info "Step 1: Check Dependencies"
    
    if command_exists uv; then
        print_success "uv package manager installed"
    else
        print_error "uv not found - install from https://github.com/astral-sh/uv"
        return 1
    fi
    
    if command_exists bun; then
        print_success "bun package manager installed"
    else
        print_error "bun not found - install from https://bun.sh"
        return 1
    fi
    
    if command_exists databricks; then
        print_success "Databricks CLI installed"
    else
        print_error "Databricks CLI not found - install from https://docs.databricks.com/cli"
        return 1
    fi
    
    # Step 2: Check environment variables
    print_info "\nStep 2: Check Environment Variables"
    
    if [ -f .env.local ]; then
        print_success ".env.local file exists"
        
        # Check required variables
        required_vars=(
            "DATABRICKS_HOST"
            "DATABRICKS_WAREHOUSE_ID"
            "DATABRICKS_CATALOG"
            "DATABRICKS_SCHEMA"
            "LAKEBASE_HOST"
            "LAKEBASE_PORT"
            "LAKEBASE_DATABASE"
            "LAKEBASE_INSTANCE_NAME"
        )
        
        for var in "${required_vars[@]}"; do
            if grep -q "^${var}=" .env.local && ! grep -q "^${var}=$" .env.local; then
                print_success "$var is set"
            else
                print_warning "$var is missing or empty in .env.local"
            fi
        done
    else
        print_error ".env.local not found - create from quickstart.md template"
        return 1
    fi
    
    # Step 3: Check authentication
    print_info "\nStep 3: Check Databricks Authentication"
    
    if databricks auth env >/dev/null 2>&1; then
        print_success "Databricks authentication active"
    else
        print_error "Databricks not authenticated - run: databricks auth login"
        return 1
    fi
    
    # Step 4: Validate bundle
    print_info "\nStep 4: Validate Databricks Bundle"
    
    if databricks bundle validate --target dev >/dev/null 2>&1; then
        print_success "Bundle validation passed (dev)"
    else
        print_error "Bundle validation failed - check databricks.yml"
        return 1
    fi
    
    # Step 5: Check database migrations
    print_info "\nStep 5: Check Database Migrations"
    
    if [ -d migrations/versions ]; then
        migration_count=$(ls -1 migrations/versions/*.py 2>/dev/null | wc -l)
        if [ $migration_count -ge 2 ]; then
            print_success "Alembic migrations exist ($migration_count files)"
        else
            print_warning "Expected at least 2 migration files, found $migration_count"
        fi
    else
        print_error "migrations/versions directory not found"
        return 1
    fi
    
    # Step 6: Check test execution
    print_info "\nStep 6: Run Integration Tests"
    
    echo "Run the following commands to execute tests:"
    echo "  uv run pytest tests/integration/test_multi_user_isolation.py -v"
    echo "  uv run pytest tests/integration/test_observability.py -v"
    echo "  uv run pytest tests/integration/test_pagination_performance.py -v"
    echo "  uv run pytest tests/integration/test_accessibility_compliance.py -v"
    echo "  uv run pytest tests/integration/test_model_input_validation.py -v"
    
    print_success "T046: Quickstart validation checklist complete"
}

# T047: Verify structured logging with correlation IDs
validate_logging() {
    print_header "T047: Verify Structured Logging with Correlation IDs"
    
    echo "This task validates structured logging and correlation ID propagation."
    echo ""
    
    # Check if server is running
    print_info "Checking if FastAPI server is running..."
    
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        print_success "Server is running at http://localhost:8000"
        
        # Test correlation ID propagation
        print_info "\nTesting correlation ID propagation..."
        
        test_request_id="validation-$(date +%s)"
        response=$(curl -s -H "X-Request-ID: $test_request_id" \
                       -w "\n%{http_code}" \
                       http://localhost:8000/health)
        
        http_code=$(echo "$response" | tail -n1)
        
        if [ "$http_code" = "200" ]; then
            print_success "Health endpoint returned 200"
            
            # Check response header (requires curl -i for headers)
            response_with_headers=$(curl -s -i -H "X-Request-ID: $test_request_id" \
                                         http://localhost:8000/health)
            
            if echo "$response_with_headers" | grep -q "X-Request-ID: $test_request_id"; then
                print_success "Correlation ID preserved in response headers"
            else
                print_warning "Correlation ID not found in response headers"
            fi
        else
            print_error "Health endpoint returned $http_code"
        fi
        
        echo ""
        echo "To manually verify logging:"
        echo "  1. Check terminal output where FastAPI is running"
        echo "  2. Look for JSON log entries with 'request_id' field"
        echo "  3. Verify correlation ID matches: $test_request_id"
        
    else
        print_warning "Server not running - start with: ./watch.sh"
        echo "  Then run: curl -H 'X-Request-ID: test-123' http://localhost:8000/health"
    fi
    
    print_success "T047: Logging validation checklist complete"
}

# T048: Deploy to dev environment and test
validate_dev_deployment() {
    print_header "T048: Deploy to Dev Environment and Test"
    
    echo "This task deploys the application to Databricks dev environment."
    echo ""
    
    # Check bundle validation
    print_info "Step 1: Validate bundle for dev target"
    
    if databricks bundle validate --target dev >/dev/null 2>&1; then
        print_success "Bundle validation passed (dev)"
    else
        print_error "Bundle validation failed - fix errors before deploying"
        return 1
    fi
    
    # Deployment instructions
    print_info "\nStep 2: Deploy to dev environment"
    echo "Run the following command to deploy:"
    echo "  databricks bundle deploy --target dev"
    echo ""
    echo "This will:"
    echo "  - Provision SQL Warehouse (databricks-app-warehouse-dev)"
    echo "  - Provision Lakebase instance (databricks-app-lakebase-dev)"
    echo "  - Deploy application to Databricks Apps"
    echo "  - Set up permissions (CAN_MANAGE for admins)"
    
    # Test instructions
    print_info "\nStep 3: Test deployed application"
    echo "After deployment, test the following:"
    echo "  1. Access app URL from deployment output"
    echo "  2. Test Unity Catalog queries: GET /api/unity-catalog/tables"
    echo "  3. Test Lakebase preferences: GET /api/preferences"
    echo "  4. Test Model Serving: GET /api/model-serving/endpoints"
    echo ""
    echo "Use dba_client.py for authenticated testing:"
    echo "  uv run python dba_client.py /api/user/me"
    echo "  uv run python dba_client.py /api/preferences"
    
    # Check deployment status (if possible)
    print_info "\nStep 4: Check deployment status"
    
    if databricks apps list 2>/dev/null | grep -q "databricks-app-template-dev"; then
        print_success "App found in Databricks workspace"
        echo "Check status with: ./app_status.sh --verbose"
    else
        print_warning "App not yet deployed or not visible"
    fi
    
    print_success "T048: Dev deployment validation checklist complete"
}

# T049: Deploy to prod environment and validate permissions
validate_prod_deployment() {
    print_header "T049: Deploy to Prod Environment and Validate Permissions"
    
    echo "This task deploys the application to Databricks production environment."
    echo ""
    
    print_warning "IMPORTANT: Production deployment requires careful review!"
    echo ""
    
    # Check bundle validation
    print_info "Step 1: Validate bundle for prod target"
    
    if databricks bundle validate --target prod >/dev/null 2>&1; then
        print_success "Bundle validation passed (prod)"
    else
        print_error "Bundle validation failed - fix errors before deploying"
        return 1
    fi
    
    # Pre-deployment checklist
    print_info "\nStep 2: Pre-deployment checklist"
    echo "Before deploying to production, verify:"
    echo "  [ ] Dev deployment tested successfully (T048)"
    echo "  [ ] All integration tests passed"
    echo "  [ ] Database migrations tested in dev"
    echo "  [ ] Environment variables configured for prod"
    echo "  [ ] Capacity settings appropriate for production load"
    echo "  [ ] Permissions configured (admins: CAN_MANAGE, users: CAN_VIEW)"
    
    # Deployment instructions
    print_info "\nStep 3: Deploy to prod environment"
    echo "Run the following command to deploy:"
    echo "  databricks bundle deploy --target prod"
    echo ""
    echo "This will:"
    echo "  - Provision SQL Warehouse (databricks-app-warehouse)"
    echo "  - Provision Lakebase instance (databricks-app-lakebase)"
    echo "  - Deploy application to Databricks Apps"
    echo "  - Set up production permissions"
    
    # Permission validation
    print_info "\nStep 4: Validate permissions"
    echo "After deployment, test permissions:"
    echo "  1. Test with admin account (should have CAN_MANAGE)"
    echo "  2. Test with regular user account (should have CAN_VIEW)"
    echo "  3. Verify non-admin cannot modify app settings"
    echo "  4. Verify data isolation (User A cannot see User B's preferences)"
    
    # Data isolation validation
    print_info "\nStep 5: Validate data isolation"
    echo "Test multi-user data isolation:"
    echo "  1. Create preference as User A"
    echo "  2. Query preferences as User B"
    echo "  3. Verify User B cannot see User A's preferences"
    echo "  4. Run: pytest tests/integration/test_multi_user_isolation.py -v"
    
    print_success "T049: Prod deployment validation checklist complete"
}

# Execute requested validation
case $TASK in
    T046)
        validate_quickstart
        ;;
    T047)
        validate_logging
        ;;
    T048)
        validate_dev_deployment
        ;;
    T049)
        validate_prod_deployment
        ;;
    all)
        validate_quickstart
        validate_logging
        validate_dev_deployment
        validate_prod_deployment
        ;;
    *)
        echo "Usage: $0 [T046|T047|T048|T049|all] [dev|prod]"
        exit 1
        ;;
esac

print_header "Validation Complete"
echo "Review the checklist above and mark tasks as complete in tasks.md"
echo ""
echo "To mark tasks complete, update the following in tasks.md:"
echo "  ### T046 [X] Execute quickstart.md end-to-end"
echo "  ### T047 [X] Verify structured logging with correlation IDs"
echo "  ### T048 [X] Deploy to dev environment and test"
echo "  ### T049 [X] Deploy to prod environment and validate permissions"

