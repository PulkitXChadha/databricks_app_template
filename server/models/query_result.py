"""QueryResult Pydantic model for Unity Catalog query execution results.

Represents the result of a Unity Catalog query execution.
Source: Generated from SQL Warehouse query execution.
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from server.models.data_source import DataSource


class QueryStatus(str, Enum):
    """Query execution status."""
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    SUCCEEDED = 'SUCCEEDED'
    FAILED = 'FAILED'


class QueryResult(BaseModel):
    """Result of a Unity Catalog query execution.
    
    Attributes:
        query_id: Unique identifier for this query
        data_source: The table that was queried
        sql_statement: The SQL query that was executed
        rows: Query result rows (array of dictionaries)
        row_count: Number of rows returned
        execution_time_ms: Query execution time in milliseconds
        user_id: User who executed the query
        executed_at: When query was executed
        status: Query execution status
        error_message: Error message if query failed (optional)
    """
    
    query_id: str = Field(..., min_length=1, description='Unique query identifier')
    data_source: DataSource = Field(..., description='Queried table metadata')
    sql_statement: str = Field(..., min_length=1, description='Executed SQL query')
    rows: list[dict] = Field(default=[], description='Query result rows')
    row_count: int = Field(..., ge=0, description='Number of rows returned')
    execution_time_ms: int = Field(..., gt=0, description='Execution time (ms)')
    user_id: str = Field(..., description='User who executed query')
    executed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description='Query execution timestamp'
    )
    status: QueryStatus = Field(
        default=QueryStatus.PENDING,
        description='Query execution status'
    )
    error_message: str | None = Field(
        default=None,
        description='Error message if failed'
    )
    
    @field_validator('sql_statement')
    @classmethod
    def validate_select_only(cls, v: str) -> str:
        """Ensure only SELECT queries are allowed (safety requirement)."""
        normalized = v.strip().upper()
        if not normalized.startswith('SELECT'):
            raise ValueError('Only SELECT queries are allowed')
        return v
    
    @field_validator('row_count')
    @classmethod
    def validate_row_count_matches(cls, v: int, info) -> int:
        """Ensure row_count matches the length of rows array."""
        if 'rows' in info.data and len(info.data['rows']) != v:
            raise ValueError('row_count must equal len(rows)')
        return v
    
    @field_validator('error_message')
    @classmethod
    def validate_error_message_on_failure(cls, v: str | None, info) -> str | None:
        """Ensure error_message is present when status is FAILED."""
        if 'status' in info.data and info.data['status'] == QueryStatus.FAILED:
            if not v:
                raise ValueError('error_message required when status is FAILED')
        return v
    
    class Config:
        json_schema_extra = {
            'example': {
                'query_id': 'qry_abc123',
                'data_source': {
                    'catalog_name': 'main',
                    'schema_name': 'samples',
                    'table_name': 'demo_data',
                    'access_level': 'READ'
                },
                'sql_statement': 'SELECT * FROM main.samples.demo_data LIMIT 100',
                'rows': [
                    {'id': 1, 'name': 'Sample A'},
                    {'id': 2, 'name': 'Sample B'}
                ],
                'row_count': 2,
                'execution_time_ms': 245,
                'user_id': 'user@example.com',
                'executed_at': '2025-10-04T12:00:00Z',
                'status': 'SUCCEEDED',
                'error_message': None
            }
        }
