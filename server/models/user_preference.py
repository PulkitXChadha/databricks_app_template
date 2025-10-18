"""User Preference SQLAlchemy Model

Represents user-specific application state and preferences stored in Lakebase.
"""

import os
from sqlalchemy import Column, Integer, String, JSON, DateTime, Index, UniqueConstraint
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class UserPreference(Base):
    """User preferences stored in Lakebase.
    
    Table: user_preferences
    
    Columns:
        id: Auto-incremented primary key
        user_id: User identifier (indexed for data isolation)
        preference_key: Preference category
        preference_value: Preference data as JSON
        created_at: Creation timestamp
        updated_at: Last update timestamp
    
    Constraints:
        - UNIQUE(user_id, preference_key): One preference per user per key
        - INDEX on user_id for efficient filtering
    """
    
    __tablename__ = 'user_preferences'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    preference_key = Column(String(100), nullable=False)
    preference_value = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Conditionally set schema based on environment
    # SQLite (used in tests) doesn't support schemas, Postgres does
    _use_schema = os.getenv('USE_DB_SCHEMA', 'true').lower() == 'true'
    if _use_schema:
        __table_args__ = (
            UniqueConstraint('user_id', 'preference_key', name='uq_user_preference'),
            Index('idx_user_preferences_user_id', 'user_id'),
            {'schema': 'public'}
        )
    else:
        __table_args__ = (
            UniqueConstraint('user_id', 'preference_key', name='uq_user_preference'),
            Index('idx_user_preferences_user_id', 'user_id'),
        )
    
    def __repr__(self) -> str:
        return (
            f"<UserPreference(id={self.id}, user_id='{self.user_id}', "
            f"preference_key='{self.preference_key}')>"
        )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'preference_key': self.preference_key,
            'preference_value': self.preference_value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# Allowed preference keys (enum for validation)
ALLOWED_PREFERENCE_KEYS = {
    'dashboard_layout',
    'favorite_tables',
    'theme'
}


def validate_preference_key(key: str) -> bool:
    """Validate preference key is in allowed set."""
    return key in ALLOWED_PREFERENCE_KEYS