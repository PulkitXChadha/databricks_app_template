#!/usr/bin/env python3
"""Fetch user access token for local OBO testing.

This script retrieves a user access token from the Databricks CLI for local
development and testing of On-Behalf-Of (OBO) authentication flows.

Usage:
    # Get token and export for use in curl requests
    export DATABRICKS_USER_TOKEN=$(python scripts/get_user_token.py)
    
    # Use in API requests
    curl -H "X-Forwarded-Access-Token: $DATABRICKS_USER_TOKEN" \
         http://localhost:8000/api/user/me

Prerequisites:
    - Databricks CLI installed (https://docs.databricks.com/dev-tools/cli/)
    - Authenticated with your workspace: databricks auth login --host <workspace-url>

See also:
    - docs/LOCAL_DEVELOPMENT.md for detailed testing instructions
    - quickstart.md Phase 2 for OBO testing scenarios
"""

import subprocess
import sys


def get_databricks_user_token() -> str:
    """Fetch user access token from Databricks CLI.
    
    Returns:
        User access token string
        
    Raises:
        SystemExit: If CLI is not installed or authentication fails
    """
    try:
        result = subprocess.run(
            ["databricks", "auth", "token"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to fetch token: {e.stderr}", file=sys.stderr)
        print("\nTo authenticate, run:", file=sys.stderr)
        print("  databricks auth login --host https://your-workspace.cloud.databricks.com", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: Databricks CLI not installed", file=sys.stderr)
        print("\nInstall using:", file=sys.stderr)
        print("  curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    token = get_databricks_user_token()
    print(token)

