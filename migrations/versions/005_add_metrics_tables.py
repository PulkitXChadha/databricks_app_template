"""Add metrics tables for performance and usage tracking

Revision ID: 005
Revises: 004
Create Date: 2025-10-20 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
  # Create performance_metrics table
  op.create_table(
    'performance_metrics',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.Column('endpoint', sa.String(length=500), nullable=False),
    sa.Column('method', sa.String(length=10), nullable=False),
    sa.Column('status_code', sa.Integer(), nullable=False),
    sa.Column('response_time_ms', sa.Float(), nullable=False),
    sa.Column('user_id', sa.String(length=255), nullable=True),
    sa.Column('error_type', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id'),
  )

  # Create indexes for performance_metrics
  op.create_index('ix_performance_metrics_timestamp', 'performance_metrics', ['timestamp'])
  op.create_index('ix_performance_metrics_endpoint', 'performance_metrics', ['endpoint'])
  op.create_index('ix_performance_metrics_user_id', 'performance_metrics', ['user_id'])

  # Create usage_events table
  op.create_table(
    'usage_events',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.Column('event_type', sa.String(length=100), nullable=False),
    sa.Column('user_id', sa.String(length=255), nullable=False),
    sa.Column('page_name', sa.String(length=255), nullable=True),
    sa.Column('element_id', sa.String(length=255), nullable=True),
    sa.Column('success', sa.Boolean(), nullable=True),
    sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.PrimaryKeyConstraint('id'),
  )

  # Create indexes for usage_events
  op.create_index('ix_usage_events_timestamp', 'usage_events', ['timestamp'])
  op.create_index('ix_usage_events_event_type', 'usage_events', ['event_type'])
  op.create_index('ix_usage_events_user_id', 'usage_events', ['user_id'])

  # Create aggregated_metrics table
  op.create_table(
    'aggregated_metrics',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('time_bucket', sa.DateTime(timezone=True), nullable=False),
    sa.Column('metric_type', sa.String(length=50), nullable=False),
    sa.Column('endpoint_path', sa.String(length=500), nullable=True),
    sa.Column('event_type', sa.String(length=100), nullable=True),
    sa.Column('aggregated_values', postgresql.JSON(astext_type=sa.Text()), nullable=False),
    sa.Column('sample_count', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
  )

  # Create indexes for aggregated_metrics
  op.create_index('ix_aggregated_metrics_time_bucket', 'aggregated_metrics', ['time_bucket'])
  op.create_index('ix_aggregated_metrics_metric_type', 'aggregated_metrics', ['metric_type'])
  op.create_index('ix_aggregated_metrics_endpoint_path', 'aggregated_metrics', ['endpoint_path'])
  op.create_index('ix_aggregated_metrics_event_type', 'aggregated_metrics', ['event_type'])


def downgrade():
  # Drop aggregated_metrics table and indexes
  op.drop_index('ix_aggregated_metrics_event_type', table_name='aggregated_metrics')
  op.drop_index('ix_aggregated_metrics_endpoint_path', table_name='aggregated_metrics')
  op.drop_index('ix_aggregated_metrics_metric_type', table_name='aggregated_metrics')
  op.drop_index('ix_aggregated_metrics_time_bucket', table_name='aggregated_metrics')
  op.drop_table('aggregated_metrics')

  # Drop usage_events table and indexes
  op.drop_index('ix_usage_events_user_id', table_name='usage_events')
  op.drop_index('ix_usage_events_event_type', table_name='usage_events')
  op.drop_index('ix_usage_events_timestamp', table_name='usage_events')
  op.drop_table('usage_events')

  # Drop performance_metrics table and indexes
  op.drop_index('ix_performance_metrics_user_id', table_name='performance_metrics')
  op.drop_index('ix_performance_metrics_endpoint', table_name='performance_metrics')
  op.drop_index('ix_performance_metrics_timestamp', table_name='performance_metrics')
  op.drop_table('performance_metrics')
