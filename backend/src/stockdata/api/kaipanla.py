"""开盘啦数据查询 API。"""

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from stockdata.db import get_session
from stockdata.jobs.kaipanla import run_kpl_job

router = APIRouter(prefix="/kpl", tags=["kpl"])


@router.get("/sentiment")
def get_sentiment(
    trade_date: date_type | None = None,
    session: Session = Depends(get_session),
):
    sql = "SELECT * FROM kpl_sentiment"
    params: dict = {}
    if trade_date:
        sql += " WHERE trade_date=:td"
        params["td"] = trade_date
    else:
        sql += " ORDER BY trade_date DESC LIMIT 1"
    r = session.execute(text(sql), params).mappings().first()
    return dict(r) if r else None


@router.get("/ladder")
def get_ladder(
    trade_date: date_type | None = None,
    session: Session = Depends(get_session),
):
    sql = "SELECT * FROM kpl_ladder"
    params: dict = {}
    if trade_date:
        sql += " WHERE trade_date=:td"
        params["td"] = trade_date
    else:
        sql += " ORDER BY trade_date DESC LIMIT 1"
    r = session.execute(text(sql), params).mappings().first()
    return dict(r) if r else None


@router.get("/consecutive")
def get_consecutive(
    trade_date: date_type | None = None,
    min_days: int = Query(2),
    session: Session = Depends(get_session),
):
    """查某日的连板个股（含题材）。不传日期取最近一天。"""
    if trade_date is None:
        td = session.execute(text("SELECT MAX(trade_date) FROM kpl_consecutive")).scalar()
        if not td:
            return {"trade_date": None, "stocks": []}
        trade_date = date_type.fromisoformat(td) if isinstance(td, str) else td
    rows = session.execute(text("""
        SELECT ts_code, name, days, pct_chg, theme, board_desc, market_cap
        FROM kpl_consecutive
        WHERE trade_date=:td AND days>=:m
        ORDER BY days DESC, pct_chg DESC
    """), {"td": trade_date, "m": min_days}).mappings().all()
    return {"trade_date": trade_date, "stocks": [dict(r) for r in rows]}


@router.get("/broken")
def get_broken(
    trade_date: date_type | None = None,
    session: Session = Depends(get_session),
):
    if trade_date is None:
        td = session.execute(text("SELECT MAX(trade_date) FROM kpl_broken")).scalar()
        if not td:
            return {"trade_date": None, "stocks": []}
        trade_date = date_type.fromisoformat(td) if isinstance(td, str) else td
    rows = session.execute(text("""
        SELECT ts_code, name, pct_chg, sector FROM kpl_broken
        WHERE trade_date=:td ORDER BY pct_chg DESC
    """), {"td": trade_date}).mappings().all()
    return {"trade_date": trade_date, "stocks": [dict(r) for r in rows]}


@router.get("/lhb")
def get_lhb(
    trade_date: date_type | None = None,
    session: Session = Depends(get_session),
):
    """龙虎榜个股汇总。"""
    if trade_date is None:
        td = session.execute(text("SELECT MAX(trade_date) FROM kpl_lhb")).scalar()
        if not td:
            return {"trade_date": None, "stocks": []}
        trade_date = date_type.fromisoformat(td) if isinstance(td, str) else td
    rows = session.execute(text("""
        SELECT ts_code, name, pct_chg, reason, buy_in, net FROM kpl_lhb
        WHERE trade_date=:td ORDER BY ABS(buy_in) DESC
    """), {"td": trade_date}).mappings().all()
    return {"trade_date": trade_date, "stocks": [dict(r) for r in rows]}


@router.get("/lhb/seats/{ts_code}")
def get_lhb_seats(
    ts_code: str,
    trade_date: date_type | None = None,
    session: Session = Depends(get_session),
):
    """单股某日的龙虎榜席位明细。"""
    sql = """
        SELECT trade_date, side, rank, broker, buy_in, sell_out, net_buy, is_dy
        FROM kpl_lhb_seat WHERE ts_code=:c
    """
    params: dict = {"c": ts_code}
    if trade_date:
        sql += " AND trade_date=:td"
        params["td"] = trade_date
    sql += " ORDER BY trade_date DESC, side, rank"
    rows = session.execute(text(sql), params).mappings().all()
    return {"ts_code": ts_code, "seats": [dict(r) for r in rows]}


@router.get("/auction")
def get_auction(
    trade_date: date_type | None = None,
    session: Session = Depends(get_session),
):
    if trade_date is None:
        td = session.execute(text("SELECT MAX(trade_date) FROM kpl_auction")).scalar()
        if not td:
            return {"trade_date": None, "stocks": []}
        trade_date = date_type.fromisoformat(td) if isinstance(td, str) else td
    rows = session.execute(text("""
        SELECT ts_code, name, tag, direction, themes, pct_chg, turnover,
               net_amount, big_order_buy, big_order_sell, score
        FROM kpl_auction WHERE trade_date=:td ORDER BY score DESC
    """), {"td": trade_date}).mappings().all()
    return {"trade_date": trade_date, "stocks": [dict(r) for r in rows]}


@router.post("/run")
def trigger_kpl_job(
    trade_date: date_type | None = None,
    with_lhb_detail: bool = True,
):
    """手动触发一次 Kaipanla 数据抓取（不阻塞调用方，可指定历史日期回填）。"""
    return run_kpl_job(target_date=trade_date, with_lhb_detail=with_lhb_detail)
