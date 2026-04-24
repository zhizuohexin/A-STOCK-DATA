from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from stockdata.api.schemas import StockOut
from stockdata.crud import record_job, upsert_stocks
from stockdata.db import get_session
from stockdata.models import Stock
from stockdata.providers import get_provider

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("", response_model=list[StockOut])
def list_stocks(
    q: str | None = None,
    industry: str | None = None,
    limit: int = 200,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    stmt = select(Stock)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Stock.ts_code.like(like), Stock.symbol.like(like), Stock.name.like(like)))
    if industry:
        stmt = stmt.where(Stock.industry == industry)
    stmt = stmt.order_by(Stock.ts_code).offset(offset).limit(min(limit, 1000))
    return session.execute(stmt).scalars().all()


@router.get("/{ts_code}", response_model=StockOut)
def get_stock(ts_code: str, session: Session = Depends(get_session)):
    stock = session.get(Stock, ts_code)
    if not stock:
        raise HTTPException(404, "stock not found")
    return stock


@router.post("/sync")
def sync_stock_list(provider: str = "tushare", session: Session = Depends(get_session)):
    """Pull full stock basic list from provider and upsert."""
    try:
        p = get_provider(provider)
        rows = p.fetch_stock_list()
        n = upsert_stocks(session, rows)
        session.commit()
        record_job(session, "sync_stock_list", "success", rows_affected=n)
        return {"rows_upserted": n}
    except Exception as e:
        session.rollback()
        record_job(session, "sync_stock_list", "failed", message=str(e))
        raise HTTPException(500, f"sync failed: {e}") from e
