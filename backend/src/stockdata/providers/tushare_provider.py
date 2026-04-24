from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import tushare as ts

from stockdata.config import settings
from stockdata.providers.base import DataProvider

logger = logging.getLogger(__name__)


def _fmt(d: date) -> str:
    return d.strftime("%Y%m%d")


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(str(s), "%Y%m%d").date()
    except (ValueError, TypeError):
        return None


class TushareProvider(DataProvider):
    name = "tushare"

    def __init__(self, token: str | None = None) -> None:
        self.token = token or settings.tushare_token
        if not self.token:
            raise RuntimeError("TUSHARE_TOKEN not set")
        ts.set_token(self.token)
        self.pro = ts.pro_api()

    def fetch_stock_list(self) -> list[dict[str, Any]]:
        df = self.pro.stock_basic(
            exchange="",
            list_status="L",
            fields="ts_code,symbol,name,area,industry,market,list_date",
        )
        rows: list[dict[str, Any]] = []
        for _, r in df.iterrows():
            rows.append(
                {
                    "ts_code": r["ts_code"],
                    "symbol": r["symbol"],
                    "name": r["name"],
                    "area": r.get("area"),
                    "industry": r.get("industry"),
                    "market": r.get("market"),
                    "list_date": _parse_date(r.get("list_date")),
                    "is_active": 1,
                }
            )
        return rows

    def fetch_daily_quotes(self, trade_date: date) -> list[dict[str, Any]]:
        d = _fmt(trade_date)
        df = self.pro.daily(trade_date=d)
        # 合并换手率 (daily_basic)
        try:
            basic = self.pro.daily_basic(trade_date=d, fields="ts_code,turnover_rate")
            turnover_map = dict(zip(basic["ts_code"], basic["turnover_rate"]))
        except Exception as e:
            logger.warning("daily_basic fetch failed: %s", e)
            turnover_map = {}

        rows: list[dict[str, Any]] = []
        for _, r in df.iterrows():
            rows.append(
                {
                    "ts_code": r["ts_code"],
                    "trade_date": _parse_date(r["trade_date"]),
                    "open": _num(r.get("open")),
                    "high": _num(r.get("high")),
                    "low": _num(r.get("low")),
                    "close": _num(r.get("close")),
                    "pre_close": _num(r.get("pre_close")),
                    "change": _num(r.get("change")),
                    "pct_chg": _num(r.get("pct_chg")),
                    "vol": _num(r.get("vol")),
                    "amount": _num(r.get("amount")),
                    "turnover_rate": _num(turnover_map.get(r["ts_code"])),
                }
            )
        return rows

    def fetch_limit_up(self, trade_date: date) -> list[dict[str, Any]]:
        d = _fmt(trade_date)
        # Tushare 涨停池接口 limit_list_d，需 2000 积分。
        # 注意：kpl_list（开盘啦）是独立付费数据源，2000 档没权限，不要做 fallback。
        df = self.pro.limit_list_d(trade_date=d, limit_type="U")

        rows: list[dict[str, Any]] = []
        if df is None or df.empty:
            return rows
        for _, r in df.iterrows():
            rows.append(
                {
                    "ts_code": r.get("ts_code"),
                    "trade_date": _parse_date(r.get("trade_date") or d),
                    "name": r.get("name"),
                    "close": _num(r.get("close")),
                    "pct_chg": _num(r.get("pct_chg")),
                    "amount": _num(r.get("amount")),
                    "fd_amount": _num(r.get("fd_amount") or r.get("fc_ratio")),
                    "first_time": _str_or_none(r.get("first_time")),
                    "last_time": _str_or_none(r.get("last_time")),
                    "open_times": _int(r.get("open_times")),
                    "up_stat": _str_or_none(r.get("up_stat")),
                    "limit_times": _int(r.get("limit_times") or r.get("lu_time")),
                    "limit": r.get("limit") or "U",
                }
            )
        return rows

    def fetch_sectors(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        # 行业
        try:
            df = self.pro.index_classify(level="L1", src="SW2021")
            for _, r in df.iterrows():
                rows.append(
                    {
                        "ts_code": r["index_code"],
                        "name": r["industry_name"],
                        "type": "I",
                        "src": "SW2021",
                    }
                )
        except Exception as e:
            logger.warning("index_classify failed: %s", e)
        # 概念 (同花顺)
        try:
            df = self.pro.ths_index(exchange="A", type="N")
            for _, r in df.iterrows():
                rows.append(
                    {
                        "ts_code": r["ts_code"],
                        "name": r["name"],
                        "type": "C",
                        "src": "THS",
                    }
                )
        except Exception as e:
            logger.warning("ths_index failed: %s", e)
        return rows

    def fetch_sector_daily(self, trade_date: date) -> list[dict[str, Any]]:
        d = _fmt(trade_date)
        rows: list[dict[str, Any]] = []
        # 同花顺概念板块日线
        try:
            df = self.pro.ths_daily(trade_date=d)
            for _, r in df.iterrows():
                rows.append(
                    {
                        "sector_code": r["ts_code"],
                        "trade_date": _parse_date(r.get("trade_date") or d),
                        "name": r.get("name"),
                        "close": _num(r.get("close")),
                        "pct_chg": _num(r.get("pct_change") or r.get("pct_chg")),
                        "vol": _num(r.get("vol")),
                        "amount": _num(r.get("amount")),
                    }
                )
        except Exception as e:
            logger.warning("ths_daily failed: %s", e)
        return rows

    def fetch_intraday_bars(self, ts_code: str, trade_date: date, freq: str = "1min") -> list[dict[str, Any]]:
        start = datetime.combine(trade_date, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")
        end = datetime.combine(trade_date, datetime.max.time()).strftime("%Y-%m-%d %H:%M:%S")
        df = ts.pro_bar(ts_code=ts_code, freq=freq, start_date=start, end_date=end)
        rows: list[dict[str, Any]] = []
        if df is None:
            return rows
        for _, r in df.iterrows():
            bar_time = r.get("trade_time") or r.get("trade_date")
            if isinstance(bar_time, str):
                try:
                    bar_time = datetime.strptime(bar_time, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue
            rows.append(
                {
                    "ts_code": ts_code,
                    "bar_time": bar_time,
                    "open": _num(r.get("open")),
                    "high": _num(r.get("high")),
                    "low": _num(r.get("low")),
                    "close": _num(r.get("close")),
                    "vol": _num(r.get("vol")),
                    "amount": _num(r.get("amount")),
                }
            )
        return rows


def _num(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        if f != f:  # NaN
            return None
        return f
    except (TypeError, ValueError):
        return None


def _int(v: Any) -> int | None:
    f = _num(v)
    return int(f) if f is not None else None


def _str_or_none(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None
