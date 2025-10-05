"""User Session Pydantic Model

Represents an authenticated user's interaction session with the application.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime


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
    
    user_id: str = Field(..., min_length=1, description="Unique user identifier")
    user_name: str = Field(..., min_length=1, description="Display name")
    email: EmailStr = Field(..., description="User email address")
    active: bool = Field(default=True, description="Account active status")
    session_token: str = Field(..., min_length=10, description="Session authentication token")
    workspace_url: str = Field(..., description="Databricks workspace URL")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation time")
    expires_at: datetime = Field(..., description="Token expiration time")
    
    @field_validator('workspace_url')
    @classmethod
    def validate_workspace_url(cls, v: str) -> str:
        """Validate workspace URL is a Databricks domain."""
        if not v.startswith('https://') or '.databricks.com' not in v:
            raise ValueError('workspace_url must be a valid Databricks workspace URL')
        return v
    
    @field_validator('expires_at')
    @classmethod
    def validate_expiration(cls, v: datetime, info) -> datetime:
        """Validate expiration is after creation time."""
        if 'created_at' in info.data and v <= info.data['created_at']:
            raise ValueError('expires_at must be after created_at')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "user@example.com",
                "user_name": "John Doe",
                "email": "user@example.com",
                "active": True,
                "session_token": "dapi1234567890abcdef",
                "workspace_url": "https://example.cloud.databricks.com",
                "created_at": "2025-10-05T12:00:00Z",
                "expires_at": "2025-10-05T20:00:00Z"
            }
        }
    }