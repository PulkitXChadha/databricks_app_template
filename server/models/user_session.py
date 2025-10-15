"""User Session and Authentication Models

Represents authenticated users and their session context.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from enum import Enum


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


class AuthenticationErrorCode(str, Enum):
    """Standardized error codes for authentication failures."""
    AUTH_EXPIRED = "AUTH_EXPIRED"
    AUTH_INVALID = "AUTH_INVALID"
    AUTH_MISSING = "AUTH_MISSING"
    AUTH_USER_IDENTITY_FAILED = "AUTH_USER_IDENTITY_FAILED"
    AUTH_RATE_LIMITED = "AUTH_RATE_LIMITED"
    AUTH_MALFORMED = "AUTH_MALFORMED"


@dataclass
class AuthenticationContext:
    """Authentication context for a single request with OBO-only authentication.

    Contains all authentication-related information for the current request,
    including user token and correlation ID.
    """
    user_token: str  # Required user access token (OBO-only)
    correlation_id: str
    user_id: Optional[str] = None  # Lazy-loaded from user identity extraction


class UserIdentity(BaseModel):
    """User identity extracted from Databricks authentication.

    Represents the authenticated user's identity information
    retrieved from the Databricks workspace.
    """
    user_id: str = Field(..., description="User identifier (email or UUID)")
    display_name: str = Field(..., description="User's display name")
    active: bool = Field(default=True, description="Whether user is active")
    extracted_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When identity was extracted"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "user@example.com",
                "display_name": "Jane Doe",
                "active": True,
                "extracted_at": "2025-10-10T12:34:56Z"
            }
        }
    }


class UserInfoResponse(BaseModel):
    """Response model for /api/user/me endpoint."""
    user_id: str = Field(..., description="User email address")
    display_name: str = Field(..., description="User's display name")
    active: bool = Field(default=True, description="Whether user is active")
    workspace_url: str = Field(..., description="Databricks workspace URL")

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "user@example.com",
                "display_name": "John Doe",
                "active": True,
                "workspace_url": "https://example.cloud.databricks.com"
            }
        }
    }


class WorkspaceInfoResponse(BaseModel):
    """Response model for /api/user/me/workspace endpoint."""
    workspace_id: str = Field(..., description="Workspace identifier")
    workspace_url: str = Field(..., description="Workspace URL")
    workspace_name: str = Field(..., description="Workspace display name")

    model_config = {
        "json_schema_extra": {
            "example": {
                "workspace_id": "1234567890",
                "workspace_url": "https://example.cloud.databricks.com",
                "workspace_name": "Production Workspace"
            }
        }
    }


class AuthenticationStatusResponse(BaseModel):
    """Response model for /api/auth/status endpoint."""
    authenticated: bool = Field(default=True, description="Whether request is authenticated")
    auth_mode: str = Field(..., description="Authentication mode (always 'obo' - OBO-only authentication)")
    has_user_identity: bool = Field(..., description="Whether user identity is available")
    user_id: Optional[str] = Field(None, description="User email if available")

    model_config = {
        "json_schema_extra": {
            "example": {
                "authenticated": True,
                "auth_mode": "obo",
                "has_user_identity": True,
                "user_id": "user@example.com"
            }
        }
    }


class AuthenticationErrorResponse(BaseModel):
    """Error response for authentication failures."""
    detail: str = Field(..., description="Error message")
    error_code: AuthenticationErrorCode = Field(..., description="Standardized error code")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry (for rate limiting)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "User access token has expired",
                "error_code": "AUTH_EXPIRED",
                "retry_after": None
            }
        }
    }