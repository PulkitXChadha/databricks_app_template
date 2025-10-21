"""User router for Databricks user information."""

import os

from fastapi import APIRouter, Depends, HTTPException, Request

from server.lib.auth import get_current_user_id, get_user_token
from server.models.user_session import (
    AuthenticationStatusResponse,
    UserInfoResponse,
    UserWorkspaceInfo,
    WorkspaceInfo,
    WorkspaceInfoResponse,
)
from server.services.user_service import UserService

router = APIRouter()


@router.get('/auth/status', response_model=AuthenticationStatusResponse)
async def get_auth_status(request: Request):
    """Get authentication status for the current request.

    Returns information about authentication mode and user identity.
    This endpoint does NOT require authentication - it reports the auth status.
    """
    # Extract auth context from request state (set by middleware)
    user_token = getattr(request.state, 'user_token', None)
    auth_mode = getattr(request.state, 'auth_mode', 'service_principal')

    # If no token, return service principal mode
    if not user_token:
        return AuthenticationStatusResponse(
            authenticated=True,  # Service principal is authenticated
            auth_mode=auth_mode,
            has_user_identity=False,
            user_id=None
        )

    # Try to get user identity
    try:
        service = UserService(user_token=user_token)
        user_identity = await service.get_user_info()
        return AuthenticationStatusResponse(
            authenticated=True,
            auth_mode=auth_mode,
            has_user_identity=True,
            user_id=user_identity.user_id
        )
    except Exception:
        # Token exists but is invalid - still in OBO mode
        return AuthenticationStatusResponse(
            authenticated=True,
            auth_mode=auth_mode,
            has_user_identity=False,
            user_id=None
        )


@router.get('/me', response_model=UserInfoResponse)
async def get_current_user(user_token: str = Depends(get_user_token)):
  """Get current user information from Databricks using OBO authentication.

  Requires X-Forwarded-Access-Token header with valid user access token.

  Returns:
      UserInfoResponse with userName, displayName, active status, and emails

  Raises:
      401: Authentication required (missing or invalid token)
      500: Failed to fetch user info
  """
  try:
    service = UserService(user_token=user_token)
    user_identity = await service.get_user_info()

    return UserInfoResponse(
      userName=user_identity.user_id,
      displayName=user_identity.display_name,
      active=user_identity.active,
      emails=[user_identity.user_id]
    )
  except HTTPException:
    # Re-raise HTTP exceptions (like 401) as-is
    raise
  except Exception as e:
    raise HTTPException(
      status_code=500,
      detail=f'Failed to fetch user info: {str(e)}'
    )


@router.get('/me/workspace', response_model=WorkspaceInfoResponse)
async def get_user_workspace(user_token: str = Depends(get_user_token)):
  """Get workspace information for current user using OBO authentication.

  Requires X-Forwarded-Access-Token header with valid user access token.

  Returns:
      WorkspaceInfoResponse with user and workspace information

  Raises:
      401: Authentication required (missing or invalid token)
  """
  service = UserService(user_token=user_token)
  user_identity = await service.get_user_info()

  # Get workspace info from service (returns WorkspaceInfoResponse from old model)
  workspace_info = await service.get_workspace_info()

  return WorkspaceInfoResponse(
    user=UserWorkspaceInfo(
      userName=user_identity.user_id,
      displayName=user_identity.display_name,
      active=user_identity.active
    ),
    workspace=WorkspaceInfo(
      name=workspace_info.workspace_name,
      url=workspace_info.workspace_url
    )
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
    'headers': dict(request.headers),
    'auth_state': {
      'has_user_token': bool(user_token),
      'token_length': len(user_token) if user_token else 0,
      'token_preview': user_token[:30] + '...' if user_token and len(user_token) > 30 else user_token,
      'user_id': user_id,
      'auth_mode': getattr(request.state, 'auth_mode', 'unknown'),
      'has_user_token_state': getattr(request.state, 'has_user_token', False)
    },
    'environment': {
      'databricks_host': os.getenv('DATABRICKS_HOST', 'not set'),
      'has_databricks_env': bool(os.getenv('DATABRICKS_HOST'))
    }
  }
