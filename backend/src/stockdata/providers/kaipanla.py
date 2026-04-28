"""开盘啦数据增强 Provider（Kaipanla Quant API，inst 套餐）。

不实现 DataProvider 抽象基类（场景不同：复盘 + L2 + 龙虎榜，非原始行情）。
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from stockdata.config import settings

logger = logging.getLogger(__name__)


def _ts_code(code: str) -> str:
    """6 位数字 → 002580.SZ / 600519.SH 形式。"""
    if "." in code:
        return code
    if code.startswith("6"):
        return f"{code}.SH"
    if code.startswith(("0", "3")):
        return f"{code}.SZ"
    if code.startswith(("4", "8", "9")):
        return f"{code}.BJ"
    return code


def _parse_pct(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().rstrip("%")
    try:
        return float(s)
    except ValueError:
        return None


class KaipanlaProvider:
    name = "kaipanla"
    BASE = "http://124.222.49.67:3000"

    def __init__(self, api_key: str | None = None, timeout: float = 15.0) -> None:
        key = api_key or os.environ.get("KAIPANLA_API_KEY") or getattr(settings, "kaipanla_api_key", "")
        if not key:
            logger.warning("KAIPANLA_API_KEY not set; KaipanlaProvider will fail")
        self.client = httpx.Client(
            base_url=self.BASE,
            headers={"x-api-key": key, "User-Agent": "stockdata/1.0"},
            timeout=timeout,
        )

    def close(self) -> None:
        try:
            self.client.close()
        except Exception:
            pass

    def __del__(self) -> None:
        self.close()

    def _get(self, path: str, params: dict | None = None) -> dict:
        r = self.client.get(path, params=params or {})
        r.raise_for_status()
        return r.json()

    # --- 大盘情绪 ---
    def fetch_sentiment(self, trade_date: str | None = None) -> dict[str, Any]:
        params = {"date": trade_date} if trade_date else None
        return self._get("/api/sentiment", params)

    def fetch_ladder(self, trade_date: str | None = None) -> dict[str, Any]:
        params = {"date": trade_date} if trade_date else None
        return self._get("/api/ladder", params)

    # --- 连板个股（每个高度一次请求）---
    def fetch_consecutive(self, level: int, trade_date: str | None = None) -> list[dict]:
        params = {"date": trade_date} if trade_date else None
        data = self._get(f"/api/consecutive/{level}", params)
        rows: list[dict] = []
        for st in data.get("stocks") or []:
            rows.append({
                "trade_date": data.get("date"),
                "ts_code": _ts_code(st["code"]),
                "name": st.get("name"),
                "days": st.get("days") or level,
                "pct_chg": _parse_pct(st.get("changePct")),
                "theme": st.get("theme"),
                "board_desc": st.get("boardDesc"),
                "market_cap": st.get("marketCap"),
            })
        return rows

    def fetch_consecutive_all(self, trade_date: str | None = None, max_level: int = 10) -> list[dict]:
        """拉所有 level 的连板（2..max_level），合并返回。"""
        out: list[dict] = []
        for lv in range(2, max_level + 1):
            try:
                rows = self.fetch_consecutive(lv, trade_date)
                if not rows:
                    break  # 高度往上越少，第一次空就没必要继续
                out.extend(rows)
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (400, 404):
                    break
                raise
        return out

    # --- 炸板池 ---
    def fetch_broken(self, trade_date: str | None = None) -> list[dict]:
        params = {"date": trade_date} if trade_date else None
        data = self._get("/api/broken", params)
        rows = []
        for st in data.get("stocks") or []:
            rows.append({
                "trade_date": data.get("date"),
                "ts_code": _ts_code(st["code"]),
                "name": st.get("name"),
                "pct_chg": _parse_pct(st.get("changePct")),
                "sector": st.get("sector"),
            })
        return rows

    # --- 龙虎榜 ---
    def fetch_lhb_list(self, trade_date: str | None = None) -> list[dict]:
        params = {"date": trade_date} if trade_date else None
        data = self._get("/api/lhb/list", params)
        rows = []
        for st in data.get("stocks") or []:
            rows.append({
                "trade_date": data.get("date"),
                "ts_code": _ts_code(st["code"]),
                "name": st.get("name"),
                "pct_chg": _parse_pct(st.get("changePct")),
                "reason": st.get("reason"),
                "buy_in": float(st["buyIn"]) if st.get("buyIn") not in (None, "") else None,
                "net": st.get("net"),
            })
        return rows

    def fetch_lhb_detail(self, code: str, trade_date: str | None = None) -> dict[str, Any]:
        """单股席位穿透。code 可传 6 位或带后缀。"""
        c = code.split(".")[0]  # API 接受 6 位
        params = {"date": trade_date} if trade_date else None
        return self._get(f"/api/lhb/detail/{c}", params)

    # --- 竞价异动 ---
    def fetch_market_auction(self) -> list[dict]:
        data = self._get("/api/market/auction")
        rows = []
        for st in data.get("stocks") or []:
            rows.append({
                "trade_date": data.get("date"),
                "ts_code": _ts_code(st["code"]),
                "name": st.get("name"),
                "tag": st.get("tag") or None,
                "direction": st.get("direction"),
                "themes": st.get("themes"),
                "pct_chg": _parse_pct(st.get("changePct")),
                "turnover": st.get("turnover"),
                "market_cap": st.get("marketCap"),
                "buy_amount": st.get("buyAmount"),
                "sell_amount": st.get("sellAmount"),
                "net_amount": st.get("netAmount"),
                "big_order_buy": st.get("bigOrderBuy"),
                "big_order_sell": st.get("bigOrderSell"),
                "score": st.get("score"),
            })
        return rows
