from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, delete, select
from sqlalchemy.orm import Session

from stockdata.api.schemas import DeleteResponse, IntradayBarOut
from stockdata.crud import record_job, upsert_intraday_bars
from stockdata.db import get_session
from stockdata.models import IntradayBar
from stockdata.providers import get_provider

router = APIRouter(prefix="/intraday", tags=["intraday"])


@router.get("", response_model=list[IntradayBarOut])
def list_intraday(
    code: str = Query(..., description="ts_code, e.g. 000001.SZ"),
    trade_date: date | None = None,
    limit: int = 500,
    session: Session = Depends(get_session),
):
    stmt = select(IntradayBar).where(IntradayBar.ts_code == code)
    if trade_date:
        start = datetime.combine(trade_date, datetime.min.time())
        end = datetime.combine(trade_date, datetime.max.time())
        stmt = stmt.where(and_(IntradayBar.bar_time >= start, IntradayBar.bar_time <= end))
    stmt = stmt.order_by(IntradayBar.bar_time).limit(min(limit, 1000))
    return session.execute(stmt).scalars().all()


@router.post("/fetch")
def fetch_intraday(
    code: str,
    trade_date: date,
    freq: str = "1min",
    provider: str = "tushare",
    session: Session = Depends(get_session),
):
    """按需拉取某股当日分钟K线入库。给 agent 或前端用。"""
    try:
        p = get_provider(provider)
        rows = p.fetch_intraday_bars(code, trade_date, freq=freq)
        n = upsert_intraday_bars(session, rows)
        session.commit()
        record_job(session, "fetch_intraday", "success", message=f"{code}/{trade_date}", rows_affected=n)
        return {"rows_upserted": n}
    except Exception as e:
        session.rollback()
        record_job(session, "fetch_intraday", "failed", message=str(e))
        raise HTTPException(500, str(e)) from e


@router.delete("", response_model=DeleteResponse)
def delete_intraday(
    code: str | None = None,
    before_date: date | None = None,
    session: Session = Depends(get_session),
):
    """清理分时数据。不带参数默认拒绝（避免误清全表）。"""
    if not any([code, before_date]):
        raise HTTPException(400, "code or before_date required")
    stmt = delete(IntradayBar)
    conds = []
    if code:
        conds.append(IntradayBar.ts_code == code)
    if before_date:
        conds.append(IntradayBar.bar_time < datetime.combine(before_date, datetime.min.time()))
    stmt = stmt.where(and_(*conds))
    result = session.execute(stmt)
    session.commit()
    return DeleteResponse(rows_deleted=result.rowcount or 0)
