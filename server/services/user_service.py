"""User service for Databricks user operations."""

import os
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from databricks.sdk.service.iam import User


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
      # If client initialization fails, create a basic client with explicit OAuth
      # This ensures the service can still instantiate
      import logging
      logging.warning(f"Failed to initialize WorkspaceClient: {e}. Using default client.")
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
      return Config(
        host=databricks_host,
        client_id=client_id,
        client_secret=client_secret
      )
    
    # Otherwise, return empty config and let SDK auto-configure
    # (this will use whatever single method is available)
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
