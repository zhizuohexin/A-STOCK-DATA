from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, delete, select
from sqlalchemy.orm import Session

from stockdata.api.schemas import DeleteResponse, LimitUpOut
from stockdata.crud import record_job, upsert_limit_up
from stockdata.db import get_session
from stockdata.models import LimitUpDaily
from stockdata.providers import get_provider

router = APIRouter(prefix="/limit-down", tags=["limit-down"])


@router.get("", response_model=list[LimitUpOut])
def list_limit_down(
    trade_date: date | None = None,
    limit: int = 500,
    session: Session = Depends(get_session),
):
    stmt = select(LimitUpDaily).where(LimitUpDaily.limit == "D")
    if trade_date:
        stmt = stmt.where(LimitUpDaily.trade_date == trade_date)
    stmt = stmt.order_by(
        LimitUpDaily.trade_date.desc(),
        LimitUpDaily.pct_chg.asc().nullslast(),  # 跌停默认按跌幅最大
    ).limit(limit)
    return session.execute(stmt).scalars().all()


@router.post("/backfill")
def backfill_limit_down(
    trade_date: date,
    provider: str = "tushare",
    session: Session = Depends(get_session),
):
    try:
        p = get_provider(provider)
        rows = p.fetch_limit_pool(trade_date, limit_type="D")
        n = upsert_limit_up(session, rows)
        session.commit()
        record_job(session, "backfill_limit_down", "success", message=str(trade_date), rows_affected=n)
        return {"rows_upserted": n}
    except Exception as e:
        session.rollback()
        record_job(session, "backfill_limit_down", "failed", message=str(e))
        raise HTTPException(500, str(e)) from e


@router.delete("", response_model=DeleteResponse)
def delete_limit_down(
    trade_date: date | None = None,
    code: str | None = None,
    session: Session = Depends(get_session),
):
    if not any([trade_date, code]):
        raise HTTPException(400, "trade_date or code required")
    stmt = delete(LimitUpDaily).where(LimitUpDaily.limit == "D")
    conds = []
    if trade_date:
        conds.append(LimitUpDaily.trade_date == trade_date)
    if code:
        conds.append(LimitUpDaily.ts_code == code)
    stmt = stmt.where(and_(*conds))
    result = session.execute(stmt)
    session.commit()
    return DeleteResponse(rows_deleted=result.rowcount or 0)
