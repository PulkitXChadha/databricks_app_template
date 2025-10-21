from sqlalchemy import Column, String, Boolean, DateTime, JSON, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from server.lib.database import Base
import uuid
from datetime import datetime


class UsageEvent(Base):
    """
    Usage event tracking for user interactions.
    Stores page views, clicks, form submissions, and feature usage for 7-day retention.
    """
    __tablename__ = 'usage_events'
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    event_type = Column(String(100), nullable=False)
    user_id = Column(String(255), nullable=False)
    page_name = Column(String(255), nullable=True)
    element_id = Column(String(255), nullable=True)
    success = Column(Boolean, nullable=True)
    event_metadata = Column(JSON, nullable=True)
    
    __table_args__ = (
        Index('ix_usage_events_timestamp', 'timestamp'),
        Index('ix_usage_events_event_type', 'event_type'),
        Index('ix_usage_events_user_id', 'user_id'),
    )

