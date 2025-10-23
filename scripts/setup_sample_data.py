"""Sample Data Setup Script for Databricks Integrations.

This script creates minimal sample data for:
1. Unity Catalog: Sample table in main.samples.demo_data
2. Lakebase: Sample user preferences records

Run with flags to control what gets created:
- --create-all: Create both Unity Catalog and Lakebase sample data
- --unity-catalog: Create Unity Catalog sample data only
- --lakebase: Create Lakebase sample data only
- --cleanup: Remove sample data (destructive!)
"""

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import click
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import OperationalError

# Load environment variables from .env.local
env_path = Path(__file__).parent.parent / '.env.local'
console = Console()
if env_path.exists():
  load_dotenv(env_path)
  console.print(f'[dim]Loaded environment from {env_path}[/dim]')
else:
  console.print(f'[dim]No .env.local file found at {env_path}, using system environment[/dim]')


def _create_workspace_client() -> WorkspaceClient:
  """Create WorkspaceClient with explicit OAuth configuration.

  This explicitly uses OAuth credentials to avoid conflicts with PAT tokens
  that might be present in the environment.

  Returns:
      WorkspaceClient configured with OAuth or default auth
  """
  databricks_host = os.getenv('DATABRICKS_HOST')
  client_id = os.getenv('DATABRICKS_CLIENT_ID')
  client_secret = os.getenv('DATABRICKS_CLIENT_SECRET')

  # If OAuth credentials are available, use them explicitly
  if databricks_host and client_id and client_secret:
    cfg = Config(
      host=databricks_host,
      client_id=client_id,
      client_secret=client_secret,
      auth_type='oauth-m2m',  # Explicitly force OAuth to ignore PAT tokens
    )
    return WorkspaceClient(config=cfg)

  # Otherwise, let SDK auto-configure (will use single available method)
  return WorkspaceClient()


def get_databricks_oauth_token() -> str:
  """Get OAuth token using Databricks CLI as fallback."""
  try:
    host = os.getenv('DATABRICKS_HOST')
    if not host:
      raise Exception('DATABRICKS_HOST not set')

    # Try to get token using databricks CLI
    cmd = ['databricks', 'auth', 'token', '--host', host.rstrip('/')]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)

    token = result.stdout.strip()
    if token:
      return token
    raise Exception('Empty token returned')

  except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
    raise Exception(f'Failed to get OAuth token via CLI: {e}')


@click.group()
def cli():
  """Sample data setup for Databricks App Template."""
  pass


@cli.command()
@click.option('--catalog', default=None, help='Unity Catalog name (from DATABRICKS_CATALOG)')
@click.option('--schema', default=None, help='Schema name (from DATABRICKS_SCHEMA)')
@click.option('--table', default='demo_data', help='Table name')
@click.option('--rows', default=100, type=int, help='Number of sample rows (max 100)')
def unity_catalog(catalog, schema, table, rows):
  """Create sample table in Unity Catalog."""
  # Get from environment variables if not provided via CLI
  catalog = catalog or os.getenv('DATABRICKS_CATALOG')
  schema = schema or os.getenv('DATABRICKS_SCHEMA')

  if not catalog or not schema:
    console.print('[red]Error: Catalog and schema must be specified[/red]')
    console.print(
      '[yellow]Set DATABRICKS_CATALOG and DATABRICKS_SCHEMA in .env.local or use --catalog and --schema flags[/yellow]'
    )
    sys.exit(1)

  if rows > 100:
    console.print('[yellow]Warning: Limiting rows to 100 as per spec constraint[/yellow]')
    rows = 100

  console.print('\n[bold]Creating Unity Catalog sample data...[/bold]')
  console.print(f'Target: {catalog}.{schema}.{table}')

  try:
    # Initialize Databricks client with explicit OAuth configuration
    client = _create_workspace_client()
    warehouse_id = os.getenv('DATABRICKS_WAREHOUSE_ID')

    if not warehouse_id:
      console.print('[red]Error: DATABRICKS_WAREHOUSE_ID not set in environment[/red]')
      sys.exit(1)

    # Create schema if not exists
    console.print(f'[cyan]1. Creating schema {catalog}.{schema}...[/cyan]')
    client.statement_execution.execute_statement(
      warehouse_id=warehouse_id,
      statement=f'CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}',
    )

    # Create sample table
    console.print(f'[cyan]2. Creating table {catalog}.{schema}.{table}...[/cyan]')
    create_table_sql = f"""
      CREATE TABLE IF NOT EXISTS {catalog}.{schema}.{table} (
        id INT,
        name STRING,
        value DOUBLE,
        category STRING,
        created_at TIMESTAMP
      )
    """
    client.statement_execution.execute_statement(
      warehouse_id=warehouse_id, statement=create_table_sql
    )

    # Insert sample data
    console.print(f'[cyan]3. Inserting {rows} sample rows...[/cyan]')

    # Generate sample data in batches
    categories = ['A', 'B', 'C', 'D', 'E']
    batch_size = 20
    for i in range(0, rows, batch_size):
      batch_rows = min(batch_size, rows - i)
      values = []
      for j in range(batch_rows):
        idx = i + j + 1
        values.append(
          f"({idx}, 'Sample {idx}', {idx * 100.0}, '{categories[idx % len(categories)]}', current_timestamp())"
        )

      insert_sql = f"""
        INSERT INTO {catalog}.{schema}.{table} (id, name, value, category, created_at)
        VALUES {', '.join(values)}
      """
      client.statement_execution.execute_statement(warehouse_id=warehouse_id, statement=insert_sql)

    # Verify data
    console.print('[cyan]4. Verifying data...[/cyan]')
    verify_sql = f'SELECT COUNT(*) as count FROM {catalog}.{schema}.{table}'
    result = client.statement_execution.execute_statement(
      warehouse_id=warehouse_id, statement=verify_sql
    )

    # Display success message
    console.print('\n[green]✓ Unity Catalog sample data created successfully![/green]')
    console.print(f'  Table: {catalog}.{schema}.{table}')
    console.print(f'  Rows: {rows}')

    # Show sample data
    sample_sql = f'SELECT * FROM {catalog}.{schema}.{table} LIMIT 5'
    sample_result = client.statement_execution.execute_statement(
      warehouse_id=warehouse_id, statement=sample_sql
    )

    # Create table for display
    table_display = Table(title='Sample Data Preview')
    table_display.add_column('ID', style='cyan')
    table_display.add_column('Name')
    table_display.add_column('Value', justify='right')
    table_display.add_column('Category')

    # Note: Actual result parsing would depend on SDK response format
    console.print('\n[dim]Sample rows created successfully. Use the app to view data.[/dim]')

  except Exception as e:
    console.print(f'[red]Error creating Unity Catalog sample data: {e}[/red]')
    sys.exit(1)


