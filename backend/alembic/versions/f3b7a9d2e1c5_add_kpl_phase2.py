"""add KPL phase2 tables: withdrawal/market_ladder/news/conception_history/history_strength

Revision ID: f3b7a9d2e1c5
Revises: e6f9a2c4d8b3
Create Date: 2026-04-29 13:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3b7a9d2e1c5'
down_revision: Union[str, Sequence[str], None] = 'e6f9a2c4d8b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'kpl_withdrawal',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('ts_code', sa.String(length=16), nullable=False),
        sa.Column('name', sa.String(length=32), nullable=True),
        sa.Column('pct_chg', sa.Float(), nullable=True),
        sa.Column('withdrawal_pct', sa.Float(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'ts_code', name='uq_kpl_withdrawal'),
    )
    with op.batch_alter_table('kpl_withdrawal', schema=None) as bop:
        bop.create_index('ix_kpl_withdrawal_trade_date', ['trade_date'])
        bop.create_index('ix_kpl_withdrawal_ts_code', ['ts_code'])

    op.create_table(
        'kpl_market_ladder',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('tip', sa.String(length=8), nullable=False),
        sa.Column('ts_code', sa.String(length=16), nullable=False),
        sa.Column('stock_name', sa.String(length=32), nullable=True),
        sa.Column('tips', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'ts_code', name='uq_kpl_market_ladder'),
    )
    with op.batch_alter_table('kpl_market_ladder', schema=None) as bop:
        bop.create_index('ix_kpl_market_ladder_trade_date', ['trade_date'])
        bop.create_index('ix_kpl_market_ladder_tip', ['tip'])
        bop.create_index('ix_kpl_market_ladder_ts_code', ['ts_code'])

    op.create_table(
        'kpl_news',
        sa.Column('news_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=True),
        sa.Column('sector', sa.String(length=64), nullable=True),
        sa.Column('keyword', sa.String(length=64), nullable=True),
        sa.Column('source', sa.String(length=32), nullable=True),
        sa.Column('news_time', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=8), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('news_id'),
    )
    with op.batch_alter_table('kpl_news', schema=None) as bop:
        bop.create_index('ix_kpl_news_keyword', ['keyword'])
        bop.create_index('ix_kpl_news_news_time', ['news_time'])

    op.create_table(
        'kpl_news_stock',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('news_id', sa.Integer(), nullable=False),
        sa.Column('ts_code', sa.String(length=16), nullable=False),
        sa.Column('stock_name', sa.String(length=32), nullable=True),
        sa.Column('pct_chg', sa.Float(), nullable=True),
        sa.Column('is_top', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('news_id', 'ts_code', name='uq_kpl_news_stock'),
    )
    with op.batch_alter_table('kpl_news_stock', schema=None) as bop:
        bop.create_index('ix_kpl_news_stock_news_id', ['news_id'])
        bop.create_index('ix_kpl_news_stock_ts_code', ['ts_code'])

    op.create_table(
        'kpl_conception_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('event_time', sa.Integer(), nullable=False),
        sa.Column('plate_text', sa.String(length=128), nullable=False),
        sa.Column('plate_code', sa.String(length=32), nullable=True),
        sa.Column('plate_name', sa.String(length=64), nullable=True),
        sa.Column('plate_je', sa.String(length=32), nullable=True),
        sa.Column('plate_zdf', sa.String(length=16), nullable=True),
        sa.Column('event_type', sa.String(length=8), nullable=True),
        sa.Column('color', sa.String(length=8), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'event_time', 'plate_text', name='uq_kpl_conception_event'),
    )
    with op.batch_alter_table('kpl_conception_history', schema=None) as bop:
        bop.create_index('ix_kpl_conception_history_trade_date', ['trade_date'])

    op.create_table(
        'kpl_history_strength',
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('strength', sa.Integer(), nullable=True),
        sa.Column('limit_up_count', sa.Integer(), nullable=True),
        sa.Column('max_consecutive', sa.Integer(), nullable=True),
        sa.Column('big_drop_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('trade_date'),
    )


def downgrade() -> None:
    for tbl in (
        'kpl_history_strength', 'kpl_conception_history',
        'kpl_news_stock', 'kpl_news',
        'kpl_market_ladder', 'kpl_withdrawal',
    ):
        op.drop_table(tbl)
