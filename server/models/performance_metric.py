import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from server.lib.database import Base


class PerformanceMetric(Base):
  """Performance metrics for API requests.
  Stores individual request timing data for 7-day retention period.
  """

  __tablename__ = 'performance_metrics'

  id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
  endpoint = Column(String(500), nullable=False)
  method = Column(String(10), nullable=False)
  status_code = Column(Integer, nullable=False)
  response_time_ms = Column(Float, nullable=False)
  user_id = Column(String(255), nullable=True)
  error_type = Column(String(255), nullable=True)

  __table_args__ = (
    Index('ix_performance_metrics_timestamp', 'timestamp'),
    Index('ix_performance_metrics_endpoint', 'endpoint'),
    Index('ix_performance_metrics_user_id', 'user_id'),
  )
