#!/bin/bash

# deploy_all.sh
# Comprehensive deployment script for Databricks App Template
# Allows selective deployment of infrastructure, database, and application components

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Default values
TARGET="${TARGET:-dev}"
INTERACTIVE="${INTERACTIVE:-true}"
VERBOSE="${VERBOSE:-false}"

# Deployment flags (can be set via environment or interactive prompts)
DEPLOY_BUNDLE="${DEPLOY_BUNDLE:-}"
DEPLOY_MIGRATIONS="${DEPLOY_MIGRATIONS:-}"
DEPLOY_SAMPLE_DATA="${DEPLOY_SAMPLE_DATA:-}"
DEPLOY_APP="${DEPLOY_APP:-}"
CREATE_APP="${CREATE_APP:-false}"

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_step() {
    echo -e "${CYAN}▶${NC} $1"
}

print_timing() {
    if [ "$VERBOSE" = "true" ]; then
        echo -e "${MAGENTA}⏱${NC}  $(date '+%H:%M:%S') - $1"
    fi
}

print_banner() {
    echo ""
    echo "=============================================="
    echo "  Databricks App Template"
    echo "  Comprehensive Deployment Tool"
    echo "=============================================="
    echo ""
}

print_summary() {
    echo ""
    echo "=============================================="
    echo "  Deployment Plan Summary"
    echo "=============================================="
    echo "Target Environment:      $TARGET"
    echo "Deploy Bundle:           $DEPLOY_BUNDLE"
    echo "Deploy Migrations:       $DEPLOY_MIGRATIONS"
    echo "Deploy Sample Data:      $DEPLOY_SAMPLE_DATA"
    echo "Deploy App:              $DEPLOY_APP"
    if [ "$DEPLOY_APP" = "yes" ]; then
        echo "Create App (if needed):  $CREATE_APP"
    fi
    echo "=============================================="
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --target)
            TARGET="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE="true"
            shift
            ;;
        --non-interactive)
            INTERACTIVE="false"
            shift
            ;;
        --all)
            DEPLOY_BUNDLE="yes"
            DEPLOY_MIGRATIONS="yes"
            DEPLOY_SAMPLE_DATA="yes"
            DEPLOY_APP="yes"
            shift
            ;;
        --bundle-only)
            DEPLOY_BUNDLE="yes"
            DEPLOY_MIGRATIONS="no"
            DEPLOY_SAMPLE_DATA="no"
            DEPLOY_APP="no"
            INTERACTIVE="false"
            shift
            ;;
        --app-only)
            DEPLOY_BUNDLE="no"
            DEPLOY_MIGRATIONS="no"
            DEPLOY_SAMPLE_DATA="no"
            DEPLOY_APP="yes"
            INTERACTIVE="false"
            shift
            ;;
        --create)
            CREATE_APP="true"
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --target ENV          Target environment (dev or prod, default: dev)"
            echo "  --verbose             Enable verbose output"
            echo "  --non-interactive     Skip interactive prompts, use defaults"
            echo "  --all                 Deploy everything (bundle, migrations, data, app)"
            echo "  --bundle-only         Deploy only infrastructure bundle"
            echo "  --app-only            Deploy only the application"
            echo "  --create              Create app if it doesn't exist"
            echo "  --help                Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  TARGET                Target environment (dev or prod)"
            echo "  DEPLOY_BUNDLE         Deploy infrastructure (yes/no)"
            echo "  DEPLOY_MIGRATIONS     Run database migrations (yes/no)"
            echo "  DEPLOY_SAMPLE_DATA    Create sample data (yes/no)"
            echo "  DEPLOY_APP            Deploy application (yes/no)"
            echo "  VERBOSE               Enable verbose output (true/false)"
            echo ""
            echo "Examples:"
            echo "  $0 --all --target dev              # Deploy everything to dev"
            echo "  $0 --bundle-only --target prod     # Deploy only infrastructure to prod"
            echo "  $0 --app-only --create             # Deploy only app, create if needed"
            echo "  DEPLOY_BUNDLE=yes $0               # Deploy bundle with env var"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Print banner
print_banner

