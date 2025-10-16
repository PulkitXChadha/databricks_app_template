#!/bin/bash
# Refresh local development token
# This script gets a fresh OAuth token from Databricks and updates the client/.env.local file

set -e

echo "🔐 Refreshing Databricks OAuth token for local development..."
echo ""

# Get fresh token from Databricks CLI
TOKEN_OUTPUT=$(databricks auth token 2>&1)

# Check if authentication was successful
if [ $? -ne 0 ]; then
  echo "❌ Failed to get token from Databricks CLI"
  echo "Please authenticate first with: databricks auth login --host https://your-workspace.cloud.databricks.com"
  exit 1
fi

# Extract the access_token from JSON output
ACCESS_TOKEN=$(echo "$TOKEN_OUTPUT" | grep -o '"access_token": "[^"]*' | sed 's/"access_token": "//')

if [ -z "$ACCESS_TOKEN" ]; then
  echo "❌ Could not extract access token from response"
  exit 1
fi

# Extract expiry time
EXPIRY=$(echo "$TOKEN_OUTPUT" | grep -o '"expiry": "[^"]*' | sed 's/"expiry": "//')

echo "✅ Got fresh token (expires: $EXPIRY)"
echo ""

# Create or update client/.env.local file
ENV_FILE="client/.env.local"

cat > "$ENV_FILE" << EOF
# Local Development Environment Variables
# This file is for local development only and should NOT be committed to git

# User OAuth token for local development
# Last refreshed: $(date)
# Expires: $EXPIRY
# To refresh: ./refresh_local_token.sh
VITE_DATABRICKS_USER_TOKEN=$ACCESS_TOKEN
EOF

echo "✅ Token saved to $ENV_FILE"
echo ""
echo "📝 Next steps:"
echo "   1. Restart your development server (./watch.sh)"
echo "   2. Reload your browser at http://localhost:5173/"
echo "   3. Token expires in ~1 hour, run this script again to refresh"
echo ""
echo "💡 Tip: Add this to your workflow:"
echo "   ./refresh_local_token.sh && ./watch.sh"

