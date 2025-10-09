import os
import uuid
from logging.config import fileConfig
from dotenv import load_dotenv

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config as DatabricksConfig
from sqlalchemy import engine_from_config, event
from sqlalchemy import pool

from alembic import context


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
        cfg = DatabricksConfig(
            host=databricks_host,
            client_id=client_id,
            client_secret=client_secret,
            auth_type="oauth-m2m"  # Explicitly force OAuth to ignore PAT tokens
        )
        return WorkspaceClient(config=cfg)
    
    # Otherwise, let SDK auto-configure (will use single available method)
    return WorkspaceClient()

# Load environment variables from .env.local
load_dotenv(dotenv_path='.env.local')

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url with Databricks SDK configuration
if not config.get_main_option("sqlalchemy.url"):
    app_config = DatabricksConfig()
    # For Lakebase, use client_id (OAuth) or DATABRICKS_USER (PAT) as username
    # The actual token/password is provided via event listener
    postgres_username = app_config.client_id or os.getenv("DATABRICKS_USER") or "token"
    postgres_host = os.getenv("PGHOST") or os.getenv("LAKEBASE_HOST")
    postgres_port = os.getenv("LAKEBASE_PORT", "5432")
    postgres_database = os.getenv("LAKEBASE_DATABASE")
    
    if all([postgres_host, postgres_database]):
        # Connection string format: postgresql+psycopg://<username>:@<host>:<port>/<database>?sslmode=require
        # Password is provided dynamically via event listener
        # SSL is required for Lakebase connections
        connection_string = (
            f"postgresql+psycopg://{postgres_username}:@"
            f"{postgres_host}:{postgres_port}/{postgres_database}?sslmode=require"
        )
        config.set_main_option("sqlalchemy.url", connection_string)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    Uses Databricks SDK for authentication (PAT or OAuth).

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    
    # Set up authentication via event listener
    # Use explicit OAuth configuration to avoid conflicts with PAT tokens
    workspace_client = _create_workspace_client()
    
    # Get Lakebase instance name from host (extract instance UID and look up name)
    lakebase_host = os.getenv("PGHOST") or os.getenv("LAKEBASE_HOST")
    lakebase_database = os.getenv("LAKEBASE_DATABASE")
    
    # Extract instance UID from host and look up the actual instance name
    instance_name = None
    if lakebase_host and "instance-" in lakebase_host:
        # Extract UID from host (format: instance-{uid}.database.cloud.databricks.com)
        instance_uid = lakebase_host.split(".")[0].replace("instance-", "")
        
        # Look up the instance by UID to get the actual name
        try:
            instances = list(workspace_client.database.list_database_instances())
            for inst in instances:
                if inst.uid == instance_uid:
                    instance_name = inst.name
                    break
        except Exception:
            # If lookup fails, fallback to using env var if available
            instance_name = os.getenv("LAKEBASE_INSTANCE_NAME")
    
    @event.listens_for(connectable, "do_connect")
    def provide_token(dialect, conn_rec, cargs, cparams):
        """Provide authentication token for Lakebase using OAuth"""
        # For Lakebase, generate OAuth token using Databricks SDK
        # If LAKEBASE_TOKEN is already an OAuth token, use it directly
        lakebase_token = os.getenv("LAKEBASE_TOKEN")
        
        if lakebase_token and not lakebase_token.startswith("dapi"):
            # Already an OAuth token
            cparams["password"] = lakebase_token
        elif instance_name:
            # Generate OAuth token for Lakebase instance
            try:
                cred = workspace_client.database.generate_database_credential(
                    request_id=str(uuid.uuid4()),
                    instance_names=[instance_name]
                )
                cparams["password"] = cred.token
            except Exception as e:
                # Fallback to LAKEBASE_TOKEN if generation fails
                if lakebase_token:
                    cparams["password"] = lakebase_token
                else:
                    raise Exception(f"Failed to generate Lakebase OAuth token: {e}")
        elif lakebase_token:
            # Use provided token as fallback
            cparams["password"] = lakebase_token
        else:
            raise Exception("No valid Lakebase authentication method available")

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
