"""Unity Catalog API Router

FastAPI endpoints for Unity Catalog table querying.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Any
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
import os

from server.services.unity_catalog_service import UnityCatalogService
from server.models.data_source import DataSource
from server.models.query_result import QueryResult
from server.lib.structured_logger import StructuredLogger

router = APIRouter()
logger = StructuredLogger(__name__)


# Request/Response models
class QueryTableRequest(BaseModel):
    """Request body for table query."""
    catalog: str = Field(..., description="Catalog name")
    schema: str = Field(..., description="Schema name", alias="schema")
    table: str = Field(..., description="Table name")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum rows")
    offset: int = Field(default=0, ge=0, description="Row offset for pagination")
    filters: dict[str, Any] | None = Field(default=None, description="Optional column filters")
    
    model_config = {
        "populate_by_name": True  # Allow both 'schema' and alias
    }


async def get_user_token(request: Request) -> str | None:
    """Extract user access token from request state.
    
    The token is set by middleware from the x-forwarded-access-token header.
    This enables user authorization (on-behalf-of-user).
    
    Args:
        request: FastAPI request object
        
    Returns:
        User access token or None if not available
    """
    return getattr(request.state, 'user_token', None)


async def get_current_user_id(request: Request) -> str:
    """Extract user ID (email) from authentication context.
    
    In Databricks Apps, extracts the actual user's email from the user token.
    In local development, returns a development user identifier.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User email string
    """
    user_token = await get_user_token(request)
    databricks_host = os.getenv('DATABRICKS_HOST')
    
    # Only try to get user info if we have both token and host (Databricks Apps environment)
    if user_token and databricks_host:
        try:
            # Get user information using the user's access token
            cfg = Config(
                host=databricks_host,
                token=user_token
            )
            client = WorkspaceClient(config=cfg)
            user = client.current_user.me()
            
            # Get user email (primary email)
            user_email = user.user_name or "unknown-user@databricks.com"
            
            logger.info(
                "Retrieved user information from token",
                user_id=user_email,
                display_name=user.display_name
            )
            
            return user_email
            
        except Exception as e:
            logger.warning(
                f"Failed to get user info from token: {str(e)}",
                exc_info=True
            )
            # Fall back to generic identifier
            return "authenticated-user@databricks.com"
    else:
        # Local development mode - return development user identifier
        return "dev-user@example.com"


@router.get("/catalogs", response_model=list[str])
async def list_catalogs(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    user_token: str | None = Depends(get_user_token)
):
    """List accessible Unity Catalog catalogs.
    
    Returns:
        List of catalog names the user has access to
        
    Raises:
        401: Authentication required (EC-003)
        403: Permission denied (EC-004)
        503: Database unavailable (EC-002)
    """
    logger.info(
        "Listing Unity Catalog catalogs",
        user_id=user_id
    )
    
    try:
        service = UnityCatalogService(user_token=user_token)
        catalogs = await service.list_catalogs(user_id=user_id)
        
        logger.info(
            f"Retrieved {len(catalogs)} catalogs",
            user_id=user_id,
            catalog_count=len(catalogs)
        )
        
        return catalogs
        
    except Exception as e:
        logger.error(
            f"Error listing catalogs: {str(e)}",
            exc_info=True,
            user_id=user_id
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "DATABASE_UNAVAILABLE",
                "message": "Database service temporarily unavailable.",
                "technical_details": {"error_type": type(e).__name__},
                "retry_after": 10
            }
        )


@router.get("/schemas", response_model=list[str])
async def list_schemas(
    request: Request,
    catalog: str,
    user_id: str = Depends(get_current_user_id),
    user_token: str | None = Depends(get_user_token)
):
    """List schemas in a Unity Catalog catalog.
    
    Query Parameters:
        catalog: Catalog name
        
    Returns:
        List of schema names in the catalog
        
    Raises:
        401: Authentication required (EC-003)
        403: Permission denied (EC-004)
        503: Database unavailable (EC-002)
    """
    logger.info(
        "Listing Unity Catalog schemas",
        user_id=user_id,
        catalog=catalog
    )
    
    try:
        service = UnityCatalogService(user_token=user_token)
        schemas = await service.list_schemas(
            catalog=catalog,
            user_id=user_id
        )
        
        logger.info(
            f"Retrieved {len(schemas)} schemas from catalog",
            user_id=user_id,
            catalog=catalog,
            schema_count=len(schemas)
        )
        
        return schemas
        
    except PermissionError as e:
        logger.error(
            f"Permission denied: {str(e)}",
            user_id=user_id,
            catalog=catalog
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "CATALOG_PERMISSION_DENIED",
                "message": "You don't have access to this catalog.",
                "technical_details": {
                    "catalog": catalog
                }
            }
        )
    except Exception as e:
        logger.error(
            f"Error listing schemas: {str(e)}",
            exc_info=True,
            user_id=user_id
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "DATABASE_UNAVAILABLE",
                "message": "Database service temporarily unavailable.",
                "technical_details": {"error_type": type(e).__name__},
                "retry_after": 10
            }
        )


@router.get("/table-names", response_model=list[str])
async def list_table_names(
    request: Request,
    catalog: str,
    schema: str,
    user_id: str = Depends(get_current_user_id),
    user_token: str | None = Depends(get_user_token)
):
    """List table names in a Unity Catalog schema.
    
    Query Parameters:
        catalog: Catalog name
        schema: Schema name
        
    Returns:
        List of table names in the schema
        
    Raises:
        401: Authentication required (EC-003)
        403: Permission denied (EC-004)
        503: Database unavailable (EC-002)
    """
    logger.info(
        "Listing Unity Catalog table names",
        user_id=user_id,
        catalog=catalog,
        schema=schema
    )
    
    try:
        service = UnityCatalogService(user_token=user_token)
        table_names = await service.list_table_names(
            catalog=catalog,
            schema=schema,
            user_id=user_id
        )
        
        logger.info(
            f"Retrieved {len(table_names)} tables from schema",
            user_id=user_id,
            catalog=catalog,
            schema=schema,
            table_count=len(table_names)
        )
        
        return table_names
        
    except PermissionError as e:
        logger.error(
            f"Permission denied: {str(e)}",
            user_id=user_id,
            catalog=catalog,
            schema=schema
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "CATALOG_PERMISSION_DENIED",
                "message": "You don't have access to this catalog/schema.",
                "technical_details": {
                    "catalog": catalog,
                    "schema": schema
                }
            }
        )
    except Exception as e:
        logger.error(
            f"Error listing table names: {str(e)}",
            exc_info=True,
            user_id=user_id
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "DATABASE_UNAVAILABLE",
                "message": "Database service temporarily unavailable.",
                "technical_details": {"error_type": type(e).__name__},
                "retry_after": 10
            }
        )


@router.get("/tables", response_model=list[DataSource])
async def list_tables(
    request: Request,
    catalog: str | None = None,
    schema: str | None = None,
    user_id: str = Depends(get_current_user_id),
    user_token: str | None = Depends(get_user_token)
):
    """List accessible Unity Catalog tables.
    
    Query Parameters:
        catalog: Catalog name filter (optional)
        schema: Schema name filter (optional)
        
    Returns:
        List of DataSource objects with table metadata
        
    Raises:
        401: Authentication required (EC-003)
        403: Permission denied (EC-004)
        503: Database unavailable (EC-002)
    """
    try:
        service = UnityCatalogService(user_token=user_token)
        tables = await service.list_tables(
            catalog=catalog,
            schema=schema,
            user_id=user_id
        )
        return tables
        
    except PermissionError as e:
        logger.error(
            f"Permission denied: {str(e)}",
            user_id=user_id,
            catalog=catalog,
            schema=schema
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "CATALOG_PERMISSION_DENIED",
                "message": "You don't have access to this catalog/schema.",
                "technical_details": {
                    "catalog": catalog,
                    "schema": schema
                }
            }
        )
    except Exception as e:
        logger.error(
            f"Error listing tables: {str(e)}",
            exc_info=True,
            user_id=user_id
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "DATABASE_UNAVAILABLE",
                "message": "Database service temporarily unavailable.",
                "technical_details": {"error_type": type(e).__name__},
                "retry_after": 10
            }
        )


@router.get("/query", response_model=QueryResult)
async def query_table_get(
    request: Request,
    catalog: str,
    schema: str,
    table: str,
    limit: int = 100,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
    user_token: str | None = Depends(get_user_token)
):
    """Execute SELECT query on Unity Catalog table (GET method).
    
    Query Parameters:
        catalog: Catalog name
        schema: Schema name
        table: Table name
        limit: Maximum rows (1-1000, default: 100)
        offset: Row offset for pagination (default: 0)
        
    Returns:
        QueryResult with data and execution metadata
        
    Raises:
        400: Invalid query parameters
        403: Permission denied (EC-004)
        404: Table not found
        503: Database unavailable (EC-002)
    """
    logger.info(
        "Querying Unity Catalog table",
        user_id=user_id,
        table=f"{catalog}.{schema}.{table}",
        limit=limit,
        offset=offset
    )
    
    try:
        service = UnityCatalogService(user_token=user_token)
        result = await service.query_table(
            catalog=catalog,
            schema=schema,
            table=table,
            limit=limit,
            offset=offset,
            user_id=user_id
        )
        
        logger.info(
            f"Query completed: {result.get('row_count', 0)} rows returned",
            user_id=user_id,
            table=f"{catalog}.{schema}.{table}",
            row_count=result.get('row_count', 0),
            execution_time_ms=result.get('execution_time_ms', 0)
        )
        
        return result
        
    except ValueError as e:
        # Invalid parameters
        logger.warning(
            f"Invalid query parameters: {str(e)}",
            user_id=user_id
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_QUERY",
                "message": str(e)
            }
        )
    
    except PermissionError as e:
        logger.error(
            f"Permission denied: {str(e)}",
            user_id=user_id,
            table=f"{catalog}.{schema}.{table}"
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "CATALOG_PERMISSION_DENIED",
                "message": "You don't have access to this table.",
                "technical_details": {
                    "catalog": catalog,
                    "schema": schema,
                    "table": table
                }
            }
        )
    
    except Exception as e:
        # Check if table not found
        if "not found" in str(e).lower() or "does not exist" in str(e).lower():
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "TABLE_NOT_FOUND",
                    "message": f"Table {catalog}.{schema}.{table} not found."
                }
            )
        
        logger.error(
            f"Error querying table: {str(e)}",
            exc_info=True,
            user_id=user_id
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "DATABASE_UNAVAILABLE",
                "message": "Database service temporarily unavailable.",
                "technical_details": {"error_type": type(e).__name__},
                "retry_after": 10
            }
        )


@router.post("/query", response_model=QueryResult)
async def query_table_post(
    http_request: Request,
    request: QueryTableRequest,
    user_id: str = Depends(get_current_user_id),
    user_token: str | None = Depends(get_user_token)
):
    """Execute SELECT query on Unity Catalog table (POST method).
    
    Request Body:
        catalog: Catalog name
        schema: Schema name
        table: Table name
        limit: Maximum rows (1-1000, default: 100)
        offset: Row offset for pagination (default: 0)
        filters: Optional column filters
        
    Returns:
        QueryResult with data and execution metadata
        
    Raises:
        400: Invalid query parameters
        403: Permission denied (EC-004)
        404: Table not found
        503: Database unavailable (EC-002)
    """
    logger.info(
        "Querying Unity Catalog table (POST)",
        user_id=user_id,
        table=f"{request.catalog}.{request.schema}.{request.table}",
        limit=request.limit,
        offset=request.offset
    )
    
    try:
        service = UnityCatalogService(user_token=user_token)
        result = await service.query_table(
            catalog=request.catalog,
            schema=request.schema,
            table=request.table,
            limit=request.limit,
            offset=request.offset,
            user_id=user_id
        )
        
        logger.info(
            f"Query completed: {result.get('row_count', 0)} rows returned",
            user_id=user_id,
            table=f"{request.catalog}.{request.schema}.{request.table}",
            row_count=result.get('row_count', 0),
            execution_time_ms=result.get('execution_time_ms', 0)
        )
        
        return result
        
    except ValueError as e:
        # Invalid parameters
        logger.warning(
            f"Invalid query parameters: {str(e)}",
            user_id=user_id
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_QUERY",
                "message": str(e)
            }
        )
    
    except PermissionError as e:
        logger.error(
            f"Permission denied: {str(e)}",
            user_id=user_id,
            table=f"{request.catalog}.{request.schema}.{request.table}"
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "CATALOG_PERMISSION_DENIED",
                "message": "You don't have access to this table.",
                "technical_details": {
                    "catalog": request.catalog,
                    "schema": request.schema,
                    "table": request.table
                }
            }
        )
    
    except Exception as e:
        # Check if table not found
        if "not found" in str(e).lower() or "does not exist" in str(e).lower():
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "TABLE_NOT_FOUND",
                    "message": f"Table {request.catalog}.{request.schema}.{request.table} not found."
                }
            )
        
        logger.error(
            f"Error querying table: {str(e)}",
            exc_info=True,
            user_id=user_id
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "DATABASE_UNAVAILABLE",
                "message": "Database service temporarily unavailable.",
                "technical_details": {"error_type": type(e).__name__},
                "retry_after": 10
            }
        )
