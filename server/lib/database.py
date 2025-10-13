"""Lakebase Database Connection Module

Provides SQLAlchemy engine with connection pooling for Lakebase (Postgres in Databricks).
Uses Databricks SDK for secure, token-based authentication with automatic token caching.
Supports on-behalf-of-user (OBO) authentication for per-user database access.
"""

import base64
import json
import os
import uuid
from typing import Generator

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from sqlalchemy import create_engine, Engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool


def _create_workspace_client(user_token: str | None = None) -> WorkspaceClient:
    """Create WorkspaceClient with appropriate authentication.
    
    For on-behalf-of-user (OBO) authentication, pass the user's access token.
    For service principal authentication, pass None.
    
    IMPORTANT: When using OBO, we must ONLY use the token parameter to avoid
    conflicts with environment variables (DATABRICKS_CLIENT_ID, etc.) that
    may be present in Databricks Apps deployments.
    
    Args:
        user_token: Optional user access token for OBO authentication
    
    Returns:
        WorkspaceClient configured with appropriate auth
    """
    databricks_host = os.getenv('DATABRICKS_HOST')
    
    # On-behalf-of-user authentication: Use ONLY the user token
    # We MUST explicitly set auth_type="pat" to prevent SDK from detecting OAuth env vars
    if user_token:
        if databricks_host:
            if not databricks_host.startswith('http'):
                databricks_host = f'https://{databricks_host}'
            # Use auth_type="pat" to force token-only auth and ignore OAuth env vars
            cfg = Config(
                host=databricks_host,
                token=user_token,
                auth_type="pat"  # Forces SDK to use ONLY the token, ignoring OAuth env vars
            )
        else:
            # In Databricks Apps, host is auto-detected
            cfg = Config(
                token=user_token,
                auth_type="pat"  # Forces SDK to use ONLY the token, ignoring OAuth env vars
            )
        return WorkspaceClient(config=cfg)
    
    # Service principal authentication: Use OAuth M2M (app-level access)
    # Only use when OBO token is not available
    client_id = os.getenv('DATABRICKS_CLIENT_ID')
    client_secret = os.getenv('DATABRICKS_CLIENT_SECRET')
    
    if databricks_host and client_id and client_secret:
        cfg = Config(
            host=databricks_host,
            client_id=client_id,
            client_secret=client_secret,
            auth_type="oauth-m2m"  # Explicit OAuth, ignores PAT tokens in env
        )
        return WorkspaceClient(config=cfg)
    
    # Fallback: Let SDK auto-configure (local development)
    return WorkspaceClient()


