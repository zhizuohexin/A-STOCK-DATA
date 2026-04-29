"""Upsert helpers — each table has a (ts_code, trade_date)-style unique key."""

from datetime import date as date_type
from typing import Any

from sqlalchemy import delete as sa_delete, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from stockdata.models import (
    DailyQuote,
    IntradayBar,
    JobRun,
    KplAuction,
    KplBroken,
    KplConsecutive,
    KplLadder,
    KplConceptionHistory,
    KplDashboard,
    KplDashboardSector,
    KplDashboardTop,
    KplEmotion,
    KplHistoryAnalysis,
    KplHistoryStrength,
    KplLhb,
    KplLhbSeat,
    KplMarketLadder,
    KplNews,
    KplNewsSelected,
    KplNewsStock,
    KplSectorLadder,
    KplSectorNews,
    KplSectorsHeat,
    KplSentiment,
    KplWithdrawal,
    KplYouzi,
    KplYouziTrade,
    LimitUpDaily,
    Sector,
    SectorDaily,
    SectorLimitUpHeat,
    Stock,
    StockSector,
)


def _upsert(session: Session, model: type, rows: list[dict[str, Any]], conflict_cols: list[str]) -> int:
    if not rows:
        return 0
    table = model.__table__
    stmt = sqlite_insert(table).values(rows)
    update_cols = {
        c.name: stmt.excluded[c.name]
        for c in table.columns
        if c.name not in conflict_cols and c.name != "id" and c.name != "created_at"
    }
    stmt = stmt.on_conflict_do_update(index_elements=conflict_cols, set_=update_cols)
    result = session.execute(stmt)
    return result.rowcount or len(rows)


def upsert_stocks(session: Session, rows: list[dict[str, Any]]) -> int:
    return _upsert(session, Stock, rows, ["ts_code"])


def upsert_daily_quotes(session: Session, rows: list[dict[str, Any]]) -> int:
    return _upsert(session, DailyQuote, rows, ["ts_code", "trade_date"])


def upsert_limit_up(session: Session, rows: list[dict[str, Any]]) -> int:
    return _upsert(session, LimitUpDaily, rows, ["ts_code", "trade_date"])


def upsert_sectors(session: Session, rows: list[dict[str, Any]]) -> int:
    return _upsert(session, Sector, rows, ["ts_code"])


def upsert_sector_daily(session: Session, rows: list[dict[str, Any]]) -> int:
    return _upsert(session, SectorDaily, rows, ["sector_code", "trade_date"])


def upsert_intraday_bars(session: Session, rows: list[dict[str, Any]]) -> int:
    return _upsert(session, IntradayBar, rows, ["ts_code", "bar_time"])


def upsert_stock_sectors(session: Session, rows: list[dict[str, Any]]) -> int:
    return _upsert(session, StockSector, rows, ["ts_code", "sector_code"])


def replace_stock_sectors_for_src(session: Session, src: str, rows: list[dict[str, Any]]) -> int:
    """全量替换某个 src（EM/THS）的映射：先删后插。"""
    from sqlalchemy import delete

    session.execute(delete(StockSector).where(StockSector.src == src))
    if rows:
        session.execute(StockSector.__table__.insert(), rows)
    return len(rows)


def upsert_kpl_dashboard(session: Session, payload: dict) -> dict:
    """fetch_auction_dashboard 的整包入库（board + tops + sectors）。同日 DELETE 重写幂等。"""
    td_str = payload.get("trade_date")
    if not td_str:
        return {"board": 0, "tops": 0, "sectors": 0}
    td = date_type.fromisoformat(td_str) if isinstance(td_str, str) else td_str
    # board
    board_row = {**payload["board"], "trade_date": td, "snapshot_time": payload.get("snapshot_time")}
    n_board = _upsert(session, KplDashboard, [board_row], ["trade_date"])
    # tops 先删后插
    session.execute(sa_delete(KplDashboardTop).where(KplDashboardTop.trade_date == td))
    tops = [{**t, "trade_date": td} for t in payload.get("tops") or []]
    if tops:
        session.execute(KplDashboardTop.__table__.insert(), tops)
    # sectors 先删后插
    session.execute(sa_delete(KplDashboardSector).where(KplDashboardSector.trade_date == td))
    sectors = [{**s, "trade_date": td} for s in payload.get("sectors") or [] if s.get("sector_code")]
    if sectors:
        session.execute(KplDashboardSector.__table__.insert(), sectors)
    return {"board": n_board, "tops": len(tops), "sectors": len(sectors)}