@cli.command()
@click.option('--num-records', default=5, type=int, help='Number of sample preferences')
def lakebase(num_records):
  """Create sample user preferences in Lakebase."""
  console.print('\n[bold]Creating Lakebase sample data...[/bold]')

  # Get connection parameters
  lakebase_host = os.getenv('PGHOST') or os.getenv('LAKEBASE_HOST')
  lakebase_port = os.getenv('LAKEBASE_PORT', '5432')
  lakebase_database = os.getenv('LAKEBASE_DATABASE')
  # Use DATABRICKS_USER as username, fall back to "token"
  postgres_username = os.getenv('DATABRICKS_USER', 'token')

  if not all([lakebase_host, lakebase_database]):
    console.print('[red]Error: Lakebase environment variables not set[/red]')
    console.print('Required: LAKEBASE_HOST (or PGHOST), LAKEBASE_DATABASE')
    sys.exit(1)

  # Build connection string (password will be provided via event listener)
  connection_string = (
    f'postgresql+psycopg://{postgres_username}:@'
    f'{lakebase_host}:{lakebase_port}/{lakebase_database}?sslmode=require'
  )

  try:
    # Create engine with OAuth token authentication
    console.print('[cyan]1. Connecting to Lakebase...[/cyan]')
    engine = create_engine(
      connection_string,
      pool_pre_ping=True,
      pool_recycle=3600,  # Recycle connections after 1 hour (token expiry)
    )

    # Set up OAuth token authentication with explicit configuration
    workspace_client = _create_workspace_client()

    # Get instance name - prioritize explicit LAKEBASE_INSTANCE_NAME
    # This should be the logical bundle name like 'databricks-app-lakebase-dev'
    # NOT the technical UUID like 'instance-0fac1568-...'
    instance_name = os.getenv('LAKEBASE_INSTANCE_NAME')
    if not instance_name:
      console.print('[yellow]⚠️  LAKEBASE_INSTANCE_NAME not set in .env.local[/yellow]')
      console.print(
        '[yellow]    Using logical name from bundle: databricks-app-lakebase-dev[/yellow]'
      )
      instance_name = 'databricks-app-lakebase-dev'  # Default to dev instance

    @event.listens_for(engine, 'do_connect')
    def provide_token(dialect, conn_rec, cargs, cparams):
      """Provide authentication token for Lakebase using OAuth."""
      lakebase_token = os.getenv('LAKEBASE_TOKEN')

      if lakebase_token and not lakebase_token.startswith('dapi'):
        # Already an OAuth token
        cparams['password'] = lakebase_token
      elif instance_name:
        # Generate OAuth token for Lakebase instance
        try:
          console.print(f'[dim]Generating OAuth token for Lakebase instance: {instance_name}[/dim]')
          cred = workspace_client.database.generate_database_credential(
            request_id=str(uuid.uuid4()), instance_names=[instance_name]
          )
          cparams['password'] = cred.token
        except Exception as e:
          # Fallback to LAKEBASE_TOKEN or CLI OAuth token
          if lakebase_token:
            console.print('[yellow]SDK OAuth generation failed, using LAKEBASE_TOKEN[/yellow]')
            cparams['password'] = lakebase_token
          else:
            try:
              console.print('[yellow]SDK OAuth failed, trying Databricks CLI...[/yellow]')
              cli_token = get_databricks_oauth_token()
              cparams['password'] = cli_token
              console.print('[dim]Using OAuth token from Databricks CLI[/dim]')
            except Exception as cli_error:
              console.print('[red]All authentication methods failed[/red]')
              console.print(f'[red]SDK error: {e}[/red]')
              console.print(f'[red]CLI error: {cli_error}[/red]')
              console.print('[yellow]Tip: Set LAKEBASE_TOKEN manually in .env.local[/yellow]')
              raise Exception('Failed to generate Lakebase OAuth token')
      elif lakebase_token:
        # Use provided token as fallback
        cparams['password'] = lakebase_token
      else:
        raise Exception('No valid Lakebase authentication method available')

    # Verify table exists
    console.print('[cyan]2. Verifying user_preferences table...[/cyan]')
    with engine.connect() as conn:
      result = conn.execute(
        text(
          """
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_name = 'user_preferences'
      """
        )
      )
      if result.scalar() == 0:
        console.print('[yellow]Warning: user_preferences table does not exist[/yellow]')
        console.print('[yellow]Run alembic migrations first: alembic upgrade head[/yellow]')
        sys.exit(1)

    # Insert sample preferences
    console.print(f'[cyan]3. Inserting {num_records} sample preferences...[/cyan]')

    sample_preferences = [
      ('sample_user_1', 'theme', {'mode': 'dark', 'accent_color': 'blue'}),
      ('sample_user_1', 'dashboard_layout', {'widgets': ['chart1', 'table2'], 'columns': 3}),
      (
        'sample_user_2',
        'favorite_tables',
        {'tables': ['main.samples.demo_data', 'main.samples.users']},
      ),
      ('sample_user_2', 'theme', {'mode': 'light', 'accent_color': 'green'}),
      ('sample_user_3', 'dashboard_layout', {'widgets': ['metrics1'], 'columns': 2}),
    ]

    with engine.connect() as conn:
      for i, (user_id, pref_key, pref_value) in enumerate(sample_preferences[:num_records]):
        # Use upsert to avoid conflicts - convert dict to JSON string
        pref_value_json = json.dumps(pref_value)

        conn.execute(
          text(
            """
          INSERT INTO user_preferences (user_id, preference_key, preference_value, created_at, updated_at)
          VALUES (:user_id, :preference_key, CAST(:preference_value AS jsonb), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
          ON CONFLICT (user_id, preference_key) 
          DO UPDATE SET 
            preference_value = EXCLUDED.preference_value,
            updated_at = CURRENT_TIMESTAMP
        """
          ),
          {'user_id': user_id, 'preference_key': pref_key, 'preference_value': pref_value_json},
        )
      conn.commit()

    # Verify data
    console.print('[cyan]4. Verifying data...[/cyan]')
    with engine.connect() as conn:
      result = conn.execute(text('SELECT COUNT(*) FROM user_preferences'))
      count = result.scalar()

    console.print('\n[green]✓ Lakebase sample data created successfully![/green]')
    console.print('  Table: user_preferences')
    console.print(f'  Records: {count}')

  except OperationalError as e:
    console.print(f'[red]Database connection error: {e}[/red]')
    console.print('[yellow]Check your Lakebase credentials and connection settings[/yellow]')
    sys.exit(1)
  except Exception as e:
    console.print(f'[red]Error creating Lakebase sample data: {e}[/red]')
    sys.exit(1)


