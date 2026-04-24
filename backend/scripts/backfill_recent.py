"""批量回溯最近 N 个交易日的数据。

用法:
    # 快路：日线 + 板块日线（约 1 分钟）
    cd backend && uv run python -m scripts.backfill_recent --days 5

    # 加涨停池（慢，约 1 小时/次）
    cd backend && uv run python -m scripts.backfill_recent --days 5 --include-limit

    # 只回溯涨停池（后台跑）
    cd backend && nohup uv run python -m scripts.backfill_recent --days 5 --only-limit > /tmp/bf.log 2>&1 &
"""

from __future__ import annotations

import argparse
import logging
import time
from datetime import date, timedelta

from stockdata.crud import (
    upsert_daily_quotes,
    upsert_limit_up,
    upsert_sector_daily,
    upsert_sectors,
    upsert_stocks,
)
from stockdata.db import SessionLocal
from stockdata.providers import get_provider

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)

RATE_LIMIT_SLEEP = 61 * 60  # Tushare limit_list_d 限 1/小时，sleep 61 分钟


def recent_trading_days(n: int, end: date | None = None) -> list[date]:
    """最近 N 个工作日（不考虑 A 股法定节假日，仅周末过滤）。"""
    d = end or date.today()
    out: list[date] = []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= timedelta(days=1)
    return list(reversed(out))


def sync_basic(session, tushare, eastmoney) -> None:
    log.info("=== 基础数据：股票列表 + 板块列表 ===")
    try:
        rows = tushare.fetch_stock_list()
        n = upsert_stocks(session, rows)
        session.commit()
        log.info("stocks: %s", n)
    except Exception as e:
        session.rollback()
        log.warning("stocks failed: %s", e)

    try:
        rows = eastmoney.fetch_sectors()
        n = upsert_sectors(session, rows)
        session.commit()
        log.info("sectors: %s", n)
    except Exception as e:
        session.rollback()
        log.warning("sectors failed: %s", e)


def backfill_fast(days: list[date], session, tushare, eastmoney) -> None:
    log.info("=== 日线行情（tushare）===")
    for d in days:
        try:
            rows = tushare.fetch_daily_quotes(d)
            n = upsert_daily_quotes(session, rows)
            session.commit()
            log.info("  %s daily_quotes: %s", d, n)
        except Exception as e:
            session.rollback()
            log.warning("  %s daily_quotes failed: %s", d, e)

    log.info("=== 板块日线（eastmoney，批量）===")
    # 批量一次拉所有板块近 N 日（~200 次 HTTP，约 30 秒）
    try:
        n_days = len(days)
        rows = eastmoney.fetch_sector_daily_range(end_date=days[-1], days=n_days)
        # 只保留在 days 集合里的日期
        target = set(days)
        rows = [r for r in rows if r["trade_date"] in target]
        n = upsert_sector_daily(session, rows)
        session.commit()
        log.info("  sector_daily: %s 行（跨 %s 天）", n, n_days)
    except Exception as e:
        session.rollback()
        log.warning("  sector_daily 批量失败: %s", e)


def backfill_limit(days: list[date], session, tushare) -> None:
    """Tushare `limit_list_d` 2000 分限 1/小时。按需 sleep。"""
    calls = [(d, t) for d in days for t in ("U", "D")]
    log.info("=== 涨停/跌停池（tushare, 限频 1/小时）===")
    log.info("计划 %s 次调用，预计耗时约 %s 小时", len(calls), len(calls))

    for i, (d, t) in enumerate(calls):
        label = "涨停" if t == "U" else "跌停"
        attempt = 0
        while attempt < 2:
            try:
                rows = tushare.fetch_limit_pool(d, limit_type=t)
                n = upsert_limit_up(session, rows)
                session.commit()
                log.info("[%d/%d] %s %s %s: %s 行", i + 1, len(calls), d, t, label, n)
                break
            except Exception as e:
                session.rollback()
                err = str(e)
                if "频率超限" in err or "rate" in err.lower() or "1次/小时" in err:
                    if attempt == 0:
                        log.warning("  限频，sleep %d 分钟后重试...", RATE_LIMIT_SLEEP // 60)
                        time.sleep(RATE_LIMIT_SLEEP)
                        attempt += 1
                        continue
                    log.error("  重试仍失败: %s", e)
                    break
                else:
                    log.error("  %s %s 失败: %s", d, t, e)
                    break

        # 每次调用后 sleep 61 分钟（最后一次不 sleep）
        if i < len(calls) - 1:
            log.info("  sleep %d 分钟后做下一个...", RATE_LIMIT_SLEEP // 60)
            time.sleep(RATE_LIMIT_SLEEP)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=5)
    p.add_argument("--include-limit", action="store_true", help="同时回溯涨停池（慢）")
    p.add_argument("--only-limit", action="store_true", help="只回溯涨停池，跳过日线/板块")
    args = p.parse_args()

    days = recent_trading_days(args.days)
    log.info("目标：最近 %d 个交易日 %s ~ %s", args.days, days[0], days[-1])

    session = SessionLocal()
    tushare = get_provider("tushare")
    eastmoney = get_provider("eastmoney")

    try:
        if not args.only_limit:
            sync_basic(session, tushare, eastmoney)
            backfill_fast(days, session, tushare, eastmoney)

        if args.include_limit or args.only_limit:
            backfill_limit(days, session, tushare)
    finally:
        session.close()

    log.info("完成。")


if __name__ == "__main__":
    main()
