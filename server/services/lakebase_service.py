"""Lakebase Service

Service for user preferences and application state in Lakebase (Postgres).
Uses service principal for database connections (per FR-011).
Implements application-level data isolation via user_id filtering.
"""

from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from server.models.user_preference import UserPreference, validate_preference_key
from server.lib.database import get_db_session
from server.lib.structured_logger import StructuredLogger, log_event

logger = StructuredLogger(__name__)


class LakebaseService:
    """Service for Lakebase transactional data.
    
    Provides methods to:
    - Get user preferences (user-scoped via user_id filtering)
    - Save/update user preferences
    - Delete user preferences
    
    IMPORTANT: This service NEVER accepts user_token (per FR-011).
    Database connection uses service principal ONLY.
    Data isolation enforced via WHERE user_id = ? in all queries.
    """
    
    def __init__(self, db_session: Session | None = None):
        """Initialize Lakebase service.
        
        Args:
            db_session: Database session (auto-created if None, uses service principal)
        
        Note:
            This service does NOT accept user_token parameter.
            All database operations use service principal authentication.
            User isolation is enforced via user_id parameter in method calls.
        """
        self.db_session = db_session
        
        log_event("service.initialized", context={
            "service_name": "LakebaseService",
            "auth_mode": "service_principal",
            "data_isolation": "user_id_filtering"
        })
    
    async def get_preferences(
        self,
        user_id: str,
        preference_key: str | None = None
    ) -> list[dict[str, Any]]:
        """Get user preferences (user-scoped, data isolated).
        
        IMPORTANT: Validates user_id presence before query execution (per FR-014).
        Uses service principal for database connection (per FR-011).
        Data isolation via WHERE user_id = ? (per FR-013).
        
        Args:
            user_id: User identifier (from authentication context, REQUIRED)
            preference_key: Specific preference key (optional, returns all if None)
            
        Returns:
            List of preference dictionaries
            
        Raises:
            ValueError: If user_id is empty or None (per FR-014)
            SQLAlchemyError: If database query fails (EC-002)
        """
        # Validate user_id presence before query execution (FR-014)
        if not user_id or not isinstance(user_id, str) or len(user_id.strip()) == 0:
            raise ValueError("User identity required for data access")
        
        try:
            # Use provided session or create new one (always service principal)
            if self.db_session:
                return self._query_preferences(self.db_session, user_id, preference_key)
            else:
                # Always use service principal session (FR-011)
                for session in get_db_session():
                    return self._query_preferences(session, user_id, preference_key)
                    
        except SQLAlchemyError as e:
            log_event("service.database_query", level="ERROR", context={
                "service_name": "LakebaseService",
                "operation": "get_preferences",
                "query_type": "select",
                "user_id": user_id,
                "error_type": type(e).__name__,
                "error_message": str(e)
            })
            raise
    
    def _query_preferences(
        self,
        session: Session,
        user_id: str,
        preference_key: str | None
    ) -> list[dict[str, Any]]:
        """Internal method to query preferences.
        
        CRITICAL: All queries MUST include WHERE user_id = ? for data isolation (FR-013).
        
        Args:
            session: Database session (service principal connection)
            user_id: User identifier (for WHERE clause filtering)
            preference_key: Optional preference key filter
            
        Returns:
            List of preference dictionaries
        """
        # Build query with user_id filter (FR-013: data isolation)
        query = session.query(UserPreference).filter_by(user_id=user_id)
        
        # Add preference_key filter if specified
        if preference_key:
            query = query.filter_by(preference_key=preference_key)
        
        # Execute query
        preferences = query.all()
        
        log_event("service.database_query", context={
            "service_name": "LakebaseService",
            "operation": "get_preferences",
            "query_type": "select",
            "user_id": user_id,
            "result_count": len(preferences)
        })
        
        return [pref.to_dict() for pref in preferences]
    
    async def save_preference(
        self,
        user_id: str,
        preference_key: str,
        preference_value: dict[str, Any]
    ) -> dict[str, Any]:
        """Save or update user preference (user-scoped).
        
        IMPORTANT: Validates user_id presence before database operation (per FR-014).
        Uses service principal for database connection (per FR-011).
        Stores user_id with preference for data isolation (per FR-010).
        
        Args:
            user_id: User identifier (from authentication context, REQUIRED)
            preference_key: Preference category
            preference_value: Preference data as JSON
            
        Returns:
            Saved preference dictionary
            
        Raises:
            ValueError: If user_id is empty or preference_key is invalid (per FR-014)
            SQLAlchemyError: If database operation fails (EC-002)
        """
        # Validate user_id presence before database operation (FR-014)
        if not user_id or not isinstance(user_id, str) or len(user_id.strip()) == 0:
            raise ValueError("User identity required for data access")
        
        # Validate preference key
        if not validate_preference_key(preference_key):
            raise ValueError(f"Invalid preference_key: {preference_key}. Allowed keys: dashboard_layout, favorite_tables, theme")
        
        try:
            # Use provided session or create new one (always service principal)
            if self.db_session:
                return self._save_preference(self.db_session, user_id, preference_key, preference_value)
            else:
                # Always use service principal session (FR-011)
                for session in get_db_session():
                    return self._save_preference(session, user_id, preference_key, preference_value)
                    
        except SQLAlchemyError as e:
            log_event("service.database_query", level="ERROR", context={
                "service_name": "LakebaseService",
                "operation": "save_preference",
                "query_type": "upsert",
                "user_id": user_id,
                "preference_key": preference_key,
                "error_type": type(e).__name__,
                "error_message": str(e)
            })
            raise
    
    def _save_preference(
        self,
        session: Session,
        user_id: str,
        preference_key: str,
        preference_value: dict[str, Any]
    ) -> dict[str, Any]:
        """Internal method to save preference.
        
        CRITICAL: Stores user_id with preference for data isolation (FR-010).
        Queries filter by user_id + preference_key for upsert operation (FR-013).
        
        Args:
            session: Database session (service principal connection)
            user_id: User identifier (stored with preference)
            preference_key: Preference category
            preference_value: Preference data
            
        Returns:
            Saved preference dictionary
        """
        # Check if preference exists (user_id + preference_key unique) - FR-013
        existing = session.query(UserPreference).filter_by(
            user_id=user_id,
            preference_key=preference_key
        ).first()
        
        if existing:
            # Update existing preference
            existing.preference_value = preference_value
            session.commit()
            session.refresh(existing)
            
            log_event("service.database_query", context={
                "service_name": "LakebaseService",
                "operation": "save_preference",
                "query_type": "update",
                "user_id": user_id,
                "preference_key": preference_key
            })
            
            return existing.to_dict()
        else:
            # Create new preference with user_id (FR-010)
            new_pref = UserPreference(
                user_id=user_id,
                preference_key=preference_key,
                preference_value=preference_value
            )
            session.add(new_pref)
            session.commit()
            session.refresh(new_pref)
            
            log_event("service.database_query", context={
                "service_name": "LakebaseService",
                "operation": "save_preference",
                "query_type": "insert",
                "user_id": user_id,
                "preference_key": preference_key
            })
            
            return new_pref.to_dict()
    
    async def delete_preference(
        self,
        user_id: str,
        preference_key: str
    ) -> bool:
        """Delete user preference (user-scoped).
        
        IMPORTANT: Validates user_id presence before database operation (per FR-014).
        Uses service principal for database connection (per FR-011).
        Filters by user_id to prevent cross-user deletion (per FR-013).
        
        Args:
            user_id: User identifier (from authentication context, REQUIRED)
            preference_key: Preference category to delete
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            ValueError: If user_id is empty (per FR-014)
            SQLAlchemyError: If database operation fails (EC-002)
        """
        # Validate user_id presence before database operation (FR-014)
        if not user_id or not isinstance(user_id, str) or len(user_id.strip()) == 0:
            raise ValueError("User identity required for data access")
        
        try:
            # Use provided session or create new one (always service principal)
            if self.db_session:
                return self._delete_preference(self.db_session, user_id, preference_key)
            else:
                # Always use service principal session (FR-011)
                for session in get_db_session():
                    return self._delete_preference(session, user_id, preference_key)
                    
        except SQLAlchemyError as e:
            log_event("service.database_query", level="ERROR", context={
                "service_name": "LakebaseService",
                "operation": "delete_preference",
                "query_type": "delete",
                "user_id": user_id,
                "preference_key": preference_key,
                "error_type": type(e).__name__,
                "error_message": str(e)
            })
            raise
    
    def _delete_preference(
        self,
        session: Session,
        user_id: str,
        preference_key: str
    ) -> bool:
        """Internal method to delete preference.
        
        CRITICAL: Filters by user_id to prevent cross-user deletion (FR-013).
        
        Args:
            session: Database session (service principal connection)
            user_id: User identifier (for WHERE clause filtering)
            preference_key: Preference category
            
        Returns:
            True if deleted, False if not found
        """
        # Find preference (user_id + preference_key unique) - FR-013
        preference = session.query(UserPreference).filter_by(
            user_id=user_id,
            preference_key=preference_key
        ).first()
        
        if preference:
            session.delete(preference)
            session.commit()
            
            log_event("service.database_query", context={
                "service_name": "LakebaseService",
                "operation": "delete_preference",
                "query_type": "delete",
                "user_id": user_id,
                "preference_key": preference_key,
                "result": "deleted"
            })
            
            return True
        else:
            log_event("service.database_query", context={
                "service_name": "LakebaseService",
                "operation": "delete_preference",
                "query_type": "delete",
                "user_id": user_id,
                "preference_key": preference_key,
                "result": "not_found"
            })
            
            return False
