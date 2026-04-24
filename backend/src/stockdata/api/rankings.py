from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from stockdata.analytics.rankings import latest_trade_date, top_n_day_gainers, top_sector_gainers
from stockdata.db import get_session

router = APIRouter(prefix="/rankings", tags=["rankings"])


@router.get("/gainers")
def gainers(
    days: int = Query(5, ge=1, le=60),
    top: int = Query(10, ge=1, le=100),
    end_date: date | None = None,
    session: Session = Depends(get_session),
):
    """N 日涨幅前 top 名。end_date 不传则取数据库里最新一个交易日。"""
    if end_date is None:
        end_date = latest_trade_date(session)
    return {
        "days": days,
        "top": top,
        "end_date": end_date,
        "items": top_n_day_gainers(session, days=days, top=top, end_date=end_date),
    }


@router.get("/sectors")
def sector_gainers(
    trade_date: date | None = None,
    top: int = Query(5, ge=1, le=50),
    type: str | None = Query(None, description="I=行业 C=概念"),
    session: Session = Depends(get_session),
):
    if trade_date is None:
        trade_date = latest_trade_date(session)
    if trade_date is None:
        return {"trade_date": None, "top": top, "items": []}
    return {
        "trade_date": trade_date,
        "top": top,
        "items": top_sector_gainers(session, trade_date=trade_date, top=top, sector_type=type),
    }
