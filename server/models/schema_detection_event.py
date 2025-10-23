"""SQLAlchemy model for schema detection event logging."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class SchemaDetectionEvent(Base):
  """Schema detection event log for observability and debugging."""

  __tablename__ = 'schema_detection_events'

  id = Column(Integer, primary_key=True, autoincrement=True)
  correlation_id = Column(String(36), nullable=False, index=True)
  endpoint_name = Column(String(255), nullable=False, index=True)
  detected_type = Column(String(50), nullable=False)
  status = Column(String(20), nullable=False)
  latency_ms = Column(Integer, nullable=False)
  error_details = Column(Text, nullable=True)
  user_id = Column(String(255), nullable=False, index=True)
  created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

  def __repr__(self):
    return (
      f'<SchemaDetectionEvent(id={self.id}, endpoint={self.endpoint_name}, status={self.status})>'
    )
