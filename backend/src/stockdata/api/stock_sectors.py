from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import and_, delete, text
from sqlalchemy.orm import Session

from stockdata.crud import record_job, replace_stock_sectors_for_src
from stockdata.db import get_session
from stockdata.models import StockSector
from stockdata.providers import get_provider
from stockdata.services.manual_sectors import (
    attach_limit_up_table,
    attach_manual_sectors,
    lookup_stock,
    parse_limit_up_table,
    parse_sector_screenshot,
)
from stockdata.services.uploads import MAX_BYTES

router = APIRouter(prefix="/stock-sectors", tags=["stock-sectors"])


class ManualAttachIn(BaseModel):
    ts_code: str
    sector_names: list[str]


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
def concepts_for_stock(
    ts_code: str,
    src: str | None = Query(None, description="过滤来源 EM/SW/THS/MANUAL，不传=全部"),
    session: Session = Depends(get_session),
):
    """某只股所属的所有板块（行业 + 概念），按板块来源可过滤。"""
    sql = """
    SELECT s.ts_code AS sector_code, s.name, s.type, ss.src
    FROM stock_sectors ss
    JOIN sectors s ON s.ts_code = ss.sector_code
    WHERE ss.ts_code = :ts_code
    """
    params: dict = {"ts_code": ts_code}
    if src:
        sql += " AND ss.src = :src"
        params["src"] = src
    sql += " ORDER BY s.type, s.name"
    rows = session.execute(text(sql), params).mappings().all()
    return {"ts_code": ts_code, "sectors": [dict(r) for r in rows]}


@router.post("/manual")
def attach_manual(
    payload: ManualAttachIn,
    session: Session = Depends(get_session),
):
    """手动批量给某只股加板块（src=MANUAL，幂等）。板块名找不到会自动建。"""
    stock = lookup_stock(session, ts_code=payload.ts_code, name=None)
    if not stock:
        raise HTTPException(404, f"stock not found: {payload.ts_code}")
    return attach_manual_sectors(session, stock["ts_code"], payload.sector_names)


@router.delete("/manual")
def delete_manual(
    ts_code: str = Query(...),
    sector_code: str | None = Query(None, description="不传则删除该股所有 MANUAL 关联"),
    session: Session = Depends(get_session),
):
    """删除手动添加的关联。仅影响 src=MANUAL 的行。"""
    stmt = delete(StockSector).where(
        and_(StockSector.ts_code == ts_code, StockSector.src == "MANUAL")
    )
    if sector_code:
        stmt = stmt.where(StockSector.sector_code == sector_code)
    result = session.execute(stmt)
    session.commit()
    return {"rows_deleted": result.rowcount or 0}


@router.post("/from-image")
async def from_image(
    file: UploadFile = File(...),
    ts_code: str | None = Form(None, description="不传则用 OCR 识别股票名"),
    dry_run: bool = Form(False, description="True 只解析不入库"),
    session: Session = Depends(get_session),
):
    """上传同花顺/东财个股板块截图，自动解析并入库（src=MANUAL）。"""
    data = await file.read()
    if not data:
        raise HTTPException(400, "empty file")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, f"image too large: {len(data)} bytes")

    parsed = parse_sector_screenshot(data)
    stock = lookup_stock(session, ts_code=ts_code, name=parsed["stock_name"])
    if not stock:
        raise HTTPException(
            404,
            f"stock not found. parsed_name={parsed['stock_name']!r}, "
            f"sectors={parsed['sector_names']}",
        )
    if dry_run:
        return {
            "stock": stock,
            "parsed_sectors": parsed["sector_names"],
            "raw_lines": parsed["raw_lines"],
            "would_attach": parsed["sector_names"],
        }
    result = attach_manual_sectors(session, stock["ts_code"], parsed["sector_names"])
    return {"stock": stock, "parsed_sectors": parsed["sector_names"], **result}


@router.post("/sync-industry-slow")
def sync_industry_slow_endpoint(
    background_tasks: BackgroundTasks,
    max_minutes: int = Query(30, description="最多跑多少分钟，到时自动停"),
    sleep_sec: float = Query(1.5, description="每板块间隔秒数，越大越稳"),
    session: Session = Depends(get_session),
):
    """慢速同步行业板块成员（push2 域名，被 ban 即停 + 自然续传）。

    后台触发，立刻返回。可重复调用直到 pending=0。
    查看进度：GET /api/jobs/runs?job_name=sync_industry_slow&limit=5
    """
    from stockdata.jobs.industry_slow import sync_industry_slow

    pending_count = session.execute(text("""
        SELECT COUNT(*) FROM sectors s
        LEFT JOIN stock_sectors ss ON ss.sector_code = s.ts_code
        WHERE s.type = 'I' AND ss.ts_code IS NULL
          AND s.ts_code LIKE 'BK%'
    """)).scalar() or 0
    background_tasks.add_task(sync_industry_slow, max_minutes, sleep_sec)
    return {
        "started": True,
        "pending_industry_sectors": pending_count,
        "max_minutes": max_minutes,
        "sleep_sec": sleep_sec,
        "tip": "查看进度: GET /api/jobs/runs?job_name=sync_industry_slow&limit=5",
    }


@router.get("/from-east/{ts_code}")
def from_east(
    ts_code: str,
    attach: bool = Query(False, description="True 时把结果入 stock_sectors 表"),
    src: str = Query("EM", description="attach 时入库标记的 src，默认 EM；想永久保留用 MANUAL"),
    session: Session = Depends(get_session),
):
    """实时查东财此股的所属概念板块（含选入原因）。可选直接入库。"""
    east = get_provider("eastmoney")
    boards = east.fetch_stock_concept_boards(ts_code)
    if not attach:
        return {"ts_code": ts_code, "boards": boards}
    # 入库：板块在 sectors 表中确保存在 + stock_sectors 写入
    from datetime import datetime as _dt

    from stockdata.models import Sector, StockSector

    inserted = 0
    for b in boards:
        sec_code = b["sector_code"]
        if not session.execute(
            text("SELECT 1 FROM sectors WHERE ts_code=:c"), {"c": sec_code}
        ).first():
            session.add(Sector(ts_code=sec_code, name=b["sector_name"], type="C", src="EM"))
            session.flush()
        if not session.execute(
            text("SELECT 1 FROM stock_sectors WHERE ts_code=:c AND sector_code=:s"),
            {"c": ts_code, "s": sec_code},
        ).first():
            session.add(
                StockSector(ts_code=ts_code, sector_code=sec_code, src=src, updated_at=_dt.utcnow())
            )
            inserted += 1
    session.commit()
    return {"ts_code": ts_code, "boards": boards, "inserted": inserted}


@router.post("/from-limit-up-image")
async def from_limit_up_image(
    file: UploadFile = File(...),
    dry_run: bool = Form(False),
    session: Session = Depends(get_session),
):
    """上传涨停复盘表（多股带题材分组），批量给每只股加题材关联（src=MANUAL）。"""
    data = await file.read()
    if not data:
        raise HTTPException(400, "empty file")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, f"image too large: {len(data)} bytes")
    parsed = parse_limit_up_table(data)
    if dry_run:
        return parsed
    return attach_limit_up_table(session, parsed)
