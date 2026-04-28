"""Upsert helpers — each table has a (ts_code, trade_date)-style unique key."""

from datetime import date as date_type
from typing import Any

from sqlalchemy import delete as sa_delete, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from stockdata.models import (
    DailyQuote,
    IntradayBar,
    JobRun,
    KplAuction,
    KplBroken,
    KplConsecutive,
    KplLadder,
    KplLhb,
    KplLhbSeat,
    KplSentiment,
    LimitUpDaily,
    Sector,
    SectorDaily,
    SectorLimitUpHeat,
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


def recompute_sector_heat(session: Session, trade_date: date_type, min_count: int = 10) -> int:
    """重算某日 concept 板块涨停热度并入库（仅 limit_up_count >= min_count）。幂等。"""
    session.execute(sa_delete(SectorLimitUpHeat).where(SectorLimitUpHeat.trade_date == trade_date))
    rows = session.execute(
        text(
            """
            SELECT s.ts_code AS sector_code, s.name AS sector_name,
                   COUNT(*) AS limit_up_count, MAX(l.limit_times) AS max_consecutive
            FROM limit_up_daily l
            JOIN stock_sectors ss ON ss.ts_code = l.ts_code
            JOIN sectors s ON s.ts_code = ss.sector_code AND s.type='C'
            WHERE l.trade_date = :td AND l."limit" = 'U'
            GROUP BY s.ts_code, s.name
            HAVING COUNT(*) >= :min_count
            """
        ),
        {"td": trade_date, "min_count": min_count},
    ).mappings().all()
    if not rows:
        return 0
    session.execute(
        SectorLimitUpHeat.__table__.insert(),
        [{"trade_date": trade_date, **dict(r)} for r in rows],
    )
    return len(rows)


def upsert_kpl_sentiment(session: Session, row: dict) -> int:
    return _upsert(session, KplSentiment, [row], ["trade_date"])


def upsert_kpl_ladder(session: Session, row: dict) -> int:
    return _upsert(session, KplLadder, [row], ["trade_date"])


def upsert_kpl_consecutive(session: Session, rows: list[dict]) -> int:
    return _upsert(session, KplConsecutive, rows, ["trade_date", "ts_code"])


def upsert_kpl_broken(session: Session, rows: list[dict]) -> int:
    return _upsert(session, KplBroken, rows, ["trade_date", "ts_code"])


def upsert_kpl_lhb(session: Session, rows: list[dict]) -> int:
    return _upsert(session, KplLhb, rows, ["trade_date", "ts_code"])


def upsert_kpl_lhb_seat(session: Session, rows: list[dict]) -> int:
    return _upsert(session, KplLhbSeat, rows, ["trade_date", "ts_code", "side", "rank", "broker"])


def upsert_kpl_auction(session: Session, rows: list[dict]) -> int:
    return _upsert(session, KplAuction, rows, ["trade_date", "ts_code"])


def attach_kpl_themes(session: Session, ts_code: str, theme_str: str | None) -> int:
    """把开盘啦给的题材字符串（"光刻胶、化工"）拆开后入 stock_sectors（src='KPL'）。

    板块 name 找不到则自动建（type='C', src='KPL'）。返回新增关联数。
    """
    if not theme_str:
        return 0
    import re
    import uuid
    from datetime import datetime as _dt

    names = [t.strip() for t in re.split(r"[、,，]", theme_str) if t.strip()]
    inserted = 0
    for name in names:
        if len(name) > 32:
            continue
        # 找现有 sector
        r = session.execute(
            text("SELECT ts_code FROM sectors WHERE name=:n LIMIT 1"),
            {"n": name},
        ).first()
        if r:
            sec_code = r[0]
        else:
            sec_code = f"KPL_{uuid.uuid4().hex[:8].upper()}"
            session.add(Sector(ts_code=sec_code, name=name, type="C", src="KPL"))
            session.flush()
        # 关联
        existing = session.execute(
            text("SELECT 1 FROM stock_sectors WHERE ts_code=:c AND sector_code=:s"),
            {"c": ts_code, "s": sec_code},
        ).first()
        if not existing:
            session.add(StockSector(
                ts_code=ts_code, sector_code=sec_code, src="KPL",
                updated_at=_dt.utcnow(),
            ))
            inserted += 1
    return inserted


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
