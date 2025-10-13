"""User router for Databricks user information."""

import os
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional

from server.services.user_service import UserService
from server.lib.auth import get_auth_context, get_user_token
from server.models.user_session import (
    AuthenticationStatusResponse,
    AuthenticationContext,
    UserInfoResponse,
    WorkspaceInfoResponse
)

router = APIRouter()


class UserInfo(BaseModel):
  """Databricks user information."""

  userName: str
  displayName: str | None = None
  active: bool
  emails: list[str] = []


class UserWorkspaceInfo(BaseModel):
  """User and workspace information."""

  user: UserInfo
  workspace: dict


@router.get('/auth/status', response_model=AuthenticationStatusResponse)
async def get_auth_status(auth_context: AuthenticationContext = Depends(get_auth_context)):
    """Get authentication status for the current request.

    Returns information about the authentication mode (OBO vs service principal)
    and whether a user identity is available.
    """
    return AuthenticationStatusResponse(
        authenticated=True,
        auth_mode=auth_context.auth_mode,
        has_user_identity=auth_context.user_id is not None,
        user_id=auth_context.user_id
    )


@router.get('/me', response_model=UserInfoResponse)
async def get_current_user(user_token: Optional[str] = Depends(get_user_token)):
  """Get current user information from Databricks.
  
  Uses OBO authentication when X-Forwarded-Access-Token header is present.
  Falls back to service principal if header is missing (for testing only).
  
  Returns:
      UserInfoResponse with user_id, display_name, active status, and workspace_url
  """
  service = UserService(user_token=user_token)
  user_identity = await service.get_user_info()
  
  return UserInfoResponse(
    user_id=user_identity.user_id,
    display_name=user_identity.display_name,
    active=user_identity.active,
    workspace_url=os.environ.get("DATABRICKS_HOST", "")
  )


@router.get('/me/workspace', response_model=WorkspaceInfoResponse)
async def get_user_workspace(user_token: Optional[str] = Depends(get_user_token)):
  """Get workspace information for current user.
  
  Uses OBO authentication to get user-specific workspace details.
  Calls UserService.get_workspace_info() public method per FR-006a.
  
  Returns:
      WorkspaceInfoResponse with workspace_id, workspace_url, workspace_name
  """
  service = UserService(user_token=user_token)
  workspace_info = await service.get_workspace_info()
  
  return WorkspaceInfoResponse(
    workspace_id=workspace_info.workspace_id,
    workspace_url=workspace_info.workspace_url,
    workspace_name=workspace_info.workspace_name
  )
