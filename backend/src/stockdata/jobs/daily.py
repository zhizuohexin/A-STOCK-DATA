"""收盘后的日线/涨停/板块抓取任务。"""

from __future__ import annotations

import logging
from datetime import date, datetime

from stockdata.crud import (
    record_job,
    upsert_daily_quotes,
    upsert_limit_up,
    upsert_sector_daily,
    upsert_sectors,
    upsert_stocks,
)
from stockdata.db import SessionLocal
from stockdata.providers import get_provider

logger = logging.getLogger(__name__)


def run_daily_job(
    target_date: date | None = None,
    quote_provider: str = "tushare",
    sector_provider: str = "eastmoney",
) -> dict:
    """完整抓一天的数据：股票列表 + 日线 + 涨停 (tushare) + 板块 + 板块日线 (eastmoney)。"""
    target_date = target_date or date.today()
    started = datetime.utcnow()
    summary: dict[str, int | str | list[str]] = {"date": str(target_date), "errors": []}
    errors: list[str] = []

    session = SessionLocal()
    try:
        p = get_provider(quote_provider)
        sp = get_provider(sector_provider)

        # 1. 股票基础信息（覆盖更新，捕获新上市）
        try:
            rows = p.fetch_stock_list()
            n = upsert_stocks(session, rows)
            session.commit()
            summary["stocks"] = n
        except Exception as e:  # noqa: BLE001
            session.rollback()
            errors.append(f"stocks: {e}")

        # 2. 日线
        try:
            rows = p.fetch_daily_quotes(target_date)
            n = upsert_daily_quotes(session, rows)
            session.commit()
            summary["daily_quotes"] = n
        except Exception as e:  # noqa: BLE001
            session.rollback()
            errors.append(f"daily_quotes: {e}")

        # 3. 涨停池
        try:
            rows = p.fetch_limit_up(target_date)
            n = upsert_limit_up(session, rows)
            session.commit()
            summary["limit_up"] = n
        except Exception as e:  # noqa: BLE001
            session.rollback()
            errors.append(f"limit_up: {e}")

        # 4. 板块（东财）
        try:
            rows = sp.fetch_sectors()
            n = upsert_sectors(session, rows)
            session.commit()
            summary["sectors"] = n
        except Exception as e:  # noqa: BLE001
            session.rollback()
            errors.append(f"sectors: {e}")

        # 5. 板块日线（东财）
        try:
            rows = sp.fetch_sector_daily(target_date)
            n = upsert_sector_daily(session, rows)
            session.commit()
            summary["sector_daily"] = n
        except Exception as e:  # noqa: BLE001
            session.rollback()
            errors.append(f"sector_daily: {e}")

        total = sum(v for v in summary.values() if isinstance(v, int))
        summary["errors"] = errors
        record_job(
            session,
            "daily_job",
            "success" if not errors else "partial",
            message=f"{target_date} elapsed={int((datetime.utcnow() - started).total_seconds())}s",
            rows_affected=total,
        )
        logger.info("daily_job done: %s", summary)
        return summary
    finally:
        session.close()
