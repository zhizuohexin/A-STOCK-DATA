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
