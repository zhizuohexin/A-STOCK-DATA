"""行业板块成员同步（慢速 + 自然续传）。

走 push2 域名（fetch_sector_members），易被东财 IP 限流。策略：
- 自然续传：每次只拉 stock_sectors 中尚无成员的行业板块
- 每板块立即 commit，被 ban 立刻 break 不重试
- 单实例锁，避免并发触发更严限速
- 调度不接，由用户手动 POST /api/stock-sectors/sync-industry-slow 触发
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

from sqlalchemy import text

from stockdata.crud import record_job
from stockdata.db import SessionLocal
from stockdata.models import StockSector
from stockdata.providers import get_provider

logger = logging.getLogger(__name__)

_lock = threading.Lock()


def sync_industry_slow(max_minutes: int = 30, sleep_sec: float = 1.5) -> dict | None:
    """慢速同步未入库的行业板块成员。

    返回 None 表示已有任务在跑（被锁拒绝）。
    """
    if not _lock.acquire(blocking=False):
        logger.warning("sync_industry_slow already running, refused")
        return None

    started = datetime.utcnow()
    deadline = started.timestamp() + max_minutes * 60
    session = SessionLocal()
    east = get_provider("eastmoney")
    completed = 0
    inserted = 0
    stopped_at: str | None = None
    error_msg: str | None = None
    try:
        # 只处理东财 BK 开头的行业代码；申万 801xxx.SI 走 tushare 路线
        pending = session.execute(text("""
            SELECT s.ts_code, s.name FROM sectors s
            LEFT JOIN stock_sectors ss ON ss.sector_code = s.ts_code
            WHERE s.type = 'I' AND ss.ts_code IS NULL
              AND s.ts_code LIKE 'BK%'
            ORDER BY s.ts_code
        """)).all()
        total_pending = len(pending)
        logger.info("sync_industry_slow: %d pending industry sectors", total_pending)

        for sec_code, name in pending:
            if datetime.utcnow().timestamp() > deadline:
                stopped_at = sec_code
                error_msg = f"deadline {max_minutes}min reached"
                break
            try:
                members = east.fetch_sector_members(sec_code)
            except Exception as e:  # noqa: BLE001
                stopped_at = sec_code
                error_msg = f"{type(e).__name__}: {e}"
                logger.warning("banned at %s (%s): %s", sec_code, name, error_msg)
                break

            for ts_code in members:
                exists = session.execute(
                    text("SELECT 1 FROM stock_sectors WHERE ts_code=:c AND sector_code=:s"),
                    {"c": ts_code, "s": sec_code},
                ).first()
                if not exists:
                    session.add(StockSector(
                        ts_code=ts_code, sector_code=sec_code, src="EM",
                        updated_at=datetime.utcnow(),
                    ))
                    inserted += 1
            session.commit()  # 每板块立即提交，绝不批量
            completed += 1
            logger.info("  %s %s: %d members, total inserted=%d",
                        sec_code, name, len(members), inserted)
            time.sleep(sleep_sec)

        result = {
            "total_pending": total_pending,
            "completed": completed,
            "remaining": total_pending - completed,
            "inserted": inserted,
            "stopped_at": stopped_at,
            "error": error_msg,
            "elapsed_sec": int((datetime.utcnow() - started).total_seconds()),
        }
        status = "success" if stopped_at is None else "partial"
        record_job(session, "sync_industry_slow", status,
                   message=str(result), rows_affected=inserted)
        logger.info("sync_industry_slow done: %s", result)
        return result
    except Exception as e:
        session.rollback()
        record_job(session, "sync_industry_slow", "failed", message=str(e))
        logger.exception("sync_industry_slow crashed")
        raise
    finally:
        session.close()
        _lock.release()
