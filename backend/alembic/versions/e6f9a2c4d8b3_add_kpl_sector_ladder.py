"""add kpl_sector_ladder table

Revision ID: e6f9a2c4d8b3
Revises: d4a8e5c9b2f1
Create Date: 2026-04-29 12:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e6f9a2c4d8b3'
down_revision: Union[str, Sequence[str], None] = 'd4a8e5c9b2f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'kpl_sector_ladder',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('sector_code', sa.String(length=32), nullable=False),
        sa.Column('sector_name', sa.String(length=64), nullable=True),
        sa.Column('ts_code', sa.String(length=16), nullable=False),
        sa.Column('stock_name', sa.String(length=32), nullable=True),
        sa.Column('td_type', sa.String(length=8), nullable=True),
        sa.Column('tips', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'sector_code', 'ts_code', name='uq_kpl_sector_ladder'),
    )
    with op.batch_alter_table('kpl_sector_ladder', schema=None) as batch_op:
        batch_op.create_index('ix_kpl_sector_ladder_trade_date', ['trade_date'], unique=False)
        batch_op.create_index('ix_kpl_sector_ladder_sector_code', ['sector_code'], unique=False)
        batch_op.create_index('ix_kpl_sector_ladder_ts_code', ['ts_code'], unique=False)


def downgrade() -> None:
    op.drop_table('kpl_sector_ladder')