def upsert_kpl_emotion(session: Session, trade_date: date_type, row: dict) -> int:
    return _upsert(session, KplEmotion, [{**row, "trade_date": trade_date}], ["trade_date"])


def upsert_kpl_youzi(session: Session, traders: list[dict], trades: list[dict]) -> dict:
    """游资名册 upsert + 当日 trades 入库。同 (date, trader, side, ts_code, seat) 幂等。"""
    n_traders = _upsert(session, KplYouzi, traders, ["trader_id"])
    if not trades:
        return {"traders": n_traders, "trades": 0}
    # 处理 trade_date 字符串 → date
    cleaned = []
    for t in trades:
        td_str = t.get("trade_date")
        if isinstance(td_str, str):
            try:
                t = {**t, "trade_date": date_type.fromisoformat(td_str)}
            except ValueError:
                continue
        if not t.get("trade_date") or not t.get("ts_code"):
            continue
        # seat_name 不能是 None（unique constraint 要求，sqlite 中 None 会被视为不同）
        if t.get("seat_name") is None:
            t["seat_name"] = "未知"
        cleaned.append(t)
    n_trades = _upsert(session, KplYouziTrade, cleaned, ["trade_date", "trader_id", "side", "ts_code", "seat_name"])
    return {"traders": n_traders, "trades": n_trades}


def upsert_kpl_history_analysis(session: Session, rows: list[dict]) -> int:
    if not rows:
        return 0
    cleaned = []
    for r in rows:
        td_str = r.get("trade_date")
        td = date_type.fromisoformat(td_str) if isinstance(td_str, str) else td_str
        if td:
            cleaned.append({**r, "trade_date": td})
    return _upsert(session, KplHistoryAnalysis, cleaned, ["trade_date"])


def upsert_kpl_sector_news(session: Session, rows: list[dict]) -> int:
    if not rows:
        return 0
    return _upsert(session, KplSectorNews, rows, ["sector_code", "news_id"])


def upsert_kpl_news_selected(session: Session, rows: list[dict]) -> int:
    if not rows:
        return 0
    return _upsert(session, KplNewsSelected, rows, ["article_id"])


def upsert_kpl_withdrawal(session: Session, rows: list[dict]) -> int:
    if not rows:
        return 0
    td_str = rows[0].get("trade_date")
    td = date_type.fromisoformat(td_str) if isinstance(td_str, str) else td_str
    if not td:
        return 0
    session.execute(sa_delete(KplWithdrawal).where(KplWithdrawal.trade_date == td))
    inserted = []
    for r in rows:
        if not r.get("ts_code"):
            continue
        inserted.append({**r, "trade_date": td})
    if inserted:
        session.execute(KplWithdrawal.__table__.insert(), inserted)
    return len(inserted)


def upsert_kpl_market_ladder(session: Session, rows: list[dict]) -> int:
    if not rows:
        return 0
    td_str = rows[0].get("trade_date")
    td = date_type.fromisoformat(td_str) if isinstance(td_str, str) else td_str
    if not td:
        return 0
    session.execute(sa_delete(KplMarketLadder).where(KplMarketLadder.trade_date == td))
    inserted = []
    for r in rows:
        if not r.get("ts_code"):
            continue
        inserted.append({**r, "trade_date": td})
    if inserted:
        session.execute(KplMarketLadder.__table__.insert(), inserted)
    return len(inserted)


def upsert_kpl_news(session: Session, news_rows: list[dict], stock_rows: list[dict]) -> dict:
    """新闻入库 + 关联股入库 + 自动 attach 关键词到 stock_sectors（src='KPL'）。"""
    if not news_rows:
        return {"news": 0, "stocks": 0, "themes_added": 0}
    # 用 sqlite ON CONFLICT DO UPDATE
    n_news = _upsert(session, KplNews, news_rows, ["news_id"])
    n_stocks = 0
    if stock_rows:
        n_stocks = _upsert(session, KplNewsStock, stock_rows, ["news_id", "ts_code"])
    # attach keyword 到 stock_sectors
    themes_added = 0
    keyword_by_news = {n["news_id"]: n.get("keyword") for n in news_rows if n.get("keyword")}
    for s in stock_rows:
        kw = keyword_by_news.get(s["news_id"])
        if not kw:
            continue
        themes_added += attach_kpl_themes(session, s["ts_code"], kw)
    return {"news": n_news, "stocks": n_stocks, "themes_added": themes_added}


