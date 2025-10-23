"""create model_inference_logs table

Revision ID: 002
Revises: 001
Create Date: 2025-10-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  """Create model_inference_logs table for tracking model predictions."""
  op.create_table(
    'model_inference_logs',
    sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
    sa.Column('request_id', sa.String(length=100), nullable=False),
    sa.Column('endpoint_name', sa.String(length=255), nullable=False),
    sa.Column('user_id', sa.String(length=255), nullable=False),
    sa.Column('inputs', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('predictions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('execution_time_ms', sa.Integer(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column(
      'created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False
    ),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
  )

  # Create indexes for efficient queries
  op.create_index('idx_inference_user_id', 'model_inference_logs', ['user_id'])
  op.create_index('idx_inference_endpoint', 'model_inference_logs', ['endpoint_name'])
  op.create_index('idx_inference_request_id', 'model_inference_logs', ['request_id'])


def downgrade() -> None:
  """Drop model_inference_logs table."""
  op.drop_index('idx_inference_request_id', table_name='model_inference_logs')
  op.drop_index('idx_inference_endpoint', table_name='model_inference_logs')
  op.drop_index('idx_inference_user_id', table_name='model_inference_logs')
  op.drop_table('model_inference_logs')
