"""Lakebase API Router.

FastAPI endpoints for user preferences (Lakebase CRUD operations).
"""

from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from server.lib.auth import get_current_user_id
from server.lib.structured_logger import StructuredLogger
from server.services.lakebase_service import LakebaseService

router = APIRouter()
logger = StructuredLogger(__name__)


# Enums for validation
class PreferenceKey(str, Enum):
    """Allowed preference keys."""
    DASHBOARD_LAYOUT = 'dashboard_layout'
    FAVORITE_TABLES = 'favorite_tables'
    THEME = 'theme'


# Request/Response models
class SavePreferenceRequest(BaseModel):
    """Request body for saving preference."""
    preference_key: PreferenceKey = Field(..., description='Preference category')
    preference_value: dict[str, Any] = Field(..., description='Preference data as JSON')


class UserPreferenceResponse(BaseModel):
    """Response model for user preference."""
    id: int
    user_id: str
    preference_key: str
    preference_value: dict[str, Any]
    created_at: str
    updated_at: str


@router.get('/preferences', response_model=list[UserPreferenceResponse])
async def get_preferences(
    request: Request,
    preference_key: str | None = None,
    user_id: str = Depends(get_current_user_id)
):
    """Get user preferences (user-scoped, data isolated).

    Extracts user_id from OBO token and filters database queries.
    Uses service principal for database connection (per FR-011).

    Query Parameters:
        preference_key: Specific preference key (optional, returns all if omitted)

    Returns:
        List of user preferences

    Raises:
        401: User authentication required
        503: Database unavailable (EC-002)
    """
    logger.info(
        'Getting user preferences',
        user_id=user_id,
        preference_key=preference_key
    )

    try:
        # LakebaseService uses service principal for database connection (FR-011)
        service = LakebaseService()
        preferences = await service.get_preferences(
            user_id=user_id,
            preference_key=preference_key
        )

        logger.info(
            f'Retrieved {len(preferences)} preferences for user',
            user_id=user_id,
            count=len(preferences)
        )

        return preferences

    except ValueError as e:
        # Lakebase not configured
        if 'Lakebase is not configured' in str(e):
            logger.warning(
                f'Lakebase not configured: {str(e)}',
                user_id=user_id
            )
            raise HTTPException(
                status_code=503,
                detail={
                    'error_code': 'LAKEBASE_NOT_CONFIGURED',
                    'message': 'User preferences are not available. Lakebase database is not configured for this deployment.',
                    'technical_details': {
                        'error_type': 'ConfigurationError',
                        'suggestion': 'Configure Lakebase resource in databricks.yml or set PGHOST and LAKEBASE_DATABASE environment variables.'
                    },
                    'retry_after': None
                }
            )
        # Other ValueError
        raise HTTPException(
            status_code=400,
            detail={
                'error_code': 'INVALID_REQUEST',
                'message': str(e)
            }
        )

    except Exception as e:
        logger.error(
            f'Error getting preferences: {str(e)}',
            exc_info=True,
            user_id=user_id
        )
        raise HTTPException(
            status_code=503,
            detail={
                'error_code': 'DATABASE_UNAVAILABLE',
                'message': 'Database service temporarily unavailable.',
                'technical_details': {'error_type': type(e).__name__},
                'retry_after': 10
            }
        )


