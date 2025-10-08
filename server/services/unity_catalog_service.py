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
            catalog_name = catalog or os.getenv('DATABRICKS_CATALOG', 'main')
            schema_name = schema or os.getenv('DATABRICKS_SCHEMA', 'samples')
            
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
            
            # Execute COUNT query to get total row count
            count_statement = f"SELECT COUNT(*) as total_count FROM {catalog}.{schema}.{table}"
            total_row_count = None
            
            try:
                count_response = self.client.statement_execution.execute_statement(
                    warehouse_id=self.warehouse_id,
                    statement=count_statement,
                    wait_timeout='30s'
                )
                
                if (hasattr(count_response, 'status') and 
                    count_response.status and 
                    count_response.status.state == StatementState.SUCCEEDED and
                    hasattr(count_response, 'result') and 
                    count_response.result and
                    hasattr(count_response.result, 'data_array') and
                    count_response.result.data_array):
                    # Extract total count from first row
                    total_row_count = int(count_response.result.data_array[0][0])
                    logger.info(f"Total row count for {catalog}.{schema}.{table}: {total_row_count}")
            except Exception as count_error:
                logger.warning(f"Failed to get total row count: {count_error}")
                # Continue without total count - pagination will still work based on returned rows
            
            # Execute query via SQL Warehouse
            response = self.client.statement_execution.execute_statement(
                warehouse_id=self.warehouse_id,
                statement=sql_statement,
                wait_timeout='30s'
            )
            
            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Check query status
            if not hasattr(response, 'status') or not response.status:
                raise AttributeError("Response object missing 'status' attribute")
            
            if response.status.state == StatementState.SUCCEEDED:
                # Parse results and extract column metadata
                result_data = response.result if hasattr(response, 'result') else None
                rows, result_column_names = self._parse_result_data(result_data)
                columns = self._extract_columns_from_result(result_data)
                
                # Get table metadata (reuse from list_tables)
                # Use columns from query result if metadata fetch fails
                data_source = await self._get_table_metadata(catalog, schema, table, fallback_columns=columns)
                
                # If we got generic column names (col_0, col_1, etc) but have proper column definitions,
                # remap the row data to use the correct column names
                if rows and not result_column_names and data_source.columns:
                    logger.info("Remapping generic column names to actual column names from metadata")
                    remapped_rows = []
                    for row in rows:
                        remapped_row = {}
                        for idx, col_def in enumerate(data_source.columns):
                            generic_key = f"col_{idx}"
                            if generic_key in row:
                                remapped_row[col_def.name] = row[generic_key]
                        remapped_rows.append(remapped_row)
                    rows = remapped_rows
                    logger.info(f"Remapped rows to use columns: {[col.name for col in data_source.columns]}")
                
                query_result = QueryResult(
                    query_id=query_id,
                    data_source=data_source,
                    sql_statement=sql_statement,
                    rows=rows,
                    row_count=len(rows),
                    total_row_count=total_row_count,
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
                data_source = await self._get_table_metadata(catalog, schema, table, fallback_columns=None)
                
                return QueryResult(
                    query_id=query_id,
                    data_source=data_source,
                    sql_statement=sql_statement,
                    rows=[],
                    row_count=0,
                    total_row_count=None,
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
    
    def _extract_columns_from_result(self, result: Any) -> list[ColumnDefinition]:
        """Extract column definitions from query result.
        
        Args:
            result: Statement execution result
            
        Returns:
            List of ColumnDefinition objects
        """
        columns = []
        try:
            if result and hasattr(result, 'manifest') and result.manifest:
                if hasattr(result.manifest, 'schema') and result.manifest.schema:
                    if hasattr(result.manifest.schema, 'columns') and result.manifest.schema.columns:
                        for col in result.manifest.schema.columns:
                            # Extract type name - handle both string and object types
                            type_name = "STRING"
                            if hasattr(col, 'type_name'):
                                if hasattr(col.type_name, 'value'):
                                    type_name = col.type_name.value
                                else:
                                    type_name = str(col.type_name)
                            
                            columns.append(ColumnDefinition(
                                name=col.name,
                                data_type=type_name,
                                nullable=True  # Assume nullable for query results
                            ))
        except Exception as e:
            logger.warning(f"Could not extract columns from result: {e}")
        
        return columns
    
    def _parse_result_data(self, result: Any) -> tuple[list[dict[str, Any]], list[str]]:
        """Parse SQL statement result into list of dictionaries and extract column names.
        
        Args:
            result: Statement execution result
            
        Returns:
            Tuple of (rows, column_names)
        """
        try:
            if not result:
                logger.warning("No result object returned from query")
                return [], []
            
            if not hasattr(result, 'data_array') or not result.data_array:
                logger.warning("Result has no data_array or data_array is empty")
                return [], []
            
            # Try multiple ways to get column names
            column_names = []
            
            # Method 1: From manifest.schema.columns
            if hasattr(result, 'manifest') and result.manifest:
                if hasattr(result.manifest, 'schema') and result.manifest.schema:
                    if hasattr(result.manifest.schema, 'columns') and result.manifest.schema.columns:
                        column_names = [col.name for col in result.manifest.schema.columns]
                        logger.info(f"Extracted column names from manifest.schema: {column_names}")
            
            # Method 2: From chunks (alternative path in SDK)
            if not column_names and hasattr(result, 'manifest') and result.manifest:
                if hasattr(result.manifest, 'chunks') and result.manifest.chunks:
                    # Sometimes column info is in chunks
                    logger.info(f"Checking chunks for column info")
            
            if not column_names:
                logger.warning("Could not extract column names from result, will use table metadata order")
            
            # Convert rows to dictionaries
            rows = []
            for row_data in result.data_array:
                row_dict = {}
                for idx, value in enumerate(row_data):
                    column_name = column_names[idx] if idx < len(column_names) else f"col_{idx}"
                    row_dict[column_name] = value
                rows.append(row_dict)
            
            logger.info(f"Parsed {len(rows)} rows with {len(column_names) if column_names else 'generic'} column names")
            
            return rows, column_names
            
        except Exception as e:
            logger.error(
                f"Error parsing result data: {str(e)}",
                exc_info=True
            )
            raise
    
    async def _get_table_metadata(
        self, 
        catalog: str, 
        schema: str, 
        table: str,
        fallback_columns: list[ColumnDefinition] | None = None
    ) -> DataSource:
        """Get table metadata for DataSource.
        
        Args:
            catalog: Catalog name
            schema: Schema name
            table: Table name
            fallback_columns: Columns to use if metadata fetch fails
            
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
                columns=columns if columns else (fallback_columns or [ColumnDefinition(name="unknown", data_type="STRING", nullable=True)]),
                owner=table_info.owner or "unknown",
                access_level=AccessLevel.READ,
                last_refreshed=datetime.utcnow()
            )
        except Exception as e:
            logger.warning(f"Failed to fetch table metadata, using fallback columns: {e}")
            # Fallback if metadata fetch fails - use columns from query result
            return DataSource(
                catalog_name=catalog,
                schema_name=schema,
                table_name=table,
                columns=fallback_columns or [ColumnDefinition(name="unknown", data_type="STRING", nullable=True)],
                owner="unknown",
                access_level=AccessLevel.READ,
                last_refreshed=datetime.utcnow()
            )
