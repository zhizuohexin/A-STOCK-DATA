from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, delete, select
from sqlalchemy.orm import Session

from stockdata.api.schemas import BackfillRequest, BackfillResponse, DailyQuoteOut, DeleteResponse
from stockdata.crud import record_job, upsert_daily_quotes
from stockdata.db import get_session
from stockdata.models import DailyQuote
from stockdata.providers import get_provider

router = APIRouter(prefix="/quotes", tags=["quotes"])

MAX_BACKFILL_DAYS = 31  # 回溯最多 1 个月


@router.get("", response_model=list[DailyQuoteOut])
def list_quotes(
    code: str | None = None,
    start: date | None = None,
    end: date | None = None,
    limit: int = 500,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    stmt = select(DailyQuote)
    conds = []
    if code:
        conds.append(DailyQuote.ts_code == code)
    if start:
        conds.append(DailyQuote.trade_date >= start)
    if end:
        conds.append(DailyQuote.trade_date <= end)
    if conds:
        stmt = stmt.where(and_(*conds))
    stmt = stmt.order_by(DailyQuote.trade_date.desc(), DailyQuote.ts_code).offset(offset).limit(min(limit, 2000))
    return session.execute(stmt).scalars().all()


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
