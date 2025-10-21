#!/usr/bin/env python3
"""
Get Lakebase Host Information

This script helps retrieve Lakebase connection details when the automated
deployment process fails to retrieve them.

Usage:
    python scripts/get_lakebase_host.py [--instance-name NAME]
    
Environment Variables:
    TARGET - Environment target (dev or prod), defaults to 'dev'
"""

import json
import subprocess
import sys
import argparse
import os


def run_command(cmd):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def get_database_instances():
    """Get list of database instances."""
    returncode, stdout, stderr = run_command(
        "databricks database list-database-instances --output json"
    )
    
    if returncode != 0:
        print(f"Error listing database instances: {stderr}", file=sys.stderr)
        return None
    
    try:
        data = json.loads(stdout)
        # Handle both list and dict formats
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return data.get('instances', data.get('database_instances', []))
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        return None


def get_warehouses():
    """Get list of SQL warehouses."""
    returncode, stdout, stderr = run_command(
        "databricks warehouses list --output json"
    )
    
    if returncode != 0:
        print(f"Error listing warehouses: {stderr}", file=sys.stderr)
        return None
    
    try:
        data = json.loads(stdout)
        if isinstance(data, dict):
            return data.get('warehouses', data)
        return data
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve Lakebase connection details"
    )
    parser.add_argument(
        '--instance-name',
        help='Lakebase instance name (auto-detected from TARGET if not provided)'
    )
    parser.add_argument(
        '--warehouse-name',
        help='SQL Warehouse name (auto-detected from TARGET if not provided)'
    )
    parser.add_argument(
        '--target',
        default=os.environ.get('TARGET', 'dev'),
        choices=['dev', 'prod'],
        help='Environment target (default: dev)'
    )
    parser.add_argument(
        '--output-format',
        choices=['text', 'env', 'json'],
        default='text',
        help='Output format (default: text)'
    )
    
    args = parser.parse_args()
    
    # Determine resource names based on target
    if args.instance_name:
        instance_name = args.instance_name
    else:
        instance_name = f"databricks-app-lakebase-{args.target}" if args.target == "dev" else "databricks-app-lakebase"
    
    if args.warehouse_name:
        warehouse_name = args.warehouse_name
    else:
        warehouse_name = f"databricks-app-warehouse-{args.target}" if args.target == "dev" else "databricks-app-warehouse"
    
    # Get database instances
    instances = get_database_instances()
    if instances is None:
        print("Failed to retrieve database instances", file=sys.stderr)
        sys.exit(1)
    
    # Find the specific instance
    lakebase_host = None
    lakebase_port = 5432
    lakebase_instance = None
    
    for inst in instances:
        if inst.get('name') == instance_name:
            lakebase_instance = inst
            lakebase_host = inst.get('host', inst.get('hostname', ''))
            break
    
    # Get warehouses
    warehouses = get_warehouses()
    warehouse_id = None
    
    if warehouses:
        for w in warehouses:
            if w.get('name') == warehouse_name:
                warehouse_id = w.get('id', '')
                break
    
    # Output results
    if args.output_format == 'json':
        output = {
            'lakebase_host': lakebase_host,
            'lakebase_port': lakebase_port,
            'lakebase_instance_name': instance_name,
            'lakebase_database': 'app_database',
            'warehouse_id': warehouse_id,
            'warehouse_name': warehouse_name,
            'found_instance': lakebase_instance is not None,
            'found_warehouse': warehouse_id is not None
        }
        print(json.dumps(output, indent=2))
    
    elif args.output_format == 'env':
        if lakebase_host:
            print(f"LAKEBASE_HOST={lakebase_host}")
            print(f"PGHOST={lakebase_host}")
            print(f"LAKEBASE_PORT={lakebase_port}")
            print(f"LAKEBASE_DATABASE=app_database")
            print(f"LAKEBASE_INSTANCE_NAME={instance_name}")
        if warehouse_id:
            print(f"DATABRICKS_WAREHOUSE_ID={warehouse_id}")
    
    else:  # text
        print(f"Looking for resources in '{args.target}' environment...")
        print()
        print("=" * 60)
        print("Lakebase Connection Details")
        print("=" * 60)
        
        if lakebase_instance:
            print(f"✓ Found Lakebase instance: {instance_name}")
            if lakebase_host:
                print(f"  Host:     {lakebase_host}")
                print(f"  Port:     {lakebase_port}")
                print(f"  Database: app_database")
                print()
                print("Add these to your .env.local:")
                print(f"  LAKEBASE_HOST={lakebase_host}")
                print(f"  PGHOST={lakebase_host}")
                print(f"  LAKEBASE_PORT={lakebase_port}")
                print(f"  LAKEBASE_DATABASE=app_database")
                print(f"  LAKEBASE_INSTANCE_NAME={instance_name}")
            else:
                print("  ⚠ Host information not available")
        else:
            print(f"✗ Lakebase instance '{instance_name}' not found")
            print()
            print("Available instances:")
            if instances:
                for inst in instances:
                    print(f"  - {inst.get('name', 'unknown')}")
            else:
                print("  None found")
        
        print()
        print("=" * 60)
        print("SQL Warehouse Details")
        print("=" * 60)
        
        if warehouse_id:
            print(f"✓ Found SQL Warehouse: {warehouse_name}")
            print(f"  ID: {warehouse_id}")
            print()
            print("Add this to your .env.local:")
            print(f"  DATABRICKS_WAREHOUSE_ID={warehouse_id}")
        else:
            print(f"✗ SQL Warehouse '{warehouse_name}' not found")
            print()
            if warehouses:
                print("Available warehouses:")
                for w in warehouses:
                    print(f"  - {w.get('name', 'unknown')} (ID: {w.get('id', 'N/A')})")
        
        print()
    
    # Exit with appropriate code
    if lakebase_host or warehouse_id:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()