def upsert_kpl_conception_history(session: Session, rows: list[dict]) -> int:
    if not rows:
        return 0
    # 同日先 DELETE，再插入
    td_str = rows[0].get("trade_date")
    td = date_type.fromisoformat(td_str) if isinstance(td_str, str) else td_str
    if not td:
        return 0
    session.execute(sa_delete(KplConceptionHistory).where(KplConceptionHistory.trade_date == td))
    inserted = []
    seen = set()
    for r in rows:
        key = (r["event_time"], r["plate_text"])
        if key in seen:
            continue
        seen.add(key)
        inserted.append({**r, "trade_date": td})
    if inserted:
        session.execute(KplConceptionHistory.__table__.insert(), inserted)
    return len(inserted)


def upsert_kpl_history_strength(session: Session, rows: list[dict]) -> int:
    """100 日市场强度。trade_date 为 PK，逐行 upsert。"""
    if not rows:
        return 0
    inserted = []
    for r in rows:
        td_str = r.get("trade_date")
        td = date_type.fromisoformat(td_str) if isinstance(td_str, str) else td_str
        if not td:
            continue
        inserted.append({**r, "trade_date": td})
    return _upsert(session, KplHistoryStrength, inserted, ["trade_date"])


def upsert_kpl_sector_ladder(session: Session, rows: list[dict]) -> int:
    """开盘啦板块涨停梯队入库。同 (trade_date, sector_code, ts_code) 唯一。

    rows 里 trade_date 字符串会被转 date。同日先 DELETE 再 INSERT 幂等。
    """
    if not rows:
        return 0
    td_str = rows[0].get("trade_date")
    if not td_str:
        return 0
    td = date_type.fromisoformat(td_str) if isinstance(td_str, str) else td_str
    session.execute(sa_delete(KplSectorLadder).where(KplSectorLadder.trade_date == td))
    inserted = []
    for r in rows:
        if not r.get("sector_code") or not r.get("ts_code"):
            continue
        inserted.append({
            "trade_date": td,
            "sector_code": str(r["sector_code"]),
            "sector_name": r.get("sector_name"),
            "ts_code": r["ts_code"],
            "stock_name": r.get("stock_name"),
            "td_type": r.get("td_type"),
            "tips": r.get("tips"),
        })
    if inserted:
        session.execute(KplSectorLadder.__table__.insert(), inserted)
    return len(inserted)


def upsert_kpl_sectors_heat(session: Session, rows: list[dict]) -> int:
    """开盘啦板块强度入库（独立表，与 sector_limit_up_heat 并存）。同日先 DELETE 后 INSERT 幂等。"""
    if not rows:
        return 0
    td_str = rows[0].get("trade_date")
    if not td_str:
        return 0
    td = date_type.fromisoformat(td_str) if isinstance(td_str, str) else td_str
    session.execute(sa_delete(KplSectorsHeat).where(KplSectorsHeat.trade_date == td))
    inserted = []
    for r in rows:
        if not r.get("sector_code"):
            continue
        inserted.append({
            "trade_date": td,
            "sector_code": str(r["sector_code"]),
            "sector_name": r.get("sector_name"),
            "count": r.get("count"),
        })
    if inserted:
        session.execute(KplSectorsHeat.__table__.insert(), inserted)
    return len(inserted)


def recompute_sector_heat_from_kpl(session: Session, rows: list[dict]) -> int:
    """用开盘啦 /api/sectors 数据更新 sector_limit_up_heat。

    rows 由 KaipanlaProvider.fetch_sectors_strength() 提供，每条含
    sector_code (申万 801xxx)、sector_name、count、trade_date(str)。
    板块在 sectors 表里没有则按需建（src='KPL'）。同日先 DELETE 再 INSERT 幂等。
    """
    from datetime import datetime as _dt

    if not rows:
        return 0
    # 取该日期，做幂等
    td_str = rows[0].get("trade_date")
    if not td_str:
        return 0
    td = date_type.fromisoformat(td_str) if isinstance(td_str, str) else td_str
    session.execute(sa_delete(SectorLimitUpHeat).where(SectorLimitUpHeat.trade_date == td))

    inserted: list[dict] = []
    for r in rows:
        sec_code = r["sector_code"]
        name = r["sector_name"] or sec_code
        # 在 sectors 表里查是否有，没有就按 name 找，再没有就建
        existing = session.execute(
            text("SELECT ts_code FROM sectors WHERE ts_code=:c"),
            {"c": sec_code},
        ).first()
        if not existing:
            by_name = session.execute(
                text("SELECT ts_code FROM sectors WHERE name=:n LIMIT 1"),
                {"n": name},
            ).first()
            if by_name:
                sec_code = by_name[0]
            else:
                session.add(Sector(ts_code=sec_code, name=name, type="C", src="KPL"))
                session.flush()
        inserted.append({
            "trade_date": td,
            "sector_code": sec_code,
            "sector_name": name,
            "limit_up_count": r.get("count"),
            "max_consecutive": None,  # KPL sectors 接口没给最大连板，留空
        })
    if inserted:
        session.execute(SectorLimitUpHeat.__table__.insert(), inserted)
    return len(inserted)


