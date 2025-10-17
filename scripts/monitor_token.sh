#!/bin/bash
# Background token monitor - automatically refreshes OAuth token before expiry
# This script runs in the background and seamlessly manages token lifecycle

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECK_INTERVAL=300  # Check every 5 minutes
REFRESH_THRESHOLD=600  # Auto-refresh when < 10 minutes remaining

# Track refresh attempts to avoid infinite loops on failure
REFRESH_FAILED=false

while true; do
  sleep $CHECK_INTERVAL
  
  # Check token status
  if [ -x "$SCRIPT_DIR/scripts/check_token_expiry.sh" ]; then
    TOKEN_STATUS=$("$SCRIPT_DIR/scripts/check_token_expiry.sh")
    TOKEN_EXIT_CODE=$?
    
    # Token is expired or expiring soon - auto-refresh it
    if [ $TOKEN_EXIT_CODE -eq 1 ] || [ $TOKEN_EXIT_CODE -eq 2 ]; then
      
      # Only attempt refresh if we haven't failed recently
      if [ "$REFRESH_FAILED" = false ]; then
        echo ""
        echo "🔄 Token expiring soon, automatically refreshing..."
        
        # Attempt to refresh token
        if [ -x "$SCRIPT_DIR/refresh_local_token.sh" ]; then
          if "$SCRIPT_DIR/refresh_local_token.sh" --quiet > /dev/null 2>&1; then
            # Refresh succeeded
            NEW_STATUS=$("$SCRIPT_DIR/scripts/check_token_expiry.sh")
            echo "✅ Token automatically refreshed - $NEW_STATUS"
            echo ""
            REFRESH_FAILED=false
          else
            # Refresh failed - show manual instructions
            REFRESH_FAILED=true
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "⚠️  AUTOMATIC TOKEN REFRESH FAILED"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            echo "Could not automatically refresh your OAuth token."
            echo "This usually means your Databricks CLI session expired."
            echo ""
            echo "Please manually refresh by running:"
            echo "   ./refresh_local_token.sh"
            echo ""
            echo "Or restart the development server:"
            echo "   Ctrl+C to stop, then ./watch.sh"
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
          fi
        else
          echo "⚠️  Token refresh script not found, skipping auto-refresh"
        fi
      fi
      
    else
      # Token is valid (> 10 minutes remaining)
      REFRESH_FAILED=false
    fi
  fi
done

