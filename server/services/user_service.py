"""User service for Databricks user operations with OBO-only authentication."""

import os
import logging
import time
from typing import Optional
from fastapi import HTTPException
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from databricks.sdk.service.iam import User

from server.lib.structured_logger import StructuredLogger, log_event
from server.lib.metrics import record_upstream_api_call, record_auth_retry
from server.models.user_session import UserIdentity, InternalWorkspaceInfo

# Import retry decorator after defining logger to avoid circular imports
logger = StructuredLogger(__name__)


class UserService:
  """Service for managing Databricks user operations with OBO-only authentication."""

  def __init__(self, user_token: Optional[str] = None):
    """Initialize the user service with OBO authentication.
    
    Args:
        user_token: User access token (None for service principal mode)
        
    Note:
        If user_token is None, the service will use service principal authentication.
        Methods that require user identity (get_user_info, get_user_id) will raise
        HTTPException(401) if called without a user token.
    """
    self.user_token = user_token
    self.workspace_url = os.getenv('DATABRICKS_HOST', '')
    
    # Log authentication mode selection
    if user_token:
      log_event("auth.mode", context={
        "mode": "obo",
        "auth_type": "pat",
        "service": "UserService"
      })
    else:
      log_event("auth.mode", context={
        "mode": "service_principal",
        "auth_type": "oauth_m2m",
        "service": "UserService"
      })

  def _get_client(self) -> WorkspaceClient:
    """Get WorkspaceClient with appropriate authentication.
    
    Uses user access token (OBO) if available, otherwise service principal.
    
    Returns:
        WorkspaceClient configured with appropriate authentication
    """
    # Ensure DATABRICKS_HOST is set
    if not self.workspace_url:
      raise ValueError("DATABRICKS_HOST environment variable is not set")
    
    # Ensure host has proper format
    host = self.workspace_url if self.workspace_url.startswith('http') else f'https://{self.workspace_url}'
    
    # Create client with or without user token
    if self.user_token:
      # On-Behalf-Of-User Authentication (OBO)
      log_event("service.client_created", context={
        "service_name": "UserService",
        "auth_mode": "obo",
        "auth_type": "pat",
        "has_host": bool(host)
      })
      
      return WorkspaceClient(
        host=host,
        token=self.user_token,
        auth_type="pat"  # REQUIRED: Explicit authentication type
      )
    else:
      # Service Principal Authentication (OAuth M2M)
      log_event("service.client_created", context={
        "service_name": "UserService",
        "auth_mode": "service_principal",
        "auth_type": "oauth_m2m",
        "has_host": bool(host)
      })
      
      # Use OAuth M2M (env vars: DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET)
      return WorkspaceClient(
        host=host
      )

  async def get_user_info(self) -> UserIdentity:
    """Get authenticated user's information from Databricks using OBO authentication.
    
    Returns:
        UserIdentity with user_id (email), display_name, and active status
        
    Raises:
        HTTPException: 401 if authentication fails
    """
    from server.lib.auth import with_auth_retry
    from datetime import datetime
    
    # Track API call timing for metrics
    start_time = time.time()
    
    @with_auth_retry
    async def _fetch_user_info():
      client = self._get_client()
      # Note: This is a blocking call, but wrapped in async for retry compatibility
      import asyncio
      user = await asyncio.to_thread(client.current_user.me)
      return user
    
    try:
      user = await _fetch_user_info()
      
      # Record successful API call metrics
      duration_seconds = time.time() - start_time
      record_upstream_api_call(
        service="databricks",
        operation="get_user_info",
        duration_seconds=duration_seconds
      )
      
      user_identity = UserIdentity(
        user_id=user.user_name or 'unknown@example.com',
        display_name=user.display_name or 'Unknown User',
        active=user.active or False,
        extracted_at=datetime.utcnow()
      )
      
      log_event("auth.user_id_extracted", context={
        "user_id": user_identity.user_id,
        "method": "UserService.get_user_info",
        "duration_ms": duration_seconds * 1000
      })
      
      return user_identity
      
    except Exception as e:
      # Record failed API call metrics
      duration_seconds = time.time() - start_time
      record_upstream_api_call(
        service="databricks",
        operation="get_user_info",
        duration_seconds=duration_seconds
      )
      
      log_event("auth.failed", level="ERROR", context={
        "error_type": type(e).__name__,
        "error_message": str(e),
        "has_token": bool(self.user_token),
        "service": "UserService"
      })
      
      # Return standardized error response
      raise HTTPException(
        status_code=401,
        detail={
          "error_code": "AUTH_USER_IDENTITY_FAILED",
          "message": "User authentication required. Please provide a valid user access token."
        }
      ) from e

  async def get_user_id(self) -> str:
    """Extract user_id for database operations. Returns email address.
    
    This method is specifically for extracting the user_id to use
    in database queries for multi-user data isolation.
    
    Returns:
        User email address (user_id)
        
    Raises:
        HTTPException: 401 if user_token is missing or authentication fails
    """
    if not self.user_token:
      raise HTTPException(
        status_code=401,
        detail="User authentication required"
      )
    
    user_info = await self.get_user_info()
    return user_info.user_id

  async def get_workspace_info(self) -> InternalWorkspaceInfo:
    """Get workspace information using OBO authentication.
    
    Returns:
        InternalWorkspaceInfo with workspace_id, workspace_url, workspace_name
        
    Raises:
        HTTPException: 401 if authentication fails
    """
    from server.lib.auth import with_auth_retry
    
    @with_auth_retry
    async def _fetch_workspace_info():
      client = self._get_client()
      # Get workspace information - using workspace URL from config
      # Note: Not all SDK versions expose workspace metadata directly
      # Fall back to constructing from config
      workspace_url = client.config.host
      
      # Extract workspace name/ID from URL if available
      workspace_name = "Default Workspace"
      workspace_id = "unknown"
      
      if workspace_url:
        # Try to extract deployment name from URL
        try:
          deployment_name = workspace_url.split('//')[1].split('.')[0]
          workspace_name = deployment_name.replace('-', ' ').title()
        except (IndexError, AttributeError):
          pass
      
      return workspace_url, workspace_id, workspace_name
    
    try:
      workspace_url, workspace_id, workspace_name = await _fetch_workspace_info()
      
      return InternalWorkspaceInfo(
        workspace_id=workspace_id,
        workspace_url=workspace_url or self.workspace_url,
        workspace_name=workspace_name
      )
      
    except Exception as e:
      log_event("service.api_call_failed", level="ERROR", context={
        "service_name": "UserService",
        "operation": "get_workspace_info",
        "error_type": type(e).__name__,
        "error_message": str(e)
      })
      raise HTTPException(
        status_code=401,
        detail="Failed to retrieve workspace information"
      ) from e
