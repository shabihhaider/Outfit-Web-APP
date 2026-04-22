"""add_is_archived_to_wardrobe_items

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'wardrobe_items',
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='0')
    )


def downgrade():
    op.drop_column('wardrobe_items', 'is_archived')
