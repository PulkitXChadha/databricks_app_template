"""Lakebase Database Connection Module

Provides SQLAlchemy engine with connection pooling for Lakebase (Postgres in Databricks).
Uses Databricks SDK for secure, token-based authentication with automatic token caching.
"""

import os
import uuid
from typing import Generator

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from sqlalchemy import create_engine, Engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool


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
            client_secret=client_secret
        )
        return WorkspaceClient(config=cfg)
    
    # Otherwise, let SDK auto-configure (will use single available method)
    return WorkspaceClient()


def get_lakebase_connection_string() -> str:
    """Build Lakebase connection string using Databricks SDK.
    
    Environment variables:
        PGHOST: Lakebase host (exposed automatically when Lakebase resource is added)
        LAKEBASE_PORT: Database port (default: 5432)
        LAKEBASE_DATABASE: Database name
    
    Returns:
        PostgreSQL connection string for token-based authentication
        
    Raises:
        ValueError: If required environment variables are missing
    """
    # Get client_id from OAuth credentials if available
    client_id = os.getenv('DATABRICKS_CLIENT_ID')
    # For Lakebase, use client_id (OAuth) or DATABRICKS_USER (PAT) as username
    # The actual token/password is provided via event listener
    postgres_username = client_id or os.getenv('DATABRICKS_USER') or "token"
    postgres_host = os.getenv('PGHOST') or os.getenv('LAKEBASE_HOST')
    postgres_port = os.getenv('LAKEBASE_PORT', '5432')
    postgres_database = os.getenv('LAKEBASE_DATABASE')
    
    if not all([postgres_host, postgres_database]):
        missing = []
        if not postgres_host:
            missing.append('PGHOST or LAKEBASE_HOST')
        if not postgres_database:
            missing.append('LAKEBASE_DATABASE')
        raise ValueError(f"Missing required configuration: {', '.join(missing)}")
    
    # Connection string format: postgresql+psycopg://<username>:@<host>:<port>/<database>?sslmode=require
    # Password is provided dynamically via event listener
    # SSL is required for Lakebase connections
    return f"postgresql+psycopg://{postgres_username}:@{postgres_host}:{postgres_port}/{postgres_database}?sslmode=require"


def create_lakebase_engine(
    connection_string: str | None = None,
    pool_size: int = 10,
    max_overflow: int = 10,
    pool_pre_ping: bool = True
) -> Engine:
    """Create SQLAlchemy engine with QueuePool for Lakebase.
    
    Uses Databricks SDK for secure OAuth token authentication. The token is
    automatically cached and refreshed by WorkspaceClient.
    
    Args:
        connection_string: Database connection string (auto-generated if None)
        pool_size: Number of connections to maintain in pool
        max_overflow: Maximum overflow connections beyond pool_size
        pool_pre_ping: Test connections before use to detect stale connections
        
    Returns:
        Configured SQLAlchemy engine with OAuth token authentication
        
    Example:
        engine = create_lakebase_engine(pool_size=10, max_overflow=10)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
    """
    if connection_string is None:
        connection_string = get_lakebase_connection_string()
    
    engine = create_engine(
        connection_string,
        poolclass=QueuePool,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=pool_pre_ping,  # Verify connections before use
        pool_recycle=3600,  # Recycle connections after 1 hour
        echo=False  # Set to True for SQL query logging (debugging)
    )
    
    # Set up authentication via event listener
    # Use explicit OAuth configuration to avoid conflicts with PAT tokens
    workspace_client = _create_workspace_client()
    
    # Get Lakebase instance name
    # Use LAKEBASE_INSTANCE_NAME if provided (logical name from bundle)
    # Otherwise extract from host (but this may not work with SDK)
    instance_name = os.getenv('LAKEBASE_INSTANCE_NAME')
    
    if not instance_name:
        lakebase_host = os.getenv('PGHOST') or os.getenv('LAKEBASE_HOST')
        # Extract instance name from host (format: instance-{id}.database.cloud.databricks.com)
        if lakebase_host and "instance-" in lakebase_host:
            instance_name = lakebase_host.split(".")[0]  # Gets "instance-{id}"
    
    @event.listens_for(engine, "do_connect")
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
    
    return engine


# Global engine instance (lazy-initialized)
_engine: Engine | None = None


def get_engine() -> Engine:
    """Get or create global engine instance.
    
    Returns:
        Global SQLAlchemy engine instance
        
    Raises:
        ValueError: If Lakebase is not configured
        
    Usage:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM user_preferences"))
    """
    global _engine
    if _engine is None:
        # Check if Lakebase is configured before creating engine
        if not is_lakebase_configured():
            raise ValueError(
                "Lakebase is not configured. Please set PGHOST/LAKEBASE_HOST and LAKEBASE_DATABASE environment variables, "
                "or configure a Lakebase resource in your databricks.yml deployment."
            )
        _engine = create_lakebase_engine()
    return _engine


def is_lakebase_configured() -> bool:
    """Check if Lakebase database is configured.
    
    Returns:
        True if Lakebase environment variables are set, False otherwise
    """
    postgres_host = os.getenv('PGHOST') or os.getenv('LAKEBASE_HOST')
    postgres_database = os.getenv('LAKEBASE_DATABASE')
    return bool(postgres_host and postgres_database)


def get_session_factory() -> sessionmaker:
    """Get session factory for ORM operations.
    
    Returns:
        Session factory bound to global engine
        
    Usage:
        SessionFactory = get_session_factory()
        with SessionFactory() as session:
            preferences = session.query(UserPreference).filter_by(user_id=user_id).all()
    """
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session() -> Generator[Session, None, None]:
    """Get database session for dependency injection.
    
    Yields:
        Database session
        
    Usage (FastAPI):
        @app.get("/preferences")
        async def get_preferences(db: Session = Depends(get_db_session)):
            return db.query(UserPreference).all()
    """
    SessionFactory = get_session_factory()
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def test_connection() -> bool:
    """Test Lakebase database connection.
    
    Returns:
        True if connection successful, False otherwise
        
    Usage:
        if test_connection():
            print("Database connection OK")
        else:
            print("Database connection failed")
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"Database connection test failed: {e}")
        return False
