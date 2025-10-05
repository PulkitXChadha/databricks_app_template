"""Lakebase API Router

FastAPI endpoints for user preferences (Lakebase CRUD operations).
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Any
from enum import Enum

from server.services.lakebase_service import LakebaseService
from server.lib.structured_logger import StructuredLogger

router = APIRouter()
logger = StructuredLogger(__name__)


# Enums for validation
class PreferenceKey(str, Enum):
    """Allowed preference keys."""
    DASHBOARD_LAYOUT = "dashboard_layout"
    FAVORITE_TABLES = "favorite_tables"
    THEME = "theme"


# Request/Response models
class SavePreferenceRequest(BaseModel):
    """Request body for saving preference."""
    preference_key: PreferenceKey = Field(..., description="Preference category")
    preference_value: dict[str, Any] = Field(..., description="Preference data as JSON")


class UserPreferenceResponse(BaseModel):
    """Response model for user preference."""
    id: int
    user_id: str
    preference_key: str
    preference_value: dict[str, Any]
    created_at: str
    updated_at: str


async def get_current_user_id() -> str:
    """Extract user ID from authentication context.
    
    TODO: Implement proper authentication extraction from Databricks Apps context.
    For now, returns placeholder for development.
    
    Returns:
        User ID string
    """
    # Placeholder - in production, extract from Databricks authentication context
    return "dev-user@example.com"


@router.get("/preferences", response_model=list[UserPreferenceResponse])
async def get_preferences(
    preference_key: str | None = None,
    user_id: str = Depends(get_current_user_id)
):
    """Get user preferences (user-scoped, data isolated).
    
    Query Parameters:
        preference_key: Specific preference key (optional, returns all if omitted)
        
    Returns:
        List of user preferences
        
    Raises:
        503: Database unavailable (EC-002)
    """
    try:
        service = LakebaseService()
        preferences = await service.get_preferences(
            user_id=user_id,
            preference_key=preference_key
        )
        return preferences
        
    except Exception as e:
        logger.error(
            f"Error getting preferences: {str(e)}",
            exc_info=True,
            user_id=user_id
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "DATABASE_UNAVAILABLE",
                "message": "Database service temporarily unavailable.",
                "technical_details": {"error_type": type(e).__name__},
                "retry_after": 10
            }
        )


@router.post("/preferences", response_model=UserPreferenceResponse)
async def save_preference(
    request: SavePreferenceRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Create or update user preference (user-scoped).
    
    Request Body:
        preference_key: Preference category (dashboard_layout, favorite_tables, theme)
        preference_value: Preference data as JSON
        
    Returns:
        Saved preference
        
    Raises:
        400: Invalid preference data
        503: Database unavailable (EC-002)
    """
    try:
        service = LakebaseService()
        preference = await service.save_preference(
            user_id=user_id,
            preference_key=request.preference_key.value,
            preference_value=request.preference_value
        )
        return preference
        
    except ValueError as e:
        logger.warning(
            f"Invalid preference data: {str(e)}",
            user_id=user_id
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_PREFERENCE",
                "message": str(e)
            }
        )
    
    except Exception as e:
        logger.error(
            f"Error saving preference: {str(e)}",
            exc_info=True,
            user_id=user_id
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "DATABASE_UNAVAILABLE",
                "message": "Database service temporarily unavailable.",
                "technical_details": {"error_type": type(e).__name__},
                "retry_after": 10
            }
        )


@router.delete("/preferences/{preference_key}", status_code=204)
async def delete_preference(
    preference_key: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete user preference (user-scoped).
    
    Path Parameters:
        preference_key: Preference key to delete
        
    Returns:
        204 No Content on success
        
    Raises:
        404: Preference not found for this user
        503: Database unavailable (EC-002)
    """
    try:
        service = LakebaseService()
        deleted = await service.delete_preference(
            user_id=user_id,
            preference_key=preference_key
        )
        
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "PREFERENCE_NOT_FOUND",
                    "message": f"Preference '{preference_key}' not found for this user."
                }
            )
        
        return None  # 204 No Content
        
    except HTTPException:
        raise  # Re-raise 404
    
    except Exception as e:
        logger.error(
            f"Error deleting preference: {str(e)}",
            exc_info=True,
            user_id=user_id
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "DATABASE_UNAVAILABLE",
                "message": "Database service temporarily unavailable.",
                "technical_details": {"error_type": type(e).__name__},
                "retry_after": 10
            }
        )
