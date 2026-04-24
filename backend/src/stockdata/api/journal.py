import json
import logging
from datetime import date as _date
from pathlib import Path
from typing import Type

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from stockdata.api.schemas import DeleteResponse, JournalEntryOut
from stockdata.config import settings
from stockdata.db import Base, get_session
from stockdata.models import MasterTracking, ReviewReference, TradingRecord
from stockdata.services.uploads import save_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/journal", tags=["journal"])

CATEGORY_MAP: dict[str, Type[Base]] = {
    "trading": TradingRecord,
    "review": ReviewReference,
    "master": MasterTracking,
}


def _model(category: str) -> Type[Base]:
    if category not in CATEGORY_MAP:
        raise HTTPException(404, f"unknown category: {category}")
    return CATEGORY_MAP[category]


def _serialize(row) -> JournalEntryOut:
    return JournalEntryOut(
        id=row.id,
        entry_date=row.entry_date,
        content=row.content or "",
        images=json.loads(row.images or "[]"),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/{category}", response_model=list[JournalEntryOut])
def list_entries(
    category: str,
    date: _date | None = Query(None, description="按当日查；不传取最近 limit 条"),
    limit: int = Query(50, ge=1, le=500),
    session: Session = Depends(get_session),
):
    Model = _model(category)
    stmt = select(Model)
    if date is not None:
        stmt = stmt.where(Model.entry_date == date)
    stmt = stmt.order_by(Model.entry_date.desc(), Model.id.desc()).limit(limit)
    rows = session.execute(stmt).scalars().all()
    return [_serialize(r) for r in rows]


@router.get("/{category}/dates")
def list_dates(
    category: str,
    session: Session = Depends(get_session),
):
    """返回有记录的日期（最近 180 个），给前端日历/快速选择用。"""
    Model = _model(category)
    stmt = select(Model.entry_date).distinct().order_by(Model.entry_date.desc()).limit(180)
    rows = session.execute(stmt).scalars().all()
    return {"dates": [d.isoformat() for d in rows]}


@router.post("/{category}", response_model=JournalEntryOut)
async def create_entry(
    category: str,
    entry_date: _date = Form(...),
    content: str = Form(""),
    images: list[UploadFile] = File(default_factory=list),
    session: Session = Depends(get_session),
):
    Model = _model(category)
    if not content.strip() and not images:
        raise HTTPException(400, "content 或 images 至少提供一个")

    saved_paths: list[str] = []
    for f in images or []:
        if not f.filename:
            continue
        try:
            web_path, _ = await save_image(f, category, entry_date)
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        saved_paths.append(web_path)

    row = Model(
        entry_date=entry_date,
        content=content,
        images=json.dumps(saved_paths, ensure_ascii=False),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _serialize(row)


@router.delete("/{category}/{entry_id}", response_model=DeleteResponse)
def delete_entry(
    category: str,
    entry_id: int,
    session: Session = Depends(get_session),
):
    Model = _model(category)
    row = session.get(Model, entry_id)
    if row is None:
        raise HTTPException(404, "not found")

    for web_path in json.loads(row.images or "[]"):
        if not web_path.startswith("/uploads/"):
            continue
        rel = web_path[len("/uploads/") :]
        fp = Path(settings.uploads_dir) / rel
        try:
            if fp.is_file():
                fp.unlink()
        except OSError:
            logger.warning("failed to delete file %s", fp)

    session.delete(row)
    session.commit()
    return DeleteResponse(rows_deleted=1)
