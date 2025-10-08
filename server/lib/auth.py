"""Authentication utilities for FastAPI endpoints.

Provides dependency functions for extracting user information from requests.
"""

import os
from fastapi import Request

from server.services.user_service import UserService
from server.lib.structured_logger import StructuredLogger

logger = StructuredLogger(__name__)


async def get_user_token(request: Request) -> str | None:
    """Extract user access token from request state.
    
    The token is set by middleware from the x-forwarded-access-token header.
    This enables user authorization (on-behalf-of-user).
    
    Args:
        request: FastAPI request object
        
    Returns:
        User access token or None if not available
    """
    return getattr(request.state, 'user_token', None)


async def get_current_user_id(request: Request) -> str:
    """Extract user ID (email) from authentication context.
    
    In Databricks Apps, extracts the actual user's email from the user token.
    In local development, returns a development user identifier.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User email string
    """
    user_token = await get_user_token(request)
    databricks_host = os.getenv('DATABRICKS_HOST')
    
    # Only try to get user info if we have token (Databricks Apps environment)
    if user_token:
        try:
            # Use UserService with user token to get actual user info
            service = UserService(user_token=user_token)
            user_info = service.get_user_info()
            user_email = user_info.get('userName', 'authenticated-user@databricks.com')
            
            logger.info(
                "Retrieved user information from token",
                user_id=user_email,
                display_name=user_info.get('displayName'),
                has_databricks_host=bool(databricks_host)
            )
            
            return user_email
            
        except Exception as e:
            logger.warning(
                f"Failed to get user info from token: {str(e)}",
                exc_info=True,
                has_token=bool(user_token),
                has_databricks_host=bool(databricks_host)
            )
            # Fall back to generic identifier - this ensures app continues working
            return "authenticated-user@databricks.com"
    else:
        # Local development mode - return development user identifier
        logger.info("No user token found, using local development mode")
        return "dev-user@example.com"

