"""User service for Databricks user operations."""

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
from server.models.user_session import UserIdentity, WorkspaceInfoResponse

# Import retry decorator after defining logger to avoid circular imports
logger = StructuredLogger(__name__)


class UserService:
  """Service for managing Databricks user operations."""

  def __init__(self, user_token: Optional[str] = None):
    """Initialize the user service with Databricks workspace client.
    
    Args:
        user_token: Optional user access token for OBO authorization.
                   If None, uses service principal credentials.
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
        "auth_type": "oauth-m2m",
        "service": "UserService"
      })

  def _get_client(self) -> WorkspaceClient:
    """Get WorkspaceClient with appropriate authentication and timeout.
    
    This method implements the dual authentication pattern:
    - Pattern A: Service Principal (when user_token is None)
    - Pattern B: On-Behalf-Of-User (when user_token is provided)
    
    Both patterns include 30-second timeout configuration per NFR-010.
    
    Returns:
        WorkspaceClient configured with correct authentication
    """
    # Configure timeout using SDK's built-in Config class
    config = Config()
    config.timeout = 30  # 30-second timeout per NFR-010
    config.retry_timeout = 30  # Allow full timeout window
    
    if self.user_token:
      # Pattern B: On-Behalf-Of-User Authentication
      log_event("service.client_created", context={
        "service_name": "UserService",
        "auth_mode": "obo",
        "auth_type": "pat"
      })
      
      if self.workspace_url:
        # Ensure host has proper format
        host = self.workspace_url if self.workspace_url.startswith('http') else f'https://{self.workspace_url}'
        return WorkspaceClient(
          host=host,
          token=self.user_token,
          auth_type="pat",  # REQUIRED: Explicit authentication type
          config=config
        )
      else:
        # In Databricks Apps, host is auto-detected
        return WorkspaceClient(
          token=self.user_token,
          auth_type="pat",
          config=config
        )
    else:
      # Pattern A: Service Principal Authentication
      log_event("service.client_created", context={
        "service_name": "UserService",
        "auth_mode": "service_principal",
        "auth_type": "oauth-m2m"
      })
      
      client_id = os.getenv('DATABRICKS_CLIENT_ID')
      client_secret = os.getenv('DATABRICKS_CLIENT_SECRET')
      
      if self.workspace_url and client_id and client_secret:
        # Ensure host has proper format
        host = self.workspace_url if self.workspace_url.startswith('http') else f'https://{self.workspace_url}'
        return WorkspaceClient(
          host=host,
          client_id=client_id,
          client_secret=client_secret,
          auth_type="oauth-m2m",  # REQUIRED: Explicit authentication type
          config=config
        )
      else:
        # Fallback for local development
        logger.warning(
          "Service principal credentials not complete. Using SDK auto-detection. "
          "For Databricks Apps, set DATABRICKS_HOST, DATABRICKS_CLIENT_ID, and DATABRICKS_CLIENT_SECRET."
        )
        if self.workspace_url:
          host = self.workspace_url if self.workspace_url.startswith('http') else f'https://{self.workspace_url}'
          return WorkspaceClient(host=host, config=config)
        return WorkspaceClient(config=config)

  async def get_user_info(self) -> UserIdentity:
    """Get authenticated user's information from Databricks.
    
    Uses OBO authentication when user_token is available,
    falls back to service principal otherwise.
    
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
      raise HTTPException(
        status_code=401,
        detail="Failed to extract user identity"
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

  async def get_workspace_info(self) -> WorkspaceInfoResponse:
    """Get workspace information using OBO or service principal authentication.
    
    This public method encapsulates authentication mode selection internally
    per FR-006a. Routers should call this method directly instead of using
    _get_client() (which is internal).
    
    Returns:
        WorkspaceInfoResponse with workspace_id, workspace_url, workspace_name
        
    Raises:
        HTTPException: 401 if OBO authentication fails
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
      
      return WorkspaceInfoResponse(
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
