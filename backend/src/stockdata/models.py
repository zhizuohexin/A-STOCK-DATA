from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Float, Index, Integer, String, Text, UniqueConstraint, func
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


class StockSector(Base):
    """股票 ↔ 板块多对多关联。一只股通常属于 1 个行业 + 多个概念。"""

    __tablename__ = "stock_sectors"

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    sector_code: Mapped[str] = mapped_column(String(32), primary_key=True)
    src: Mapped[str | None] = mapped_column(String(16), nullable=True)  # EM / THS
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_stock_sectors_sector", "sector_code"),)


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


class _JournalMixin:
    """三个笔记模块共用字段。独立表，但字段一致。"""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entry_date: Mapped[date] = mapped_column(Date, index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    # JSON 数组字符串：["/uploads/trading/2026-04/xxx.jpg", ...]
    images: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class KplSentiment(Base):
    """开盘啦大盘情绪打分（每日一行）。"""

    __tablename__ = "kpl_sentiment"

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    limit_up: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_limit_up: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_down: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_limit_down: Mapped[int | None] = mapped_column(Integer, nullable=True)
    up_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    down_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    flat_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class KplLadder(Base):
    """开盘啦连板梯队汇总（每日一行）。"""

    __tablename__ = "kpl_ladder"

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    first_board: Mapped[int | None] = mapped_column(Integer, nullable=True)
    second_board: Mapped[int | None] = mapped_column(Integer, nullable=True)
    third_board: Mapped[int | None] = mapped_column(Integer, nullable=True)
    high_board: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    comment: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class KplConsecutive(Base):
    """开盘啦连板个股明细（每日 N 行，含题材）。"""

    __tablename__ = "kpl_consecutive"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    ts_code: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Float, nullable=True)
    theme: Mapped[str | None] = mapped_column(String(128), nullable=True)
    board_desc: Mapped[str | None] = mapped_column(String(32), nullable=True)
    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("trade_date", "ts_code", name="uq_kpl_consec_date_code"),)


class KplBroken(Base):
    """开盘啦炸板池（每日 N 行，含 sector 题材）。"""

    __tablename__ = "kpl_broken"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    ts_code: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Float, nullable=True)
    sector: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("trade_date", "ts_code", name="uq_kpl_broken_date_code"),)


class KplLhb(Base):
    """开盘啦龙虎榜个股汇总（每日 N 行）。"""

    __tablename__ = "kpl_lhb"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    ts_code: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    buy_in: Mapped[float | None] = mapped_column(Float, nullable=True)
    net: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("trade_date", "ts_code", name="uq_kpl_lhb_date_code"),)


class KplLhbSeat(Base):
    """开盘啦龙虎榜席位明细（每日每股每席位一行，含 isDY 游资标识）。"""

    __tablename__ = "kpl_lhb_seat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    ts_code: Mapped[str] = mapped_column(String(16), index=True)
    side: Mapped[str] = mapped_column(String(2))  # B=买 / S=卖
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    broker: Mapped[str] = mapped_column(String(128))
    buy_in: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_out: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_buy: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_dy: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("trade_date", "ts_code", "side", "rank", "broker", name="uq_kpl_lhb_seat"),
        Index("ix_kpl_lhb_seat_broker", "broker"),
    )


class KplSectorLadder(Base):
    """开盘啦板块涨停梯队：每个热点板块下的涨停个股 + 连板描述。"""

    __tablename__ = "kpl_sector_ladder"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    sector_code: Mapped[str] = mapped_column(String(32), index=True)
    sector_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ts_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    td_type: Mapped[str | None] = mapped_column(String(8), nullable=True)
    tips: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("trade_date", "sector_code", "ts_code", name="uq_kpl_sector_ladder"),
    )


