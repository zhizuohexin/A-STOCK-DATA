from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, delete, select
from sqlalchemy.orm import Session

from stockdata.api.schemas import DeleteResponse, SectorDailyOut, SectorOut
from stockdata.crud import record_job, upsert_sector_daily, upsert_sectors
from stockdata.db import get_session
from stockdata.models import Sector, SectorDaily
from stockdata.providers import get_provider

router = APIRouter(prefix="/sectors", tags=["sectors"])


@router.get("", response_model=list[SectorOut])
def list_sectors(type: str | None = None, session: Session = Depends(get_session)):
    stmt = select(Sector)
    if type:
        stmt = stmt.where(Sector.type == type)
    return session.execute(stmt.order_by(Sector.type, Sector.ts_code)).scalars().all()


@router.get("/daily", response_model=list[SectorDailyOut])
def list_sector_daily(
    trade_date: date | None = None,
    sector_code: str | None = None,
    limit: int = 200,
    session: Session = Depends(get_session),
):
    stmt = select(SectorDaily)
    conds = []
    if trade_date:
        conds.append(SectorDaily.trade_date == trade_date)
    if sector_code:
        conds.append(SectorDaily.sector_code == sector_code)
    if conds:
        stmt = stmt.where(and_(*conds))
    stmt = stmt.order_by(SectorDaily.trade_date.desc(), SectorDaily.pct_chg.desc().nullslast()).limit(limit)
    return session.execute(stmt).scalars().all()


@router.post("/sync")
def sync_sectors(provider: str = "eastmoney", session: Session = Depends(get_session)):
    try:
        p = get_provider(provider)
        rows = p.fetch_sectors()
        n = upsert_sectors(session, rows)
        session.commit()
        record_job(session, "sync_sectors", "success", rows_affected=n)
        return {"rows_upserted": n}
    except Exception as e:
        session.rollback()
        record_job(session, "sync_sectors", "failed", message=str(e))
        raise HTTPException(500, str(e)) from e


@router.post("/daily/backfill")
def backfill_sector_daily(
    trade_date: date,
    provider: str = "eastmoney",
    session: Session = Depends(get_session),
):
    try:
        p = get_provider(provider)
        rows = p.fetch_sector_daily(trade_date)
        n = upsert_sector_daily(session, rows)
        session.commit()
        record_job(session, "backfill_sector_daily", "success", message=str(trade_date), rows_affected=n)
        return {"rows_upserted": n}
    except Exception as e:
        session.rollback()
        record_job(session, "backfill_sector_daily", "failed", message=str(e))
        raise HTTPException(500, str(e)) from e


@router.delete("/daily", response_model=DeleteResponse)
def delete_sector_daily(
    trade_date: date | None = None,
    sector_code: str | None = None,
    session: Session = Depends(get_session),
):
    if not any([trade_date, sector_code]):
        raise HTTPException(400, "trade_date or sector_code required")
    stmt = delete(SectorDaily)
    conds = []
    if trade_date:
        conds.append(SectorDaily.trade_date == trade_date)
    if sector_code:
        conds.append(SectorDaily.sector_code == sector_code)
    stmt = stmt.where(and_(*conds))
    result = session.execute(stmt)
    session.commit()
    return DeleteResponse(rows_deleted=result.rowcount or 0)
