from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from stockdata.crud import record_job, replace_stock_sectors_for_src
from stockdata.db import get_session
from stockdata.providers import get_provider

router = APIRouter(prefix="/stock-sectors", tags=["stock-sectors"])


@router.post("/sync")
def sync_stock_sectors(
    sector_type: str | None = Query(None, description="I=行业 C=概念 不传=全部"),
    provider: str = "eastmoney",
    session: Session = Depends(get_session),
):
    """同步股票↔板块映射。200 个板块约 30 秒完成。"""
    try:
        p = get_provider(provider)
        rows = p.fetch_all_stock_sectors(sector_type=sector_type)
        n = replace_stock_sectors_for_src(session, src="EM" if provider == "eastmoney" else provider.upper(), rows=rows)
        session.commit()
        record_job(session, "sync_stock_sectors", "success", message=f"type={sector_type}", rows_affected=n)
        return {"rows_inserted": n}
    except Exception as e:
        session.rollback()
        record_job(session, "sync_stock_sectors", "failed", message=str(e))
        raise HTTPException(500, str(e)) from e


@router.get("/for-stock/{ts_code}")
def concepts_for_stock(ts_code: str, session: Session = Depends(get_session)):
    """某只股所属的所有板块（行业 + 概念）。"""
    rows = session.execute(
        text(
            """
            SELECT s.ts_code AS sector_code, s.name, s.type
            FROM stock_sectors ss
            JOIN sectors s ON s.ts_code = ss.sector_code
            WHERE ss.ts_code = :ts_code
            ORDER BY s.type, s.name
            """
        ),
        {"ts_code": ts_code},
    ).mappings().all()
    return {"ts_code": ts_code, "sectors": [dict(r) for r in rows]}
