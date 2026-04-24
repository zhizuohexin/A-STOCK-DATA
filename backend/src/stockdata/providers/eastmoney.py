"""Eastmoney 东方财富 free HTTP API provider.

Best for: sectors (行业+概念板块)、板块日线、intraday K-line.
Weak at: full stock_list + daily_quotes 批量（东财只有单股查询，跑完要循环 5000+ 次，不实际）。
所以日线/涨停还是用 tushare，板块/分时走 eastmoney。
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime
from typing import Any

import httpx

from stockdata.providers.base import DataProvider

logger = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": UA, "Referer": "https://quote.eastmoney.com/"}


class EastmoneyProvider(DataProvider):
    name = "eastmoney"

    BASE_PUSH = "https://push2.eastmoney.com"
    BASE_HIS = "https://push2his.eastmoney.com"
    BASE_EX = "https://push2ex.eastmoney.com"

    def __init__(self, timeout: float = 15.0) -> None:
        self.client = httpx.Client(headers=HEADERS, timeout=timeout)

    def close(self) -> None:
        try:
            self.client.close()
        except Exception:
            pass

    def __del__(self) -> None:
        self.close()

    # --- not the best fit for eastmoney; keep for interface completeness ---

    def fetch_stock_list(self) -> list[dict[str, Any]]:
        logger.warning("eastmoney.fetch_stock_list not implemented; use tushare")
        return []

    def fetch_daily_quotes(self, trade_date: date) -> list[dict[str, Any]]:
        logger.warning("eastmoney.fetch_daily_quotes not implemented (would require 5000+ calls); use tushare")
        return []

    def fetch_limit_pool(self, trade_date: date, limit_type: str = "U") -> list[dict[str, Any]]:
        """Eastmoney 涨跌停池。limit_type: U=涨停 D=跌停。"""
        endpoint = "getTopicDTPool" if limit_type == "D" else "getTopicZTPool"
        dpt = "wz.dtzt" if limit_type == "D" else "wz.ztzt"
        url = f"{self.BASE_EX}/{endpoint}"
        params = {
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "dpt": dpt,
            "Pageindex": 0,
            "pagesize": 500,
            "sort": "fbt:asc",
            "date": trade_date.strftime("%Y%m%d"),
        }
        r = self.client.get(url, params=params)
        r.raise_for_status()
        payload = r.json().get("data") or {}
        pool = payload.get("pool") or []
        rows: list[dict[str, Any]] = []
        for item in pool:
            code = item.get("c")
            market = item.get("m")
            if not code:
                continue
            suffix = "SH" if market == 1 else "SZ"
            rows.append(
                {
                    "ts_code": f"{code}.{suffix}",
                    "trade_date": trade_date,
                    "name": item.get("n"),
                    "close": _num(item.get("p")) and _num(item.get("p")) / 1000,
                    "pct_chg": _num(item.get("zdp")),
                    "amount": _num(item.get("amount")),
                    "fd_amount": _num(item.get("fund")),
                    "first_time": _secs_to_hhmmss(item.get("fbt")),
                    "last_time": _secs_to_hhmmss(item.get("lbt")),
                    "open_times": _int(item.get("zbc")),
                    "limit_times": _int(item.get("lbc")),
                    "limit": limit_type,
                }
            )
        return rows

    # --- eastmoney strengths ---

    def fetch_sectors(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        rows += self._sector_list("m:90+t:2", "I")  # 行业
        rows += self._sector_list("m:90+t:3", "C")  # 概念
        return rows

    def _sector_list(self, fs: str, type_: str) -> list[dict[str, Any]]:
        """翻页抓全部板块列表。"""
        out: list[dict[str, Any]] = []
        pn = 1
        while True:
            r = self.client.get(
                f"{self.BASE_PUSH}/api/qt/clist/get",
                params={
                    "pn": pn,
                    "pz": 200,
                    "po": 1,
                    "np": 1,
                    "fltt": 2,
                    "invt": 2,
                    "fid": "f3",
                    "fs": fs,
                    "fields": "f12,f14",
                },
            )
            r.raise_for_status()
            data = (r.json() or {}).get("data") or {}
            diff = data.get("diff") or []
            total = data.get("total") or 0
            if not diff:
                break
            for item in diff:
                code = item.get("f12") or ""
                if not code:
                    continue
                out.append(
                    {
                        "ts_code": code if code.startswith("BK") else f"BK{code}",
                        "name": item.get("f14"),
                        "type": type_,
                        "src": "EM",
                    }
                )
            if total > 0 and len(out) >= total:
                break
            if len(diff) == 0:
                break
            pn += 1
            if pn > 20:  # safety
                break
            time.sleep(0.1)
        return out

    def fetch_sector_daily(self, trade_date: date) -> list[dict[str, Any]]:
        """当日板块日线用 clist 快照；历史日期用 kline 每板块循环（慢）。"""
        today = date.today()
        if trade_date == today:
            rows: list[dict[str, Any]] = []
            rows += self._sector_daily_snapshot("m:90+t:2", trade_date)
            rows += self._sector_daily_snapshot("m:90+t:3", trade_date)
            return rows
        return self._sector_daily_historical(trade_date)

    def _sector_daily_snapshot(self, fs: str, trade_date: date) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        pn = 1
        while True:
            r = self.client.get(
                f"{self.BASE_PUSH}/api/qt/clist/get",
                params={
                    "pn": pn,
                    "pz": 200,
                    "po": 1,
                    "np": 1,
                    "fltt": 2,
                    "invt": 2,
                    "fid": "f3",
                    "fs": fs,
                    "fields": "f12,f14,f2,f3,f5,f6",
                },
            )
            r.raise_for_status()
            data = (r.json() or {}).get("data") or {}
            diff = data.get("diff") or []
            total = data.get("total") or 0
            if not diff:
                break
            for item in diff:
                code = item.get("f12") or ""
                if not code:
                    continue
                out.append(
                    {
                        "sector_code": code if code.startswith("BK") else f"BK{code}",
                        "trade_date": trade_date,
                        "name": item.get("f14"),
                        "close": _num(item.get("f2")),
                        "pct_chg": _num(item.get("f3")),
                        "vol": _num(item.get("f5")),
                        "amount": _num(item.get("f6")),
                    }
                )
            if total > 0 and len(out) >= total:
                break
            if len(diff) == 0:
                break
            pn += 1
            if pn > 20:  # safety
                break
            time.sleep(0.1)
        return out

    def _sector_daily_historical(self, trade_date: date) -> list[dict[str, Any]]:
        # 单日历史：等价于范围=1
        return self.fetch_sector_daily_range(end_date=trade_date, days=1)

    def fetch_sector_members(self, sector_code: str) -> list[str]:
        """拉单个板块的成分股代码列表。sector_code 形如 BK1029。"""
        code = sector_code.removeprefix("BK")
        r = self.client.get(
            f"{self.BASE_PUSH}/api/qt/clist/get",
            params={
                "pn": 1,
                "pz": 2000,
                "po": 1,
                "np": 1,
                "fltt": 2,
                "invt": 2,
                "fid": "f3",
                "fs": f"b:BK{code}",
                "fields": "f12,f13",
            },
        )
        r.raise_for_status()
        diff = ((r.json() or {}).get("data") or {}).get("diff") or []
        out: list[str] = []
        for item in diff:
            code = item.get("f12") or ""
            market = item.get("f13")
            if not code:
                continue
            suffix = "SH" if market == 1 else "SZ" if market == 0 else "BJ"
            out.append(f"{code}.{suffix}")
        return out

    def fetch_all_stock_sectors(self, sector_type: str | None = None) -> list[dict[str, Any]]:
        """批量：拉所有板块成分股，返回 (ts_code, sector_code) 对。"""
        sectors = self.fetch_sectors()
        if sector_type:
            sectors = [s for s in sectors if s["type"] == sector_type]
        rows: list[dict[str, Any]] = []
        for i, sec in enumerate(sectors):
            try:
                members = self.fetch_sector_members(sec["ts_code"])
                for ts_code in members:
                    rows.append({"ts_code": ts_code, "sector_code": sec["ts_code"], "src": "EM"})
            except Exception as e:  # noqa: BLE001
                logger.warning("members fetch failed for %s: %s", sec["ts_code"], e)
                time.sleep(0.5)
                continue
            if i % 50 == 49:
                time.sleep(0.5)
            else:
                time.sleep(0.05)
        return rows

    def fetch_sector_daily_range(
        self,
        end_date: date,
        days: int = 5,
    ) -> list[dict[str, Any]]:
        """批量：一次拉取所有板块近 days 个交易日的日线。

        每板块 1 次 HTTP；板块间 sleep 防止东财断连接。
        """
        sectors = self.fetch_sectors()
        out: list[dict[str, Any]] = []
        for i, sec in enumerate(sectors):
            secid = f"90.{sec['ts_code'].removeprefix('BK')}"
            try:
                kline = self._kline(secid, klt=101, lmt=days + 5)
            except Exception as e:  # noqa: BLE001
                logger.warning("sector %s kline failed: %s", sec["ts_code"], e)
                time.sleep(0.5)
                continue
            for bar in kline:
                td = bar.get("trade_date")
                if isinstance(td, date) and td <= end_date:
                    out.append(
                        {
                            "sector_code": sec["ts_code"],
                            "trade_date": td,
                            "name": sec["name"],
                            "close": bar["close"],
                            "pct_chg": bar["pct_chg"],
                            "vol": bar["vol"],
                            "amount": bar["amount"],
                        }
                    )
            if i % 50 == 49:
                time.sleep(0.5)
            else:
                time.sleep(0.05)
        return out

    def fetch_intraday_bars(
        self, ts_code: str, trade_date: date, freq: str = "1min"
    ) -> list[dict[str, Any]]:
        secid = _ts_code_to_secid(ts_code)
        klt = {"1min": 1, "5min": 5, "15min": 15, "30min": 30, "60min": 60}.get(freq, 1)
        # 取近 240 根，覆盖一天
        klines = self._kline(secid, klt=klt, lmt=240)
        out: list[dict[str, Any]] = []
        for bar in klines:
            bt = bar.get("bar_time")
            if not isinstance(bt, datetime):
                continue
            if bt.date() != trade_date:
                continue
            out.append(
                {
                    "ts_code": ts_code,
                    "bar_time": bt,
                    "open": bar["open"],
                    "high": bar["high"],
                    "low": bar["low"],
                    "close": bar["close"],
                    "vol": bar["vol"],
                    "amount": bar["amount"],
                }
            )
        return out

    # --- shared kline parser ---

    def _kline(self, secid: str, klt: int, lmt: int = 240) -> list[dict[str, Any]]:
        r = self.client.get(
            f"{self.BASE_HIS}/api/qt/stock/kline/get",
            params={
                "secid": secid,
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "klt": klt,
                "fqt": 1,
                "lmt": lmt,
                "end": "20500000",
            },
        )
        r.raise_for_status()
        data = (r.json() or {}).get("data") or {}
        klines = data.get("klines") or []
        rows: list[dict[str, Any]] = []
        for line in klines:
            parts = line.split(",")
            if len(parts) < 9:
                continue
            ts_str = parts[0]
            bar_time: datetime | date
            try:
                if len(ts_str) > 10:
                    bar_time = datetime.strptime(ts_str, "%Y-%m-%d %H:%M")
                    trade_date = bar_time.date()
                else:
                    trade_date = datetime.strptime(ts_str, "%Y-%m-%d").date()
                    bar_time = trade_date
            except ValueError:
                continue
            rows.append(
                {
                    "bar_time": bar_time,
                    "trade_date": trade_date if isinstance(bar_time, datetime) else bar_time,
                    "open": _num(parts[1]),
                    "close": _num(parts[2]),
                    "high": _num(parts[3]),
                    "low": _num(parts[4]),
                    "vol": _num(parts[5]),
                    "amount": _num(parts[6]),
                    "pct_chg": _num(parts[8]),
                }
            )
        return rows


def _num(v: Any) -> float | None:
    if v is None or v == "" or v == "-":
        return None
    try:
        f = float(v)
        return None if f != f else f  # NaN guard
    except (TypeError, ValueError):
        return None


def _int(v: Any) -> int | None:
    f = _num(v)
    return int(f) if f is not None else None


def _ts_code_to_secid(ts_code: str) -> str:
    """000001.SZ -> 0.000001, 600000.SH -> 1.600000"""
    code, _, exchange = ts_code.partition(".")
    market = "1" if exchange.upper() in ("SH", "SSE") else "0"
    return f"{market}.{code}"


def _secs_to_hhmmss(secs: Any) -> str | None:
    """Eastmoney first_time/last_time is seconds since 00:00:00 (e.g. 33000 = 09:10:00)."""
    n = _int(secs)
    if n is None or n <= 0:
        return None
    h, rem = divmod(n, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
