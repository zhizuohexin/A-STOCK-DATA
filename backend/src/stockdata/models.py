from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Float, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from stockdata.db import Base


class Stock(Base):
    __tablename__ = "stocks"

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(32))
    area: Mapped[str | None] = mapped_column(String(32), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(64), nullable=True)
    market: Mapped[str | None] = mapped_column(String(16), nullable=True)
    list_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class DailyQuote(Base):
    __tablename__ = "daily_quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(16), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    open: Mapped[float | None] = mapped_column(Float, nullable=True)
    high: Mapped[float | None] = mapped_column(Float, nullable=True)
    low: Mapped[float | None] = mapped_column(Float, nullable=True)
    close: Mapped[float | None] = mapped_column(Float, nullable=True)
    pre_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    change: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Float, nullable=True)
    vol: Mapped[float | None] = mapped_column(Float, nullable=True)  # 手
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)  # 千元
    turnover_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ts_code", "trade_date", name="uq_daily_quotes_code_date"),
        Index("ix_daily_quotes_date_code", "trade_date", "ts_code"),
    )


class LimitUpDaily(Base):
    """涨停板池（含连板数）。"""

    __tablename__ = "limit_up_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(16), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    close: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    fd_amount: Mapped[float | None] = mapped_column(Float, nullable=True)  # 封单金额
    first_time: Mapped[str | None] = mapped_column(String(16), nullable=True)  # 首次封板时间
    last_time: Mapped[str | None] = mapped_column(String(16), nullable=True)  # 最后封板时间
    open_times: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 炸板次数
    up_stat: Mapped[str | None] = mapped_column(String(16), nullable=True)  # 涨停统计
    limit_times: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 连板数
    limit: Mapped[str | None] = mapped_column(String(8), nullable=True)  # U/D/Z 涨停/跌停/炸板
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("ts_code", "trade_date", name="uq_limit_up_code_date"),)


class Sector(Base):
    """板块（行业/概念）。"""

    __tablename__ = "sectors"

    ts_code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(16))  # I=行业 C=概念
    src: Mapped[str | None] = mapped_column(String(32), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class SectorDaily(Base):
    """板块日线。"""

    __tablename__ = "sector_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sector_code: Mapped[str] = mapped_column(String(32), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    close: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Float, nullable=True)
    vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("sector_code", "trade_date", name="uq_sector_daily_code_date"),)


class IntradayBar(Base):
    """盘中1分钟K线（滚动保留，次日清理）。"""

    __tablename__ = "intraday_bars"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(16), index=True)
    bar_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    open: Mapped[float | None] = mapped_column(Float, nullable=True)
    high: Mapped[float | None] = mapped_column(Float, nullable=True)
    low: Mapped[float | None] = mapped_column(Float, nullable=True)
    close: Mapped[float | None] = mapped_column(Float, nullable=True)
    vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (UniqueConstraint("ts_code", "bar_time", name="uq_intraday_code_time"),)


class JobRun(Base):
    """任务执行日志（给前端看健康状态）。"""

    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_name: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16))  # success/failed/running
    message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    rows_affected: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
