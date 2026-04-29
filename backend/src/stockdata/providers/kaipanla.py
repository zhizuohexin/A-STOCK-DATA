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
        """拉所有 level 的涨停股（1..max_level，含首板），合并返回。"""
        out: list[dict] = []
        for lv in range(1, max_level + 1):
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

    def fetch_sector_ladder(self, trade_date: str | None = None) -> list[dict]:
        """开盘啦板块涨停梯队：每个热点板块 + 板块下涨停个股 + 连板描述。

        支持 ?date= 历史回溯。返回扁平化的 list:
        [{trade_date, sector_code, sector_name, ts_code, stock_name, td_type, tips}, ...]
        """
        params = {"date": trade_date} if trade_date else {}
        # 接口要求传 code 参数，但实际返全部板块；传任意 valid 板块代码即可
        params["code"] = "801001"
        data = self._get("/api/sector-ladder", params)
        out: list[dict] = []
        for grp in data.get("List") or []:
            sec_code = str(grp.get("ZSCode") or "")
            sec_name = grp.get("ZSName")
            for td in grp.get("TD") or []:
                td_type = str(td.get("TDType") or "")
                for st in td.get("Stock") or []:
                    code = st.get("StockID")
                    if not code:
                        continue
                    out.append({
                        "trade_date": trade_date,
                        "sector_code": sec_code,
                        "sector_name": sec_name,
                        "ts_code": _ts_code(code),
                        "stock_name": st.get("StockName"),
                        "td_type": td_type,
                        "tips": st.get("Tips") or None,
                    })
        return out

    # --- 板块强度（含涨停 count，仅当天）---
    def fetch_sectors_strength(self) -> list[dict]:
        """开盘啦板块强度排行。每个板块带 count（涨停数）。

        ⚠️ 此接口不支持历史回溯，传 ?date= 也只返当天。
        返回字段：{trade_date, sector_code (801xxx), sector_name, count}
        """
        data = self._get("/api/sectors")
        rows = []
        for st in data.get("sectors") or []:
            rows.append({
                "trade_date": data.get("date"),
                "sector_code": str(st.get("code") or ""),
                "sector_name": st.get("name"),
                "count": st.get("count"),
            })
        return rows

    # --- 大幅回撤池 ---
    def fetch_withdrawal(self, trade_date: str | None = None) -> list[dict]:
        params = {"date": trade_date} if trade_date else {}
        data = self._get("/api/withdrawal", params)
        out = []
        for st in data.get("stocks") or []:
            code = st.get("code")
            if not code:
                continue
            out.append({
                "trade_date": data.get("date") or trade_date,
                "ts_code": _ts_code(code),
                "name": st.get("name"),
                "pct_chg": _parse_pct(st.get("changePct")),
                "withdrawal_pct": _parse_pct(st.get("withdrawalPct")),
                "price": st.get("price"),
            })
        return out

    # --- 空间板梯队 ---
    def fetch_market_ladder(self, trade_date: str | None = None) -> list[dict]:
        params = {"date": trade_date} if trade_date else {}
        data = self._get("/api/market-ladder", params)
        out = []
        for grp in data.get("List") or []:
            tip = str(grp.get("Tip") or "")
            for st in grp.get("Stocks") or []:
                code = st.get("StockID")
                if not code:
                    continue
                out.append({
                    "trade_date": trade_date,
                    "tip": tip,
                    "ts_code": _ts_code(code),
                    "stock_name": st.get("Name"),
                    "tips": st.get("Tips") or None,
                })
        return out

    # --- 题材新闻 ---
    def fetch_news_themes(self, limit: int = 30) -> dict:
        params = {"limit": limit} if limit else {}
        data = self._get("/api/news/themes", params)
        news_items = data.get("news") or []
        out_news: list[dict] = []
        out_stocks: list[dict] = []
        for n in news_items:
            nid = n.get("id")
            if not nid:
                continue
            t = n.get("time")
            try:
                from datetime import datetime as _dt
                news_time = _dt.fromisoformat(t.replace("Z", "+00:00")) if t else None
            except Exception:
                news_time = None
            out_news.append({
                "news_id": int(nid),
                "title": n.get("title"),
                "sector": n.get("sector") or None,
                "keyword": n.get("keyword") or None,
                "source": n.get("source"),
                "news_time": news_time,
                "status": n.get("status"),
            })
            for s in n.get("stocks") or []:
                code = s.get("code")
                if not code:
                    continue
                out_stocks.append({
                    "news_id": int(nid),
                    "ts_code": _ts_code(code),
                    "stock_name": s.get("name"),
                    "pct_chg": _parse_pct(s.get("changePct")),
                    "is_top": 1 if s.get("isTop") else 0,
                })
        return {"news": out_news, "stocks": out_stocks}

    # --- 盘中题材异动事件流 ---
    def fetch_conception_history(self, trade_date: str | None = None) -> list[dict]:
        params = {"date": trade_date} if trade_date else {}
        data = self._get("/api/conception/history", params)
        td = trade_date or data.get("date")
        out = []
        for e in data.get("list") or []:
            txt = e.get("Plate") or ""
            tm = e.get("Time")
            if not txt or tm is None:
                continue
            out.append({
                "trade_date": td,
                "event_time": int(tm),
                "plate_text": txt,
                "plate_code": e.get("PlateCode") or None,
                "plate_name": e.get("PlateName") or None,
                "plate_je": e.get("PlateJE") or None,
                "plate_zdf": e.get("PlateZDF") or None,
                "event_type": e.get("Type") or None,
                "color": e.get("Color") or None,
            })
        return out

    # --- 历史 100 日市场强度曲线 ---
    def fetch_history_strength(self) -> list[dict]:
        data = self._get("/api/history/strength")
        out = []
        for d in data.get("days") or []:
            td = d.get("date")
            if not td:
                continue
            out.append({
                "trade_date": td,
                "strength": d.get("strength"),
                "limit_up_count": d.get("limitUpCount"),
                "max_consecutive": d.get("maxConsecutive"),
                "big_drop_count": d.get("bigDropCount"),
            })
        return out

    # --- 实时类（15:00 拉一次入库当日终值）---

    def fetch_auction_dashboard(self) -> dict:
        """竞价全景看板。返回 board / weatherVane.topUp/topDown / sectorFace 三段。"""
        data = self._get("/api/auction/dashboard")
        td_str = data.get("date")
        snap_time = data.get("time")
        b = data.get("board") or {}
        wv = data.get("weatherVane") or {}
        sf = data.get("sectorFace") or []
        return {
            "trade_date": td_str,
            "snapshot_time": snap_time,
            "board": {
                "today_zhang_ting": b.get("todayZhangTing"),
                "last_zhang_ting": b.get("lastZhangTing"),
                "today_feng_ban": b.get("todayFengBan"),
                "last_feng_ban_rate": b.get("lastFengBanRate"),
                "today_die_ting": b.get("todayDieTing"),
                "last_die_ting": b.get("lastDieTing"),
                "up_count": b.get("upCount"),
                "down_count": b.get("downCount"),
                "flat_count": b.get("flatCount"),
                "intensity": b.get("intensity"),
                "last_zt_money": b.get("lastZTMoney"),
                "last_lb_money": b.get("lastLBMoney"),
            },
            "tops": [
                *[{"direction": "up", "rank": i + 1, "ts_code": _ts_code(s["code"]),
                   "name": s.get("name"), "pct_chg": _parse_pct(s.get("changePct")),
                   "sector": s.get("sector")} for i, s in enumerate(wv.get("topUp") or [])],
                *[{"direction": "down", "rank": i + 1, "ts_code": _ts_code(s["code"]),
                   "name": s.get("name"), "pct_chg": _parse_pct(s.get("changePct")),
                   "sector": s.get("sector")} for i, s in enumerate(wv.get("topDown") or [])],
            ],
            "sectors": [
                {"sector_code": str(s.get("sectorId") or ""), "sector_name": s.get("name"),
                 "pct_chg": _parse_pct(s.get("changePct"))} for s in sf
            ],
        }

    def fetch_emotion(self) -> dict:
        """实时情绪 + 涨跌区间分布 + 量比（拉两个接口合并）。"""
        try:
            d1 = self._get("/api/emotion/distribution")
        except Exception:
            d1 = {}
        return {
            "up_count": d1.get("upCount"),
            "down_count": d1.get("downCount"),
            "limit_up": d1.get("limitUp"),
            "limit_down": d1.get("limitDown"),
            "today_vol": d1.get("todayVol"),
            "yest_vol": d1.get("yestVol"),
            "vol_ratio": d1.get("volRatio"),
        }

    # --- 历史/累积类（17:30 daily_job 拉）---

    def fetch_youzi_trends(self, trade_date: str | None = None) -> dict:
        """游资动向：8 个游资 × N 条操盘明细。返回扁平化的 traders + trades。"""
        params = {"date": trade_date} if trade_date else {}
        data = self._get("/api/youzi/trends", params)
        traders: list[dict] = []
        trades: list[dict] = []
        for t in data.get("traders") or []:
            tid = str(t.get("id") or "")
            if not tid:
                continue
            traders.append({"trader_id": tid, "name": t.get("name")})
            for rec in t.get("records") or []:
                for side, items in (("B", rec.get("buys") or []), ("S", rec.get("sells") or [])):
                    for item in items:
                        code = item.get("stockCode")
                        if not code:
                            continue
                        trades.append({
                            "trade_date": item.get("date") or trade_date,
                            "trader_id": tid,
                            "side": side,
                            "seat_name": item.get("seatName"),
                            "ts_code": _ts_code(code),
                            "buy": item.get("buy"),
                            "sell": item.get("sell"),
                            "net_amount": item.get("netAmount"),
                        })
        return {"traders": traders, "trades": trades}

    def fetch_history_analysis(self) -> list[dict]:
        """长周期涨跌停 + 炸板率趋势。"""
        data = self._get("/api/history/analysis")
        out = []
        for d in data.get("trends") or []:
            td = d.get("date")
            if not td:
                continue
            out.append({
                "trade_date": td,
                "limit_up": d.get("limitUp"),
                "limit_down": d.get("limitDown"),
                "broken": d.get("broken"),
                "blown": d.get("blown"),
                "blown_rate": d.get("blownRate"),
            })
        return out

    def fetch_sector_news(self, sector_code: str) -> list[dict]:
        """单板块新闻流。"""
        data = self._get(f"/api/sector/news/{sector_code}")
        out = []
        for n in data.get("news") or []:
            from datetime import datetime as _dt
            tm = n.get("time")
            try:
                news_time = _dt.fromtimestamp(int(tm)) if tm else None
            except Exception:
                news_time = None
            out.append({
                "sector_code": sector_code,
                "news_id": str(n.get("id") or ""),
                "title": n.get("title"),
                "news_time": news_time,
                "news_type": n.get("type"),
            })
        return out

    def fetch_news_selected(self) -> list[dict]:
        """编辑精选深度文章。"""
        data = self._get("/api/news/selected")
        out = []
        for a in data.get("List") or []:
            aid = a.get("ID")
            if not aid:
                continue
            from datetime import datetime as _dt
            ct = a.get("CreateTime")
            try:
                create_time = _dt.fromtimestamp(int(ct)) if ct else None
            except Exception:
                create_time = None
            img = ""
            try:
                imgs = (a.get("img") or {}).get("List") or []
                img = imgs[0] if imgs else ""
            except Exception:
                pass
            import json as _json
            out.append({
                "article_id": int(aid),
                "title": a.get("Title"),
                "account": a.get("Account"),
                "create_time": create_time,
                "img_url": img or None,
                "related": _json.dumps(a.get("Stock") or [], ensure_ascii=False) or None,
            })
        return out

    # --- 个股涨停基因（按需查，不入库）---
    def fetch_stock_ztgene(self, code: str) -> dict:
        c = code.split(".")[0]
        return self._get(f"/api/stock/ztgene/{c}")

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
