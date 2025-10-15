"""User router for Databricks user information."""

import os
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional

from server.services.user_service import UserService
from server.lib.auth import get_auth_context, get_user_token, get_current_user_id
from server.models.user_session import (
    AuthenticationStatusResponse,
    AuthenticationContext,
    UserInfoResponse,
    WorkspaceInfoResponse
)

router = APIRouter()


@router.get('/auth/status', response_model=AuthenticationStatusResponse)
async def get_auth_status(auth_context: AuthenticationContext = Depends(get_auth_context)):
    """Get authentication status for the current request (OBO-only).

    Returns information about OBO authentication and user identity.
    """
    return AuthenticationStatusResponse(
        authenticated=True,
        auth_mode="obo",  # OBO-only (hardcoded)
        has_user_identity=auth_context.user_id is not None,
        user_id=auth_context.user_id
    )


@router.get('/me', response_model=UserInfoResponse)
async def get_current_user(user_token: str = Depends(get_user_token)):
  """Get current user information from Databricks using OBO authentication.
  
  Requires X-Forwarded-Access-Token header with valid user access token.
  
  Returns:
      UserInfoResponse with user_id, display_name, active status, and workspace_url
      
  Raises:
      401: Authentication required (missing or invalid token)
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
async def get_user_workspace(user_token: str = Depends(get_user_token)):
  """Get workspace information for current user using OBO authentication.
  
  Requires X-Forwarded-Access-Token header with valid user access token.
  
  Returns:
      WorkspaceInfoResponse with workspace_id, workspace_url, workspace_name
      
  Raises:
      401: Authentication required (missing or invalid token)
  """
  service = UserService(user_token=user_token)
  workspace_info = await service.get_workspace_info()
  
  return WorkspaceInfoResponse(
    workspace_id=workspace_info.workspace_id,
    workspace_url=workspace_info.workspace_url,
    workspace_name=workspace_info.workspace_name
  )


@router.get('/debug/headers')
async def debug_headers(
  request: Request,
  user_token: str = Depends(get_user_token),
  user_id: str = Depends(get_current_user_id)
):
  """Debug endpoint to diagnose authentication header issues.
  
  Returns all request headers and authentication state to help diagnose
  why user tokens might not be extracted correctly.
  
  Returns:
      dict with headers, auth state, and token information
  """
  return {
    "headers": dict(request.headers),
    "auth_state": {
      "has_user_token": bool(user_token),
      "token_length": len(user_token) if user_token else 0,
      "token_preview": user_token[:30] + "..." if user_token and len(user_token) > 30 else user_token,
      "user_id": user_id,
      "auth_mode": getattr(request.state, 'auth_mode', 'unknown'),
      "has_user_token_state": getattr(request.state, 'has_user_token', False)
    },
    "environment": {
      "databricks_host": os.getenv('DATABRICKS_HOST', 'not set'),
      "has_databricks_env": bool(os.getenv('DATABRICKS_HOST'))
    }
  }
