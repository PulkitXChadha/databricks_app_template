"""Data Source Pydantic Model.

Represents a Unity Catalog table that the application can query.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class AccessLevel(str, Enum):
    """User's access level to a table."""
    READ = 'READ'
    WRITE = 'WRITE'
    NONE = 'NONE'


class ColumnDefinition(BaseModel):
    """Column metadata for a table.

    Attributes:
        name: Column name
        data_type: Column data type (SQL type)
        nullable: Whether column allows NULL values
    """

    name: str = Field(..., description='Column name')
    data_type: str = Field(..., description='SQL data type')
    nullable: bool = Field(default=True, description='NULL allowed')

    model_config = {
        'json_schema_extra': {
            'example': {
                'name': 'customer_id',
                'data_type': 'BIGINT',
                'nullable': False
            }
        }
    }


class DataSource(BaseModel):
    """Unity Catalog table metadata.

    Attributes:
        catalog_name: Unity Catalog name (e.g., 'main')
        schema_name: Schema name within catalog
        table_name: Table name
        columns: List of column definitions
        row_count: Approximate number of rows
        size_bytes: Approximate table size in bytes
        owner: Table owner user/group
        access_level: User's access level
        last_refreshed: When metadata was last fetched
    """

    catalog_name: str = Field(..., pattern=r'^[a-zA-Z0-9_.\-]+$', description='Catalog name')
    schema_name: str = Field(..., pattern=r'^[a-zA-Z0-9_.\-]+$', description='Schema name')
    table_name: str = Field(..., pattern=r'^[a-zA-Z0-9_.\-]+$', description='Table name')
    columns: list[ColumnDefinition] = Field(..., min_length=1, description='Column definitions')
    row_count: int | None = Field(default=None, description='Approximate row count')
    size_bytes: int | None = Field(default=None, description='Approximate size in bytes')
    owner: str = Field(..., description='Table owner')
    access_level: AccessLevel = Field(default=AccessLevel.NONE, description='User access level')
    last_refreshed: datetime = Field(default_factory=datetime.utcnow, description='Metadata refresh time')

    @property
    def full_name(self) -> str:
        """Fully qualified table name: catalog.schema.table."""
        return f'{self.catalog_name}.{self.schema_name}.{self.table_name}'

    @field_validator('access_level')
    @classmethod
    def validate_access(cls, v: AccessLevel) -> AccessLevel:
        """Validate user has access to this table."""
        if v == AccessLevel.NONE:
            raise ValueError('User has no access to this table')
        return v

    @field_validator('columns')
    @classmethod
    def validate_columns(cls, v: list[ColumnDefinition]) -> list[ColumnDefinition]:
        """Validate at least one column exists."""
        if not v:
            raise ValueError('Table must have at least one column')
        return v

    model_config = {
        'json_schema_extra': {
            'example': {
                'catalog_name': 'main',
                'schema_name': 'samples',
                'table_name': 'demo_data',
                'columns': [
                    {'name': 'id', 'data_type': 'INT', 'nullable': False},
                    {'name': 'name', 'data_type': 'STRING', 'nullable': True}
                ],
                'row_count': 1000,
                'size_bytes': 50000,
                'owner': 'data_team',
                'access_level': 'READ',
                'last_refreshed': '2025-10-05T12:00:00Z'
            }
        }
    }
