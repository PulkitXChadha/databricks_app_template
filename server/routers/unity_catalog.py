"""Unity Catalog API Router

FastAPI endpoints for Unity Catalog table querying.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Any

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


async def get_current_user_id() -> str:
    """Extract user ID from authentication context.
    
    TODO: Implement proper authentication extraction from Databricks Apps context.
    For now, returns placeholder for development.
    
    Returns:
        User ID string
    """
    # Placeholder - in production, extract from Databricks authentication context
    return "dev-user@example.com"


@router.get("/tables", response_model=list[DataSource])
async def list_tables(
    catalog: str | None = None,
    schema: str | None = None,
    user_id: str = Depends(get_current_user_id)
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
        service = UnityCatalogService()
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


@router.post("/query", response_model=QueryResult)
async def query_table(
    request: QueryTableRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Execute SELECT query on Unity Catalog table.
    
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
    try:
        service = UnityCatalogService()
        result = await service.query_table(
            catalog=request.catalog,
            schema=request.schema,
            table=request.table,
            limit=request.limit,
            offset=request.offset,
            user_id=user_id
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
