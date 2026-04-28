"""手动维护股票↔板块关联（src='MANUAL'，永不被自动同步覆盖）。

支持两种入口：
1. 上传截图（同花顺/东财个股板块页）→ OCR 解析 → 自动入库
2. 直接传 ts_code + sector_names 列表 → 入库
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from stockdata.models import Sector, StockSector
from stockdata.services.ocr import run_ocr_with_boxes

logger = logging.getLogger(__name__)

# 同花顺/东财截图常见的"非板块名"文本，解析时排除
_NON_SECTOR_TOKENS = {
    "行业板块", "概念板块", "对应龙头股", "对应人气股", "细分行业",
    "最相关", "看点", "资讯", "盘口", "资金", "简况", "诊股", "股票",
    "下单", "社区", "删自选", "功能", "F10", "Level-2", "level-2",
    "深证", "上证", "创业板", "沪深300", "App", "同花顺",
}

_PERCENT_RE = re.compile(r"^[+\-]?\d+(\.\d+)?%$")
_PRICE_RE = re.compile(r"^\d+(\.\d+)?$")  # 纯小数（价格、指数）
_LIMIT_TAG_RE = re.compile(r"^涨停\d+$")  # "涨停12"
_TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")  # 17:56
_PCT_TAIL_RE = re.compile(r"\s*[+\-]?\d+(\.\d+)?%\s*$")  # 行尾百分比


def _is_junk(t: str) -> bool:
    if not t or len(t) > 30:
        return True
    if t in _NON_SECTOR_TOKENS:
        return True
    if _PERCENT_RE.match(t) or _PRICE_RE.match(t) or _LIMIT_TAG_RE.match(t) or _TIME_RE.match(t):
        return True
    # 单纯的数字（如 5G 不算，但 60、5G、14995.75 要区分）
    return False


def parse_sector_screenshot(image_bytes: bytes) -> dict[str, Any]:
    """解析同花顺/东财个股板块截图。

    返回：
      {
        "stock_name": str | None,
        "sector_names": list[str],
        "raw_lines": list[str]   # 调试用
      }
    """
    items, width, height = run_ocr_with_boxes(image_bytes)
    if not items:
        return {"stock_name": None, "sector_names": [], "raw_lines": []}

    # 1) 顶部红条：取 y < height*0.15 区域里最长的中文 token，认为是股票名
    stock_name: str | None = None
    top_items = [it for it in items if it["y"] < height * 0.15]
    chinese_top = [
        it for it in top_items
        if re.search(r"[\u4e00-\u9fa5]", it["text"]) and len(it["text"]) >= 2
        and not _is_junk(it["text"])
    ]
    if chinese_top:
        # 选 x 居中、长度 >=2 的（兼顾"圣阳股份"这种 4 字）
        chinese_top.sort(key=lambda it: (-len(it["text"]), abs(it["x"] + it["w"] / 2 - width / 2)))
        stock_name = chinese_top[0]["text"]

    # 2) 板块名：x 在左半边（< width*0.5），y 在中间区域（>height*0.15 且 <height*0.92）
    left_items = [
        it for it in items
        if it["x"] < width * 0.5
        and it["y"] > height * 0.15
        and it["y"] < height * 0.92
    ]
    # 按 y 排序后，逐行处理
    left_items.sort(key=lambda it: (it["y"], it["x"]))

    # 行聚合：y 差小于行高 0.6 倍归为一行
    rows: list[list[dict]] = []
    for it in left_items:
        if rows and abs(it["y"] - rows[-1][0]["y"]) < it["h"] * 0.6:
            rows[-1].append(it)
        else:
            rows.append([it])

    sector_names: list[str] = []
    seen: set[str] = set()
    for row in rows:
        # 一行的所有左侧 text 拼起来
        text_parts = [it["text"] for it in sorted(row, key=lambda x: x["x"])]
        joined = " ".join(text_parts).strip()
        # 去掉行尾百分比
        joined = _PCT_TAIL_RE.sub("", joined).strip()
        # 拆分 token，过滤垃圾
        tokens = [t for t in re.split(r"\s+", joined) if t and not _is_junk(t)]
        if not tokens:
            continue
        # 板块名通常是第一个/合并后的中文 token
        candidate = "".join(tokens) if all(re.search(r"[\u4e00-\u9fa5]", t) for t in tokens) else tokens[0]
        # 进一步清洗：去掉中间空格
        candidate = re.sub(r"\s+", "", candidate)
        # 至少 2 个字，且包含中文或字母数字混合（如 5G）
        if len(candidate) < 2:
            continue
        if not re.search(r"[\u4e00-\u9fa5A-Za-z]", candidate):
            continue
        if candidate in _NON_SECTOR_TOKENS or candidate in seen:
            continue
        seen.add(candidate)
        sector_names.append(candidate)

    raw_lines = [it["text"] for it in items]
    return {
        "stock_name": stock_name,
        "sector_names": sector_names,
        "raw_lines": raw_lines,
    }


_STOCK_CODE_RE = re.compile(r"^[036]\d{5}$")  # A 股代码：0/3/6 开头 6 位
_GROUP_TITLE_RE = re.compile(r"[【\[](.+?)[】\]]")  # 【XXX】或 [XXX]
_HEADER_TOKENS = {"代码", "简称", "名称", "时间", "板", "涨幅", "原因", "首封", "连板"}


def parse_limit_up_table(image_bytes: bytes) -> dict[str, Any]:
    """解析涨停复盘表（多股票分组带题材）。

    格式特征：
      【题材A】N 只 X 亿
        000001  XX股份  09:30  3  10.0%  题材A详细
        000002  YY股份  09:31  2  9.9%   题材A
      【题材B】...

    返回：
      {
        "groups": [
          {
            "title": "国产芯片",
            "stocks": [{"ts_code": "000001.SZ", "name": "XX股份", "reason": "算力", "time": "09:30", "limit_times": 3}],
          },
          ...
        ],
        "raw_lines": [...]
      }
    """
    items, width, height = run_ocr_with_boxes(image_bytes)
    if not items:
        return {"groups": [], "raw_lines": []}

    # 按 y 排序后聚合行
    items.sort(key=lambda it: (it["y"], it["x"]))
    rows: list[list[dict]] = []
    for it in items:
        if rows and abs(it["y"] - rows[-1][0]["y"]) < it["h"] * 0.6:
            rows[-1].append(it)
        else:
            rows.append([it])
    # 行内按 x 排序
    for row in rows:
        row.sort(key=lambda it: it["x"])

    groups: list[dict] = []
    current_title: str | None = None
    current_stocks: list[dict] = []

    for row in rows:
        line = " ".join(it["text"] for it in row).strip()
        # 1) 题材分组标题
        m = _GROUP_TITLE_RE.search(line)
        if m and ("只" in line or "亿" in line or len(line) < 25):
            if current_title is not None:
                groups.append({"title": current_title, "stocks": current_stocks})
            current_title = m.group(1).strip()
            current_stocks = []
            continue
        # 2) 表头行（代码 简称 ...）跳过
        tokens = [it["text"] for it in row]
        if any(t in _HEADER_TOKENS for t in tokens):
            continue
        # 3) 找 6 位股票代码 token
        code_token = None
        code_idx = -1
        for i, t in enumerate(tokens):
            if _STOCK_CODE_RE.match(t):
                code_token = t
                code_idx = i
                break
        if not code_token:
            continue
        # 假设 code 之后顺序是：name、time、limit_times、pct_chg、reason
        rest = tokens[code_idx + 1:]
        name = rest[0] if rest else None
        time_v = next((t for t in rest if _TIME_RE.match(t)), None)
        # limit_times：纯数字 1-9 单字符（区分百分比和价格）
        limit_times = None
        for t in rest:
            if t.isdigit() and 1 <= int(t) <= 30 and t != time_v:
                limit_times = int(t)
                break
        # reason：最后一个非数字、非时间、非百分比的中文 token
        reason = None
        for t in reversed(rest):
            if (
                t != name
                and not _TIME_RE.match(t)
                and not _PERCENT_RE.match(t)
                and not t.isdigit()
                and re.search(r"[\u4e00-\u9fa5A-Za-z]", t)
                and not _is_junk(t)
            ):
                reason = t
                break
        # 推断市场后缀
        if code_token.startswith("6"):
            ts_code = f"{code_token}.SH"
        elif code_token.startswith(("0", "3")):
            ts_code = f"{code_token}.SZ"
        else:
            continue
        current_stocks.append({
            "ts_code": ts_code,
            "name": name,
            "time": time_v,
            "limit_times": limit_times,
            "reason": reason,
        })

    if current_title is not None:
        groups.append({"title": current_title, "stocks": current_stocks})

    return {"groups": groups, "raw_lines": [it["text"] for it in items]}


def attach_limit_up_table(session: Session, parsed: dict[str, Any]) -> dict[str, Any]:
    """把 parse_limit_up_table 的结果入库：每只股关联（分组题材 + 末尾原因题材）。"""
    summary: list[dict] = []
    for g in parsed.get("groups", []):
        title = g["title"].strip()
        # 跳过非题材类的标题（如"市场连板股"、"涨停板复盘"这种汇总标题）
        if title in {"市场连板股", "涨停板复盘", "涨停板", "复盘"}:
            group_sector = None
        else:
            group_sector = title
        for st in g.get("stocks", []):
            sector_names: list[str] = []
            if group_sector:
                sector_names.append(group_sector)
            if st.get("reason") and st["reason"] != group_sector:
                sector_names.append(st["reason"])
            if not sector_names:
                continue
            # 验证 ts_code 在 stocks 表里
            stock = lookup_stock(session, ts_code=st["ts_code"], name=st.get("name"))
            if not stock:
                summary.append({**st, "added": [], "skipped": [{"reason": "stock not found"}]})
                continue
            r = attach_manual_sectors(session, stock["ts_code"], sector_names)
            summary.append({"ts_code": stock["ts_code"], "name": stock["name"], **r})
    return {"groups_count": len(parsed.get("groups", [])), "stocks_processed": len(summary), "details": summary}


def lookup_stock(session: Session, *, ts_code: str | None, name: str | None) -> dict | None:
    """根据 ts_code 或 name 查股票。"""
    if ts_code:
        r = session.execute(
            text("SELECT ts_code, name FROM stocks WHERE ts_code=:c"),
            {"c": ts_code},
        ).first()
        if r:
            return {"ts_code": r[0], "name": r[1]}
    if name:
        # 精确匹配优先，再前缀模糊（处理"圣阳股份"vs"圣阳"）
        for sql, p in [
            ("SELECT ts_code, name FROM stocks WHERE name=:n LIMIT 1", {"n": name}),
            ("SELECT ts_code, name FROM stocks WHERE name LIKE :n LIMIT 2", {"n": f"%{name}%"}),
        ]:
            rows = session.execute(text(sql), p).all()
            if len(rows) == 1:
                return {"ts_code": rows[0][0], "name": rows[0][1]}
    return None


def _ensure_sector(session: Session, name: str, default_type: str = "C") -> dict:
    """根据板块名找 sector，找不到自动建一个 src=MANUAL 的。

    返回 {ts_code, name, was_new}。
    """
    name = name.strip()
    # 1) 精确名匹配
    r = session.execute(
        text("SELECT ts_code, name, type FROM sectors WHERE name=:n LIMIT 1"),
        {"n": name},
    ).first()
    if r:
        return {"ts_code": r[0], "name": r[1], "was_new": False}
    # 2) 模糊匹配（处理"东数西算（算力）"vs"算力"等）
    r = session.execute(
        text("SELECT ts_code, name FROM sectors WHERE name LIKE :n LIMIT 2"),
        {"n": f"%{name}%"},
    ).all()
    if len(r) == 1:
        return {"ts_code": r[0][0], "name": r[0][1], "was_new": False}
    # 3) 自动建：MANUAL_<8位 hex>
    new_code = f"MANUAL_{uuid.uuid4().hex[:8].upper()}"
    sector = Sector(ts_code=new_code, name=name, type=default_type, src="MANUAL")
    session.add(sector)
    session.flush()
    return {"ts_code": new_code, "name": name, "was_new": True}


def attach_manual_sectors(
    session: Session,
    ts_code: str,
    sector_names: list[str],
) -> dict[str, Any]:
    """给某只股批量加板块关联（src=MANUAL，幂等）。"""
    added: list[dict] = []
    skipped: list[dict] = []
    for name in sector_names:
        try:
            sec = _ensure_sector(session, name)
        except Exception as e:  # noqa: BLE001
            skipped.append({"name": name, "reason": f"ensure_sector failed: {e}"})
            continue
        # 入 stock_sectors（unique 约束自动去重）
        existing = session.execute(
            text(
                "SELECT 1 FROM stock_sectors WHERE ts_code=:c AND sector_code=:s"
            ),
            {"c": ts_code, "s": sec["ts_code"]},
        ).first()
        if existing:
            skipped.append({"name": name, "reason": "already linked"})
            continue
        session.add(
            StockSector(
                ts_code=ts_code,
                sector_code=sec["ts_code"],
                src="MANUAL",
                updated_at=datetime.utcnow(),
            )
        )
        added.append({"sector_code": sec["ts_code"], "name": sec["name"], "was_new_sector": sec["was_new"]})
    session.commit()
    return {"ts_code": ts_code, "added": added, "skipped": skipped}
