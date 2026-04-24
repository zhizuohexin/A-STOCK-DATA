from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from stockdata.analytics.rankings import (
    latest_trade_date,
    top_limit_up_frequency,
    top_n_day_gainers,
    top_sector_gainers,
    top_sector_gainers_n_day,
)
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
    days: int = Query(1, ge=1, le=60, description="1=当日；>1=N 日累计"),
    top: int = Query(5, ge=1, le=50),
    type: str | None = Query(None, description="I=行业 C=概念"),
    session: Session = Depends(get_session),
):
    if trade_date is None:
        trade_date = latest_trade_date(session)
    if trade_date is None:
        return {"trade_date": None, "top": top, "days": days, "items": []}

    if days == 1:
        items = top_sector_gainers(session, trade_date=trade_date, top=top, sector_type=type)
    else:
        items = top_sector_gainers_n_day(session, days=days, top=top, end_date=trade_date, sector_type=type)

    return {"trade_date": trade_date, "days": days, "top": top, "items": items}


@router.get("/limit-up-frequency")
def limit_up_frequency(
    days: int = Query(5, ge=1, le=60),
    top: int = Query(20, ge=1, le=100),
    end_date: date | None = None,
    session: Session = Depends(get_session),
):
    """妖股榜：N 日内个股涨停次数排名。"""
    if end_date is None:
        end_date = latest_trade_date(session)
    return top_limit_up_frequency(session, days=days, top=top, end_date=end_date)
