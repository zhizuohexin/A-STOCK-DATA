"""add KPL phase3 tables: dashboard/emotion/youzi/history_analysis/sector_news/news_selected

Revision ID: g8c4e7f2a9d1
Revises: f3b7a9d2e1c5
Create Date: 2026-04-29 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'g8c4e7f2a9d1'
down_revision: Union[str, Sequence[str], None] = 'f3b7a9d2e1c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'kpl_dashboard',
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('today_zhang_ting', sa.Integer(), nullable=True),
        sa.Column('last_zhang_ting', sa.Integer(), nullable=True),
        sa.Column('today_feng_ban', sa.Float(), nullable=True),
        sa.Column('last_feng_ban_rate', sa.Float(), nullable=True),
        sa.Column('today_die_ting', sa.Integer(), nullable=True),
        sa.Column('last_die_ting', sa.Integer(), nullable=True),
        sa.Column('up_count', sa.Integer(), nullable=True),
        sa.Column('down_count', sa.Integer(), nullable=True),
        sa.Column('flat_count', sa.Integer(), nullable=True),
        sa.Column('intensity', sa.Integer(), nullable=True),
        sa.Column('last_zt_money', sa.Float(), nullable=True),
        sa.Column('last_lb_money', sa.Float(), nullable=True),
        sa.Column('snapshot_time', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('trade_date'),
    )

    op.create_table(
        'kpl_dashboard_top',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('direction', sa.String(length=8), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('ts_code', sa.String(length=16), nullable=False),
        sa.Column('name', sa.String(length=32), nullable=True),
        sa.Column('pct_chg', sa.Float(), nullable=True),
        sa.Column('sector', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'direction', 'rank', name='uq_kpl_dashboard_top'),
    )
    with op.batch_alter_table('kpl_dashboard_top', schema=None) as bop:
        bop.create_index('ix_kpl_dashboard_top_trade_date', ['trade_date'])

    op.create_table(
        'kpl_dashboard_sector',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('sector_code', sa.String(length=32), nullable=False),
        sa.Column('sector_name', sa.String(length=64), nullable=True),
        sa.Column('pct_chg', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'sector_code', name='uq_kpl_dashboard_sector'),
    )
    with op.batch_alter_table('kpl_dashboard_sector', schema=None) as bop:
        bop.create_index('ix_kpl_dashboard_sector_trade_date', ['trade_date'])

    op.create_table(
        'kpl_emotion',
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('up_count', sa.Integer(), nullable=True),
        sa.Column('down_count', sa.Integer(), nullable=True),
        sa.Column('limit_up', sa.Integer(), nullable=True),
        sa.Column('limit_down', sa.Integer(), nullable=True),
        sa.Column('today_vol', sa.Float(), nullable=True),
        sa.Column('yest_vol', sa.Float(), nullable=True),
        sa.Column('vol_ratio', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('trade_date'),
    )

    op.create_table(
        'kpl_youzi',
        sa.Column('trader_id', sa.String(length=16), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('trader_id'),
    )

    op.create_table(
        'kpl_youzi_trade',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('trader_id', sa.String(length=16), nullable=False),
        sa.Column('side', sa.String(length=2), nullable=False),
        sa.Column('seat_name', sa.String(length=128), nullable=True),
        sa.Column('ts_code', sa.String(length=16), nullable=False),
        sa.Column('buy', sa.Float(), nullable=True),
        sa.Column('sell', sa.Float(), nullable=True),
        sa.Column('net_amount', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'trader_id', 'side', 'ts_code', 'seat_name', name='uq_kpl_youzi_trade'),
    )
    with op.batch_alter_table('kpl_youzi_trade', schema=None) as bop:
        bop.create_index('ix_kpl_youzi_trade_trade_date', ['trade_date'])
        bop.create_index('ix_kpl_youzi_trade_trader_id', ['trader_id'])
        bop.create_index('ix_kpl_youzi_trade_ts_code', ['ts_code'])

    op.create_table(
        'kpl_history_analysis',
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('limit_up', sa.Integer(), nullable=True),
        sa.Column('limit_down', sa.Integer(), nullable=True),
        sa.Column('broken', sa.Integer(), nullable=True),
        sa.Column('blown', sa.Integer(), nullable=True),
        sa.Column('blown_rate', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('trade_date'),
    )

    op.create_table(
        'kpl_sector_news',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sector_code', sa.String(length=32), nullable=False),
        sa.Column('news_id', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=True),
        sa.Column('news_time', sa.DateTime(), nullable=True),
        sa.Column('news_type', sa.String(length=8), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sector_code', 'news_id', name='uq_kpl_sector_news'),
    )
    with op.batch_alter_table('kpl_sector_news', schema=None) as bop:
        bop.create_index('ix_kpl_sector_news_sector_code', ['sector_code'])
        bop.create_index('ix_kpl_sector_news_news_time', ['news_time'])

    op.create_table(
        'kpl_news_selected',
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=True),
        sa.Column('account', sa.String(length=64), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.Column('img_url', sa.String(length=256), nullable=True),
        sa.Column('related', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('article_id'),
    )
    with op.batch_alter_table('kpl_news_selected', schema=None) as bop:
        bop.create_index('ix_kpl_news_selected_create_time', ['create_time'])


def downgrade() -> None:
    for tbl in (
        'kpl_news_selected', 'kpl_sector_news', 'kpl_history_analysis',
        'kpl_youzi_trade', 'kpl_youzi', 'kpl_emotion',
        'kpl_dashboard_sector', 'kpl_dashboard_top', 'kpl_dashboard',
    ):
        op.drop_table(tbl)
