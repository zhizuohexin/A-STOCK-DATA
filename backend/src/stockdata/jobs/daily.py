"""收盘后的日线/涨停/板块抓取任务。"""

from __future__ import annotations

import logging
from datetime import date, datetime

from stockdata.crud import (
    recompute_sector_heat,
    record_job,
    upsert_daily_quotes,
    upsert_kpl_sector_ladder,
    upsert_kpl_sectors_heat,
    upsert_limit_up,
    upsert_sector_daily,
    upsert_sectors,
    upsert_stocks,
)
from stockdata.providers.kaipanla import KaipanlaProvider
from stockdata.db import SessionLocal
from stockdata.jobs.kaipanla import run_kpl_job
from stockdata.providers import get_provider

logger = logging.getLogger(__name__)


def run_daily_job(
    target_date: date | None = None,
    quote_provider: str = "tushare",
    sector_provider: str = "eastmoney",
    limit_provider: str = "eastmoney",
) -> dict:
    """完整抓一天的数据。

    quote_provider: 股票列表 + 日线（tushare 强项）
    sector_provider: 板块 + 板块日线（eastmoney 强项）
    limit_provider: 涨/跌停池（默认 eastmoney 公开接口；tushare limit_list_d 频次受限）
    """
    target_date = target_date or date.today()
    started = datetime.utcnow()
    summary: dict[str, int | str | list[str]] = {"date": str(target_date), "errors": []}
    errors: list[str] = []

    session = SessionLocal()
    try:
        p = get_provider(quote_provider)
        sp = get_provider(sector_provider)
        lp = get_provider(limit_provider)

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

        # 3. 涨停 + 跌停池（先 lp，0 行则 fallback 到 tushare）
        for limit_type, key in (("U", "limit_up"), ("D", "limit_down")):
            try:
                rows = lp.fetch_limit_pool(target_date, limit_type=limit_type)
                if not rows and lp.name != p.name:
                    try:
                        rows = p.fetch_limit_pool(target_date, limit_type=limit_type)
                        logger.info("%s fallback to %s: %d rows", key, p.name, len(rows))
                    except Exception as fb_e:  # noqa: BLE001
                        errors.append(f"{key} fallback: {fb_e}")
                n = upsert_limit_up(session, rows)
                session.commit()
                summary[key] = n
            except Exception as e:  # noqa: BLE001
                session.rollback()
                errors.append(f"{key}: {e}")

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

        # 6a. SQL 自己算的板块热度（基于 limit_up_daily + stock_sectors）
        try:
            n = recompute_sector_heat(session, target_date, min_count=10)
            session.commit()
            summary["sector_heat_sql"] = n
        except Exception as e:  # noqa: BLE001
            session.rollback()
            errors.append(f"sector_heat_sql: {e}")

        # 6b. 开盘啦给的板块热度（sectors_strength 仅当天，sector_ladder 支持历史）
        kpl = KaipanlaProvider()
        try:
            if target_date == date.today():
                try:
                    rows = kpl.fetch_sectors_strength()
                    if rows:
                        n = upsert_kpl_sectors_heat(session, rows)
                        session.commit()
                        summary["sector_heat_kpl"] = n
                except Exception as e:  # noqa: BLE001
                    session.rollback()
                    errors.append(f"sector_heat_kpl: {e}")
            # 6c. 板块涨停梯队（含每板块个股，支持历史）
            try:
                rows = kpl.fetch_sector_ladder(str(target_date))
                if rows:
                    n = upsert_kpl_sector_ladder(session, rows)
                    session.commit()
                    summary["sector_ladder_kpl"] = n
            except Exception as e:  # noqa: BLE001
                session.rollback()
                errors.append(f"sector_ladder_kpl: {e}")
        finally:
            kpl.close()

        # 7. 开盘啦增强数据（情绪/连板/炸板/龙虎榜/竞价异动 + 同步入题材库）
        try:
            kpl_summary = run_kpl_job(target_date=target_date, with_lhb_detail=True)
            for k, v in kpl_summary.items():
                if isinstance(v, int):
                    summary[f"kpl_{k}"] = v
            errors.extend(kpl_summary.get("errors") or [])
        except Exception as e:  # noqa: BLE001
            errors.append(f"kpl_job: {e}")

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
