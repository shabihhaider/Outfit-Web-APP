"""add_audit_log_and_user_consents

Revision ID: a1b2c3d4e5f6
Revises: 640f3d8513ce
Create Date: 2026-04-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '640f3d8513ce'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('detail', sa.String(length=500), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_log_user_id', 'audit_log', ['user_id'])
    op.create_index('ix_audit_log_action', 'audit_log', ['action'])
    op.create_index('ix_audit_log_created_at', 'audit_log', ['created_at'])

    op.create_table('user_consents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('consent_type', sa.String(length=30), nullable=False),
        sa.Column('granted', sa.Boolean(), nullable=False),
        sa.Column('version', sa.String(length=10), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('granted_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_consents_user_id', 'user_consents', ['user_id'])
    op.create_index('ix_consent_lookup', 'user_consents', ['user_id', 'consent_type'])


def downgrade():
    op.drop_table('user_consents')
    op.drop_table('audit_log')
