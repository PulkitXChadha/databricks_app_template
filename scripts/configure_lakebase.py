#!/usr/bin/env python3
"""Configure Lakebase for local development.

This script helps you set up Lakebase configuration in .env.local by:
1. Checking if you have a deployed bundle with Lakebase resources
2. Retrieving Lakebase instance details from Databricks
3. Updating your .env.local file with the configuration

Usage:
    python scripts/configure_lakebase.py
    python scripts/configure_lakebase.py --check-only  # Just check status
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional


def run_command(cmd: list[str]) -> tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def load_env_file(filepath: str) -> Dict[str, str]:
    """Load environment variables from a file."""
    env_vars = {}
    path = Path(filepath)
    if path.exists():
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    env_vars[key.strip()] = value.strip()
    return env_vars


def update_env_file(filepath: str, updates: Dict[str, str]):
    """Update or add environment variables in a file."""
    path = Path(filepath)
    
    # Read existing content
    existing_lines = []
    if path.exists():
        with open(path) as f:
            existing_lines = f.readlines()
    
    # Track which keys we've updated
    updated_keys = set()
    new_lines = []
    
    # Update existing keys
    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key = stripped.split('=')[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                updated_keys.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    # Add new keys
    if updated_keys != set(updates.keys()):
        new_lines.append("\n# Auto-configured Lakebase settings\n")
        for key, value in updates.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={value}\n")
    
    # Write back
    with open(path, 'w') as f:
        f.writelines(new_lines)


def check_databricks_auth() -> bool:
    """Check if user is authenticated to Databricks."""
    exit_code, _, _ = run_command(['databricks', 'current-user', 'me'])
    return exit_code == 0


def get_bundle_info(target: str = 'dev') -> Optional[Dict[str, str]]:
    """Get bundle deployment information."""
    exit_code, stdout, stderr = run_command([
        'databricks', 'bundle', 'summary', '--target', target
    ])
    
    if exit_code != 0:
        return None
    
    info = {}
    
    # Parse bundle summary for Lakebase instance name
    instance_match = re.search(r'database_instances\.[\w-]+:\s+([\w-]+)', stdout)
    if instance_match:
        info['instance_name'] = instance_match.group(1)
    
    # Parse for catalog name
    catalog_match = re.search(r'database_catalogs\.[\w-]+:\s+([\w-]+)', stdout)
    if catalog_match:
        info['catalog_name'] = catalog_match.group(1)
    
    return info if info else None


def get_lakebase_details(instance_name: str) -> Optional[Dict[str, str]]:
    """Get Lakebase instance details from Databricks."""
    # Try to get instance details using Databricks CLI
    # Note: This requires the Databricks CLI to support database instances
    
    # For now, we'll guide the user to get this from the console
    print(f"\n📝 Please retrieve Lakebase details for instance: {instance_name}")
    print("\nSteps:")
    print("1. Go to Databricks Console → Data → Lakebase")
    print(f"2. Find instance: {instance_name}")
    print("3. Copy the connection details:")
    print("   - Host (format: instance-xyz.database.cloud.databricks.com)")
    print("   - Port (default: 5432)")
    print("   - Database name")
    print()
    
    host = input("Enter Lakebase Host (or press Enter to skip): ").strip()
    if not host:
        return None
    
    port = input("Enter Port [5432]: ").strip() or "5432"
    database = input("Enter Database name [app_database]: ").strip() or "app_database"
    
    return {
        'host': host,
        'port': port,
        'database': database
    }


def main():
    """Main configuration script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Configure Lakebase for local development')
    parser.add_argument('--check-only', action='store_true', help='Only check current status')
    parser.add_argument('--target', default='dev', help='Bundle target (dev or prod)')
    args = parser.parse_args()
    
    print("🔧 Lakebase Local Development Configuration")
    print("=" * 50)
    
    # Check if .env.local exists
    env_local_path = Path('.env.local')
    if not env_local_path.exists():
        print("\n⚠️  .env.local not found")
        if not args.check_only:
            print("📝 Creating .env.local from template...")
            template_path = Path('.env.local.template')
            if template_path.exists():
                import shutil
                shutil.copy(template_path, env_local_path)
                print("✅ Created .env.local - please configure it with your values")
            else:
                print("❌ .env.local.template not found!")
                return 1
    
    # Load current configuration
    env_vars = load_env_file('.env.local')
    
    # Check Lakebase configuration status
    print("\n📊 Current Lakebase Configuration:")
    print(f"  PGHOST: {env_vars.get('PGHOST', '❌ Not set')}")
    print(f"  LAKEBASE_HOST: {env_vars.get('LAKEBASE_HOST', '❌ Not set')}")
    print(f"  LAKEBASE_DATABASE: {env_vars.get('LAKEBASE_DATABASE', '❌ Not set')}")
    print(f"  LAKEBASE_INSTANCE_NAME: {env_vars.get('LAKEBASE_INSTANCE_NAME', '❌ Not set')}")
    print(f"  LAKEBASE_PORT: {env_vars.get('LAKEBASE_PORT', '5432')}")
    
    if args.check_only:
        is_configured = bool(
            (env_vars.get('PGHOST') or env_vars.get('LAKEBASE_HOST')) 
            and env_vars.get('LAKEBASE_DATABASE')
        )
        if is_configured:
            print("\n✅ Lakebase is configured for local development")
            return 0
        else:
            print("\n❌ Lakebase is NOT configured")
            print("\n💡 Run without --check-only to configure")
            return 1
    
    # Check Databricks authentication
    print("\n🔐 Checking Databricks authentication...")
    if not check_databricks_auth():
        print("❌ Not authenticated to Databricks")
        print("💡 Run: databricks auth login")
        return 1
    print("✅ Authenticated")
    
    # Check for deployed bundle
    print(f"\n📦 Checking for deployed bundle (target: {args.target})...")
    bundle_info = get_bundle_info(args.target)
    
    if bundle_info:
        print("✅ Found deployed bundle:")
        for key, value in bundle_info.items():
            print(f"   {key}: {value}")
        
        # Get instance details
        instance_name = bundle_info.get('instance_name')
        if instance_name:
            details = get_lakebase_details(instance_name)
            if details:
                # Update .env.local
                updates = {
                    'PGHOST': details['host'],
                    'LAKEBASE_HOST': details['host'],
                    'LAKEBASE_PORT': details['port'],
                    'LAKEBASE_DATABASE': details['database'],
                    'LAKEBASE_INSTANCE_NAME': instance_name
                }
                
                print(f"\n📝 Updating .env.local...")
                update_env_file('.env.local', updates)
                print("✅ Configuration updated!")
                print("\n💡 Next steps:")
                print("   1. Start the app: ./watch.sh")
                print("   2. The app will use auto-generated OAuth tokens for Lakebase")
                print("   3. Tokens auto-refresh every hour via Databricks SDK")
                return 0
    else:
        print("⚠️  No bundle deployed yet")
        print("\n💡 To deploy Lakebase resources:")
        print("   1. databricks bundle deploy --target dev")
        print("   2. Wait 2-3 minutes for resources to be ready")
        print("   3. Run this script again")
        print("\n📝 Or manually configure .env.local with your Lakebase details")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

