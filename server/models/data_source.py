"""DataSource Pydantic model for Unity Catalog table metadata.

Represents a Unity Catalog table that the application can query.
Source: Unity Catalog managed tables.
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator, computed_field


class AccessLevel(str, Enum):
    """User's access level to a Unity Catalog table."""
    READ = 'READ'
    WRITE = 'WRITE'
    NONE = 'NONE'


class ColumnDefinition(BaseModel):
    """Column metadata for a Unity Catalog table.
    
    Attributes:
        name: Column name
        data_type: Column data type (INT, STRING, DOUBLE, etc.)
        nullable: Whether column allows NULL values
    """
    
    name: str = Field(..., description='Column name')
    data_type: str = Field(..., description='Column data type')
    nullable: bool = Field(default=True, description='Allows NULL values')
    
    class Config:
        json_schema_extra = {
            'example': {
                'name': 'id',
                'data_type': 'INT',
                'nullable': False
            }
        }


class DataSource(BaseModel):
    """Unity Catalog table metadata with access control information.
    
    Attributes:
        catalog_name: Unity Catalog name (e.g., 'main')
        schema_name: Schema name within catalog (e.g., 'samples')
        table_name: Table name (e.g., 'demo_data')
        columns: List of column definitions
        row_count: Approximate number of rows (may be None)
        size_bytes: Approximate table size in bytes (may be None)
        owner: Table owner user or group
        access_level: User's access level to this table
        last_refreshed: When metadata was last fetched
    """
    
    catalog_name: str = Field(
        ...,
        pattern=r'^[a-zA-Z0-9_]+$',
        description='Unity Catalog name'
    )
    schema_name: str = Field(
        ...,
        pattern=r'^[a-zA-Z0-9_]+$',
        description='Schema name'
    )
    table_name: str = Field(
        ...,
        pattern=r'^[a-zA-Z0-9_]+$',
        description='Table name'
    )
    columns: list[ColumnDefinition] = Field(
        ...,
        min_length=1,
        description='Column definitions'
    )
    row_count: int | None = Field(default=None, description='Approximate row count')
    size_bytes: int | None = Field(default=None, description='Approximate size in bytes')
    owner: str = Field(..., description='Table owner')
    access_level: AccessLevel = Field(
        default=AccessLevel.NONE,
        description='User access level'
    )
    last_refreshed: datetime = Field(
        default_factory=datetime.utcnow,
        description='Metadata last fetched'
    )
    
    @computed_field  # type: ignore[misc]
    @property
    def full_name(self) -> str:
        """Fully qualified table name (catalog.schema.table)."""
        return f'{self.catalog_name}.{self.schema_name}.{self.table_name}'
    
    @field_validator('access_level')
    @classmethod
    def validate_access(cls, v: AccessLevel) -> AccessLevel:
        """Ensure user has at least some access to the table."""
        if v == AccessLevel.NONE:
            raise ValueError('User has no access to this table')
        return v
    
    class Config:
        json_schema_extra = {
            'example': {
                'catalog_name': 'main',
                'schema_name': 'samples',
                'table_name': 'demo_data',
                'columns': [
                    {'name': 'id', 'data_type': 'INT', 'nullable': False},
                    {'name': 'name', 'data_type': 'STRING', 'nullable': True}
                ],
                'row_count': 100,
                'size_bytes': 4096,
                'owner': 'user@example.com',
                'access_level': 'READ',
                'last_refreshed': '2025-10-04T12:00:00Z'
            }
        }
