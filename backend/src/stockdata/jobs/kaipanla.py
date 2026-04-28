"""开盘啦 Kaipanla 每日数据抓取 + 同步维护题材库。

调用顺序（每个独立 try/except，不互相影响）：
  1. sentiment      → kpl_sentiment
  2. ladder         → kpl_ladder
  3. consecutive    → kpl_consecutive  + 同步 stock_sectors (src='KPL')
  4. broken         → kpl_broken       + 同步 stock_sectors (src='KPL')
  5. lhb/list       → kpl_lhb
  6. lhb/detail     → kpl_lhb_seat（对每只 lhb 上榜股逐个拉，含游资席位）
  7. market/auction → kpl_auction      + 同步 stock_sectors (src='KPL')
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime

from stockdata.crud import (
    attach_kpl_themes,
    record_job,
    upsert_kpl_auction,
    upsert_kpl_broken,
    upsert_kpl_consecutive,
    upsert_kpl_ladder,
    upsert_kpl_lhb,
    upsert_kpl_lhb_seat,
    upsert_kpl_sentiment,
)
from stockdata.db import SessionLocal
from stockdata.providers.kaipanla import KaipanlaProvider

logger = logging.getLogger(__name__)


def _to_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def run_kpl_job(target_date: date | None = None, with_lhb_detail: bool = True) -> dict:
    """完整拉一天的 Kaipanla 增强数据。

    target_date=None 则拿"最近一个交易日"（API 自动回退）。
    """
    started = datetime.utcnow()
    d_str = target_date.isoformat() if target_date else None
    summary: dict = {"date": d_str or "auto", "errors": []}
    errors: list[str] = []
    theme_added = 0

    session = SessionLocal()
    kpl = KaipanlaProvider()
    try:
        # 1. 大盘情绪
        try:
            data = kpl.fetch_sentiment(d_str)
            td = _to_date(data.get("date"))
            if td:
                upsert_kpl_sentiment(session, {
                    "trade_date": td,
                    "limit_up": data.get("limitUp"),
                    "actual_limit_up": data.get("actualLimitUp"),
                    "limit_down": data.get("limitDown"),
                    "actual_limit_down": data.get("actualLimitDown"),
                    "up_count": data.get("upCount"),
                    "down_count": data.get("downCount"),
                    "flat_count": data.get("flatCount"),
                })
                session.commit()
                summary["sentiment"] = 1
        except Exception as e:  # noqa: BLE001
            session.rollback()
            errors.append(f"sentiment: {e}")

        # 2. 连板梯队汇总
        try:
            data = kpl.fetch_ladder(d_str)
            td = _to_date(data.get("date"))
            if td:
                upsert_kpl_ladder(session, {
                    "trade_date": td,
                    "first_board": data.get("firstBoard"),
                    "second_board": data.get("second"),
                    "third_board": data.get("third"),
                    "high_board": data.get("high"),
                    "rate": data.get("rate"),
                    "comment": data.get("comment"),
                })
                session.commit()
                summary["ladder"] = 1
        except Exception as e:  # noqa: BLE001
            session.rollback()
            errors.append(f"ladder: {e}")

        # 3. 连板个股 + 同步题材
        try:
            rows = kpl.fetch_consecutive_all(d_str)
            for r in rows:
                r["trade_date"] = _to_date(r["trade_date"])
            n = upsert_kpl_consecutive(session, [r for r in rows if r["trade_date"]])
            session.commit()
            summary["consecutive"] = n
            for r in rows:
                if r.get("theme") and r.get("trade_date"):
                    theme_added += attach_kpl_themes(session, r["ts_code"], r["theme"])
            session.commit()
        except Exception as e:  # noqa: BLE001
            session.rollback()
            errors.append(f"consecutive: {e}")

        # 4. 炸板池 + 同步题材
        try:
            rows = kpl.fetch_broken(d_str)
            for r in rows:
                r["trade_date"] = _to_date(r["trade_date"])
            n = upsert_kpl_broken(session, [r for r in rows if r["trade_date"]])
            session.commit()
            summary["broken"] = n
            for r in rows:
                if r.get("sector") and r.get("trade_date"):
                    theme_added += attach_kpl_themes(session, r["ts_code"], r["sector"])
            session.commit()
        except Exception as e:  # noqa: BLE001
            session.rollback()
            errors.append(f"broken: {e}")

        # 5. 龙虎榜个股汇总
        lhb_codes: list[str] = []
        try:
            rows = kpl.fetch_lhb_list(d_str)
            for r in rows:
                r["trade_date"] = _to_date(r["trade_date"])
            valid = [r for r in rows if r["trade_date"]]
            n = upsert_kpl_lhb(session, valid)
            session.commit()
            summary["lhb"] = n
            lhb_codes = [r["ts_code"] for r in valid]
        except Exception as e:  # noqa: BLE001
            session.rollback()
            errors.append(f"lhb: {e}")

        # 6. lhb/detail 席位穿透（对每只榜上股）
        if with_lhb_detail and lhb_codes:
            seat_inserted = 0
            for ts_code in lhb_codes:
                try:
                    detail = kpl.fetch_lhb_detail(ts_code, d_str)
                    detail_td = _to_date(detail.get("date"))
                    if not detail_td:
                        continue
                    seat_rows = []
                    for side, key in (("B", "buySeats"), ("S", "sellSeats")):
                        for s in detail.get(key) or []:
                            seat_rows.append({
                                "trade_date": detail_td,
                                "ts_code": ts_code,
                                "side": side,
                                "rank": int(s["rank"]) if s.get("rank") else None,
                                "broker": s.get("broker") or "未知",
                                "buy_in": s.get("buyIn"),
                                "sell_out": s.get("sellOut"),
                                "net_buy": s.get("netBuy"),
                                "is_dy": 1 if s.get("isDY") else 0,
                            })
                    if seat_rows:
                        upsert_kpl_lhb_seat(session, seat_rows)
                        session.commit()
                        seat_inserted += len(seat_rows)
                    time.sleep(0.3)  # 略限速
                except Exception as e:  # noqa: BLE001
                    session.rollback()
                    errors.append(f"lhb_detail/{ts_code}: {e}")
            summary["lhb_seats"] = seat_inserted

        # 7. 竞价异动 + 同步题材
        try:
            rows = kpl.fetch_market_auction()
            for r in rows:
                r["trade_date"] = _to_date(r["trade_date"])
            valid = [r for r in rows if r["trade_date"]]
            n = upsert_kpl_auction(session, valid)
            session.commit()
            summary["auction"] = n
            for r in valid:
                if r.get("themes"):
                    theme_added += attach_kpl_themes(session, r["ts_code"], r["themes"])
            session.commit()
        except Exception as e:  # noqa: BLE001
            session.rollback()
            errors.append(f"auction: {e}")

        summary["theme_added"] = theme_added
        summary["errors"] = errors
        record_job(
            session, "kpl_job",
            "success" if not errors else "partial",
            message=f"{d_str or 'auto'} elapsed={int((datetime.utcnow() - started).total_seconds())}s",
            rows_affected=sum(v for v in summary.values() if isinstance(v, int)),
        )
        logger.info("kpl_job done: %s", summary)
        return summary
    finally:
        session.close()
        kpl.close()