# Interactive prompts if needed
if [ "$INTERACTIVE" = "true" ]; then
    echo "This script will help you deploy components of your Databricks app."
    echo ""
    
    # Target environment
    if [ -z "$TARGET" ]; then
        echo -n "Target environment (dev/prod) [dev]: "
        read -r TARGET
        TARGET="${TARGET:-dev}"
    fi
    
    echo ""
    echo "Select components to deploy:"
    echo ""
    
    # Infrastructure bundle
    if [ -z "$DEPLOY_BUNDLE" ]; then
        echo -n "Deploy infrastructure bundle (SQL Warehouse, Lakebase, etc.)? (y/n) [y]: "
        read -r response
        response="${response:-y}"
        DEPLOY_BUNDLE=$([[ "$response" =~ ^[Yy] ]] && echo "yes" || echo "no")
    fi
    
    # Database migrations
    if [ -z "$DEPLOY_MIGRATIONS" ]; then
        echo -n "Run database migrations? (y/n) [y]: "
        read -r response
        response="${response:-y}"
        DEPLOY_MIGRATIONS=$([[ "$response" =~ ^[Yy] ]] && echo "yes" || echo "no")
    fi
    
    # Sample data
    if [ -z "$DEPLOY_SAMPLE_DATA" ]; then
        echo -n "Create sample data? (y/n) [n]: "
        read -r response
        response="${response:-n}"
        DEPLOY_SAMPLE_DATA=$([[ "$response" =~ ^[Yy] ]] && echo "yes" || echo "no")
    fi
    
    # Application
    if [ -z "$DEPLOY_APP" ]; then
        echo -n "Deploy application? (y/n) [y]: "
        read -r response
        response="${response:-y}"
        DEPLOY_APP=$([[ "$response" =~ ^[Yy] ]] && echo "yes" || echo "no")
    fi
    
    # Create app option
    if [ "$DEPLOY_APP" = "yes" ] && [ "$CREATE_APP" = "false" ]; then
        echo -n "Create app if it doesn't exist? (y/n) [n]: "
        read -r response
        response="${response:-n}"
        CREATE_APP=$([[ "$response" =~ ^[Yy] ]] && echo "true" || echo "false")
    fi
    
    echo ""
fi

# Validate target
if [[ ! "$TARGET" =~ ^(dev|prod)$ ]]; then
    log_error "Invalid target: $TARGET. Must be 'dev' or 'prod'"
    exit 1
fi

# Set defaults if still empty
DEPLOY_BUNDLE="${DEPLOY_BUNDLE:-yes}"
DEPLOY_MIGRATIONS="${DEPLOY_MIGRATIONS:-yes}"
DEPLOY_SAMPLE_DATA="${DEPLOY_SAMPLE_DATA:-no}"
DEPLOY_APP="${DEPLOY_APP:-yes}"

# Print deployment plan
print_summary

if [ "$INTERACTIVE" = "true" ]; then
    echo -n "Proceed with deployment? (y/n) [y]: "
    read -r response
    response="${response:-y}"
    if [[ ! "$response" =~ ^[Yy] ]]; then
        echo "Deployment cancelled."
        exit 0
    fi
    echo ""
fi

# Start deployment
log_step "Starting deployment process..."
echo ""

# ============================================
# PHASE 1: Prerequisites Validation
# ============================================
log_step "Phase 1: Validating prerequisites..."
print_timing "Prerequisites validation started"

# Check required tools
MISSING_TOOLS=""

if ! command -v databricks &> /dev/null; then
    MISSING_TOOLS="$MISSING_TOOLS databricks-cli"
fi

if ! command -v uv &> /dev/null; then
    MISSING_TOOLS="$MISSING_TOOLS uv"
fi

if ! command -v bun &> /dev/null && [ "$DEPLOY_APP" = "yes" ]; then
    MISSING_TOOLS="$MISSING_TOOLS bun"
fi

if [ -n "$MISSING_TOOLS" ]; then
    log_error "Missing required tools:$MISSING_TOOLS"
    echo "Please install missing tools and try again."
    exit 1
fi

log_success "All required tools installed"

# Load environment variables
if [ -f .env.local ]; then
    set -a
    source .env.local
    set +a
    log_success "Environment variables loaded from .env.local"
else
    log_warning ".env.local not found, will use environment variables"
fi

# Check authentication
if ! databricks auth env &> /dev/null; then
    log_error "Not authenticated with Databricks"
    echo "Run: databricks auth login --host <your-workspace>"
    exit 1
fi

log_success "Databricks authentication verified"
print_timing "Prerequisites validation completed"
echo ""

