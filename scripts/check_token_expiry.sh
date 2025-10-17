#!/bin/bash
# Check if the OAuth token is expired or about to expire
# Returns 0 if token is valid, 1 if expired or missing

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$SCRIPT_DIR/client/.env.local"

# Check if env file exists
if [ ! -f "$ENV_FILE" ]; then
  echo "⚠️  No token file found at $ENV_FILE"
  exit 1
fi

# Extract expiry time from env file
EXPIRY=$(grep "# Expires:" "$ENV_FILE" | sed 's/# Expires: //' | xargs)

if [ -z "$EXPIRY" ]; then
  echo "⚠️  Could not find expiry time in token file"
  exit 1
fi

# Parse expiry time and compare with current time
if command -v gdate >/dev/null 2>&1; then
  # macOS with GNU coreutils
  EXPIRY_EPOCH=$(gdate -d "$EXPIRY" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "${EXPIRY:0:19}" +%s 2>/dev/null || echo "0")
else
  # Linux or macOS without GNU coreutils
  EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "${EXPIRY:0:19}" +%s 2>/dev/null || echo "0")
fi

if [ "$EXPIRY_EPOCH" = "0" ]; then
  echo "⚠️  Could not parse expiry time: $EXPIRY"
  exit 1
fi

NOW_EPOCH=$(date +%s)
SECONDS_UNTIL_EXPIRY=$((EXPIRY_EPOCH - NOW_EPOCH))

# Token is expired
if [ $SECONDS_UNTIL_EXPIRY -lt 0 ]; then
  echo "❌ Token expired $((-SECONDS_UNTIL_EXPIRY / 60)) minutes ago"
  exit 1
fi

# Token expires in less than 5 minutes (warning threshold)
if [ $SECONDS_UNTIL_EXPIRY -lt 300 ]; then
  MINUTES=$((SECONDS_UNTIL_EXPIRY / 60))
  echo "⚠️  Token expires in $MINUTES minutes"
  exit 2
fi

# Token is valid
MINUTES=$((SECONDS_UNTIL_EXPIRY / 60))
echo "✅ Token valid for $MINUTES more minutes"
exit 0

