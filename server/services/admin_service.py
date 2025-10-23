"""Admin privilege checking service for Databricks workspace admin verification.

This service calls the Databricks Workspace API to verify if a user has
workspace admin privileges. Results are cached for 5 minutes to reduce API calls.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from databricks.sdk import WorkspaceClient
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# In-memory cache for admin status (5-minute TTL)
# Structure: {user_id: {"is_admin": bool, "expires_at": datetime}}
_admin_cache: dict[str, dict] = {}


def _get_admin_group_names() -> set[str]:
  """Get the list of admin group names from environment variable.

  Returns:
      Set of admin group names (lowercase for case-insensitive comparison)
  """
  admin_groups_env = os.getenv('ADMIN_GROUPS', 'admins,workspace_admins,administrators')
  return {name.strip().lower() for name in admin_groups_env.split(',')}


async def is_workspace_admin(user_token: str, user_id: str) -> bool:
  """Check if user has Databricks workspace admin privileges.

  This function calls the Databricks Workspace API to check if the user
  is a member of any admin groups. Results are cached for 5 minutes.

  Args:
      user_token: Databricks On-Behalf-Of-User (OBO) token
      user_id: User identifier (email or username)

  Returns:
      True if user is a workspace admin, False otherwise

  Raises:
      HTTPException: 503 Service Unavailable if API call fails
  """
  cache_key = f'admin_check:{user_id}'

  # Check cache first
  if cache_key in _admin_cache:
    cached_result = _admin_cache[cache_key]
    if datetime.utcnow() < cached_result['expires_at']:
      logger.debug(f'Admin check cache hit for user {user_id}: {cached_result["is_admin"]}')
      return cached_result['is_admin']
    else:
      # Cache expired, remove it
      del _admin_cache[cache_key]

  # Call Databricks API
  try:
    logger.info(f'Checking admin status for user {user_id}')
    client = WorkspaceClient(token=user_token)
    current_user = client.current_user.me()

    # Get admin group names from environment
    admin_group_names = _get_admin_group_names()

    # Check if user has workspace admin role
    # Use 'display' field from groups array (case-insensitive)
    user_groups = current_user.groups or []
    is_admin = any(
      group.display.lower() in admin_group_names for group in user_groups if group.display
    )

    # Cache result for 5 minutes
    _admin_cache[cache_key] = {
      'is_admin': is_admin,
      'expires_at': datetime.utcnow() + timedelta(minutes=5),
    }

    logger.info(
      f'Admin check for user {user_id}: {is_admin} '
      f'(groups: {[g.display for g in user_groups if g.display]})'
    )
    return is_admin

  except Exception as e:
    logger.error(f'Failed to check admin status for user {user_id}: {e}', exc_info=True)
    raise HTTPException(
      status_code=503,
      detail={
        'error': 'Service Unavailable',
        'message': 'Unable to verify admin privileges. Please try again later.',
        'status_code': 503,
      },
    ) from e


def is_workspace_admin_sync(user_info: dict) -> bool:
  """Check if user has workspace admin privileges based on user info dict.

  This is a synchronous helper function primarily for testing.
  For production use, prefer the async is_workspace_admin() function.

  Args:
      user_info: User info dict from Databricks API (with 'groups' field)

  Returns:
      True if user is a workspace admin, False otherwise

  Example user_info structure:
      {
          "id": "12345",
          "userName": "user@example.com",
          "groups": [
              {"display": "admins", "value": "group-id"}
          ]
      }
  """
  # Get admin group names from environment
  admin_group_names = _get_admin_group_names()

  # Extract groups from user info
  groups = user_info.get('groups', [])

  # Check if user has any admin group (case-insensitive)
  return any(group.get('display', '').lower() in admin_group_names for group in groups)


async def is_workspace_admin_async(user_token: str, user_id: str) -> bool:
  """Async version: Check if user has Databricks workspace admin privileges.

  This function calls the Databricks Workspace API to check if the user
  is a member of any admin groups. Results are cached for 5 minutes.

  Args:
      user_token: Databricks On-Behalf-Of-User (OBO) token
      user_id: User identifier (email or username)

  Returns:
      True if user is a workspace admin, False otherwise

  Raises:
      HTTPException: 503 Service Unavailable if API call fails
  """
  cache_key = f'admin_check:{user_id}'

  # Check cache first
  if cache_key in _admin_cache:
    cached_result = _admin_cache[cache_key]
    if datetime.utcnow() < cached_result['expires_at']:
      logger.debug(f'Admin check cache hit for user {user_id}: {cached_result["is_admin"]}')
      return cached_result['is_admin']
    else:
      # Cache expired, remove it
      del _admin_cache[cache_key]

  # Call Databricks API
  try:
    logger.info(f'Checking admin status for user {user_id}')
    client = WorkspaceClient(token=user_token)
    current_user = client.current_user.me()

    # Convert to dict format for is_workspace_admin helper
    user_info = {
      'id': current_user.id,
      'userName': current_user.user_name,
      'groups': [
        {'display': group.display, 'value': group.value}
        for group in (current_user.groups or [])
        if group.display
      ],
    }

    # Use synchronous helper to check admin status
    is_admin = is_workspace_admin_sync(user_info)

    # Cache result for 5 minutes
    _admin_cache[cache_key] = {
      'is_admin': is_admin,
      'expires_at': datetime.utcnow() + timedelta(minutes=5),
    }

    logger.info(
      f'Admin check for user {user_id}: {is_admin} '
      f'(groups: {[g["display"] for g in user_info["groups"]]})'
    )
    return is_admin

  except Exception as e:
    logger.error(f'Failed to check admin status for user {user_id}: {e}', exc_info=True)
    raise HTTPException(
      status_code=503,
      detail={
        'error': 'Service Unavailable',
        'message': 'Unable to verify admin privileges. Please try again later.',
        'status_code': 503,
      },
    ) from e


def clear_admin_cache(user_id: Optional[str] = None) -> None:
  """Clear admin cache for a specific user or all users.

  Args:
      user_id: User ID to clear cache for. If None, clears entire cache.
  """
  if user_id:
    cache_key = f'admin_check:{user_id}'
    if cache_key in _admin_cache:
      del _admin_cache[cache_key]
      logger.info(f'Cleared admin cache for user {user_id}')
  else:
    _admin_cache.clear()
    logger.info('Cleared entire admin cache')