def _extract_username_from_token(token: str) -> str:
    """Extract username from JWT token's 'sub' field.
    
    Args:
        token: JWT token string
        
    Returns:
        Username (email) from token's subject claim
        
    Raises:
        Exception: If token cannot be decoded
    """
    try:
        # JWT format: header.payload.signature
        parts = token.split('.')
        if len(parts) < 2:
            raise ValueError("Invalid JWT format")
        
        # Decode payload (add padding if needed)
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        payload_data = json.loads(decoded)
        
        # Extract subject (username/email)
        username = payload_data.get('sub')
        if not username:
            raise ValueError("No 'sub' field in JWT token")
        
        return username
    except Exception as e:
        raise Exception(f"Failed to extract username from token: {e}")


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
    
    Note:
        The username is extracted from the OAuth token's 'sub' field.
        The connection string uses a placeholder username that will be
        replaced when the actual connection is made with the token.
    """
    # Use a placeholder username - will be replaced with actual username from token
    # The event listener will extract the real username from the JWT token
    postgres_username = "placeholder"
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
    # Username and password are provided dynamically via event listener
    # SSL is required for Lakebase connections
    return f"postgresql+psycopg://{postgres_username}:@{postgres_host}:{postgres_port}/{postgres_database}?sslmode=require"


def create_lakebase_engine(
    connection_string: str | None = None,
    pool_size: int = 10,
    max_overflow: int = 10,
    pool_pre_ping: bool = True,
    user_token: str | None = None
) -> Engine:
    """Create SQLAlchemy engine with QueuePool for Lakebase.
    
    Uses Databricks SDK for secure token authentication. The token is
    automatically cached and refreshed by WorkspaceClient.
    
    Args:
        connection_string: Database connection string (auto-generated if None)
        pool_size: Number of connections to maintain in pool
        max_overflow: Maximum overflow connections beyond pool_size
        pool_pre_ping: Test connections before use to detect stale connections
        user_token: Optional user access token for OBO authentication
        
    Returns:
        Configured SQLAlchemy engine with token authentication
        
    Example:
        # Service principal (app-level)
        engine = create_lakebase_engine(pool_size=10, max_overflow=10)
        
        # On-behalf-of-user (per-user)
        engine = create_lakebase_engine(user_token=user_access_token)
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
    # Use OBO token if provided, otherwise use service principal
    workspace_client = _create_workspace_client(user_token=user_token)
    
    # Get Lakebase instance name
    # Use LAKEBASE_INSTANCE_NAME if provided (logical name from bundle)
    # Otherwise extract from host
    instance_name = os.getenv('LAKEBASE_INSTANCE_NAME')
    
    if not instance_name:
        lakebase_host = os.getenv('PGHOST') or os.getenv('LAKEBASE_HOST')
        # Extract instance name from host (format: instance-{id}.database.cloud.databricks.com)
        if lakebase_host and "instance-" in lakebase_host:
            instance_name = lakebase_host.split(".")[0]  # Gets "instance-{id}"
    
    @event.listens_for(engine, "do_connect")
    def provide_token(dialect, conn_rec, cargs, cparams):
        """Provide authentication token and username for Lakebase.
        
        For OBO: Uses user's token to generate database credentials
        For service principal: Uses app credentials to generate database credentials
        
        The username is extracted from the JWT token's 'sub' field.
        """
        # For Lakebase, generate database credential using SDK
        # If LAKEBASE_TOKEN is already a valid token, use it directly
        lakebase_token = os.getenv("LAKEBASE_TOKEN")
        token_to_use = None
        
        if lakebase_token and not lakebase_token.startswith("dapi"):
            # Already a valid OAuth token
            token_to_use = lakebase_token
        elif instance_name:
            # Generate database credential for Lakebase instance
            try:
                cred = workspace_client.database.generate_database_credential(
                    request_id=str(uuid.uuid4()),
                    instance_names=[instance_name]
                )
                token_to_use = cred.token
            except Exception as e:
                # Fallback to LAKEBASE_TOKEN if generation fails
                if lakebase_token:
                    token_to_use = lakebase_token
                else:
                    raise Exception(f"Failed to generate Lakebase database credential: {e}")
        elif lakebase_token:
            # Use provided token as fallback
            token_to_use = lakebase_token
        else:
            raise Exception("No valid Lakebase authentication method available. Set LAKEBASE_INSTANCE_NAME or LAKEBASE_TOKEN.")
        
        # Extract username from token and set credentials
        if token_to_use:
            try:
                username = _extract_username_from_token(token_to_use)
                cparams["user"] = username
                cparams["password"] = token_to_use
            except Exception as e:
                # If username extraction fails, try with the token as-is
                # (for backwards compatibility or different token formats)
                raise Exception(f"Failed to extract username from token: {e}")
    
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
    """Get database session for dependency injection (service principal auth).
    
    Yields:
        Database session using app credentials
        
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


def get_db_session_obo(user_token: str) -> Generator[Session, None, None]:
    """Get database session with OBO authentication for dependency injection.
    
    Creates a session using the user's access token for per-user database access.
    Each user's session uses their own credentials.
    
    Args:
        user_token: User's access token from X-Forwarded-Access-Token header
    
    Yields:
        Database session using user credentials
        
    Usage (FastAPI):
        @app.get("/preferences")
        async def get_preferences(
            user_token: str = Depends(get_user_token),
            db: Session = Depends(lambda token=user_token: get_db_session_obo(token))
        ):
            return db.query(UserPreference).all()
    """
    # Create engine with user token (not cached globally)
    engine = create_lakebase_engine(user_token=user_token)
    SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        # Dispose engine after use (since it's per-user)
        engine.dispose()


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
