#!/bin/bash
# Refresh local development token
# This script gets a fresh OAuth token from Databricks and updates the client/.env.local file

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/client/.env.local"

# Parse arguments
QUIET=false
if [[ "$1" == "--quiet" ]]; then
  QUIET=true
fi

print_message() {
  if [ "$QUIET" = false ]; then
    echo "$1"
  fi
}

# Portable timeout function that works on macOS and Linux
run_with_timeout() {
  local timeout=$1
  shift
  
  # Try gtimeout first (GNU coreutils on macOS)
  if command -v gtimeout >/dev/null 2>&1; then
    gtimeout "$timeout" "$@"
    return $?
  fi
  
  # Try timeout (Linux)
  if command -v timeout >/dev/null 2>&1; then
    timeout "$timeout" "$@"
    return $?
  fi
  
  # Fallback: run command with perl-based timeout
  perl -e '
    $SIG{ALRM} = sub { die "timeout\n" };
    alarm shift @ARGV;
    exec @ARGV;
  ' "$timeout" "$@" 2>/dev/null
  return $?
}

print_message "🔐 Refreshing Databricks OAuth token for local development..."
print_message ""

# Load DATABRICKS_HOST from .env.local if it exists
if [ -f "$SCRIPT_DIR/.env.local" ]; then
  source "$SCRIPT_DIR/.env.local"
fi

# Determine which authentication method to use
if [ ! -z "$DATABRICKS_CONFIG_PROFILE" ]; then
  print_message "Using profile: $DATABRICKS_CONFIG_PROFILE"
  AUTH_ARGS="--profile $DATABRICKS_CONFIG_PROFILE"
elif [ ! -z "$DATABRICKS_HOST" ]; then
  print_message "Using host: $DATABRICKS_HOST"
  AUTH_ARGS="--host $DATABRICKS_HOST"
else
  AUTH_ARGS=""
fi

# First, check if we're authenticated and if the session is still valid
check_auth_valid() {
  local temp_check=$(mktemp)
  if [ ! -z "$AUTH_ARGS" ]; then
    run_with_timeout 5 databricks auth describe $AUTH_ARGS > "$temp_check" 2>&1 || true
  else
    run_with_timeout 5 databricks auth describe > "$temp_check" 2>&1 || true
  fi
  local result=$?
  rm -f "$temp_check"
  return $result
}

# If auth is not valid, try to refresh it automatically
if ! check_auth_valid; then
  print_message "⚠️  Authentication session expired or invalid, attempting refresh..."
  
  # Try to login non-interactively first using existing credentials
  TEMP_LOGIN=$(mktemp)
  if [ ! -z "$AUTH_ARGS" ]; then
    run_with_timeout 10 databricks auth login $AUTH_ARGS > "$TEMP_LOGIN" 2>&1 || true
  else
    run_with_timeout 10 databricks auth login > "$TEMP_LOGIN" 2>&1 || true
  fi
  LOGIN_EXIT=$?
  rm -f "$TEMP_LOGIN"
  
  if [ $LOGIN_EXIT -ne 0 ]; then
    echo "❌ Failed to refresh authentication. Please re-authenticate manually:"
    if [ ! -z "$AUTH_ARGS" ]; then
      echo "   databricks auth login $AUTH_ARGS"
    else
      echo "   databricks auth login"
    fi
    exit 1
  fi
  
  print_message "✅ Authentication refreshed"
fi

# Now try to get the token with a timeout to prevent hanging
TEMP_TOKEN_FILE=$(mktemp)

if [ ! -z "$AUTH_ARGS" ]; then
  run_with_timeout 10 databricks auth token $AUTH_ARGS > "$TEMP_TOKEN_FILE" 2>&1 || true
else
  run_with_timeout 10 databricks auth token > "$TEMP_TOKEN_FILE" 2>&1 || true
fi
TOKEN_EXIT_CODE=$?

TOKEN_OUTPUT=$(cat "$TEMP_TOKEN_FILE")
rm -f "$TEMP_TOKEN_FILE"

# Check if authentication was successful
if [ $TOKEN_EXIT_CODE -ne 0 ]; then
  echo "❌ Failed to get token from Databricks CLI (timeout or error)"
  echo ""
  echo "Error output:"
  echo "$TOKEN_OUTPUT"
  echo ""
  echo "💡 Please authenticate manually:"
  if [ ! -z "$AUTH_ARGS" ]; then
    echo "   databricks auth login $AUTH_ARGS"
  else
    echo "   databricks auth login"
  fi
  echo ""
  exit 1
fi

# Extract the access_token from JSON output
ACCESS_TOKEN=$(echo "$TOKEN_OUTPUT" | grep -o '"access_token": "[^"]*' | sed 's/"access_token": "//')

if [ -z "$ACCESS_TOKEN" ]; then
  echo "❌ Could not extract access token from response"
  echo "Response was:"
  echo "$TOKEN_OUTPUT"
  exit 1
fi

# Extract expiry time
EXPIRY=$(echo "$TOKEN_OUTPUT" | grep -o '"expiry": "[^"]*' | sed 's/"expiry": "//')

# Calculate time until expiry
if [ ! -z "$EXPIRY" ]; then
  if command -v gdate >/dev/null 2>&1; then
    # macOS with GNU coreutils
    EXPIRY_EPOCH=$(gdate -d "$EXPIRY" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "$EXPIRY" +%s 2>/dev/null || echo "")
  else
    # Linux or macOS without GNU coreutils
    EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "$EXPIRY" +%s 2>/dev/null || echo "")
  fi
  
  if [ ! -z "$EXPIRY_EPOCH" ]; then
    NOW_EPOCH=$(date +%s)
    SECONDS_UNTIL_EXPIRY=$((EXPIRY_EPOCH - NOW_EPOCH))
    MINUTES_UNTIL_EXPIRY=$((SECONDS_UNTIL_EXPIRY / 60))
    
    print_message "✅ Got fresh token (expires in ~$MINUTES_UNTIL_EXPIRY minutes)"
  else
    print_message "✅ Got fresh token (expires: $EXPIRY)"
  fi
else
  print_message "✅ Got fresh token"
fi

print_message ""

# Create or update client/.env.local file
cat > "$ENV_FILE" << EOF
# Local Development Environment Variables
# This file is for local development only and should NOT be committed to git

# User OAuth token for local development
# Last refreshed: $(date)
# Expires: $EXPIRY
# To refresh: ./refresh_local_token.sh
VITE_DATABRICKS_USER_TOKEN=$ACCESS_TOKEN
EOF

print_message "✅ Token saved to $ENV_FILE"

# Restart Vite frontend if it's running to pick up the new token
# Vite doesn't hot-reload .env.local changes
if pgrep -f "vite" > /dev/null 2>&1; then
  print_message "🔄 Restarting Vite frontend to pick up new token..."
  pkill -f "node.*vite" 2>/dev/null || true
  sleep 1
  print_message "✅ Frontend will restart automatically via watch.sh"
fi

if [ "$QUIET" = false ]; then
  echo ""
  echo "📝 Token will expire in ~1 hour. The watch.sh script will automatically"
  echo "   detect expiration and refresh it."
  echo ""
  echo "💡 If API calls still fail, try reloading your browser (Cmd+R or Ctrl+R)"
fi

exit 0

