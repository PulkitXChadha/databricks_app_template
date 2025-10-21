from sqlalchemy import Column, String, Integer, DateTime, JSON, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from server.lib.database import Base
import uuid


class AggregatedMetric(Base):
    """
    Pre-computed hourly summaries of performance and usage metrics.
    Stores aggregated data for 90-day retention period.
    """
    __tablename__ = 'aggregated_metrics'
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    time_bucket = Column(DateTime(timezone=True), nullable=False)
    metric_type = Column(String(50), nullable=False)
    endpoint_path = Column(String(500), nullable=True)
    event_type = Column(String(100), nullable=True)
    aggregated_values = Column(JSON, nullable=False)
    sample_count = Column(Integer, nullable=False)
    
    __table_args__ = (
        Index('ix_aggregated_metrics_time_bucket', 'time_bucket'),
        Index('ix_aggregated_metrics_metric_type', 'metric_type'),
        Index('ix_aggregated_metrics_endpoint_path', 'endpoint_path'),
        Index('ix_aggregated_metrics_event_type', 'event_type'),
    )

