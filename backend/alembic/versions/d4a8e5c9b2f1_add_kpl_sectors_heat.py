"""add kpl_sectors_heat table (parallel to sector_limit_up_heat)

Revision ID: d4a8e5c9b2f1
Revises: c2f5d8b1a3e7
Create Date: 2026-04-28 17:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4a8e5c9b2f1'
down_revision: Union[str, Sequence[str], None] = 'c2f5d8b1a3e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'kpl_sectors_heat',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('sector_code', sa.String(length=32), nullable=False),
        sa.Column('sector_name', sa.String(length=64), nullable=True),
        sa.Column('count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'sector_code', name='uq_kpl_sectors_heat'),
    )
    with op.batch_alter_table('kpl_sectors_heat', schema=None) as batch_op:
        batch_op.create_index('ix_kpl_sectors_heat_trade_date', ['trade_date'], unique=False)


def downgrade() -> None:
    op.drop_table('kpl_sectors_heat')
