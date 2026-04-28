"""fix kpl_lhb_seat id to Integer (SQLite ROWID autoincrement)

Revision ID: c2f5d8b1a3e7
Revises: b8e4f7a3c1d9
Create Date: 2026-04-28 14:50:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c2f5d8b1a3e7'
down_revision: Union[str, Sequence[str], None] = 'b8e4f7a3c1d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 表里目前还没数据（之前 lhb_detail 入库就失败），直接 drop 重建
    op.drop_table('kpl_lhb_seat')
    op.create_table(
        'kpl_lhb_seat',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('ts_code', sa.String(length=16), nullable=False),
        sa.Column('side', sa.String(length=2), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('broker', sa.String(length=128), nullable=False),
        sa.Column('buy_in', sa.Float(), nullable=True),
        sa.Column('sell_out', sa.Float(), nullable=True),
        sa.Column('net_buy', sa.Float(), nullable=True),
        sa.Column('is_dy', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'ts_code', 'side', 'rank', 'broker', name='uq_kpl_lhb_seat'),
    )
    with op.batch_alter_table('kpl_lhb_seat', schema=None) as batch_op:
        batch_op.create_index('ix_kpl_lhb_seat_trade_date', ['trade_date'], unique=False)
        batch_op.create_index('ix_kpl_lhb_seat_ts_code', ['ts_code'], unique=False)
        batch_op.create_index('ix_kpl_lhb_seat_broker', ['broker'], unique=False)


def downgrade() -> None:
    pass
