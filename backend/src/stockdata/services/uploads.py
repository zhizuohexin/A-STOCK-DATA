from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from stockdata.config import settings

ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def uploads_root() -> Path:
    p = Path(settings.uploads_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _ext(filename: str | None) -> str:
    if not filename:
        return ".jpg"
    ext = Path(filename).suffix.lower()
    return ext if ext in ALLOWED_EXTS else ".jpg"


async def save_image(file: UploadFile, category: str, when: date | None = None) -> tuple[str, bytes]:
    """保存图片到 uploads/{category}/{YYYY-MM}/{uuid}.ext，返回 (web 相对路径, 原始字节)。"""
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise ValueError(f"image too large: {len(data)} bytes")
    when = when or date.today()
    sub = f"{when.year:04d}-{when.month:02d}"
    ext = _ext(file.filename)
    target_dir = uploads_root() / category / sub
    target_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid4().hex}{ext}"
    target = target_dir / name
    target.write_bytes(data)
    web_path = f"/uploads/{category}/{sub}/{name}"
    return web_path, data
