"""Rename metadata column to event_metadata in usage_events table

Revision ID: 006
Revises: 005
Create Date: 2025-10-22 12:00:00.000000

"""

from alembic import op

# revision identifiers
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
  # Rename metadata column to event_metadata in usage_events table
  op.alter_column('usage_events', 'metadata', new_column_name='event_metadata')


def downgrade():
  # Rename event_metadata column back to metadata
  op.alter_column('usage_events', 'event_metadata', new_column_name='metadata')
