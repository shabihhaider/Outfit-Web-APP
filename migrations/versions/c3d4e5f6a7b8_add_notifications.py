"""add_notifications

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-12 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'notifications',
        sa.Column('id',         sa.Integer(),      nullable=False),
        sa.Column('user_id',    sa.Integer(),      nullable=False),
        sa.Column('type',       sa.String(30),     nullable=False),
        sa.Column('actor_id',   sa.Integer(),      nullable=True),
        sa.Column('post_id',    sa.Integer(),      nullable=True),
        sa.Column('message',    sa.String(200),    nullable=False),
        sa.Column('read',       sa.Boolean(),      nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(),     nullable=True),
        sa.ForeignKeyConstraint(['user_id'],  ['users.id'],          ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'],          ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['post_id'],  ['shared_outfits.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])


def downgrade():
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_table('notifications')
