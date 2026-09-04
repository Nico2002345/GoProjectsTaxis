"""trip fare negotiation

Revision ID: e62c471b29ad
Revises: 79891f5698b0
Create Date: 2026-09-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e62c471b29ad'
down_revision: Union[str, None] = '79891f5698b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'trips', sa.Column('offered_fare_cents', sa.Integer(), nullable=False, server_default='0')
    )
    op.add_column('trips', sa.Column('agreed_fare_cents', sa.Integer(), nullable=True))
    op.alter_column('trips', 'offered_fare_cents', server_default=None)

    op.create_table(
        'trip_offers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('fare_cents', sa.Integer(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('pending', 'accepted', 'rejected', name='trip_offer_status'),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('responded_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['driver_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trip_id', 'driver_id', name='uq_trip_offer_driver'),
    )
    op.create_index(op.f('ix_trip_offers_trip_id'), 'trip_offers', ['trip_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_trip_offers_trip_id'), table_name='trip_offers')
    op.drop_table('trip_offers')

    op.drop_column('trips', 'agreed_fare_cents')
    op.drop_column('trips', 'offered_fare_cents')
