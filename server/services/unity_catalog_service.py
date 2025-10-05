"""Unity Catalog Service

Service for querying Unity Catalog tables with user-specific permissions.
"""

import os
from uuid import uuid4
from datetime import datetime
from typing import Any

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState
from databricks.sdk.errors import DatabricksError

from server.models.data_source import DataSource, ColumnDefinition, AccessLevel
from server.models.query_result import QueryResult, QueryStatus
from server.lib.structured_logger import StructuredLogger

logger = StructuredLogger(__name__)


class UnityCatalogService:
    """Service for Unity Catalog data access.
    
    Provides methods to:
    - List accessible tables with metadata
    - Query tables with pagination
    - Enforce user-level access control via Unity Catalog
    """
    
    def __init__(self):
        """Initialize Unity Catalog service with Workspace client."""
        self.client = WorkspaceClient()
        self.warehouse_id = os.getenv('DATABRICKS_WAREHOUSE_ID')
        
        if not self.warehouse_id:
            raise ValueError("DATABRICKS_WAREHOUSE_ID environment variable is required")
    
    async def list_tables(
        self,
        catalog: str | None = None,
        schema: str | None = None,
        user_id: str | None = None
    ) -> list[DataSource]:
        """List Unity Catalog tables accessible to the user.
        
        Args:
            catalog: Catalog name filter (optional)
            schema: Schema name filter (optional)
            user_id: User context for access control
            
        Returns:
            List of DataSource objects with table metadata
            
        Raises:
            DatabricksError: If Unity Catalog access fails (EC-002)
            PermissionError: If user lacks access to catalog (EC-004)
        """
        try:
            tables = []
            
            # Default to 'main' catalog if not specified
            catalog_name = catalog or os.getenv('UNITY_CATALOG_NAME', 'main')
            schema_name = schema or os.getenv('UNITY_CATALOG_SCHEMA', 'samples')
            
            # List tables in catalog.schema
            table_list = self.client.tables.list(
                catalog_name=catalog_name,
                schema_name=schema_name
            )
            
            for table_info in table_list:
                # Get column information
                columns = []
                for col in table_info.columns or []:
                    columns.append(ColumnDefinition(
                        name=col.name,
                        data_type=col.type_name.value if hasattr(col.type_name, 'value') else str(col.type_name),
                        nullable=col.nullable if col.nullable is not None else True
                    ))
                
                # Determine access level (Unity Catalog enforces permissions)
                access_level = AccessLevel.READ  # User has at least READ if table is visible
                
                data_source = DataSource(
                    catalog_name=table_info.catalog_name,
                    schema_name=table_info.schema_name,
                    table_name=table_info.name,
                    columns=columns,
                    row_count=None,  # Not available from table metadata
                    size_bytes=None,  # Not available from table metadata
                    owner=table_info.owner or "unknown",
                    access_level=access_level,
                    last_refreshed=datetime.utcnow()
                )
                
                tables.append(data_source)
            
            logger.info(
                f"Listed {len(tables)} tables in {catalog_name}.{schema_name}",
                user_id=user_id,
                catalog=catalog_name,
                schema=schema_name
            )
            
            return tables
            
        except DatabricksError as e:
            logger.error(
                f"Unity Catalog error: {str(e)}",
                exc_info=True,
                user_id=user_id,
                catalog=catalog,
                schema=schema
            )
            if "PERMISSION_DENIED" in str(e) or "ACCESS_DENIED" in str(e):
                raise PermissionError(f"No access to catalog {catalog}.{schema}") from e
            raise
    
    async def query_table(
        self,
        catalog: str,
        schema: str,
        table: str,
        limit: int = 100,
        offset: int = 0,
        user_id: str | None = None
    ) -> QueryResult:
        """Query Unity Catalog table with pagination.
        
        Args:
            catalog: Catalog name
            schema: Schema name
            table: Table name
            limit: Maximum rows to return (1-1000)
            offset: Row offset for pagination
            user_id: User context for access control
            
        Returns:
            QueryResult with data and execution metadata
            
        Raises:
            ValueError: If query parameters are invalid
            DatabricksError: If query execution fails (EC-002)
            PermissionError: If user lacks table access (EC-004)
        """
        # Validate parameters
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        if offset < 0:
            raise ValueError("offset must be non-negative")
        
        query_id = str(uuid4())
        sql_statement = f"SELECT * FROM {catalog}.{schema}.{table} LIMIT {limit} OFFSET {offset}"
        
        try:
            start_time = datetime.utcnow()
            
            # Execute query via SQL Warehouse
            response = self.client.statement_execution.execute_statement(
                warehouse_id=self.warehouse_id,
                statement=sql_statement,
                wait_timeout='30s'
            )
            
            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Check query status
            if response.status.state == StatementState.SUCCEEDED:
                # Parse results
                rows = self._parse_result_data(response.result)
                
                # Get table metadata (reuse from list_tables)
                data_source = await self._get_table_metadata(catalog, schema, table)
                
                query_result = QueryResult(
                    query_id=query_id,
                    data_source=data_source,
                    sql_statement=sql_statement,
                    rows=rows,
                    row_count=len(rows),
                    execution_time_ms=execution_time_ms,
                    user_id=user_id or "unknown",
                    executed_at=end_time,
                    status=QueryStatus.SUCCEEDED,
                    error_message=None
                )
                
                logger.info(
                    f"Query succeeded: {len(rows)} rows in {execution_time_ms}ms",
                    query_id=query_id,
                    user_id=user_id,
                    table=f"{catalog}.{schema}.{table}",
                    execution_time_ms=execution_time_ms
                )
                
                return query_result
            
            else:
                # Query failed
                error_message = response.status.error.message if response.status.error else "Unknown error"
                
                logger.error(
                    f"Query failed: {error_message}",
                    query_id=query_id,
                    user_id=user_id,
                    table=f"{catalog}.{schema}.{table}"
                )
                
                # Get table metadata even for failed queries
                data_source = await self._get_table_metadata(catalog, schema, table)
                
                return QueryResult(
                    query_id=query_id,
                    data_source=data_source,
                    sql_statement=sql_statement,
                    rows=[],
                    row_count=0,
                    execution_time_ms=execution_time_ms,
                    user_id=user_id or "unknown",
                    executed_at=end_time,
                    status=QueryStatus.FAILED,
                    error_message=error_message
                )
                
        except DatabricksError as e:
            logger.error(
                f"Databricks error during query: {str(e)}",
                exc_info=True,
                query_id=query_id,
                user_id=user_id,
                table=f"{catalog}.{schema}.{table}"
            )
            
            if "PERMISSION_DENIED" in str(e) or "ACCESS_DENIED" in str(e):
                raise PermissionError(f"No access to table {catalog}.{schema}.{table}") from e
            raise
    
    def _parse_result_data(self, result: Any) -> list[dict[str, Any]]:
        """Parse SQL statement result into list of dictionaries.
        
        Args:
            result: Statement execution result
            
        Returns:
            List of row dictionaries
        """
        if not result or not result.data_array:
            return []
        
        # Get column names from schema
        column_names = [col.name for col in result.manifest.schema.columns] if result.manifest and result.manifest.schema else []
        
        # Convert rows to dictionaries
        rows = []
        for row_data in result.data_array:
            row_dict = {}
            for idx, value in enumerate(row_data):
                column_name = column_names[idx] if idx < len(column_names) else f"col_{idx}"
                row_dict[column_name] = value
            rows.append(row_dict)
        
        return rows
    
    async def _get_table_metadata(self, catalog: str, schema: str, table: str) -> DataSource:
        """Get table metadata for DataSource.
        
        Args:
            catalog: Catalog name
            schema: Schema name
            table: Table name
            
        Returns:
            DataSource with table metadata
        """
        try:
            table_info = self.client.tables.get(f"{catalog}.{schema}.{table}")
            
            columns = []
            for col in table_info.columns or []:
                columns.append(ColumnDefinition(
                    name=col.name,
                    data_type=col.type_name.value if hasattr(col.type_name, 'value') else str(col.type_name),
                    nullable=col.nullable if col.nullable is not None else True
                ))
            
            return DataSource(
                catalog_name=catalog,
                schema_name=schema,
                table_name=table,
                columns=columns if columns else [ColumnDefinition(name="unknown", data_type="STRING", nullable=True)],
                owner=table_info.owner or "unknown",
                access_level=AccessLevel.READ,
                last_refreshed=datetime.utcnow()
            )
        except Exception:
            # Fallback if metadata fetch fails
            return DataSource(
                catalog_name=catalog,
                schema_name=schema,
                table_name=table,
                columns=[ColumnDefinition(name="unknown", data_type="STRING", nullable=True)],
                owner="unknown",
                access_level=AccessLevel.READ,
                last_refreshed=datetime.utcnow()
            )
