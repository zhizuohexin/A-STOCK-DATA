from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, delete, select, text
from sqlalchemy.orm import Session

from stockdata.analytics.rankings import latest_trade_date
from stockdata.api.schemas import BackfillRequest, BackfillResponse, DailyQuoteOut, DeleteResponse
from stockdata.crud import record_job, upsert_daily_quotes
from stockdata.db import get_session
from stockdata.models import DailyQuote
from stockdata.providers import get_provider

router = APIRouter(prefix="/quotes", tags=["quotes"])

MAX_BACKFILL_DAYS = 31  # 回溯最多 1 个月


@router.get("")
def list_quotes(
    code: str | None = None,
    start: date | None = None,
    end: date | None = None,
    concept: str | None = Query(None, description="按概念名筛选 (如 '算力')"),
    limit: int = 500,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    filters = ["1=1"]
    params: dict = {"limit": min(limit, 2000), "offset": offset}
    if code:
        filters.append("q.ts_code = :code")
        params["code"] = code
    if start:
        filters.append("q.trade_date >= :start")
        params["start"] = start
    if end:
        filters.append("q.trade_date <= :end")
        params["end"] = end

    concept_join = ""
    if concept:
        filters.append("q.ts_code IN (SELECT ss.ts_code FROM stock_sectors ss JOIN sectors sec ON sec.ts_code = ss.sector_code WHERE sec.name = :concept)")
        params["concept"] = concept

    sql = f"""
    SELECT q.ts_code, s.name, s.industry, q.trade_date,
           q.open, q.high, q.low, q.close, q.pre_close,
           q.change, q.pct_chg, q.vol, q.amount, q.turnover_rate,
           (SELECT GROUP_CONCAT(sec.name, '|')
            FROM stock_sectors ss
            JOIN sectors sec ON sec.ts_code = ss.sector_code
            WHERE ss.ts_code = q.ts_code AND sec.type = 'C') AS concepts_str
    FROM daily_quotes q
    LEFT JOIN stocks s ON s.ts_code = q.ts_code
    {concept_join}
    WHERE {' AND '.join(filters)}
    ORDER BY q.trade_date DESC, q.pct_chg DESC NULLS LAST, q.ts_code
    LIMIT :limit OFFSET :offset
    """
    rows = session.execute(text(sql), params).mappings().all()
    out = []
    for r in rows:
        d = dict(r)
        cs = d.pop("concepts_str", None)
        d["concepts"] = cs.split("|") if cs else []
        out.append(d)
    return out


@router.post("/backfill", response_model=BackfillResponse)
def backfill_quotes(
    req: BackfillRequest,
    provider: str = "tushare",
    session: Session = Depends(get_session),
):
    if (req.end_date - req.start_date).days > MAX_BACKFILL_DAYS:
        raise HTTPException(400, f"backfill span must be within {MAX_BACKFILL_DAYS} days")
    if req.start_date > req.end_date:
        raise HTTPException(400, "start_date must be <= end_date")

    p = get_provider(provider)
    total = 0
    days = 0
    errors: list[str] = []
    d = req.start_date
    while d <= req.end_date:
        if d.weekday() >= 5:  # 周末跳过
            d += timedelta(days=1)
            continue
        try:
            rows = p.fetch_daily_quotes(d)
            n = upsert_daily_quotes(session, rows)
            session.commit()
            total += n
            days += 1
        except Exception as e:  # noqa: BLE001
            session.rollback()
            errors.append(f"{d}: {e}")
        d += timedelta(days=1)

    record_job(
        session,
        "backfill_quotes",
        "success" if not errors else "partial",
        message=f"{req.start_date}~{req.end_date}",
        rows_affected=total,
    )
    return BackfillResponse(days_processed=days, rows_upserted=total, errors=errors)


@router.get("/top-amount")
def top_amount(
    trade_date: date | None = None,
    top: int = Query(50, ge=1, le=500),
    session: Session = Depends(get_session),
):
    """某日成交额前 N 的股票。不传 trade_date 取最新交易日。"""
    if trade_date is None:
        trade_date = latest_trade_date(session)
    if trade_date is None:
        return {"trade_date": None, "top": top, "items": []}
    sql = """
    SELECT q.ts_code, s.name, s.industry,
           q.open, q.high, q.low, q.close, q.pre_close, q.pct_chg,
           q.vol, q.amount, q.turnover_rate
    FROM daily_quotes q
    LEFT JOIN stocks s ON s.ts_code = q.ts_code
    WHERE q.trade_date = :trade_date AND q.amount IS NOT NULL
    ORDER BY q.amount DESC
    LIMIT :top
    """
    rows = session.execute(text(sql), {"trade_date": trade_date, "top": top}).mappings().all()
    return {"trade_date": trade_date, "top": top, "items": [dict(r) for r in rows]}


@router.delete("", response_model=DeleteResponse)
def delete_quotes(
    code: str | None = None,
    start: date | None = None,
    end: date | None = None,
    session: Session = Depends(get_session),
):
    if not any([code, start, end]):
        raise HTTPException(400, "at least one of code/start/end is required")
    stmt = delete(DailyQuote)
    conds = []
    if code:
        conds.append(DailyQuote.ts_code == code)
    if start:
        conds.append(DailyQuote.trade_date >= start)
    if end:
        conds.append(DailyQuote.trade_date <= end)
    stmt = stmt.where(and_(*conds))
    result = session.execute(stmt)
    session.commit()
    return DeleteResponse(rows_deleted=result.rowcount or 0)