def recompute_sector_heat(session: Session, trade_date: date_type, min_count: int = 10) -> int:
    """重算某日 concept 板块涨停热度并入库（仅 limit_up_count >= min_count）。幂等。"""
    session.execute(sa_delete(SectorLimitUpHeat).where(SectorLimitUpHeat.trade_date == trade_date))
    rows = session.execute(
        text(
            """
            SELECT s.ts_code AS sector_code, s.name AS sector_name,
                   COUNT(*) AS limit_up_count, MAX(l.limit_times) AS max_consecutive
            FROM limit_up_daily l
            JOIN stock_sectors ss ON ss.ts_code = l.ts_code
            JOIN sectors s ON s.ts_code = ss.sector_code AND s.type='C'
            WHERE l.trade_date = :td AND l."limit" = 'U'
            GROUP BY s.ts_code, s.name
            HAVING COUNT(*) >= :min_count
            """
        ),
        {"td": trade_date, "min_count": min_count},
    ).mappings().all()
    if not rows:
        return 0
    session.execute(
        SectorLimitUpHeat.__table__.insert(),
        [{"trade_date": trade_date, **dict(r)} for r in rows],
    )
    return len(rows)


def upsert_kpl_sentiment(session: Session, row: dict) -> int:
    return _upsert(session, KplSentiment, [row], ["trade_date"])


def upsert_kpl_ladder(session: Session, row: dict) -> int:
    return _upsert(session, KplLadder, [row], ["trade_date"])


def upsert_kpl_consecutive(session: Session, rows: list[dict]) -> int:
    return _upsert(session, KplConsecutive, rows, ["trade_date", "ts_code"])


def upsert_kpl_broken(session: Session, rows: list[dict]) -> int:
    return _upsert(session, KplBroken, rows, ["trade_date", "ts_code"])


def upsert_kpl_lhb(session: Session, rows: list[dict]) -> int:
    return _upsert(session, KplLhb, rows, ["trade_date", "ts_code"])


def upsert_kpl_lhb_seat(session: Session, rows: list[dict]) -> int:
    return _upsert(session, KplLhbSeat, rows, ["trade_date", "ts_code", "side", "rank", "broker"])


def upsert_kpl_auction(session: Session, rows: list[dict]) -> int:
    return _upsert(session, KplAuction, rows, ["trade_date", "ts_code"])


def attach_kpl_themes(session: Session, ts_code: str, theme_str: str | None) -> int:
    """把开盘啦给的题材字符串（"光刻胶、化工"）拆开后入 stock_sectors（src='KPL'）。

    板块 name 找不到则自动建（type='C', src='KPL'）。返回新增关联数。
    """
    if not theme_str:
        return 0
    import re
    import uuid
    from datetime import datetime as _dt

    names = [t.strip() for t in re.split(r"[、,，]", theme_str) if t.strip()]
    inserted = 0
    for name in names:
        if len(name) > 32:
            continue
        # 找现有 sector
        r = session.execute(
            text("SELECT ts_code FROM sectors WHERE name=:n LIMIT 1"),
            {"n": name},
        ).first()
        if r:
            sec_code = r[0]
        else:
            sec_code = f"KPL_{uuid.uuid4().hex[:8].upper()}"
            session.add(Sector(ts_code=sec_code, name=name, type="C", src="KPL"))
            session.flush()
        # 关联
        existing = session.execute(
            text("SELECT 1 FROM stock_sectors WHERE ts_code=:c AND sector_code=:s"),
            {"c": ts_code, "s": sec_code},
        ).first()
        if not existing:
            session.add(StockSector(
                ts_code=ts_code, sector_code=sec_code, src="KPL",
                updated_at=_dt.utcnow(),
            ))
            inserted += 1
    return inserted


def record_job(
    session: Session,
    job_name: str,
    status: str,
    message: str | None = None,
    rows_affected: int | None = None,
) -> JobRun:
    from datetime import datetime

    job = JobRun(
        job_name=job_name,
        status=status,
        message=message,
        rows_affected=rows_affected,
        finished_at=datetime.utcnow() if status != "running" else None,
    )
    session.add(job)
    session.commit()
    return job
