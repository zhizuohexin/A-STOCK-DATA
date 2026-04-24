"""N 日涨幅排行、板块涨幅排行。都是从 daily_quotes / sector_daily 现算。"""

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def top_n_day_gainers(
    session: Session,
    days: int,
    top: int = 10,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    """Compute N 日涨幅前 top 名。

    以 end_date 为基准，取过去 days 个交易日内最早一根 K 线的 close 作为基准。
    涨幅 = (end_close - base_close) / base_close * 100
    """
    filter_end = f"AND q.trade_date <= :end_date" if end_date else ""
    params: dict[str, Any] = {"days": days, "top": top}
    if end_date:
        params["end_date"] = end_date

    sql = f"""
    WITH ranked AS (
      SELECT
        q.ts_code,
        q.trade_date,
        q.close,
        ROW_NUMBER() OVER (PARTITION BY q.ts_code ORDER BY q.trade_date DESC) AS rn_end,
        ROW_NUMBER() OVER (PARTITION BY q.ts_code ORDER BY q.trade_date DESC) AS rn
      FROM daily_quotes q
      WHERE 1=1 {filter_end}
    ),
    window AS (
      SELECT ts_code, trade_date, close, rn
      FROM ranked
      WHERE rn <= :days
    ),
    agg AS (
      SELECT
        ts_code,
        MAX(CASE WHEN rn = 1 THEN close END) AS end_close,
        MAX(CASE WHEN rn = :days THEN close END) AS base_close,
        MAX(CASE WHEN rn = 1 THEN trade_date END) AS end_date,
        MAX(CASE WHEN rn = :days THEN trade_date END) AS base_date
      FROM window
      GROUP BY ts_code
      HAVING end_close IS NOT NULL AND base_close IS NOT NULL AND base_close > 0
    )
    SELECT
      a.ts_code,
      s.name,
      s.industry,
      a.base_date,
      a.end_date,
      a.base_close,
      a.end_close,
      ROUND((a.end_close - a.base_close) / a.base_close * 100, 2) AS pct_chg
    FROM agg a
    LEFT JOIN stocks s ON s.ts_code = a.ts_code
    ORDER BY pct_chg DESC
    LIMIT :top
    """
    rows = session.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


def top_sector_gainers(
    session: Session,
    trade_date: date,
    top: int = 5,
    sector_type: str | None = None,
) -> list[dict[str, Any]]:
    """某日板块涨幅前 top 名。"""
    sql = """
    SELECT sd.sector_code, sd.name, sd.close, sd.pct_chg, sd.vol, sd.amount, s.type
    FROM sector_daily sd
    LEFT JOIN sectors s ON s.ts_code = sd.sector_code
    WHERE sd.trade_date = :trade_date
    {type_filter}
    ORDER BY sd.pct_chg DESC
    LIMIT :top
    """
    type_filter = "AND s.type = :sector_type" if sector_type else ""
    params: dict[str, Any] = {"trade_date": trade_date, "top": top}
    if sector_type:
        params["sector_type"] = sector_type
    rows = session.execute(text(sql.format(type_filter=type_filter)), params).mappings().all()
    return [dict(r) for r in rows]


def latest_trade_date(session: Session) -> date | None:
    row = session.execute(text("SELECT MAX(trade_date) FROM daily_quotes")).scalar()
    return row  # type: ignore[return-value]
