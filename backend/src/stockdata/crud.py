"""Upsert helpers — each table has a (ts_code, trade_date)-style unique key."""

from typing import Any

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from stockdata.models import (
    DailyQuote,
    IntradayBar,
    JobRun,
    LimitUpDaily,
    Sector,
    SectorDaily,
    Stock,
    StockSector,
)


def _upsert(session: Session, model: type, rows: list[dict[str, Any]], conflict_cols: list[str]) -> int:
    if not rows:
        return 0
    table = model.__table__
    stmt = sqlite_insert(table).values(rows)
    update_cols = {
        c.name: stmt.excluded[c.name]
        for c in table.columns
        if c.name not in conflict_cols and c.name != "id" and c.name != "created_at"
    }
    stmt = stmt.on_conflict_do_update(index_elements=conflict_cols, set_=update_cols)
    result = session.execute(stmt)
    return result.rowcount or len(rows)


def upsert_stocks(session: Session, rows: list[dict[str, Any]]) -> int:
    return _upsert(session, Stock, rows, ["ts_code"])


def upsert_daily_quotes(session: Session, rows: list[dict[str, Any]]) -> int:
    return _upsert(session, DailyQuote, rows, ["ts_code", "trade_date"])


def upsert_limit_up(session: Session, rows: list[dict[str, Any]]) -> int:
    return _upsert(session, LimitUpDaily, rows, ["ts_code", "trade_date"])


def upsert_sectors(session: Session, rows: list[dict[str, Any]]) -> int:
    return _upsert(session, Sector, rows, ["ts_code"])


def upsert_sector_daily(session: Session, rows: list[dict[str, Any]]) -> int:
    return _upsert(session, SectorDaily, rows, ["sector_code", "trade_date"])


def upsert_intraday_bars(session: Session, rows: list[dict[str, Any]]) -> int:
    return _upsert(session, IntradayBar, rows, ["ts_code", "bar_time"])


def upsert_stock_sectors(session: Session, rows: list[dict[str, Any]]) -> int:
    return _upsert(session, StockSector, rows, ["ts_code", "sector_code"])


def replace_stock_sectors_for_src(session: Session, src: str, rows: list[dict[str, Any]]) -> int:
    """全量替换某个 src（EM/THS）的映射：先删后插。"""
    from sqlalchemy import delete

    session.execute(delete(StockSector).where(StockSector.src == src))
    if rows:
        session.execute(StockSector.__table__.insert(), rows)
    return len(rows)


def record_job(
    session: Session,
    job_name: str,
    status: str,
    message: str | None = None,
    rows_affected: int | None = None,
) -> JobRun:
    from datetime import datetime

    job = JobRun(
        job_name=job_name,
        status=status,
        message=message,
        rows_affected=rows_affected,
        finished_at=datetime.utcnow() if status != "running" else None,
    )
    session.add(job)
    session.commit()
    return job
