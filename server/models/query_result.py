"""Query Result Pydantic Model

Represents the result of a Unity Catalog query execution.
"""

from enum import Enum
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Any

from server.models.data_source import DataSource


class QueryStatus(str, Enum):
    """Query execution status."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class QueryResult(BaseModel):
    """Unity Catalog query execution result.
    
    Attributes:
        query_id: Unique identifier for this query
        data_source: The table that was queried
        sql_statement: The SQL query that was executed
        rows: Query result rows (array of dictionaries)
        row_count: Number of rows returned
        execution_time_ms: Query execution time in milliseconds
        user_id: User who executed the query
        executed_at: When query was executed
        status: Query status
        error_message: Error message if query failed
    """
    
    query_id: str = Field(..., min_length=1, description="Unique query identifier")
    data_source: DataSource = Field(..., description="Queried table metadata")
    sql_statement: str = Field(..., min_length=1, description="Executed SQL statement")
    rows: list[dict[str, Any]] = Field(default=[], description="Result rows")
    row_count: int = Field(..., ge=0, description="Number of rows returned")
    execution_time_ms: int = Field(..., gt=0, description="Execution time in milliseconds")
    user_id: str = Field(..., description="User who executed query")
    executed_at: datetime = Field(default_factory=datetime.utcnow, description="Execution timestamp")
    status: QueryStatus = Field(default=QueryStatus.PENDING, description="Query status")
    error_message: str | None = Field(default=None, description="Error message if failed")
    
    @field_validator('sql_statement')
    @classmethod
    def validate_select_only(cls, v: str) -> str:
        """Validate query is SELECT only (no INSERT/UPDATE/DELETE for safety)."""
        normalized = v.strip().upper()
        if not normalized.startswith('SELECT'):
            raise ValueError("Only SELECT queries are allowed")
        
        # Check for dangerous keywords
        dangerous_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE']
        for keyword in dangerous_keywords:
            if keyword in normalized:
                raise ValueError(f"Dangerous SQL keyword '{keyword}' not allowed")
        
        return v
    
    @field_validator('row_count')
    @classmethod
    def validate_row_count(cls, v: int, info) -> int:
        """Validate row_count matches actual rows."""
        if 'rows' in info.data and len(info.data['rows']) != v:
            raise ValueError(f"row_count ({v}) must equal len(rows) ({len(info.data['rows'])})")
        return v
    
    @field_validator('error_message')
    @classmethod
    def validate_error_message(cls, v: str | None, info) -> str | None:
        """Validate error_message is present when status is FAILED."""
        if 'status' in info.data and info.data['status'] == QueryStatus.FAILED and not v:
            raise ValueError("error_message required when status is FAILED")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "query_id": "query-123",
                "data_source": {
                    "catalog_name": "main",
                    "schema_name": "samples",
                    "table_name": "demo_data",
                    "columns": [{"name": "id", "data_type": "INT", "nullable": False}],
                    "owner": "data_team",
                    "access_level": "READ"
                },
                "sql_statement": "SELECT * FROM main.samples.demo_data LIMIT 10",
                "rows": [{"id": 1, "name": "Sample"}],
                "row_count": 1,
                "execution_time_ms": 250,
                "user_id": "user@example.com",
                "executed_at": "2025-10-05T12:00:00Z",
                "status": "SUCCEEDED",
                "error_message": None
            }
        }
    }