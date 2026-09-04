"""payments

Revision ID: 2538a6654864
Revises: e62c471b29ad
Create Date: 2026-09-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2538a6654864'
down_revision: Union[str, None] = 'e62c471b29ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.Column('reference', sa.String(length=64), nullable=False),
        sa.Column('wompi_transaction_id', sa.String(length=64), nullable=True),
        sa.Column('amount_in_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column(
            'status',
            sa.Enum('pending', 'approved', 'declined', 'voided', 'error', name='payment_status'),
            nullable=False,
        ),
        sa.Column('checkout_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_payments_trip_id'), 'payments', ['trip_id'], unique=False)
    op.create_index(op.f('ix_payments_reference'), 'payments', ['reference'], unique=True)
    op.create_index(
        op.f('ix_payments_wompi_transaction_id'), 'payments', ['wompi_transaction_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_payments_wompi_transaction_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_reference'), table_name='payments')
    op.drop_index(op.f('ix_payments_trip_id'), table_name='payments')
    op.drop_table('payments')