class KplSectorsHeat(Base):
    """开盘啦板块强度排行（仅当天可拉，含 count 涨停数）。

    与自己 SQL 算的 sector_limit_up_heat 并存，两个数据源对比才有判断价值。
    """

    __tablename__ = "kpl_sectors_heat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    sector_code: Mapped[str] = mapped_column(String(32))
    sector_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("trade_date", "sector_code", name="uq_kpl_sectors_heat"),)


class KplAuction(Base):
    """开盘啦尾盘抢筹/竞价异动（每日 N 行，含 themes）。"""

    __tablename__ = "kpl_auction"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    ts_code: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tag: Mapped[str | None] = mapped_column(String(32), nullable=True)
    direction: Mapped[int | None] = mapped_column(Integer, nullable=True)
    themes: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Float, nullable=True)
    turnover: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    buy_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    big_order_buy: Mapped[float | None] = mapped_column(Float, nullable=True)
    big_order_sell: Mapped[float | None] = mapped_column(Float, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("trade_date", "ts_code", name="uq_kpl_auction_date_code"),)


class KplWithdrawal(Base):
    """开盘啦大幅回撤池（高位跳水个股）。"""

    __tablename__ = "kpl_withdrawal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    ts_code: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Float, nullable=True)
    withdrawal_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("trade_date", "ts_code", name="uq_kpl_withdrawal"),)


class KplMarketLadder(Base):
    """开盘啦空间板梯队（最高板/连板/首板分级）。tip 字段为开盘啦原始等级编号。"""

    __tablename__ = "kpl_market_ladder"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    tip: Mapped[str] = mapped_column(String(8), index=True)
    ts_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tips: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("trade_date", "ts_code", name="uq_kpl_market_ladder"),)


class KplNews(Base):
    """开盘啦题材新闻。news_id 用接口给的 id 主键。"""

    __tablename__ = "kpl_news"

    news_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    keyword: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    news_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String(8), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class KplNewsStock(Base):
    """新闻↔个股关联（每条新闻关联多只股，含 isTop 龙头标识）。"""

    __tablename__ = "kpl_news_stock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_id: Mapped[int] = mapped_column(Integer, index=True)
    ts_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_top: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (UniqueConstraint("news_id", "ts_code", name="uq_kpl_news_stock"),)


class KplConceptionHistory(Base):
    """开盘啦盘中题材异动事件流（按时间戳，含板块涨跌幅）。"""

    __tablename__ = "kpl_conception_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    event_time: Mapped[int] = mapped_column(Integer)  # unix 时间戳
    plate_text: Mapped[str] = mapped_column(String(128))  # "算力概念持续走强"
    plate_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    plate_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    plate_je: Mapped[str | None] = mapped_column(String(32), nullable=True)
    plate_zdf: Mapped[str | None] = mapped_column(String(16), nullable=True)
    event_type: Mapped[str | None] = mapped_column(String(8), nullable=True)
    color: Mapped[str | None] = mapped_column(String(8), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("trade_date", "event_time", "plate_text", name="uq_kpl_conception_event"),
    )


class KplHistoryStrength(Base):
    """开盘啦历史市场强度曲线（每日一行，含 strength 值 + 涨停/最大连板/跳水家数）。"""

    __tablename__ = "kpl_history_strength"

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    strength: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_up_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_consecutive: Mapped[int | None] = mapped_column(Integer, nullable=True)
    big_drop_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class KplDashboard(Base):
    """开盘啦竞价全景看板 board 段（15:00 快照入库）。"""

    __tablename__ = "kpl_dashboard"

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    today_zhang_ting: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_zhang_ting: Mapped[int | None] = mapped_column(Integer, nullable=True)
    today_feng_ban: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_feng_ban_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    today_die_ting: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_die_ting: Mapped[int | None] = mapped_column(Integer, nullable=True)
    up_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    down_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    flat_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intensity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_zt_money: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_lb_money: Mapped[float | None] = mapped_column(Float, nullable=True)
    snapshot_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class KplDashboardTop(Base):
    """开盘啦竞价风向标（topUp/topDown 各 3 只）。"""

    __tablename__ = "kpl_dashboard_top"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    direction: Mapped[str] = mapped_column(String(8))  # up / down
    rank: Mapped[int] = mapped_column(Integer)
    ts_code: Mapped[str] = mapped_column(String(16))
    name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Float, nullable=True)
    sector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("trade_date", "direction", "rank", name="uq_kpl_dashboard_top"),)