@cli.command()
@click.option('--catalog', default=None, help='Unity Catalog name (from DATABRICKS_CATALOG)')
@click.option('--schema', default=None, help='Schema name (from DATABRICKS_SCHEMA)')
@click.option('--table', default='demo_data', help='Table name')
@click.option('--uc-rows', default=100, type=int, help='Number of Unity Catalog rows')
@click.option('--lb-records', default=5, type=int, help='Number of Lakebase preferences')
@click.pass_context
def create_all(ctx, catalog, schema, table, uc_rows, lb_records):
  """Create all sample data (Unity Catalog + Lakebase)."""
  # Get from environment variables if not provided via CLI
  catalog = catalog or os.getenv('DATABRICKS_CATALOG')
  schema = schema or os.getenv('DATABRICKS_SCHEMA')

  if not catalog or not schema:
    console.print('[red]Error: Catalog and schema must be specified[/red]')
    console.print(
      '[yellow]Set DATABRICKS_CATALOG and DATABRICKS_SCHEMA in .env.local or use --catalog and --schema flags[/yellow]'
    )
    sys.exit(1)

  console.print('[bold cyan]Creating all sample data...[/bold cyan]\n')

  # Run Unity Catalog setup
  ctx.invoke(unity_catalog, catalog=catalog, schema=schema, table=table, rows=uc_rows)

  # Run Lakebase setup
  ctx.invoke(lakebase, num_records=lb_records)

  console.print('\n[bold green]✓ All sample data created successfully![/bold green]')