@router.post('/preferences', response_model=UserPreferenceResponse, status_code=201)
async def save_preference(
    http_request: Request,
    request: SavePreferenceRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Create or update user preference (user-scoped).

    Extracts user_id from OBO token and stores with preference.
    Uses service principal for database connection (per FR-011).

    Request Body:
        preference_key: Preference category (dashboard_layout, favorite_tables, theme)
        preference_value: Preference data as JSON

    Returns:
        Saved preference

    Raises:
        400: Invalid preference data
        401: User authentication required
        503: Database unavailable (EC-002)
    """
    logger.info(
        'Saving user preference',
        user_id=user_id,
        preference_key=request.preference_key.value
    )

    try:
        # LakebaseService uses service principal for database connection (FR-011)
        service = LakebaseService()
        preference = await service.save_preference(
            user_id=user_id,
            preference_key=request.preference_key.value,
            preference_value=request.preference_value
        )

        logger.info(
            'Saved user preference successfully',
            user_id=user_id,
            preference_key=request.preference_key.value
        )

        return preference

    except ValueError as e:
        # Lakebase not configured
        if 'Lakebase is not configured' in str(e):
            logger.warning(
                f'Lakebase not configured: {str(e)}',
                user_id=user_id
            )
            raise HTTPException(
                status_code=503,
                detail={
                    'error_code': 'LAKEBASE_NOT_CONFIGURED',
                    'message': 'User preferences are not available. Lakebase database is not configured for this deployment.',
                    'technical_details': {
                        'error_type': 'ConfigurationError',
                        'suggestion': 'Configure Lakebase resource in databricks.yml or set PGHOST and LAKEBASE_DATABASE environment variables.'
                    },
                    'retry_after': None
                }
            )
        # Other ValueError
        logger.warning(
            f'Invalid preference data: {str(e)}',
            user_id=user_id
        )
        raise HTTPException(
            status_code=400,
            detail={
                'error_code': 'INVALID_PREFERENCE',
                'message': str(e)
            }
        )

    except Exception as e:
        logger.error(
            f'Error saving preference: {str(e)}',
            exc_info=True,
            user_id=user_id
        )
        raise HTTPException(
            status_code=503,
            detail={
                'error_code': 'DATABASE_UNAVAILABLE',
                'message': 'Database service temporarily unavailable.',
                'technical_details': {'error_type': type(e).__name__},
                'retry_after': 10
            }
        )


@router.delete('/preferences/{preference_key}', status_code=204)
async def delete_preference(
    request: Request,
    preference_key: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete user preference (user-scoped).

    Extracts user_id from OBO token to verify ownership.
    Uses service principal for database connection (per FR-011).

    Path Parameters:
        preference_key: Preference key to delete

    Returns:
        204 No Content on success

    Raises:
        401: User authentication required
        404: Preference not found for this user
        503: Database unavailable (EC-002)
    """
    logger.info(
        'Deleting user preference',
        user_id=user_id,
        preference_key=preference_key
    )

    try:
        # LakebaseService uses service principal for database connection (FR-011)
        service = LakebaseService()
        deleted = await service.delete_preference(
            user_id=user_id,
            preference_key=preference_key
        )

        if not deleted:
            logger.warning(
                'Preference not found for deletion',
                user_id=user_id,
                preference_key=preference_key
            )
            raise HTTPException(
                status_code=404,
                detail={
                    'error_code': 'PREFERENCE_NOT_FOUND',
                    'message': f"Preference '{preference_key}' not found for this user."
                }
            )

        logger.info(
            'Deleted user preference successfully',
            user_id=user_id,
            preference_key=preference_key
        )

        return None  # 204 No Content

    except HTTPException:
        raise  # Re-raise 404

    except ValueError as e:
        # Lakebase not configured
        if 'Lakebase is not configured' in str(e):
            logger.warning(
                f'Lakebase not configured: {str(e)}',
                user_id=user_id
            )
            raise HTTPException(
                status_code=503,
                detail={
                    'error_code': 'LAKEBASE_NOT_CONFIGURED',
                    'message': 'User preferences are not available. Lakebase database is not configured for this deployment.',
                    'technical_details': {
                        'error_type': 'ConfigurationError',
                        'suggestion': 'Configure Lakebase resource in databricks.yml or set PGHOST and LAKEBASE_DATABASE environment variables.'
                    },
                    'retry_after': None
                }
            )
        # Other ValueError
        raise HTTPException(
            status_code=400,
            detail={
                'error_code': 'INVALID_REQUEST',
                'message': str(e)
            }
        )

    except Exception as e:
        logger.error(
            f'Error deleting preference: {str(e)}',
            exc_info=True,
            user_id=user_id
        )
        raise HTTPException(
            status_code=503,
            detail={
                'error_code': 'DATABASE_UNAVAILABLE',
                'message': 'Database service temporarily unavailable.',
                'technical_details': {'error_type': type(e).__name__},
                'retry_after': 10
            }
        )
