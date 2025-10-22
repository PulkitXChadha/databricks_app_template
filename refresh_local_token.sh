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

print_message "🔐 Refreshing Databricks OAuth token for local development..."
print_message ""

# Load DATABRICKS_HOST from .env.local if it exists
if [ -f "$SCRIPT_DIR/.env.local" ]; then
  source "$SCRIPT_DIR/.env.local"
fi

# Determine which authentication method to use
AUTH_CMD="databricks auth token"
if [ ! -z "$DATABRICKS_CONFIG_PROFILE" ]; then
  AUTH_CMD="$AUTH_CMD --profile $DATABRICKS_CONFIG_PROFILE"
  print_message "Using profile: $DATABRICKS_CONFIG_PROFILE"
elif [ ! -z "$DATABRICKS_HOST" ]; then
  AUTH_CMD="$AUTH_CMD --host $DATABRICKS_HOST"
  print_message "Using host: $DATABRICKS_HOST"
fi

# Try to get token, redirect stderr to capture prompts
# If running from watch.sh with log formatting, use a temp file to avoid pipeline interference
if { true >&3; } 2>/dev/null; then
  # File descriptor 3 exists (we're running from watch.sh)
  # Use temp file to capture output and bypass the log formatting pipeline
  TEMP_TOKEN_FILE=$(mktemp)
  eval "$AUTH_CMD" > "$TEMP_TOKEN_FILE" 2>&1 || true
  TOKEN_EXIT_CODE=$?
  TOKEN_OUTPUT=$(cat "$TEMP_TOKEN_FILE")
  rm -f "$TEMP_TOKEN_FILE"
else
  # Normal execution outside watch.sh
  TOKEN_OUTPUT=$(eval "$AUTH_CMD" 2>&1)
  TOKEN_EXIT_CODE=$?
fi

# Check if authentication was successful
if [ $TOKEN_EXIT_CODE -ne 0 ]; then
  echo "❌ Failed to get token from Databricks CLI"
  echo ""
  echo "Error output:"
  echo "$TOKEN_OUTPUT"
  echo ""
  echo "💡 Please authenticate first:"
  if [ ! -z "$DATABRICKS_CONFIG_PROFILE" ]; then
    echo "   databricks auth login --profile $DATABRICKS_CONFIG_PROFILE"
  elif [ ! -z "$DATABRICKS_HOST" ]; then
    echo "   databricks auth login --host $DATABRICKS_HOST"
  else
    echo "   databricks auth login --host https://your-workspace.cloud.databricks.com"
  fi
  echo ""
  exit 1
fi

# Check if we got a prompt instead of a token (authentication needed)
if echo "$TOKEN_OUTPUT" | grep -q "Databricks host"; then
  echo "🔐 Authentication required. Please complete the authentication flow..."
  echo ""
  
  # Run the command interactively
  if [ ! -z "$DATABRICKS_CONFIG_PROFILE" ]; then
    databricks auth login --profile "$DATABRICKS_CONFIG_PROFILE"
  elif [ ! -z "$DATABRICKS_HOST" ]; then
    databricks auth login --host "$DATABRICKS_HOST"
  else
    databricks auth login
  fi
  
  # Try again after authentication
  if { true >&3; } 2>/dev/null; then
    TEMP_TOKEN_FILE=$(mktemp)
    eval "$AUTH_CMD" > "$TEMP_TOKEN_FILE" 2>&1 || true
    TOKEN_EXIT_CODE=$?
    TOKEN_OUTPUT=$(cat "$TEMP_TOKEN_FILE")
    rm -f "$TEMP_TOKEN_FILE"
  else
    TOKEN_OUTPUT=$(eval "$AUTH_CMD" 2>&1)
    TOKEN_EXIT_CODE=$?
  fi
  
  if [ $TOKEN_EXIT_CODE -ne 0 ]; then
    echo "❌ Authentication failed"
    exit 1
  fi
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

if [ "$QUIET" = false ]; then
  echo ""
  echo "📝 Token will expire in ~1 hour. The watch.sh script will automatically"
  echo "   detect expiration and prompt you to refresh."
fi

exit 0

