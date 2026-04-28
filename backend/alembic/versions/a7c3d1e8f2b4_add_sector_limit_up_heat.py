"""add sector_limit_up_heat table

Revision ID: a7c3d1e8f2b4
Revises: f44eb6bd19c6
Create Date: 2026-04-27 15:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7c3d1e8f2b4'
down_revision: Union[str, Sequence[str], None] = 'f44eb6bd19c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sector_limit_up_heat',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('sector_code', sa.String(length=32), nullable=False),
        sa.Column('sector_name', sa.String(length=64), nullable=False),
        sa.Column('limit_up_count', sa.Integer(), nullable=False),
        sa.Column('max_consecutive', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'sector_code', name='uq_sector_heat_date_code'),
    )
    with op.batch_alter_table('sector_limit_up_heat', schema=None) as batch_op:
        batch_op.create_index('ix_sector_limit_up_heat_trade_date', ['trade_date'], unique=False)
        batch_op.create_index('ix_sector_limit_up_heat_sector_code', ['sector_code'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('sector_limit_up_heat', schema=None) as batch_op:
        batch_op.drop_index('ix_sector_limit_up_heat_sector_code')
        batch_op.drop_index('ix_sector_limit_up_heat_trade_date')
    op.drop_table('sector_limit_up_heat')
