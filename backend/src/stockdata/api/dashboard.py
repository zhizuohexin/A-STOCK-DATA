from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from stockdata.analytics.rankings import latest_trade_date
from stockdata.db import get_session

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(
    trade_date: date | None = None,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """复盘首页一屏数据。"""
    if trade_date is None:
        trade_date = latest_trade_date(session)
    if trade_date is None:
        return {
            "trade_date": None,
            "limit_up_count": 0,
            "limit_down_count": 0,
            "broken_limit_count": 0,
            "consecutive_breakdown": [],
            "market_distribution": {"up": 0, "flat": 0, "down": 0, "total": 0},
            "top_gainers": [],
            "top_losers": [],
            "top_amount": [],
            "top_sectors": [],
        }

    params = {"td": trade_date}

    lu_count = session.execute(
        text('SELECT COUNT(*) FROM limit_up_daily WHERE trade_date=:td AND "limit"=\'U\''),
        params,
    ).scalar() or 0

    ld_count = session.execute(
        text('SELECT COUNT(*) FROM limit_up_daily WHERE trade_date=:td AND "limit"=\'D\''),
        params,
    ).scalar() or 0

    broken_count = session.execute(
        text(
            'SELECT COUNT(*) FROM limit_up_daily '
            'WHERE trade_date=:td AND "limit"=\'U\' AND open_times IS NOT NULL AND open_times > 0'
        ),
        params,
    ).scalar() or 0

    consec_rows = session.execute(
        text(
            'SELECT limit_times, COUNT(*) FROM limit_up_daily '
            'WHERE trade_date=:td AND "limit"=\'U\' GROUP BY limit_times'
        ),
        params,
    ).all()
    buckets = {"1板": 0, "2连": 0, "3连": 0, "4连+": 0}
    for lt, cnt in consec_rows:
        if lt is None or lt <= 1:
            buckets["1板"] += cnt
        elif lt == 2:
            buckets["2连"] += cnt
        elif lt == 3:
            buckets["3连"] += cnt
        else:
            buckets["4连+"] += cnt

    dist_rows = session.execute(
        text(
            """
            SELECT
              CASE
                WHEN pct_chg > 0.01 THEN 'up'
                WHEN pct_chg < -0.01 THEN 'down'
                ELSE 'flat'
              END AS direction,
              COUNT(*) AS cnt
            FROM daily_quotes
            WHERE trade_date=:td
            GROUP BY direction
            """
        ),
        params,
    ).all()
    market_dist = {"up": 0, "flat": 0, "down": 0}
    for d, c in dist_rows:
        if d in market_dist:
            market_dist[d] = c
    total = sum(market_dist.values())

    top_gainers = session.execute(
        text(
            """
            SELECT q.ts_code, s.name, s.industry, q.close, q.pct_chg, q.amount
            FROM daily_quotes q
            LEFT JOIN stocks s ON s.ts_code = q.ts_code
            WHERE q.trade_date=:td
            ORDER BY q.pct_chg DESC NULLS LAST
            LIMIT 10
            """
        ),
        params,
    ).mappings().all()

    top_losers = session.execute(
        text(
            """
            SELECT q.ts_code, s.name, s.industry, q.close, q.pct_chg, q.amount
            FROM daily_quotes q
            LEFT JOIN stocks s ON s.ts_code = q.ts_code
            WHERE q.trade_date=:td AND q.pct_chg IS NOT NULL
            ORDER BY q.pct_chg ASC
            LIMIT 10
            """
        ),
        params,
    ).mappings().all()

    top_amount = session.execute(
        text(
            """
            SELECT q.ts_code, s.name, s.industry, q.close, q.pct_chg, q.amount
            FROM daily_quotes q
            LEFT JOIN stocks s ON s.ts_code = q.ts_code
            WHERE q.trade_date=:td AND q.amount IS NOT NULL
            ORDER BY q.amount DESC
            LIMIT 10
            """
        ),
        params,
    ).mappings().all()

    top_sectors = session.execute(
        text(
            """
            SELECT sd.sector_code, sd.name, sd.close, sd.pct_chg, sd.amount, s.type
            FROM sector_daily sd
            LEFT JOIN sectors s ON s.ts_code = sd.sector_code
            WHERE sd.trade_date=:td
            ORDER BY sd.pct_chg DESC NULLS LAST
            LIMIT 10
            """
        ),
        params,
    ).mappings().all()

    return {
        "trade_date": trade_date,
        "limit_up_count": lu_count,
        "limit_down_count": ld_count,
        "broken_limit_count": broken_count,
        "consecutive_breakdown": [{"level": k, "count": v} for k, v in buckets.items()],
        "market_distribution": {**market_dist, "total": total},
        "top_gainers": [dict(r) for r in top_gainers],
        "top_losers": [dict(r) for r in top_losers],
        "top_amount": [dict(r) for r in top_amount],
        "top_sectors": [dict(r) for r in top_sectors],
    }
