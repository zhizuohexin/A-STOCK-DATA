import logging
from threading import Lock

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

_engine = None
_lock = Lock()


def _get_engine():
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                from rapidocr_onnxruntime import RapidOCR

                logger.info("initializing RapidOCR engine (first call may download models)")
                _engine = RapidOCR()
    return _engine


def run_ocr(image_bytes: bytes) -> str:
    """识别图片文字并按行拼接返回。"""
    img = Image.open(__import__("io").BytesIO(image_bytes)).convert("RGB")
    arr = np.array(img)
    engine = _get_engine()
    result, _ = engine(arr)
    if not result:
        return ""
    # result: [[box, text, score], ...]
    return "\n".join(item[1] for item in result if item and len(item) > 1)


def run_ocr_with_boxes(image_bytes: bytes) -> tuple[list[dict], int, int]:
    """识别图片，返回 [{text, x, y, w, h}, ...] + 图片宽高。x,y 用左上角。"""
    img = Image.open(__import__("io").BytesIO(image_bytes)).convert("RGB")
    width, height = img.size
    arr = np.array(img)
    engine = _get_engine()
    result, _ = engine(arr)
    items: list[dict] = []
    if not result:
        return items, width, height
    for item in result:
        if not item or len(item) < 2:
            continue
        box, text = item[0], item[1]
        # box: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] 顺序：左上→右上→右下→左下
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x = min(xs)
        y = min(ys)
        w = max(xs) - x
        h = max(ys) - y
        items.append({"text": text.strip(), "x": float(x), "y": float(y), "w": float(w), "h": float(h)})
    return items, width, height
