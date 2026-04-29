"""每日 15:00 收盘瞬间拉一次开盘啦实时类数据快照。

实时类接口（auction/dashboard / emotion）不支持 ?date= 历史回溯，
只在收盘瞬间拍一次快照，存为当日终值。
"""

from __future__ import annotations

import logging
from datetime import date, datetime

from stockdata.crud import (
    record_job,
    upsert_kpl_dashboard,
    upsert_kpl_emotion,
)
from stockdata.db import SessionLocal
from stockdata.providers.kaipanla import KaipanlaProvider

logger = logging.getLogger(__name__)


def run_realtime_snapshot(target_date: date | None = None) -> dict:
    """拉 auction/dashboard + emotion 当前快照入库（trade_date = today）。"""
    started = datetime.utcnow()
    td = target_date or date.today()
    summary: dict = {"date": str(td), "errors": []}
    errors: list[str] = []
    session = SessionLocal()
    kpl = KaipanlaProvider()
    try:
        # 1. 竞价全景看板
        try:
            data = kpl.fetch_auction_dashboard()
            data["trade_date"] = str(td)
            r = upsert_kpl_dashboard(session, data)
            session.commit()
            summary["dashboard_board"] = r["board"]
            summary["dashboard_tops"] = r["tops"]
            summary["dashboard_sectors"] = r["sectors"]
        except Exception as e:  # noqa: BLE001
            session.rollback()
            errors.append(f"dashboard: {e}")
        # 2. 情绪/分布
        try:
            row = kpl.fetch_emotion()
            n = upsert_kpl_emotion(session, td, row)
            session.commit()
            summary["emotion"] = n
        except Exception as e:  # noqa: BLE001
            session.rollback()
            errors.append(f"emotion: {e}")

        summary["errors"] = errors
        record_job(
            session, "realtime_snapshot",
            "success" if not errors else "partial",
            message=f"{td} elapsed={int((datetime.utcnow() - started).total_seconds())}s",
            rows_affected=sum(v for v in summary.values() if isinstance(v, int)),
        )
        logger.info("realtime_snapshot done: %s", summary)
        return summary
    finally:
        session.close()
        kpl.close()
