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
    by: str = "concept",
    session: Session = Depends(get_session),
):
    """涨停按板块分组。

    by=concept（默认）：按东财概念归类，一只股可属于多个概念（同市场软件口径）；
    by=industry：按申万行业归类（一对一，粗）。
    """
    if trade_date is None:
        trade_date = latest_trade_date(session)
    if trade_date is None:
        return {"trade_date": None, "by": by, "sectors": []}

    if by == "industry":
        rows = session.execute(
            text(
                """
                SELECT COALESCE(s.industry, '未分类') AS sector_name,
                       NULL AS sector_code,
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
    else:
        # 概念分组：一只股 JOIN 多次出现，分别归到所属各个概念
        rows = session.execute(
            text(
                """
                SELECT s.name AS sector_name, s.ts_code AS sector_code,
                       l.ts_code, l.name, l.close, l.pct_chg,
                       l.limit_times, l.first_time, l.last_time, l.fd_amount, l.amount, l.open_times
                FROM limit_up_daily l
                JOIN stock_sectors ss ON ss.ts_code = l.ts_code
                JOIN sectors s ON s.ts_code = ss.sector_code AND s.type='C'
                WHERE l.trade_date=:td AND l."limit"='U'
                ORDER BY l.limit_times DESC NULLS LAST, l.pct_chg DESC NULLS LAST
                """
            ),
            {"td": trade_date},
        ).mappings().all()

    groups: dict[tuple, dict] = {}
    for r in rows:
        d = dict(r)
        sector_name = d.pop("sector_name")
        sector_code = d.pop("sector_code")
        key = (sector_name, sector_code)
        groups.setdefault(key, {"sector_name": sector_name, "sector_code": sector_code, "stocks": []})
        groups[key]["stocks"].append(d)

    sectors = [
        {
            "industry": v["sector_name"],  # 前端字段沿用 industry，避免改前端
            "sector_code": v["sector_code"],
            "count": len(v["stocks"]),
            "max_consecutive": max((s.get("limit_times") or 0) for s in v["stocks"]),
            "stocks": v["stocks"],
        }
        for v in sorted(groups.values(), key=lambda x: (-len(x["stocks"]), x["sector_name"] or ""))
    ]

    # 概念模式下额外列出"未匹配到任何概念"的涨停股，避免遗漏
    if by == "concept":
        unmatched = session.execute(
            text(
                """
                SELECT l.ts_code, l.name, l.close, l.pct_chg,
                       l.limit_times, l.first_time, l.last_time, l.fd_amount, l.amount, l.open_times
                FROM limit_up_daily l
                WHERE l.trade_date=:td AND l."limit"='U'
                  AND NOT EXISTS (
                    SELECT 1 FROM stock_sectors ss
                    JOIN sectors s ON s.ts_code = ss.sector_code AND s.type='C'
                    WHERE ss.ts_code = l.ts_code
                  )
                ORDER BY l.limit_times DESC NULLS LAST, l.pct_chg DESC NULLS LAST
                """
            ),
            {"td": trade_date},
        ).mappings().all()
        if unmatched:
            stocks_u = [dict(r) for r in unmatched]
            sectors.append(
                {
                    "industry": "未归类",
                    "sector_code": None,
                    "count": len(stocks_u),
                    "max_consecutive": max((s.get("limit_times") or 0) for s in stocks_u),
                    "stocks": stocks_u,
                }
            )

    return {"trade_date": trade_date, "by": by, "sectors": sectors}


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
