"""Example: Using App and User Authorization in Databricks Apps

This script demonstrates how to query Unity Catalog tables using both:
1. App Authorization (service principal)
2. User Authorization (on-behalf-of-user)

References:
- https://docs.databricks.com/dev-tools/databricks-apps/auth.html
"""

import os

from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

# =============================================================================
# APP AUTHORIZATION (Service Principal)
# =============================================================================


def query_with_app_authorization():
  """Query Unity Catalog using app's service principal.

  Use this for:
  - Background tasks
  - Shared configuration/metadata
  - Operations not tied to specific users

  All users see the same data based on app's permissions.
  """
  print('=' * 60)
  print('APP AUTHORIZATION (Service Principal)')
  print('=' * 60)

  # The WorkspaceClient automatically uses service principal credentials
  # from environment variables:
  # - DATABRICKS_CLIENT_ID (set automatically by Databricks Apps)
  # - DATABRICKS_CLIENT_SECRET (set automatically by Databricks Apps)
  cfg = Config()

  # Connect to SQL warehouse using OAuth
  conn = sql.connect(
    server_hostname=cfg.host,
    http_path=os.getenv('DATABRICKS_HTTP_PATH'),
    credentials_provider=lambda: cfg.authenticate,
  )

  # Query Unity Catalog table
  query = 'SELECT * FROM main.samples.nyctaxi LIMIT 10'

  print(f'Executing query: {query}')
  print('Auth mode: Service Principal')

  with conn.cursor() as cursor:
    cursor.execute(query)
    results = cursor.fetchall_arrow().to_pandas()

    print(f'\nResults: {len(results)} rows')
    print(results.head())

  conn.close()

  return results


# =============================================================================
# USER AUTHORIZATION (On-Behalf-Of-User)
# =============================================================================


def query_with_user_authorization(user_access_token: str):
  """Query Unity Catalog using user's access token.

  Use this for:
  - User-specific queries
  - Fine-grained access control
  - Enforcing Unity Catalog row filters and column masks

  Each user sees data based on their Unity Catalog permissions.

  Args:
      user_access_token: User's access token from x-forwarded-access-token header
  """
  print('\n' + '=' * 60)
  print('USER AUTHORIZATION (On-Behalf-Of-User)')
  print('=' * 60)

  # Get Databricks host
  cfg = Config()

  # Connect to SQL warehouse using user's access token
  conn = sql.connect(
    server_hostname=cfg.host,
    http_path=os.getenv('DATABRICKS_HTTP_PATH'),
    access_token=user_access_token,  # User's token!
  )

  # Query Unity Catalog table
  # Unity Catalog will apply:
  # - Row-level filters (if configured)
  # - Column masks (if configured)
  # - User's SELECT permissions
  query = 'SELECT * FROM main.samples.nyctaxi LIMIT 10'

  print(f'Executing query: {query}')
  print('Auth mode: User Token')

  with conn.cursor() as cursor:
    cursor.execute(query)
    results = cursor.fetchall_arrow().to_pandas()

    print(f'\nResults: {len(results)} rows')
    print(results.head())

  conn.close()

  return results


# =============================================================================
# FASTAPI INTEGRATION EXAMPLES
# =============================================================================


def fastapi_app_authorization_example():
  """Example: FastAPI endpoint using app authorization."""
  from fastapi import APIRouter

  router = APIRouter()

  @router.get('/background-job')
  async def run_background_job():
    """Background job that runs with app's service principal."""
    # No user context needed
    client = WorkspaceClient()  # Uses service principal

    # Query using app's permissions
    cfg = Config()
    conn = sql.connect(
      server_hostname=cfg.host,
      http_path=os.getenv('DATABRICKS_HTTP_PATH'),
      credentials_provider=lambda: cfg.authenticate,
    )

    with conn.cursor() as cursor:
      cursor.execute('SELECT COUNT(*) as total FROM main.samples.nyctaxi')
      result = cursor.fetchone()

    conn.close()

    return {'status': 'complete', 'total_records': result[0]}


def fastapi_user_authorization_example():
  """Example: FastAPI endpoint using user authorization."""
  from fastapi import APIRouter, Depends, Request

  router = APIRouter()

  async def get_user_token(request: Request) -> str | None:
    """Extract user token from request state."""
    return getattr(request.state, 'user_token', None)

  @router.get('/user-query')
  async def query_user_data(request: Request, user_token: str | None = Depends(get_user_token)):
    """Query data with user's permissions."""
    if not user_token:
      return {'error': 'User token not available'}

    # Query using user's token
    cfg = Config()
    conn = sql.connect(
      server_hostname=cfg.host,
      http_path=os.getenv('DATABRICKS_HTTP_PATH'),
      access_token=user_token,  # User's token!
    )

    with conn.cursor() as cursor:
      # Unity Catalog applies user's permissions automatically
      cursor.execute('SELECT * FROM main.samples.nyctaxi LIMIT 100')
      results = cursor.fetchall_arrow().to_pandas()

    conn.close()

    return {'rows': len(results), 'data': results.to_dict('records')}


