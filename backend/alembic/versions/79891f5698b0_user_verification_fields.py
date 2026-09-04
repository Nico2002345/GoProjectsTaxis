"""user verification fields

Revision ID: 79891f5698b0
Revises: 41f199c52445
Create Date: 2026-09-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '79891f5698b0'
down_revision: Union[str, None] = '41f199c52445'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('cedula', sa.String(length=20), nullable=False))
    op.add_column('users', sa.Column('email', sa.String(length=255), nullable=False))
    op.add_column(
        'users',
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'users', sa.Column('email_verification_pin', sa.String(length=6), nullable=True)
    )
    op.add_column(
        'users', sa.Column('email_verification_expires_at', sa.DateTime(), nullable=True)
    )
    op.add_column('users', sa.Column('terms_accepted_at', sa.DateTime(), nullable=True))

    op.create_index(op.f('ix_users_cedula'), 'users', ['cedula'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    op.alter_column('users', 'email_verified', server_default=None)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_cedula'), table_name='users')

    op.drop_column('users', 'terms_accepted_at')
    op.drop_column('users', 'email_verification_expires_at')
    op.drop_column('users', 'email_verification_pin')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'email')
    op.drop_column('users', 'cedula')