@cli.command()
@click.option('--catalog', default=None, help='Unity Catalog name (from DATABRICKS_CATALOG)')
@click.option('--schema', default=None, help='Schema name (from DATABRICKS_SCHEMA)')
@click.option('--table', default='demo_data', help='Table name')
@click.option('--confirm', is_flag=True, help='Skip confirmation prompt')
def cleanup(catalog, schema, table, confirm):
  """Remove sample data (destructive operation!)."""
  # Get from environment variables if not provided via CLI
  catalog = catalog or os.getenv('DATABRICKS_CATALOG')
  schema = schema or os.getenv('DATABRICKS_SCHEMA')

  if not catalog or not schema:
    console.print('[red]Error: Catalog and schema must be specified[/red]')
    console.print(
      '[yellow]Set DATABRICKS_CATALOG and DATABRICKS_SCHEMA in .env.local or use --catalog and --schema flags[/yellow]'
    )
    sys.exit(1)

  if not confirm:
    console.print('[yellow]This will DELETE sample data. Use --confirm flag to proceed.[/yellow]')
    sys.exit(0)

  console.print('[bold red]Cleaning up sample data...[/bold red]\n')

  try:
    # Unity Catalog cleanup
    console.print(f'[cyan]1. Dropping Unity Catalog table {catalog}.{schema}.{table}...[/cyan]')
    client = _create_workspace_client()
    warehouse_id = os.getenv('DATABRICKS_WAREHOUSE_ID')

    if warehouse_id:
      client.statement_execution.execute_statement(
        warehouse_id=warehouse_id, statement=f'DROP TABLE IF EXISTS {catalog}.{schema}.{table}'
      )
      console.print(f'[green]✓ Dropped {catalog}.{schema}.{table}[/green]')

    # Lakebase cleanup
    console.print('[cyan]2. Deleting Lakebase sample preferences...[/cyan]')
    lakebase_host = os.getenv('PGHOST') or os.getenv('LAKEBASE_HOST')
    lakebase_port = os.getenv('LAKEBASE_PORT', '5432')
    lakebase_database = os.getenv('LAKEBASE_DATABASE')
    postgres_username_cleanup = os.getenv('DATABRICKS_USER', 'token')

    if all([lakebase_host, lakebase_database]):
      # Build connection string with OAuth token support
      connection_string = (
        f'postgresql+psycopg://{postgres_username_cleanup}:@'
        f'{lakebase_host}:{lakebase_port}/{lakebase_database}?sslmode=require'
      )
      engine = create_engine(connection_string, pool_recycle=3600)

      # Set up OAuth token authentication with explicit configuration
      workspace_client_cleanup = _create_workspace_client()
      # Use logical bundle name, not technical UUID
      instance_name_cleanup = os.getenv('LAKEBASE_INSTANCE_NAME', 'databricks-app-lakebase-dev')

      @event.listens_for(engine, 'do_connect')
      def provide_cleanup_token(dialect, conn_rec, cargs, cparams):
        """Provide authentication token for Lakebase cleanup."""
        lakebase_token = os.getenv('LAKEBASE_TOKEN')

        if lakebase_token and not lakebase_token.startswith('dapi'):
          cparams['password'] = lakebase_token
        elif instance_name_cleanup:
          try:
            cred = workspace_client_cleanup.database.generate_database_credential(
              request_id=str(uuid.uuid4()), instance_names=[instance_name_cleanup]
            )
            cparams['password'] = cred.token
          except Exception as e:
            if lakebase_token:
              cparams['password'] = lakebase_token
            else:
              raise Exception(f'Failed to generate Lakebase OAuth token: {e}')
        elif lakebase_token:
          cparams['password'] = lakebase_token
        else:
          raise Exception('No valid Lakebase authentication method available')

      with engine.connect() as conn:
        conn.execute(text("DELETE FROM user_preferences WHERE user_id LIKE 'sample_user_%'"))
        conn.commit()
      console.print('[green]✓ Deleted sample preferences[/green]')

    console.print('\n[bold green]✓ Cleanup completed successfully![/bold green]')

  except Exception as e:
    console.print(f'[red]Error during cleanup: {e}[/red]')
    sys.exit(1)


if __name__ == '__main__':
  cli()