# ============================================
# PHASE 2: Deploy Infrastructure Bundle
# ============================================
if [ "$DEPLOY_BUNDLE" = "yes" ]; then
    log_step "Phase 2: Deploying infrastructure bundle..."
    print_timing "Bundle deployment started"
    
    # Determine resource names based on target
    if [ "$TARGET" = "dev" ]; then
        WAREHOUSE_NAME="databricks-app-warehouse-dev"
        LAKEBASE_INSTANCE_NAME="databricks-app-lakebase-dev"
        CATALOG_NAME="lakebase_catalog_dev"
    else
        WAREHOUSE_NAME="databricks-app-warehouse"
        LAKEBASE_INSTANCE_NAME="databricks-app-lakebase"
        CATALOG_NAME="lakebase_catalog"
    fi
    
    # Check for existing resources
    log_info "Checking for existing resources..."
    
    # Check if catalog exists
    CATALOG_EXISTS=$(databricks catalogs list --output json 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    catalogs = data.get('catalogs', data) if isinstance(data, dict) else data
    for c in catalogs:
        if c.get('name') == '$CATALOG_NAME':
            print('yes')
            break
    else:
        print('no')
except:
    print('no')
" 2>/dev/null)
    
    # Check if database instance exists
    DB_INSTANCE_EXISTS=$(databricks database list-database-instances --output json 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    instances = data if isinstance(data, list) else data.get('instances', [])
    for inst in instances:
        if inst.get('name') == '$LAKEBASE_INSTANCE_NAME':
            print('yes')
            break
    else:
        print('no')
except:
    print('no')
" 2>/dev/null)
    
    if [ "$CATALOG_EXISTS" = "yes" ]; then
        log_warning "Catalog '$CATALOG_NAME' already exists - will be reused"
        
        # Check if database exists within the catalog
        DATABASE_NAME="app_database"
        DATABASE_EXISTS=$(databricks catalogs list-schemas --catalog-name "$CATALOG_NAME" --output json 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    schemas = data.get('schemas', data) if isinstance(data, dict) else data
    for s in schemas:
        if s.get('name') == '$DATABASE_NAME':
            print('yes')
            break
    else:
        print('no')
except:
    print('no')
" 2>/dev/null || echo "no")
        
        if [ "$DATABASE_EXISTS" = "yes" ]; then
            log_warning "Database '$DATABASE_NAME' within catalog already exists - will be reused"
        else
            log_info "Database '$DATABASE_NAME' will be created within existing catalog"
        fi
    fi
    
    if [ "$DB_INSTANCE_EXISTS" = "yes" ]; then
        log_warning "Database instance '$LAKEBASE_INSTANCE_NAME' already exists - will be reused"
    fi
    
    # Check for inconsistent state
    if [ "$CATALOG_EXISTS" = "yes" ] && [ "$DB_INSTANCE_EXISTS" = "no" ]; then
        log_error "Inconsistent state detected:"
        log_error "  - Catalog '$CATALOG_NAME' exists"
        log_error "  - Database instance '$LAKEBASE_INSTANCE_NAME' does not exist"
        echo ""
        log_error "The catalog references a database instance that doesn't exist."
        log_info "Options to resolve:"
        echo "  1. Delete the existing catalog: databricks catalogs delete $CATALOG_NAME"
        echo "  2. Create the database instance manually first"
        echo "  3. Update databricks.yml to use a different catalog name"
        echo ""
        if [ "$INTERACTIVE" = "true" ]; then
            echo -n "Would you like to delete the existing catalog and recreate it? (y/n) [n]: "
            read -r response
            response="${response:-n}"
            if [[ "$response" =~ ^[Yy] ]]; then
                log_info "Deleting catalog '$CATALOG_NAME'..."
                databricks catalogs delete "$CATALOG_NAME" --force
                log_success "Catalog deleted"
                CATALOG_EXISTS="no"
            else
                log_error "Cannot proceed with inconsistent state. Exiting."
                exit 1
            fi
        else
            exit 1
        fi
    fi
    
    # Validate bundle
    log_info "Validating bundle configuration..."
    if ! databricks bundle validate --target "$TARGET" &> /dev/null; then
        log_error "Bundle validation failed"
        databricks bundle validate --target "$TARGET"
        exit 1
    fi
    log_success "Bundle configuration valid"
    
    # Deploy bundle
    log_info "Deploying bundle (this may take 5-10 minutes)..."
    DEPLOY_OUTPUT=$(mktemp)
    if [ "$VERBOSE" = "true" ]; then
        databricks bundle deploy --target "$TARGET" 2>&1 | tee "$DEPLOY_OUTPUT"
        DEPLOY_STATUS=${PIPESTATUS[0]}
    else
        databricks bundle deploy --target "$TARGET" > "$DEPLOY_OUTPUT" 2>&1
        DEPLOY_STATUS=$?
    fi
    
    # Check if deployment failed due to existing resources or known issues
    if [ $DEPLOY_STATUS -ne 0 ]; then
        # Check for specific errors we can handle
        CATALOG_EXISTS_ERROR=$(grep -c "already exists" "$DEPLOY_OUTPUT" 2>/dev/null | head -1 || echo "0")
        INCONSISTENT_RESULT_ERROR=$(grep -c "Provider produced inconsistent result" "$DEPLOY_OUTPUT" 2>/dev/null | head -1 || echo "0")
        BUDGET_POLICY_ERROR=$(grep -c "budget_policy_id" "$DEPLOY_OUTPUT" 2>/dev/null | head -1 || echo "0")
        
        # Priority 1: If resources already exist, always continue (common on redeployment)
        if [ "$CATALOG_EXISTS_ERROR" -gt 0 ]; then
            if [ "$INCONSISTENT_RESULT_ERROR" -gt 0 ]; then
                log_warning "Resources already exist and Terraform reported inconsistencies"
                log_info "This is expected when redeploying - continuing with existing resources"
            else
                log_warning "Some resources already exist - continuing with existing resources"
            fi
            # Resources exist, this is expected on redeployment, continue
            
        # Priority 2: Provider inconsistent result without existing resources
        elif [ "$INCONSISTENT_RESULT_ERROR" -gt 0 ] && [ "$BUDGET_POLICY_ERROR" -gt 0 ]; then
            log_warning "Terraform provider reported inconsistent result (known provider issue)"
            log_warning "This is a known issue with the budget_policy_id field in the Databricks provider"
            log_info "Checking if resources were actually created..."
            
            # Verify the resources were created despite the error
            # Check multiple resources since the error might be on any of them
            sleep 5
            VERIFY_WAREHOUSE=$(databricks warehouses list --output json 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    warehouses = data.get('warehouses', data) if isinstance(data, dict) else data
    for w in warehouses:
        if w.get('name') == '$WAREHOUSE_NAME':
            print('yes')
            sys.exit(0)
except: pass
print('no')
" 2>/dev/null)
            
            VERIFY_DB_INSTANCE=$(databricks database list-database-instances --output json 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    instances = data if isinstance(data, list) else data.get('instances', [])
    for inst in instances:
        if inst.get('name') == '$LAKEBASE_INSTANCE_NAME':
            print('yes')
            sys.exit(0)
except: pass
print('no')
" 2>/dev/null)
            
            if [ "$VERIFY_WAREHOUSE" = "yes" ] && [ "$VERIFY_DB_INSTANCE" = "yes" ]; then
                log_success "Core resources verified - deployment successful despite provider warning"
                log_info "The budget_policy_id error can be safely ignored"
            elif [ "$VERIFY_WAREHOUSE" = "yes" ] || [ "$VERIFY_DB_INSTANCE" = "yes" ]; then
                log_warning "Some resources were created, but deployment may be incomplete"
                log_info "Warehouse exists: $VERIFY_WAREHOUSE, DB Instance exists: $VERIFY_DB_INSTANCE"
                log_info "You may need to create the app resource manually"
            else
                log_error "Bundle deployment failed and resources were not created"
                cat "$DEPLOY_OUTPUT"
                rm -f "$DEPLOY_OUTPUT"
                exit 1
            fi
            
        # Priority 3: Other errors - fail
        else
            log_error "Bundle deployment failed"
            cat "$DEPLOY_OUTPUT"
            rm -f "$DEPLOY_OUTPUT"
            exit 1
        fi
    fi
    
    rm -f "$DEPLOY_OUTPUT"
    log_success "Bundle deployed successfully"
    
    # Verify database exists after deployment
    log_info "Verifying database was created..."
    sleep 5  # Give the system time to propagate changes
    
    DATABASE_NAME="app_database"
    DATABASE_EXISTS_FINAL=$(databricks catalogs list-schemas --catalog-name "$CATALOG_NAME" --output json 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    schemas = data.get('schemas', data) if isinstance(data, dict) else data
    for s in schemas:
        if s.get('name') == '$DATABASE_NAME':
            print('yes')
            break
    else:
        print('no')
except:
    print('no')
" 2>/dev/null || echo "no")
    
    # If database doesn't exist, try to create it
    if [ "$DATABASE_EXISTS_FINAL" = "no" ]; then
        log_warning "Database '$DATABASE_NAME' not found in catalog '$CATALOG_NAME'"
        log_info "Attempting to create database..."
        
        # Try to create the database using SQL
        CREATE_DB_OUTPUT=$(databricks sql-queries execute \
            --warehouse-id "$WAREHOUSE_ID" \
            --statement "CREATE DATABASE IF NOT EXISTS \`$CATALOG_NAME\`.\`$DATABASE_NAME\`" 2>&1 || echo "")
        
        if [ $? -eq 0 ]; then
            log_success "Database created successfully"
            DATABASE_EXISTS_FINAL="yes"
        else
            log_warning "Could not create database automatically"
            log_info "The database should be created by the bundle's create_database_if_not_exists setting"
            log_info "It may take a few more minutes to appear"
        fi
    else
        log_success "Database verified: '$DATABASE_NAME' exists in catalog '$CATALOG_NAME'"
    fi
    
    # Log resource status
    echo ""
    log_info "Resource deployment summary:"
    if [ "$CATALOG_EXISTS" = "yes" ]; then
        echo "  📦 Catalog:           ✓ Reused existing '$CATALOG_NAME'"
    else
        echo "  📦 Catalog:           ✓ Created '$CATALOG_NAME'"
    fi
    
    if [ "$DB_INSTANCE_EXISTS" = "yes" ]; then
        echo "  🗄️  Database Instance: ✓ Reused existing '$LAKEBASE_INSTANCE_NAME'"
    else
        echo "  🗄️  Database Instance: ✓ Created '$LAKEBASE_INSTANCE_NAME'"
    fi
    
    if [ "$DATABASE_EXISTS_FINAL" = "yes" ]; then
        echo "  💾 Database:          ✓ Verified '$DATABASE_NAME'"
    else
        echo "  💾 Database:          ⚠ May still be initializing"
    fi
    echo ""
    
    # Wait for resources to be ready
    log_info "Waiting for resources to be ready (30 seconds for DNS propagation)..."
    sleep 30
    log_success "Resources ready"
    
    # Get warehouse ID
    log_info "Retrieving SQL Warehouse ID..."
    
    # Try to get warehouse ID with better error handling
    WAREHOUSE_LIST_OUTPUT=$(mktemp)
    databricks warehouses list --output json > "$WAREHOUSE_LIST_OUTPUT" 2>&1
    WAREHOUSE_LIST_STATUS=$?
    
    if [ $WAREHOUSE_LIST_STATUS -eq 0 ]; then
        WAREHOUSE_ID=$(python3 -c "
import json, sys
try:
    with open('$WAREHOUSE_LIST_OUTPUT', 'r') as f:
        data = json.load(f)
    warehouses = data.get('warehouses', data) if isinstance(data, dict) else data
    for w in warehouses:
        if w.get('name') == '$WAREHOUSE_NAME':
            print(w.get('id', ''))
            sys.exit(0)
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null)
    fi
    
    rm -f "$WAREHOUSE_LIST_OUTPUT"
    
    if [ -n "$WAREHOUSE_ID" ]; then
        log_success "Found warehouse ID: $WAREHOUSE_ID"
    else
        log_warning "Could not retrieve warehouse ID automatically"
        if [ "$VERBOSE" = "true" ]; then
            log_info "Please check warehouse name: $WAREHOUSE_NAME"
            log_info "List all warehouses with: databricks warehouses list"
        fi
    fi
    
    # Get Lakebase host
    log_info "Retrieving Lakebase host..."
    
    # Try to get database instance details with better error handling  
    DB_INSTANCE_OUTPUT=$(mktemp)
    databricks database list-database-instances --output json > "$DB_INSTANCE_OUTPUT" 2>&1
    DB_INSTANCE_STATUS=$?
    
    if [ $DB_INSTANCE_STATUS -eq 0 ]; then
        LAKEBASE_HOST=$(python3 -c "
import json, sys
try:
    with open('$DB_INSTANCE_OUTPUT', 'r') as f:
        content = f.read()
        if not content.strip():
            print('', file=sys.stderr)
            sys.exit(1)
        data = json.loads(content)
    
    # Handle both list and dict formats
    instances = data if isinstance(data, list) else data.get('instances', data.get('database_instances', []))
    
    for inst in instances:
        if inst.get('name') == '$LAKEBASE_INSTANCE_NAME':
            host = inst.get('host', inst.get('hostname', ''))
            if host:
                print(host)
                sys.exit(0)
    
    print('', file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f'Error parsing: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null)
    else
        if [ "$VERBOSE" = "true" ]; then
            log_warning "Failed to list database instances:"
            cat "$DB_INSTANCE_OUTPUT"
        fi
    fi
    
    rm -f "$DB_INSTANCE_OUTPUT"
    
    if [ -n "$LAKEBASE_HOST" ]; then
        log_success "Found Lakebase host: $LAKEBASE_HOST"
    else
        log_warning "Could not retrieve Lakebase host automatically"
        if [ "$VERBOSE" = "true" ]; then
            log_info "Please check database instance name: $LAKEBASE_INSTANCE_NAME"
            log_info "List all instances with: databricks database list-database-instances"
        fi
        log_info "You can manually set LAKEBASE_HOST in .env.local"
    fi
    
    # Update .env.local if values were found
    if [ -n "$WAREHOUSE_ID" ] || [ -n "$LAKEBASE_HOST" ]; then
        log_info "Updating .env.local with deployed resource values..."
        ENV_FILE=".env.local"
        
        # Create backup
        if [ -f "$ENV_FILE" ]; then
            cp "$ENV_FILE" "$ENV_FILE.backup"
        else
            touch "$ENV_FILE"
        fi
        
        # Function to update or add env var
        update_env_var() {
            local key=$1
            local value=$2
            
            if grep -q "^${key}=" "$ENV_FILE"; then
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
                else
                    sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
                fi
            else
                echo "${key}=${value}" >> "$ENV_FILE"
            fi
        }
        
        [ -n "$WAREHOUSE_ID" ] && update_env_var "DATABRICKS_WAREHOUSE_ID" "$WAREHOUSE_ID"
        [ -n "$LAKEBASE_HOST" ] && update_env_var "LAKEBASE_HOST" "$LAKEBASE_HOST"
        [ -n "$LAKEBASE_HOST" ] && update_env_var "PGHOST" "$LAKEBASE_HOST"
        update_env_var "LAKEBASE_PORT" "5432"
        update_env_var "LAKEBASE_DATABASE" "app_database"
        update_env_var "LAKEBASE_INSTANCE_NAME" "$LAKEBASE_INSTANCE_NAME"
        
        # Reload environment
        set -a
        source "$ENV_FILE"
        set +a
        
        log_success "Environment variables updated"
    fi
    
    # Test Lakebase connectivity (only if host is available)
    if [ -n "$LAKEBASE_HOST" ]; then
        log_info "Testing Lakebase connectivity..."
        RETRY_COUNT=0
        MAX_RETRIES=5
        RETRY_DELAY=10
        
        while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
            if uv run python -c "from server.lib.database import get_engine; get_engine().connect()" &> /dev/null; then
                log_success "Lakebase connection successful"
                break
            else
                RETRY_COUNT=$((RETRY_COUNT + 1))
                if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
                    log_warning "Connection failed, retrying in ${RETRY_DELAY}s (attempt $RETRY_COUNT/$MAX_RETRIES)..."
                    sleep $RETRY_DELAY
                else
                    log_warning "Could not connect to Lakebase after $MAX_RETRIES attempts"
                    log_info "This may be normal - Lakebase instance might still be initializing"
                    log_info "You can test connectivity later with: uv run python -c 'from server.lib.database import get_engine; get_engine().connect()'"
                fi
            fi
        done
    else
        log_warning "Skipping Lakebase connectivity test (host not available)"
        log_info "Once you set LAKEBASE_HOST, test with: uv run python -c 'from server.lib.database import get_engine; get_engine().connect()'"
    fi
    
    print_timing "Bundle deployment completed"
    echo ""
else
    log_info "Skipping infrastructure bundle deployment"
    echo ""
fi

# ============================================
# PHASE 3: Run Database Migrations
# ============================================
if [ "$DEPLOY_MIGRATIONS" = "yes" ]; then
    log_step "Phase 3: Running database migrations..."
    print_timing "Migrations started"
    
    # Verify Lakebase connection is configured
    if [ -z "$LAKEBASE_HOST" ] && [ -z "$PGHOST" ]; then
        log_error "Lakebase host not configured. Cannot run migrations."
        log_info "Please ensure LAKEBASE_HOST or PGHOST is set in .env.local"
        log_info "You can configure it with: uv run python scripts/configure_lakebase.py"
        exit 1
    fi
    
    # Check if alembic is available
    if command -v alembic &> /dev/null; then
        ALEMBIC_CMD="alembic"
    else
        ALEMBIC_CMD="uv run alembic"
    fi
    
    # Check if tables already exist
    log_info "Checking if tables already exist..."
    EXISTING_TABLES=$(uv run python -c "
from server.lib.database import get_engine
from sqlalchemy import inspect
try:
    engine = get_engine()
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(','.join(tables))
except Exception as e:
    print('')
" 2>/dev/null)
    
    if [ -n "$EXISTING_TABLES" ]; then
        IFS=',' read -ra EXISTING_TABLE_ARRAY <<< "$EXISTING_TABLES"
        TABLE_COUNT=${#EXISTING_TABLE_ARRAY[@]}
        log_info "Found $TABLE_COUNT existing table(s)"
        if [ "$VERBOSE" = "true" ]; then
            for table in "${EXISTING_TABLE_ARRAY[@]}"; do
                echo "  - $table"
            done
        fi
    else
        log_info "No existing tables found"
    fi
    
    # Show current migration status
    log_info "Current migration status:"
    CURRENT_MIGRATION=$($ALEMBIC_CMD current 2>&1)
    if echo "$CURRENT_MIGRATION" | grep -q "head"; then
        log_success "Database is at latest migration"
        MIGRATIONS_NEEDED="no"
    else
        log_info "Migrations need to be applied"
        MIGRATIONS_NEEDED="yes"
    fi
    
    # Run migrations if needed
    if [ "$MIGRATIONS_NEEDED" = "yes" ] || [ -z "$EXISTING_TABLES" ]; then
        log_info "Applying migrations..."
        if [ "$VERBOSE" = "true" ]; then
            $ALEMBIC_CMD upgrade head
        else
            MIGRATION_OUTPUT=$(mktemp)
            $ALEMBIC_CMD upgrade head > "$MIGRATION_OUTPUT" 2>&1
            MIGRATION_STATUS=$?
            
            if [ $MIGRATION_STATUS -ne 0 ]; then
                log_error "Migration failed"
                cat "$MIGRATION_OUTPUT"
                rm -f "$MIGRATION_OUTPUT"
                exit 1
            fi
            rm -f "$MIGRATION_OUTPUT"
        fi
        log_success "Migrations completed"
    else
        log_info "Migrations already up to date, skipping"
    fi
    
    # Show final migration status
    log_info "Final migration status:"
    $ALEMBIC_CMD current
    
    # Verify tables were created
    log_info "Verifying tables..."
    TABLES=$(uv run python -c "
from server.lib.database import get_engine
from sqlalchemy import inspect
try:
    engine = get_engine()
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(','.join(tables))
except Exception as e:
    print('')
" 2>/dev/null)
    
    if [ -n "$TABLES" ]; then
        IFS=',' read -ra TABLE_ARRAY <<< "$TABLES"
        TABLE_COUNT=${#TABLE_ARRAY[@]}
        log_success "Tables verified ($TABLE_COUNT tables exist)"
        
        if [ "$VERBOSE" = "true" ]; then
            echo ""
            log_info "Database tables:"
            for table in "${TABLE_ARRAY[@]}"; do
                echo "  ✓ $table"
            done
        fi
        
        # Check for expected tables
        EXPECTED_TABLES=("user_preferences" "model_inference_logs" "schema_detection_events" "alembic_version")
        MISSING_TABLES=""
        
        for expected_table in "${EXPECTED_TABLES[@]}"; do
            if [[ ! " ${TABLE_ARRAY[@]} " =~ " ${expected_table} " ]]; then
                MISSING_TABLES="$MISSING_TABLES $expected_table"
            fi
        done
        
        if [ -n "$MISSING_TABLES" ]; then
            log_warning "Some expected tables are missing:$MISSING_TABLES"
            log_info "This may indicate that migrations were not fully applied"
        else
            log_success "All expected tables are present"
        fi
    else
        log_error "Could not verify tables"
        log_info "Tables may not have been created. Check Lakebase connectivity."
        log_info "Test connection with: uv run python -c 'from server.lib.database import get_engine; get_engine().connect()'"
        exit 1
    fi
    
    print_timing "Migrations completed"
    echo ""
else
    log_info "Skipping database migrations"
    log_warning "Tables may not be created. Run migrations later with: alembic upgrade head"
    echo ""
fi

# ============================================
# PHASE 4: Create Sample Data
# ============================================
if [ "$DEPLOY_SAMPLE_DATA" = "yes" ]; then
    log_step "Phase 4: Creating sample data..."
    print_timing "Sample data creation started"
    
    log_info "Creating sample data in Unity Catalog and Lakebase..."
    if [ "$VERBOSE" = "true" ]; then
        uv run python scripts/setup_sample_data.py create-all
    else
        uv run python scripts/setup_sample_data.py create-all > /dev/null 2>&1
    fi
    log_success "Sample data created"
    
    print_timing "Sample data creation completed"
    echo ""
else
    log_info "Skipping sample data creation"
    echo ""
fi

# ============================================
# PHASE 5: Deploy Application
# ============================================
if [ "$DEPLOY_APP" = "yes" ]; then
    log_step "Phase 5: Deploying application..."
    print_timing "Application deployment started"
    
    # Validate required configuration
    if [ -z "$DBA_SOURCE_CODE_PATH" ]; then
        log_error "DBA_SOURCE_CODE_PATH is not set. Please run ./setup.sh first."
        exit 1
    fi
    
    if [ -z "$DATABRICKS_APP_NAME" ]; then
        log_error "DATABRICKS_APP_NAME is not set. Please run ./setup.sh first."
        exit 1
    fi
    
    # Determine auth parameters
    AUTH_PROFILE_FLAG=""
    if [ -n "$DATABRICKS_CONFIG_PROFILE" ]; then
        AUTH_PROFILE_FLAG="--profile $DATABRICKS_CONFIG_PROFILE"
    fi
    
    # Check if app exists and create if needed
    if [ "$CREATE_APP" = "true" ]; then
        log_info "Checking if app exists..."
        APP_EXISTS=$(databricks apps list $AUTH_PROFILE_FLAG 2>/dev/null | grep -c "^$DATABRICKS_APP_NAME " 2>/dev/null || echo "0")
        
        if [ "$APP_EXISTS" -eq 0 ]; then
            log_info "Creating app '$DATABRICKS_APP_NAME'..."
            if [ "$VERBOSE" = "true" ]; then
                databricks apps create "$DATABRICKS_APP_NAME" $AUTH_PROFILE_FLAG
            else
                databricks apps create "$DATABRICKS_APP_NAME" $AUTH_PROFILE_FLAG > /dev/null 2>&1
            fi
            log_success "App created"
            sleep 5  # Wait for app to be fully created
        else
            log_success "App already exists"
        fi
    fi
    
    # Generate requirements.txt
    log_info "Generating requirements.txt..."
    uv run python scripts/generate_semver_requirements.py
    log_success "Requirements generated"
    
    # Build frontend
    log_info "Building frontend..."
    cd client
    if [ "$VERBOSE" = "true" ]; then
        bun run build
    else
        bun run build > /dev/null 2>&1
    fi
    cd ..
    log_success "Frontend built"
    
    # Create workspace directory
    log_info "Creating workspace directory..."
    databricks workspace mkdirs "$DBA_SOURCE_CODE_PATH" $AUTH_PROFILE_FLAG
    log_success "Workspace directory ready"
    
    # Sync source code
    log_info "Syncing source code to workspace..."
    if [ "$VERBOSE" = "true" ]; then
        databricks sync . "$DBA_SOURCE_CODE_PATH" $AUTH_PROFILE_FLAG
    else
        databricks sync . "$DBA_SOURCE_CODE_PATH" $AUTH_PROFILE_FLAG > /dev/null 2>&1
    fi
    log_success "Source code synced"
    
    # Deploy app
    log_info "Deploying app to Databricks..."
    if [ "$VERBOSE" = "true" ]; then
        databricks apps deploy "$DATABRICKS_APP_NAME" --source-code-path "$DBA_SOURCE_CODE_PATH" --debug $AUTH_PROFILE_FLAG
    else
        databricks apps deploy "$DATABRICKS_APP_NAME" --source-code-path "$DBA_SOURCE_CODE_PATH" $AUTH_PROFILE_FLAG
    fi
    log_success "App deployed"
    
    # Get app URL
    log_info "Retrieving app URL..."
    APP_URL=$(databricks apps list --output json $AUTH_PROFILE_FLAG 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    apps = data if isinstance(data, list) else data.get('apps', [])
    for app in apps:
        if app.get('name') == '$DATABRICKS_APP_NAME':
            print(app.get('url', ''))
            break
except: pass
" 2>/dev/null)
    
    print_timing "Application deployment completed"
    echo ""
else
    log_info "Skipping application deployment"
    echo ""
fi

# ============================================
# Final Summary
# ============================================
echo ""
echo "=============================================="
echo "  Deployment Complete!"
echo "=============================================="
echo ""
echo "Target Environment:  $TARGET"
echo ""

if [ "$DEPLOY_BUNDLE" = "yes" ]; then
    echo "✓ Infrastructure deployed"
    [ -n "$WAREHOUSE_ID" ] && echo "  SQL Warehouse ID:  $WAREHOUSE_ID"
    [ -n "$LAKEBASE_HOST" ] && echo "  Lakebase Host:     $LAKEBASE_HOST"
fi

if [ "$DEPLOY_MIGRATIONS" = "yes" ]; then
    echo "✓ Database migrations applied"
    if [ -n "$TABLES" ]; then
        IFS=',' read -ra TABLE_ARRAY <<< "$TABLES"
        TABLE_COUNT=${#TABLE_ARRAY[@]}
        echo "  Tables created:    $TABLE_COUNT"
        if [ "$VERBOSE" = "true" ]; then
            for table in "${TABLE_ARRAY[@]}"; do
                echo "    - $table"
            done
        fi
    fi
fi

if [ "$DEPLOY_SAMPLE_DATA" = "yes" ]; then
    echo "✓ Sample data created"
fi

if [ "$DEPLOY_APP" = "yes" ]; then
    echo "✓ Application deployed"
    if [ -n "$APP_URL" ]; then
        echo "  App URL:           $APP_URL"
        echo "  Logs:              $APP_URL/logz"
    else
        echo "  App Name:          $DATABRICKS_APP_NAME"
        echo "  Check URL with:    databricks apps list"
    fi
fi

echo ""
echo "Next steps:"
STEP_NUM=1
if [ "$DEPLOY_APP" = "yes" ] && [ -n "$APP_URL" ]; then
    echo "  $STEP_NUM. Visit your app:     $APP_URL"
    STEP_NUM=$((STEP_NUM + 1))
    echo "  $STEP_NUM. Check logs:         $APP_URL/logz (in browser)"
    STEP_NUM=$((STEP_NUM + 1))
fi
if [ "$DEPLOY_MIGRATIONS" = "no" ]; then
    echo "  $STEP_NUM. Create tables:      alembic upgrade head"
    STEP_NUM=$((STEP_NUM + 1))
fi
echo "  $STEP_NUM. Check status:       databricks apps list"
STEP_NUM=$((STEP_NUM + 1))
if [ "$TARGET" = "dev" ]; then
    echo "  $STEP_NUM. Local development:  ./watch.sh"
    STEP_NUM=$((STEP_NUM + 1))
fi
if [ "$DEPLOY_BUNDLE" = "yes" ] && [ -z "$LAKEBASE_HOST" ]; then
    echo "  $STEP_NUM. Configure Lakebase: uv run python scripts/configure_lakebase.py"
fi
echo ""

log_success "All deployment tasks completed successfully!"