class KplDashboardSector(Base):
    """竞价看板的板块涨跌面。"""

    __tablename__ = "kpl_dashboard_sector"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    sector_code: Mapped[str] = mapped_column(String(32))
    sector_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("trade_date", "sector_code", name="uq_kpl_dashboard_sector"),)


class KplEmotion(Base):
    """开盘啦实时情绪/分布快照（15:00 入库当日终值）。"""

    __tablename__ = "kpl_emotion"

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    up_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    down_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_up: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_down: Mapped[int | None] = mapped_column(Integer, nullable=True)
    today_vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    yest_vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    vol_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class KplYouzi(Base):
    """开盘啦游资名册（id 来自 KPL）。"""

    __tablename__ = "kpl_youzi"

    trader_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class KplYouziTrade(Base):
    """游资当日操盘明细（每条对应一个席位 + 个股 + 买/卖）。"""

    __tablename__ = "kpl_youzi_trade"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    trader_id: Mapped[str] = mapped_column(String(16), index=True)
    side: Mapped[str] = mapped_column(String(2))  # B / S
    seat_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ts_code: Mapped[str] = mapped_column(String(16), index=True)
    buy: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("trade_date", "trader_id", "side", "ts_code", "seat_name", name="uq_kpl_youzi_trade"),
        Index("ix_kpl_youzi_trade_ts_code", "ts_code"),
    )


class KplHistoryAnalysis(Base):
    """开盘啦长周期涨跌停趋势（含炸板率 blown_rate）。"""

    __tablename__ = "kpl_history_analysis"

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    limit_up: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_down: Mapped[int | None] = mapped_column(Integer, nullable=True)
    broken: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blown: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blown_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class KplSectorNews(Base):
    """开盘啦板块新闻流（按 sector_code 维度）。"""

    __tablename__ = "kpl_sector_news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sector_code: Mapped[str] = mapped_column(String(32), index=True)
    news_id: Mapped[str] = mapped_column(String(32))
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    news_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    news_type: Mapped[str | None] = mapped_column(String(8), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("sector_code", "news_id", name="uq_kpl_sector_news"),)


class KplNewsSelected(Base):
    """开盘啦编辑精选深度文章（含关联板块/股 JSON）。"""

    __tablename__ = "kpl_news_selected"

    article_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    account: Mapped[str | None] = mapped_column(String(64), nullable=True)
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    img_url: Mapped[str | None] = mapped_column(String(256), nullable=True)
    related: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: [["801001","芯片","1.07"], ["001309","德明利","1.65"]]
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SectorLimitUpHeat(Base):
    """涨停板块热度（concept 模式）。仅入库当日涨停只数 >= 阈值的板块。"""

    __tablename__ = "sector_limit_up_heat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    sector_code: Mapped[str] = mapped_column(String(32), index=True)
    sector_name: Mapped[str] = mapped_column(String(64))
    limit_up_count: Mapped[int] = mapped_column(Integer)
    max_consecutive: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("trade_date", "sector_code", name="uq_sector_heat_date_code"),
    )


class TradingRecord(_JournalMixin, Base):
    """我的交易记录。"""

    __tablename__ = "trading_records"


class ReviewReference(_JournalMixin, Base):
    """复盘参考文献。"""

    __tablename__ = "review_references"


class MasterTracking(_JournalMixin, Base):
    """学习的实盘高手跟踪。"""

    __tablename__ = "master_tracking"
