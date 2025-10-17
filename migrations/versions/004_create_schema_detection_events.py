"""Create schema_detection_events table

Revision ID: 004
Revises: 003
Create Date: 2025-10-17 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'schema_detection_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('correlation_id', sa.String(length=36), nullable=False),
        sa.Column('endpoint_name', sa.String(length=255), nullable=False),
        sa.Column('detected_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("detected_type IN ('FOUNDATION_MODEL', 'MLFLOW_MODEL', 'UNKNOWN')"),
        sa.CheckConstraint("status IN ('SUCCESS', 'FAILURE', 'TIMEOUT')"),
        sa.CheckConstraint("latency_ms >= 0")
    )
    
    # Create indexes for query performance
    op.create_index('idx_correlation_id', 'schema_detection_events', ['correlation_id'])
    op.create_index('idx_user_id', 'schema_detection_events', ['user_id'])
    op.create_index('idx_endpoint_name', 'schema_detection_events', ['endpoint_name'])
    op.create_index('idx_created_at', 'schema_detection_events', ['created_at'], postgresql_ops={'created_at': 'DESC'})

def downgrade():
    op.drop_index('idx_created_at', table_name='schema_detection_events')
    op.drop_index('idx_endpoint_name', table_name='schema_detection_events')
    op.drop_index('idx_user_id', table_name='schema_detection_events')
    op.drop_index('idx_correlation_id', table_name='schema_detection_events')
    op.drop_table('schema_detection_events')

