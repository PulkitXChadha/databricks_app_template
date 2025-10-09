"""User service for Databricks user operations."""

import os
import logging
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from databricks.sdk.service.iam import User

from server.lib.structured_logger import StructuredLogger

logger = StructuredLogger(__name__)


class UserService:
  """Service for managing Databricks user operations."""

  def __init__(self, user_token: str | None = None):
    """Initialize the user service with Databricks workspace client.
    
    Args:
        user_token: Optional user access token for OBO authorization.
                   If None, uses service principal credentials.
    """
    databricks_host = os.getenv('DATABRICKS_HOST')
    
    if user_token:
      # On-behalf-of-user (OBO) authorization: Use ONLY the user's access token
      if databricks_host:
        # Ensure host has proper format
        if not databricks_host.startswith('http'):
          databricks_host = f'https://{databricks_host}'
        cfg = Config(host=databricks_host, token=user_token)
      else:
        # In Databricks Apps, host is auto-detected
        cfg = Config(token=user_token)
      self.client = WorkspaceClient(config=cfg)
      logger.info("User service initialized with OBO user authorization")
    else:
      # App authorization: Use service principal (OAuth M2M)
      cfg = self._create_service_principal_config()
      self.client = WorkspaceClient(config=cfg)
      logger.info("User service initialized with service principal authorization")

  def _create_service_principal_config(self) -> Config:
    """Create Config for service principal authentication (OAuth M2M).
    
    For Databricks Apps, uses OAuth service principal credentials.
    The auth_type="oauth-m2m" setting ensures only OAuth is used,
    preventing conflicts with PAT tokens in the environment.
    
    Returns:
        Config object with OAuth M2M authentication
    """
    databricks_host = os.getenv('DATABRICKS_HOST')
    client_id = os.getenv('DATABRICKS_CLIENT_ID')
    client_secret = os.getenv('DATABRICKS_CLIENT_SECRET')
    
    # Use OAuth M2M with service principal credentials
    if databricks_host and client_id and client_secret:
      # Explicitly set auth_type to use ONLY OAuth M2M
      # This ignores any PAT tokens in the environment
      return Config(
        host=databricks_host,
        client_id=client_id,
        client_secret=client_secret,
        auth_type="oauth-m2m"
      )
    
    # Fallback for local development (let SDK auto-detect)
    logger.warning(
        "Service principal credentials not found. Using SDK auto-detection. "
        "For Databricks Apps, set DATABRICKS_HOST, DATABRICKS_CLIENT_ID, and DATABRICKS_CLIENT_SECRET."
    )
    if databricks_host:
      return Config(host=databricks_host)
    return Config()

  def get_current_user(self) -> User:
    """Get the current authenticated user."""
    return self.client.current_user.me()

  def get_user_info(self) -> dict:
    """Get formatted user information."""
    user = self.get_current_user()
    return {
      'userName': user.user_name or 'unknown',
      'displayName': user.display_name,
      'active': user.active or False,
      'emails': [email.value for email in (user.emails or [])],
      'groups': [group.display for group in (user.groups or [])],
    }

  def get_user_workspace_info(self) -> dict:
    """Get user workspace information."""
    user = self.get_current_user()

    # Get workspace URL from the client
    workspace_url = self.client.config.host

    return {
      'user': {
        'userName': user.user_name or 'unknown',
        'displayName': user.display_name,
        'active': user.active or False,
      },
      'workspace': {
        'url': workspace_url,
        'deployment_name': workspace_url.split('//')[1].split('.')[0] if workspace_url else None,
      },
    }
