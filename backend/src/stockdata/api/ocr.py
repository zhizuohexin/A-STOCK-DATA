import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from stockdata.api.schemas import OcrOut
from stockdata.services.ocr import run_ocr
from stockdata.services.uploads import MAX_BYTES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr", tags=["ocr"])


@router.post("", response_model=OcrOut)
async def ocr(file: UploadFile = File(...)) -> OcrOut:
    data = await file.read()
    if not data:
        raise HTTPException(400, "empty file")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, f"image too large: {len(data)} bytes")
    try:
        text = run_ocr(data)
    except Exception as e:  # noqa: BLE001
        logger.exception("ocr failed")
        raise HTTPException(500, f"ocr failed: {e}") from e
    return OcrOut(text=text)
