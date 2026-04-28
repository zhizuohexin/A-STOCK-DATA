"""每周自动同步个股↔板块映射。

走 datacenter-web RPT_F10_CORETHEME_BOARDTYPE（独立子域，比 push2 稳定），
逐股查询每只股的所属概念板块（含选入原因）。
"""

from __future__ import annotations

import logging
import time
from datetime import datetime

from sqlalchemy import text

from stockdata.crud import record_job
from stockdata.db import SessionLocal
from stockdata.models import Sector, StockSector
from stockdata.providers import get_provider

logger = logging.getLogger(__name__)


def sync_stock_sectors_weekly() -> dict:
    """全量同步个股↔板块（src='EM'，不动 MANUAL）。约 35-40 分钟。"""
    started = datetime.utcnow()
    session = SessionLocal()
    east = get_provider("eastmoney")
    inserted = 0
    new_sectors = 0
    fail = 0
    try:
        stocks = [r[0] for r in session.execute(
            text("SELECT ts_code FROM stocks ORDER BY ts_code")
        ).all()]
        logger.info("weekly sync: %d stocks", len(stocks))

        for i, ts_code in enumerate(stocks):
            boards = None
            for attempt in range(3):
                try:
                    boards = east.fetch_stock_concept_boards(ts_code)
                    break
                except Exception as e:  # noqa: BLE001
                    if attempt == 2:
                        logger.warning("%s failed: %s", ts_code, e)
                        fail += 1
                    else:
                        time.sleep(2 * (attempt + 1))
            if boards is None:
                time.sleep(0.3)
                continue
            for b in boards:
                sec_code = b["sector_code"]
                if not session.execute(
                    text("SELECT 1 FROM sectors WHERE ts_code=:c"),
                    {"c": sec_code},
                ).first():
                    session.add(Sector(
                        ts_code=sec_code, name=b["sector_name"], type="C", src="EM",
                    ))
                    session.flush()
                    new_sectors += 1
                if not session.execute(
                    text("SELECT 1 FROM stock_sectors WHERE ts_code=:c AND sector_code=:s"),
                    {"c": ts_code, "s": sec_code},
                ).first():
                    session.add(StockSector(
                        ts_code=ts_code, sector_code=sec_code, src="EM",
                        updated_at=datetime.utcnow(),
                    ))
                    inserted += 1
            if i % 50 == 49:
                session.commit()
                logger.info(
                    "weekly progress %d/%d inserted=%d new_sectors=%d fail=%d",
                    i + 1, len(stocks), inserted, new_sectors, fail,
                )
                time.sleep(1.0)
            else:
                time.sleep(0.3)

        session.commit()
        result = {
            "inserted": inserted,
            "new_sectors": new_sectors,
            "fail": fail,
            "elapsed_sec": int((datetime.utcnow() - started).total_seconds()),
        }
        status = "success" if fail < 100 else "partial"
        record_job(session, "weekly_stock_sectors_sync", status,
                   message=str(result), rows_affected=inserted)
        logger.info("weekly_stock_sectors_sync done: %s", result)
        return result
    except Exception as e:
        session.rollback()
        record_job(session, "weekly_stock_sectors_sync", "failed", message=str(e))
        raise
    finally:
        session.close()
