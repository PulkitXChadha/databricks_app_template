"""Lakebase Database Connection Module

Provides SQLAlchemy engine with connection pooling for Lakebase (Postgres in Databricks).
"""

import os
from typing import Generator

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool


def get_lakebase_connection_string() -> str:
    """Build Lakebase connection string from environment variables.
    
    Environment variables:
        LAKEBASE_HOST: Workspace hostname
        LAKEBASE_PORT: Database port (default: 5432)
        LAKEBASE_DATABASE: Database name
        LAKEBASE_TOKEN: Databricks authentication token
    
    Returns:
        PostgreSQL connection string with token authentication
        
    Raises:
        ValueError: If required environment variables are missing
    """
    host = os.getenv('LAKEBASE_HOST')
    port = os.getenv('LAKEBASE_PORT', '5432')
    database = os.getenv('LAKEBASE_DATABASE')
    token = os.getenv('LAKEBASE_TOKEN')
    
    if not all([host, database, token]):
        missing = []
        if not host:
            missing.append('LAKEBASE_HOST')
        if not database:
            missing.append('LAKEBASE_DATABASE')
        if not token:
            missing.append('LAKEBASE_TOKEN')
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    # Connection string format: postgresql+psycopg2://token:<token>@<host>:<port>/<database>
    return f"postgresql+psycopg2://token:{token}@{host}:{port}/{database}"


def create_lakebase_engine(
    connection_string: str | None = None,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_pre_ping: bool = True
) -> Engine:
    """Create SQLAlchemy engine with QueuePool for Lakebase.
    
    Args:
        connection_string: Database connection string (auto-generated if None)
        pool_size: Number of connections to maintain in pool
        max_overflow: Maximum overflow connections beyond pool_size
        pool_pre_ping: Test connections before use to detect stale connections
        
    Returns:
        Configured SQLAlchemy engine
        
    Example:
        engine = create_lakebase_engine(pool_size=5, max_overflow=10)
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
    
    return engine


# Global engine instance (lazy-initialized)
_engine: Engine | None = None


def get_engine() -> Engine:
    """Get or create global engine instance.
    
    Returns:
        Global SQLAlchemy engine instance
        
    Usage:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM user_preferences"))
    """
    global _engine
    if _engine is None:
        _engine = create_lakebase_engine()
    return _engine


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