# =============================================================================
# WORKSPACE CLIENT EXAMPLES
# =============================================================================


def list_catalogs_with_app():
  """List catalogs using app authorization."""
  client = WorkspaceClient()  # Service principal
  catalogs = list(client.catalogs.list())

  print('\nCatalogs (App Authorization):')
  for catalog in catalogs:
    print(f'  - {catalog.name}')

  return catalogs


def list_catalogs_with_user(user_token: str):
  """List catalogs using user authorization."""
  cfg = Config(host=os.getenv('DATABRICKS_HOST'), token=user_token)
  client = WorkspaceClient(config=cfg)  # User token
  catalogs = list(client.catalogs.list())

  print('\nCatalogs (User Authorization):')
  for catalog in catalogs:
    print(f'  - {catalog.name}')

  return catalogs


# =============================================================================
# COMBINED EXAMPLE
# =============================================================================


def combined_authorization_example(user_token: str):
  """Demonstrate using both authorization modes in the same operation.

  Example: Query user-specific data, but log metrics with app identity.
  """
  print('\n' + '=' * 60)
  print('COMBINED AUTHORIZATION EXAMPLE')
  print('=' * 60)

  # 1. Query data with user's permissions
  print('\n1. Querying data with user authorization...')
  cfg = Config()
  user_conn = sql.connect(
    server_hostname=cfg.host, http_path=os.getenv('DATABRICKS_HTTP_PATH'), access_token=user_token
  )

  with user_conn.cursor() as cursor:
    cursor.execute('SELECT * FROM main.samples.nyctaxi LIMIT 100')
    user_results = cursor.fetchall_arrow().to_pandas()

  user_conn.close()
  print(f'   ✓ Retrieved {len(user_results)} rows (user permissions applied)')

  # 2. Log metrics with app's service principal
  print('\n2. Logging metrics with app authorization...')
  app_conn = sql.connect(
    server_hostname=cfg.host,
    http_path=os.getenv('DATABRICKS_HTTP_PATH'),
    credentials_provider=lambda: cfg.authenticate,
  )

  with app_conn.cursor() as cursor:
    # Log to a shared metrics table (app has write access)
    cursor.execute(
      """
            INSERT INTO main.app_metrics.query_logs (
                timestamp, rows_returned, query_type
            ) VALUES (
                current_timestamp(), ?, 'user_query'
            )
        """,
      (len(user_results),),
    )

  app_conn.close()
  print('   ✓ Logged metrics to shared table')

  print('\n✓ Operation complete!')
  print('  - User data: Respects user permissions')
  print('  - App metrics: Uses app permissions')


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
  """
    This script demonstrates authorization modes.
    
    In a real Databricks App:
    - User token comes from: request.headers.get('x-forwarded-access-token')
    - Service principal credentials are automatically injected by Databricks
    """

  print('\nDatabricks App Authorization Examples')
  print('=' * 60)

  # Example 1: App Authorization (always works)
  print('\n[Example 1] Running query with app authorization...')
  try:
    query_with_app_authorization()
    print('✓ Success')
  except Exception as e:
    print(f'✗ Error: {e}')

  # Example 2: User Authorization (requires user token)
  print('\n[Example 2] User authorization example')
  print('Note: This requires a valid user token from x-forwarded-access-token header')
  print('      In production, this is automatically provided by Databricks Apps')

  # In production, you would get this from the request:
  # user_token = request.headers.get('x-forwarded-access-token')

  print('\n' + '=' * 60)
  print('SUMMARY')
  print('=' * 60)
  print("""
    App Authorization:
      - Uses service principal (automatic)
      - Consistent permissions for all users
      - Use for: background jobs, shared data, logging
    
    User Authorization:
      - Uses individual user's token
      - Enforces user-specific Unity Catalog permissions
      - Use for: user queries, fine-grained access control
      
    In FastAPI:
      1. Middleware extracts token: request.state.user_token
      2. Dependency injects token: Depends(get_user_token)
      3. Service uses token: UnityCatalogService(user_token=token)
    """)
