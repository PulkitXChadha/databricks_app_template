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
        user_token: Optional user access token for user-specific operations.
                   If None, uses service principal credentials.
    """
    try:
      if user_token:
        # Use user token for user-specific operations
        databricks_host = os.getenv('DATABRICKS_HOST')
        if databricks_host:
          # Ensure host has proper format
          if not databricks_host.startswith('http'):
            databricks_host = f'https://{databricks_host}'
          cfg = Config(host=databricks_host, token=user_token)
          self.client = WorkspaceClient(config=cfg)
        else:
          # In Databricks Apps, host is auto-detected
          # Create client with just the token
          cfg = Config(token=user_token)
          self.client = WorkspaceClient(config=cfg)
      else:
        # Use service principal credentials (OAuth)
        # Explicitly use OAuth to avoid conflict with PAT token in environment
        cfg = self._create_service_principal_config()
        self.client = WorkspaceClient(config=cfg)
    except Exception as e:
      # If client initialization fails due to auth validation warning,
      # suppress it and continue with the configured client
      error_msg = str(e)
      if "more than one authorization method" in error_msg:
        # This is expected in mixed environments (OAuth + CLI auth)
        # The SDK will use the explicitly configured method (OAuth)
        logger.debug(
          "Multiple auth methods detected, using explicitly configured OAuth",
          error=error_msg
        )
        # The client should still have been created successfully despite the validation warning
        # Re-create with the same config to ensure it works
        if user_token:
          databricks_host = os.getenv('DATABRICKS_HOST')
          if databricks_host and not databricks_host.startswith('http'):
            databricks_host = f'https://{databricks_host}'
          cfg = Config(host=databricks_host, token=user_token) if databricks_host else Config(token=user_token)
        else:
          cfg = self._create_service_principal_config()
        self.client = WorkspaceClient(config=cfg)
      else:
        # Genuine error, log and fallback
        logger.warning(
          f"Failed to initialize WorkspaceClient: {error_msg}. Using default client.",
          error=error_msg,
          exc_info=True
        )
        try:
          cfg = self._create_service_principal_config()
          self.client = WorkspaceClient(config=cfg)
        except Exception:
          # Last resort: let SDK auto-configure
          self.client = WorkspaceClient()

  def _create_service_principal_config(self) -> Config:
    """Create Config for service principal authentication (OAuth).
    
    This explicitly uses OAuth credentials to avoid conflicts with PAT tokens
    that might be present in the environment.
    
    Returns:
        Config object with OAuth authentication
    """
    databricks_host = os.getenv('DATABRICKS_HOST')
    client_id = os.getenv('DATABRICKS_CLIENT_ID')
    client_secret = os.getenv('DATABRICKS_CLIENT_SECRET')
    
    # If OAuth credentials are available, use them explicitly
    if databricks_host and client_id and client_secret:
      # Explicitly set token="" to ignore any PAT tokens in environment
      # This prevents "more than one authorization method" errors
      return Config(
        host=databricks_host,
        client_id=client_id,
        client_secret=client_secret,
        token=""  # Explicitly disable PAT authentication
      )
    
    # Otherwise, use host-only config and let SDK auto-detect auth
    # (CLI auth, profile-based auth, etc.)
    logger.warning(
        "OAuth credentials not found, falling back to SDK auto-detection. "
        "Set DATABRICKS_HOST, DATABRICKS_CLIENT_ID, and DATABRICKS_CLIENT_SECRET for explicit OAuth."
    )
    if databricks_host:
      return Config(host=databricks_host)
    # If no host either, return empty config for full auto-detection
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
