"""Lakebase Service

Service for user preferences and application state in Lakebase (Postgres).
"""

from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from server.models.user_preference import UserPreference, validate_preference_key
from server.lib.database import get_db_session
from server.lib.structured_logger import StructuredLogger

logger = StructuredLogger(__name__)


class LakebaseService:
    """Service for Lakebase transactional data.
    
    Provides methods to:
    - Get user preferences (user-scoped)
    - Save/update user preferences
    - Delete user preferences
    
    All queries filter by user_id for data isolation.
    """
    
    def __init__(self, db_session: Session | None = None):
        """Initialize Lakebase service.
        
        Args:
            db_session: Database session (auto-created if None)
        """
        self.db_session = db_session
    
    async def get_preferences(
        self,
        user_id: str,
        preference_key: str | None = None
    ) -> list[dict[str, Any]]:
        """Get user preferences (user-scoped, data isolated).
        
        Args:
            user_id: User identifier (from authentication context)
            preference_key: Specific preference key (optional, returns all if None)
            
        Returns:
            List of preference dictionaries
            
        Raises:
            SQLAlchemyError: If database query fails (EC-002)
        """
        try:
            # Use provided session or create new one
            if self.db_session:
                return self._query_preferences(self.db_session, user_id, preference_key)
            else:
                # Create new session
                for session in get_db_session():
                    return self._query_preferences(session, user_id, preference_key)
                    
        except SQLAlchemyError as e:
            logger.error(
                f"Database error getting preferences: {str(e)}",
                exc_info=True,
                user_id=user_id,
                preference_key=preference_key
            )
            raise
    
    def _query_preferences(
        self,
        session: Session,
        user_id: str,
        preference_key: str | None
    ) -> list[dict[str, Any]]:
        """Internal method to query preferences.
        
        Args:
            session: Database session
            user_id: User identifier
            preference_key: Optional preference key filter
            
        Returns:
            List of preference dictionaries
        """
        # Build query with user_id filter (data isolation)
        query = session.query(UserPreference).filter_by(user_id=user_id)
        
        # Add preference_key filter if specified
        if preference_key:
            query = query.filter_by(preference_key=preference_key)
        
        # Execute query
        preferences = query.all()
        
        logger.info(
            f"Retrieved {len(preferences)} preferences",
            user_id=user_id,
            preference_key=preference_key
        )
        
        return [pref.to_dict() for pref in preferences]
    
    async def save_preference(
        self,
        user_id: str,
        preference_key: str,
        preference_value: dict[str, Any]
    ) -> dict[str, Any]:
        """Save or update user preference (user-scoped).
        
        Args:
            user_id: User identifier (from authentication context)
            preference_key: Preference category
            preference_value: Preference data as JSON
            
        Returns:
            Saved preference dictionary
            
        Raises:
            ValueError: If preference_key is not allowed
            SQLAlchemyError: If database operation fails (EC-002)
        """
        # Validate preference key
        if not validate_preference_key(preference_key):
            raise ValueError(f"Invalid preference_key: {preference_key}. Allowed keys: dashboard_layout, favorite_tables, theme")
        
        try:
            # Use provided session or create new one
            if self.db_session:
                return self._save_preference(self.db_session, user_id, preference_key, preference_value)
            else:
                # Create new session
                for session in get_db_session():
                    return self._save_preference(session, user_id, preference_key, preference_value)
                    
        except SQLAlchemyError as e:
            logger.error(
                f"Database error saving preference: {str(e)}",
                exc_info=True,
                user_id=user_id,
                preference_key=preference_key
            )
            raise
    
    def _save_preference(
        self,
        session: Session,
        user_id: str,
        preference_key: str,
        preference_value: dict[str, Any]
    ) -> dict[str, Any]:
        """Internal method to save preference.
        
        Args:
            session: Database session
            user_id: User identifier
            preference_key: Preference category
            preference_value: Preference data
            
        Returns:
            Saved preference dictionary
        """
        # Check if preference exists (user_id + preference_key unique)
        existing = session.query(UserPreference).filter_by(
            user_id=user_id,
            preference_key=preference_key
        ).first()
        
        if existing:
            # Update existing preference
            existing.preference_value = preference_value
            session.commit()
            session.refresh(existing)
            
            logger.info(
                "Updated preference",
                user_id=user_id,
                preference_key=preference_key
            )
            
            return existing.to_dict()
        else:
            # Create new preference
            new_pref = UserPreference(
                user_id=user_id,
                preference_key=preference_key,
                preference_value=preference_value
            )
            session.add(new_pref)
            session.commit()
            session.refresh(new_pref)
            
            logger.info(
                "Created preference",
                user_id=user_id,
                preference_key=preference_key
            )
            
            return new_pref.to_dict()
    
    async def delete_preference(
        self,
        user_id: str,
        preference_key: str
    ) -> bool:
        """Delete user preference (user-scoped).
        
        Args:
            user_id: User identifier (from authentication context)
            preference_key: Preference category to delete
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            SQLAlchemyError: If database operation fails (EC-002)
        """
        try:
            # Use provided session or create new one
            if self.db_session:
                return self._delete_preference(self.db_session, user_id, preference_key)
            else:
                # Create new session
                for session in get_db_session():
                    return self._delete_preference(session, user_id, preference_key)
                    
        except SQLAlchemyError as e:
            logger.error(
                f"Database error deleting preference: {str(e)}",
                exc_info=True,
                user_id=user_id,
                preference_key=preference_key
            )
            raise
    
    def _delete_preference(
        self,
        session: Session,
        user_id: str,
        preference_key: str
    ) -> bool:
        """Internal method to delete preference.
        
        Args:
            session: Database session
            user_id: User identifier
            preference_key: Preference category
            
        Returns:
            True if deleted, False if not found
        """
        # Find preference (user_id + preference_key unique)
        preference = session.query(UserPreference).filter_by(
            user_id=user_id,
            preference_key=preference_key
        ).first()
        
        if preference:
            session.delete(preference)
            session.commit()
            
            logger.info(
                "Deleted preference",
                user_id=user_id,
                preference_key=preference_key
            )
            
            return True
        else:
            logger.info(
                "Preference not found for deletion",
                user_id=user_id,
                preference_key=preference_key
            )
            
            return False
