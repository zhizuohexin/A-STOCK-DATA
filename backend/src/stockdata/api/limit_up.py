"""涨停/连板 API：从 daily_quotes 现算（pct_chg >= 9.98），不依赖 limit_up_daily 表。"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, delete, text
from sqlalchemy.orm import Session

from stockdata.analytics.limit import get_streaks
from stockdata.analytics.rankings import latest_trade_date
from stockdata.api.schemas import DeleteResponse, LimitUpOut
from stockdata.crud import record_job, upsert_limit_up
from stockdata.db import get_session
from stockdata.models import LimitUpDaily
from stockdata.providers import get_provider

router = APIRouter(prefix="/limit-up", tags=["limit-up"])

LU_THRESHOLD = 9.98


def _latest_quote_date(session: Session) -> date | None:
    return session.execute(text("SELECT MAX(trade_date) FROM daily_quotes")).scalar()


def _list_limit_stocks(
    session: Session,
    trade_date: date,
    direction: str = "up",
    min_streak: int | None = None,
) -> list[dict]:
    """从 daily_quotes 拉取符合涨停/跌停条件的股，附连板数。"""
    streaks = get_streaks(session, trade_date, direction=direction)
    if not streaks:
        return []
    if direction == "up":
        cond = "q.pct_chg >= :th"
        order = "q.pct_chg DESC"
        th = LU_THRESHOLD
    else:
        cond = "q.pct_chg <= :th"
        order = "q.pct_chg ASC, q.amount DESC"
        th = -LU_THRESHOLD
    rows = session.execute(
        text(f"""
        SELECT q.ts_code, q.trade_date, s.name, q.close, q.pct_chg, q.amount
        FROM daily_quotes q
        LEFT JOIN stocks s ON s.ts_code = q.ts_code
        WHERE q.trade_date = :td AND {cond}
        ORDER BY {order}
        """),
        {"td": trade_date, "th": th},
    ).mappings().all()
    out = []
    for r in rows:
        d = dict(r)
        lt = streaks.get(d["ts_code"], 1)
        if min_streak and lt < min_streak:
            continue
        d["limit_times"] = lt
        # 兼容前端 LimitUpOut schema
        d["fd_amount"] = None
        d["first_time"] = None
        d["last_time"] = None
        d["open_times"] = None
        out.append(d)
    if direction == "up":
        out.sort(key=lambda x: (-(x["limit_times"] or 0), -(x["pct_chg"] or 0)))
    return out


@router.get("", response_model=list[LimitUpOut])
def list_limit_up(
    trade_date: date | None = None,
    min_limit_times: int | None = None,
    limit: int = 500,
    session: Session = Depends(get_session),
):
    if trade_date is None:
        trade_date = _latest_quote_date(session)
        if trade_date is None:
            return []
        if isinstance(trade_date, str):
            trade_date = date.fromisoformat(trade_date)
    out = _list_limit_stocks(session, trade_date, direction="up", min_streak=min_limit_times)
    return out[:limit]


@router.get("/by-sector")
def limit_up_by_sector(
    trade_date: date | None = None,
    by: str = "concept",
    session: Session = Depends(get_session),
):
    """涨停按板块（概念/行业）分组。从 daily_quotes 现算 + JOIN stock_sectors。"""
    if trade_date is None:
        trade_date = _latest_quote_date(session) or latest_trade_date(session)
        if trade_date is None:
            return {"trade_date": None, "by": by, "sectors": []}
        if isinstance(trade_date, str):
            trade_date = date.fromisoformat(trade_date)
    streaks = get_streaks(session, trade_date, direction="up")
    if not streaks:
        return {"trade_date": trade_date, "by": by, "sectors": []}

    if by == "industry":
        rows = session.execute(
            text(f"""
            SELECT COALESCE(s.industry, '未分类') AS sector_name,
                   NULL AS sector_code,
                   q.ts_code, s.name, q.close, q.pct_chg, q.amount
            FROM daily_quotes q
            LEFT JOIN stocks s ON s.ts_code = q.ts_code
            WHERE q.trade_date=:td AND q.pct_chg >= :th
            ORDER BY q.pct_chg DESC
            """),
            {"td": trade_date, "th": LU_THRESHOLD},
        ).mappings().all()
    else:
        # 概念分组：JOIN stock_sectors（含 EM/SW/MANUAL/KPL 多源）→ sectors（type='C'）
        rows = session.execute(
            text(f"""
            SELECT sec.name AS sector_name, sec.ts_code AS sector_code,
                   q.ts_code, s.name, q.close, q.pct_chg, q.amount
            FROM daily_quotes q
            LEFT JOIN stocks s ON s.ts_code = q.ts_code
            JOIN stock_sectors ss ON ss.ts_code = q.ts_code
            JOIN sectors sec ON sec.ts_code = ss.sector_code AND sec.type = 'C'
            WHERE q.trade_date=:td AND q.pct_chg >= :th
            ORDER BY q.pct_chg DESC
            """),
            {"td": trade_date, "th": LU_THRESHOLD},
        ).mappings().all()

    groups: dict[tuple, dict] = {}
    for r in rows:
        d = dict(r)
        sector_name = d.pop("sector_name")
        sector_code = d.pop("sector_code")
        d["limit_times"] = streaks.get(d["ts_code"], 1)
        d["fd_amount"] = None
        d["first_time"] = None
        d["last_time"] = None
        d["open_times"] = None
        key = (sector_name, sector_code)
        groups.setdefault(key, {"sector_name": sector_name, "sector_code": sector_code, "stocks": []})
        groups[key]["stocks"].append(d)

    sectors = [
        {
            "industry": v["sector_name"],
            "sector_code": v["sector_code"],
            "count": len(v["stocks"]),
            "max_consecutive": max((s.get("limit_times") or 0) for s in v["stocks"]),
            "stocks": sorted(v["stocks"], key=lambda x: -(x["limit_times"] or 0)),
        }
        for v in sorted(groups.values(), key=lambda x: (-len(x["stocks"]), x["sector_name"] or ""))
    ]

    # 概念模式下补"未归类"
    if by == "concept":
        unmatched = session.execute(
            text(f"""
            SELECT q.ts_code, s.name, q.close, q.pct_chg, q.amount
            FROM daily_quotes q
            LEFT JOIN stocks s ON s.ts_code = q.ts_code
            WHERE q.trade_date=:td AND q.pct_chg >= :th
              AND NOT EXISTS (
                SELECT 1 FROM stock_sectors ss
                JOIN sectors sec ON sec.ts_code = ss.sector_code AND sec.type = 'C'
                WHERE ss.ts_code = q.ts_code
              )
            ORDER BY q.pct_chg DESC
            """),
            {"td": trade_date, "th": LU_THRESHOLD},
        ).mappings().all()
        if unmatched:
            stocks_u = []
            for r in unmatched:
                d = dict(r)
                d["limit_times"] = streaks.get(d["ts_code"], 1)
                d["fd_amount"] = None
                d["first_time"] = None
                d["last_time"] = None
                d["open_times"] = None
                stocks_u.append(d)
            sectors.append({
                "industry": "未归类",
                "sector_code": None,
                "count": len(stocks_u),
                "max_consecutive": max((s.get("limit_times") or 0) for s in stocks_u),
                "stocks": stocks_u,
            })

    return {"trade_date": trade_date, "by": by, "sectors": sectors}


# ---- 以下保留：手动 backfill / 删除（操作 limit_up_daily 表，给 KPL 等其他来源用）----

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
