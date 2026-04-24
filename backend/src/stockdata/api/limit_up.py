from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, delete, select, text
from sqlalchemy.orm import Session

from stockdata.analytics.rankings import latest_trade_date
from stockdata.api.schemas import DeleteResponse, LimitUpOut
from stockdata.crud import record_job, upsert_limit_up
from stockdata.db import get_session
from stockdata.models import LimitUpDaily
from stockdata.providers import get_provider

router = APIRouter(prefix="/limit-up", tags=["limit-up"])


@router.get("", response_model=list[LimitUpOut])
def list_limit_up(
    trade_date: date | None = None,
    min_limit_times: int | None = None,
    limit: int = 500,
    session: Session = Depends(get_session),
):
    stmt = select(LimitUpDaily).where(LimitUpDaily.limit == "U")
    conds = []
    if trade_date:
        conds.append(LimitUpDaily.trade_date == trade_date)
    if min_limit_times is not None:
        conds.append(LimitUpDaily.limit_times >= min_limit_times)
    if conds:
        stmt = stmt.where(and_(*conds))
    stmt = stmt.order_by(
        LimitUpDaily.trade_date.desc(),
        LimitUpDaily.limit_times.desc().nullslast(),
        LimitUpDaily.pct_chg.desc().nullslast(),
    ).limit(limit)
    return session.execute(stmt).scalars().all()


@router.get("/by-sector")
def limit_up_by_sector(
    trade_date: date | None = None,
    session: Session = Depends(get_session),
):
    """涨停按板块（申万行业）分组，每组含涨停个股明细，按涨停数降序。"""
    if trade_date is None:
        trade_date = latest_trade_date(session)
    if trade_date is None:
        return {"trade_date": None, "sectors": []}

    rows = session.execute(
        text(
            """
            SELECT COALESCE(s.industry, '未分类') AS industry,
                   l.ts_code, l.name, l.close, l.pct_chg,
                   l.limit_times, l.first_time, l.last_time, l.fd_amount, l.amount, l.open_times
            FROM limit_up_daily l
            LEFT JOIN stocks s ON s.ts_code = l.ts_code
            WHERE l.trade_date=:td AND l."limit"='U'
            ORDER BY l.limit_times DESC NULLS LAST, l.pct_chg DESC NULLS LAST
            """
        ),
        {"td": trade_date},
    ).mappings().all()

    groups: dict[str, list] = defaultdict(list)
    for r in rows:
        d = dict(r)
        ind = d.pop("industry")
        groups[ind].append(d)

    sectors = [
        {
            "industry": ind,
            "count": len(stocks),
            "max_consecutive": max((s.get("limit_times") or 0) for s in stocks),
            "stocks": stocks,
        }
        for ind, stocks in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    ]
    return {"trade_date": trade_date, "sectors": sectors}


@router.post("/backfill")
def backfill_limit_up(
    trade_date: date,
    provider: str = "tushare",
    session: Session = Depends(get_session),
):
    try:
        p = get_provider(provider)
        rows = p.fetch_limit_pool(trade_date, limit_type="U")
        n = upsert_limit_up(session, rows)
        session.commit()
        record_job(session, "backfill_limit_up", "success", message=str(trade_date), rows_affected=n)
        return {"rows_upserted": n}
    except Exception as e:
        session.rollback()
        record_job(session, "backfill_limit_up", "failed", message=str(e))
        raise HTTPException(500, str(e)) from e


@router.delete("", response_model=DeleteResponse)
def delete_limit_up(
    trade_date: date | None = None,
    code: str | None = None,
    session: Session = Depends(get_session),
):
    if not any([trade_date, code]):
        raise HTTPException(400, "trade_date or code required")
    stmt = delete(LimitUpDaily).where(LimitUpDaily.limit == "U")
    conds = []
    if trade_date:
        conds.append(LimitUpDaily.trade_date == trade_date)
    if code:
        conds.append(LimitUpDaily.ts_code == code)
    stmt = stmt.where(and_(*conds))
    result = session.execute(stmt)
    session.commit()
    return DeleteResponse(rows_deleted=result.rowcount or 0)
