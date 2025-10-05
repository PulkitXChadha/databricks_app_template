"""UserPreference SQLAlchemy model for user-scoped application state in Lakebase.

Represents user-specific application preferences stored in Lakebase (Postgres).
All records are strictly user-isolated (no shared records).
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class UserPreference(Base):
    """User-specific application preference stored in Lakebase.
    
    Attributes:
        id: Auto-incremented primary key
        user_id: User identifier (indexed for efficient lookups)
        preference_key: Preference category (dashboard_layout, favorite_tables, theme)
        preference_value: JSON preference data (max 100KB)
        created_at: When preference was created
        updated_at: When preference was last updated
    
    Constraints:
        - UNIQUE(user_id, preference_key): One preference per user per key
        - INDEX on user_id: Fast user-scoped queries
    """
    
    __tablename__ = 'user_preferences'
    
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False,
        doc='Auto-incremented primary key'
    )
    
    user_id = Column(
        String(255),
        nullable=False,
        index=True,
        doc='User identifier (always matches authenticated user for data isolation)'
    )
    
    preference_key = Column(
        String(100),
        nullable=False,
        doc='Preference category (dashboard_layout, favorite_tables, theme)'
    )
    
    preference_value = Column(
        JSONB,
        nullable=False,
        doc='JSON preference data (max 100KB)'
    )
    
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc='When preference was created (UTC)'
    )
    
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        doc='When preference was last updated (UTC)'
    )
    
    __table_args__ = (
        UniqueConstraint('user_id', 'preference_key', name='uq_user_preferences_user_key'),
        Index('idx_user_preferences_user_id', 'user_id'),
        {'schema': 'public'}
    )
    
    def __repr__(self) -> str:
        """String representation of UserPreference."""
        return (
            f'<UserPreference(id={self.id}, user_id={self.user_id}, '
            f'preference_key={self.preference_key})>'
        )
    
    def to_dict(self) -> dict:
        """Convert UserPreference to dictionary for API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'preference_key': self.preference_key,
            'preference_value': self.preference_value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
