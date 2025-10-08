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
    if user_token:
      # Use user token for user-specific operations
      databricks_host = os.getenv('DATABRICKS_HOST')
      if databricks_host:
        cfg = Config(host=databricks_host, token=user_token)
        self.client = WorkspaceClient(config=cfg)
      else:
        # Fallback to default client in local dev
        self.client = WorkspaceClient()
    else:
      # Use service principal credentials (default)
      self.client = WorkspaceClient()

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
