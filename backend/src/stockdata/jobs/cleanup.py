"""次日凌晨清理昨日及更早的分时数据（只留最新一天给 agent 查）。"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from sqlalchemy import delete

from stockdata.crud import record_job
from stockdata.db import SessionLocal
from stockdata.models import IntradayBar

logger = logging.getLogger(__name__)


def cleanup_old_intraday(keep_days: int = 1) -> dict:
    """删除 bar_time < (today - keep_days) 的分时数据。"""
    cutoff = datetime.combine(date.today() - timedelta(days=keep_days), datetime.min.time())
    session = SessionLocal()
    try:
        stmt = delete(IntradayBar).where(IntradayBar.bar_time < cutoff)
        result = session.execute(stmt)
        session.commit()
        n = result.rowcount or 0
        record_job(session, "cleanup_intraday", "success", message=f"cutoff={cutoff.isoformat()}", rows_affected=n)
        logger.info("cleanup_intraday deleted %s rows before %s", n, cutoff)
        return {"cutoff": cutoff.isoformat(), "rows_deleted": n}
    except Exception as e:
        session.rollback()
        record_job(session, "cleanup_intraday", "failed", message=str(e))
        raise
    finally:
        session.close()
