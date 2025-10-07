#!/usr/bin/env python3
"""Generate Lakebase OAuth token using Databricks CLI.

This script generates a fresh OAuth token for Lakebase access.
The token expires after 1 hour.
"""

import subprocess
import sys

def generate_lakebase_token():
    """Generate OAuth token using Databricks CLI."""
    try:
        # Get OAuth token using databricks CLI
        result = subprocess.run(
            ['databricks', 'auth', 'token', '--host', subprocess.check_output(
                ['grep', '-E', '^DATABRICKS_HOST', '.env.local'], 
                text=True
            ).split('=')[1].strip()],
            capture_output=True,
            text=True,
            check=True
        )
        
        token = result.stdout.strip()
        print(f"Generated LAKEBASE_TOKEN (expires in 1 hour):")
        print(token)
        print(f"\nTo use this token, add it to your .env.local:")
        print(f"LAKEBASE_TOKEN={token}")
        return token
        
    except FileNotFoundError:
        print("Error: databricks CLI not found.")
        print("Install it with: pip install databricks-cli")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error getting token: {e}")
        print("Make sure you're logged in: databricks auth login")
        sys.exit(1)

if __name__ == '__main__':
    generate_lakebase_token()

