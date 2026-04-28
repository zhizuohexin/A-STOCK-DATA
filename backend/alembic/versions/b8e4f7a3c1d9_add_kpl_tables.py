"""add Kaipanla data tables

Revision ID: b8e4f7a3c1d9
Revises: a7c3d1e8f2b4
Create Date: 2026-04-28 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8e4f7a3c1d9'
down_revision: Union[str, Sequence[str], None] = 'a7c3d1e8f2b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'kpl_sentiment',
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('limit_up', sa.Integer(), nullable=True),
        sa.Column('actual_limit_up', sa.Integer(), nullable=True),
        sa.Column('limit_down', sa.Integer(), nullable=True),
        sa.Column('actual_limit_down', sa.Integer(), nullable=True),
        sa.Column('up_count', sa.Integer(), nullable=True),
        sa.Column('down_count', sa.Integer(), nullable=True),
        sa.Column('flat_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('trade_date'),
    )

    op.create_table(
        'kpl_ladder',
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('first_board', sa.Integer(), nullable=True),
        sa.Column('second_board', sa.Integer(), nullable=True),
        sa.Column('third_board', sa.Integer(), nullable=True),
        sa.Column('high_board', sa.Integer(), nullable=True),
        sa.Column('rate', sa.Float(), nullable=True),
        sa.Column('comment', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('trade_date'),
    )

    op.create_table(
        'kpl_consecutive',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('ts_code', sa.String(length=16), nullable=False),
        sa.Column('name', sa.String(length=32), nullable=True),
        sa.Column('days', sa.Integer(), nullable=True),
        sa.Column('pct_chg', sa.Float(), nullable=True),
        sa.Column('theme', sa.String(length=128), nullable=True),
        sa.Column('board_desc', sa.String(length=32), nullable=True),
        sa.Column('market_cap', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'ts_code', name='uq_kpl_consec_date_code'),
    )
    with op.batch_alter_table('kpl_consecutive', schema=None) as batch_op:
        batch_op.create_index('ix_kpl_consecutive_trade_date', ['trade_date'], unique=False)
        batch_op.create_index('ix_kpl_consecutive_ts_code', ['ts_code'], unique=False)

    op.create_table(
        'kpl_broken',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('ts_code', sa.String(length=16), nullable=False),
        sa.Column('name', sa.String(length=32), nullable=True),
        sa.Column('pct_chg', sa.Float(), nullable=True),
        sa.Column('sector', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'ts_code', name='uq_kpl_broken_date_code'),
    )
    with op.batch_alter_table('kpl_broken', schema=None) as batch_op:
        batch_op.create_index('ix_kpl_broken_trade_date', ['trade_date'], unique=False)
        batch_op.create_index('ix_kpl_broken_ts_code', ['ts_code'], unique=False)

    op.create_table(
        'kpl_lhb',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('ts_code', sa.String(length=16), nullable=False),
        sa.Column('name', sa.String(length=32), nullable=True),
        sa.Column('pct_chg', sa.Float(), nullable=True),
        sa.Column('reason', sa.String(length=64), nullable=True),
        sa.Column('buy_in', sa.Float(), nullable=True),
        sa.Column('net', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'ts_code', name='uq_kpl_lhb_date_code'),
    )
    with op.batch_alter_table('kpl_lhb', schema=None) as batch_op:
        batch_op.create_index('ix_kpl_lhb_trade_date', ['trade_date'], unique=False)
        batch_op.create_index('ix_kpl_lhb_ts_code', ['ts_code'], unique=False)

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

    op.create_table(
        'kpl_auction',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('ts_code', sa.String(length=16), nullable=False),
        sa.Column('name', sa.String(length=32), nullable=True),
        sa.Column('tag', sa.String(length=32), nullable=True),
        sa.Column('direction', sa.Integer(), nullable=True),
        sa.Column('themes', sa.String(length=128), nullable=True),
        sa.Column('pct_chg', sa.Float(), nullable=True),
        sa.Column('turnover', sa.Float(), nullable=True),
        sa.Column('market_cap', sa.Float(), nullable=True),
        sa.Column('buy_amount', sa.Float(), nullable=True),
        sa.Column('sell_amount', sa.Float(), nullable=True),
        sa.Column('net_amount', sa.Float(), nullable=True),
        sa.Column('big_order_buy', sa.Float(), nullable=True),
        sa.Column('big_order_sell', sa.Float(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'ts_code', name='uq_kpl_auction_date_code'),
    )
    with op.batch_alter_table('kpl_auction', schema=None) as batch_op:
        batch_op.create_index('ix_kpl_auction_trade_date', ['trade_date'], unique=False)
        batch_op.create_index('ix_kpl_auction_ts_code', ['ts_code'], unique=False)


def downgrade() -> None:
    for tbl in ('kpl_auction', 'kpl_lhb_seat', 'kpl_lhb', 'kpl_broken',
                'kpl_consecutive', 'kpl_ladder', 'kpl_sentiment'):
        op.drop_table(tbl)
