"""Add user_id columns for multi-user data isolation

Revision ID: 003
Revises: 002
Create Date: 2025-10-12

This migration adds user_id columns to existing tables for multi-user data isolation.
This is a greenfield deployment (first production deployment per spec), so no existing
production data needs migration. Placeholder email is for local development databases only.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
  """Add user_id columns and indices for multi-user data isolation."""
  # Check if user_id column already exists in user_preferences
  from sqlalchemy import inspect

  conn = op.get_bind()
  inspector = inspect(conn)
  existing_columns = [col['name'] for col in inspector.get_columns('user_preferences')]

  if 'user_id' not in existing_columns:
    # Add user_id column to user_preferences table
    op.add_column(
      'user_preferences',
      sa.Column(
        'user_id',
        sa.String(255),
        nullable=False,
        server_default='migration-placeholder@example.com',
      ),
    )

  # Create index for user_id in user_preferences for performance (if not exists)
  existing_indexes = [idx['name'] for idx in inspector.get_indexes('user_preferences')]
  if 'idx_user_preferences_user_id' not in existing_indexes:
    op.create_index('idx_user_preferences_user_id', 'user_preferences', ['user_id'])

  # Drop existing unique constraint if it exists (we'll recreate it with user_id)
  existing_constraints = [
    con['name'] for con in inspector.get_unique_constraints('user_preferences')
  ]

  if 'uq_preference_key' in existing_constraints:
    op.drop_constraint('uq_preference_key', 'user_preferences', type_='unique')

  # Add new unique constraint for (user_id, preference_key) combination
  if 'uq_user_preference' not in existing_constraints:
    op.create_unique_constraint(
      'uq_user_preference', 'user_preferences', ['user_id', 'preference_key']
    )

  # Check if user_id column already exists in model_inference_logs
  existing_columns_logs = [col['name'] for col in inspector.get_columns('model_inference_logs')]

  if 'user_id' not in existing_columns_logs:
    # Add user_id column to model_inference_logs table
    op.add_column(
      'model_inference_logs',
      sa.Column(
        'user_id',
        sa.String(255),
        nullable=False,
        server_default='migration-placeholder@example.com',
      ),
    )

  # Create index for user_id in model_inference_logs for performance (if not exists)
  existing_indexes_logs = [idx['name'] for idx in inspector.get_indexes('model_inference_logs')]
  if 'idx_model_inference_logs_user_id' not in existing_indexes_logs:
    op.create_index('idx_model_inference_logs_user_id', 'model_inference_logs', ['user_id'])

  # Remove server defaults after initial population (only if we added the columns)
  # This ensures new records must explicitly provide user_id
  if 'user_id' not in existing_columns:
    op.alter_column('user_preferences', 'user_id', server_default=None)
  if 'user_id' not in existing_columns_logs:
    op.alter_column('model_inference_logs', 'user_id', server_default=None)


def downgrade():
  """Remove user_id columns and restore original schema."""
  # Drop the unique constraint on (user_id, preference_key)
  op.drop_constraint('uq_user_preference', 'user_preferences', type_='unique')

  # Restore original unique constraint on preference_key only (if it existed)
  # op.create_unique_constraint('uq_preference_key', 'user_preferences', ['preference_key'])

  # Drop indices
  op.drop_index('idx_user_preferences_user_id', 'user_preferences')
  op.drop_index('idx_model_inference_logs_user_id', 'model_inference_logs')

  # Drop columns
  op.drop_column('user_preferences', 'user_id')
  op.drop_column('model_inference_logs', 'user_id')
