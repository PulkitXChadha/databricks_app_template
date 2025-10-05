"""UserSession Pydantic model for authenticated user sessions.

Represents an authenticated user's interaction session with the application.
Source: Derived from Databricks SDK authentication.
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserSession(BaseModel):
    """Authenticated user session model.
    
    Attributes:
        user_id: Unique user identifier from Databricks workspace
        user_name: Display name of the user
        email: Primary email address
        active: Whether user account is active
        session_token: Authentication token for the session
        workspace_url: Databricks workspace URL
        created_at: When session was created
        expires_at: When session token expires
    """
    
    user_id: str = Field(..., min_length=1, description='Unique user identifier')
    user_name: str = Field(..., min_length=1, description='Display name')
    email: EmailStr = Field(..., description='User email address')
    active: bool = Field(default=True, description='Account active status')
    session_token: str = Field(..., min_length=10, description='Auth token')
    workspace_url: str = Field(
        ..., 
        pattern=r'^https://.*\.databricks\.com$',
        description='Databricks workspace URL'
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description='Session creation timestamp'
    )
    expires_at: datetime = Field(..., description='Token expiration timestamp')
    
    @field_validator('expires_at')
    @classmethod
    def validate_expiration(cls, v: datetime, info) -> datetime:
        """Ensure expires_at is after created_at."""
        if 'created_at' in info.data and v <= info.data['created_at']:
            raise ValueError('expires_at must be after created_at')
        return v
    
    class Config:
        json_schema_extra = {
            'example': {
                'user_id': 'user123',
                'user_name': 'John Doe',
                'email': 'john.doe@example.com',
                'active': True,
                'session_token': 'dapi1234567890abcdef',
                'workspace_url': 'https://my-workspace.cloud.databricks.com',
                'created_at': '2025-10-04T12:00:00Z',
                'expires_at': '2025-10-04T18:00:00Z'
            }
        }
