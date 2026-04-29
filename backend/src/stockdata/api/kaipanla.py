"""开盘啦数据查询 API。"""

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from stockdata.db import get_session
from stockdata.jobs.kaipanla import run_kpl_job

router = APIRouter(prefix="/kpl", tags=["kpl"])


@router.get("/sentiment")
def get_sentiment(
    trade_date: date_type | None = None,
    session: Session = Depends(get_session),
):
    sql = "SELECT * FROM kpl_sentiment"
    params: dict = {}
    if trade_date:
        sql += " WHERE trade_date=:td"
        params["td"] = trade_date
    else:
        sql += " ORDER BY trade_date DESC LIMIT 1"
    r = session.execute(text(sql), params).mappings().first()
    return dict(r) if r else None


@router.get("/ladder")
def get_ladder(
    trade_date: date_type | None = None,
    session: Session = Depends(get_session),
):
    sql = "SELECT * FROM kpl_ladder"
    params: dict = {}
    if trade_date:
        sql += " WHERE trade_date=:td"
        params["td"] = trade_date
    else:
        sql += " ORDER BY trade_date DESC LIMIT 1"
    r = session.execute(text(sql), params).mappings().first()
    return dict(r) if r else None


@router.get("/consecutive")
def get_consecutive(
    trade_date: date_type | None = None,
    min_days: int = Query(1, description="最小连板数。默认 1 = 全部涨停（含首板）"),
    session: Session = Depends(get_session),
):
    """查某日的涨停个股（含题材，含首板）。不传日期取最近一天。"""
    if trade_date is None:
        td = session.execute(text("SELECT MAX(trade_date) FROM kpl_consecutive")).scalar()
        if not td:
            return {"trade_date": None, "stocks": []}
        trade_date = date_type.fromisoformat(td) if isinstance(td, str) else td
    rows = session.execute(text("""
        SELECT ts_code, name, days, pct_chg, theme, board_desc, market_cap
        FROM kpl_consecutive
        WHERE trade_date=:td AND days>=:m
        ORDER BY days DESC, pct_chg DESC
    """), {"td": trade_date, "m": min_days}).mappings().all()
    return {"trade_date": trade_date, "stocks": [dict(r) for r in rows]}


@router.get("/broken")
def get_broken(
    trade_date: date_type | None = None,
    session: Session = Depends(get_session),
):
    if trade_date is None:
        td = session.execute(text("SELECT MAX(trade_date) FROM kpl_broken")).scalar()
        if not td:
            return {"trade_date": None, "stocks": []}
        trade_date = date_type.fromisoformat(td) if isinstance(td, str) else td
    rows = session.execute(text("""
        SELECT ts_code, name, pct_chg, sector FROM kpl_broken
        WHERE trade_date=:td ORDER BY pct_chg DESC
    """), {"td": trade_date}).mappings().all()
    return {"trade_date": trade_date, "stocks": [dict(r) for r in rows]}


@router.get("/lhb")
def get_lhb(
    trade_date: date_type | None = None,
    session: Session = Depends(get_session),
):
    """龙虎榜个股汇总。"""
    if trade_date is None:
        td = session.execute(text("SELECT MAX(trade_date) FROM kpl_lhb")).scalar()
        if not td:
            return {"trade_date": None, "stocks": []}
        trade_date = date_type.fromisoformat(td) if isinstance(td, str) else td
    rows = session.execute(text("""
        SELECT ts_code, name, pct_chg, reason, buy_in, net FROM kpl_lhb
        WHERE trade_date=:td ORDER BY ABS(buy_in) DESC
    """), {"td": trade_date}).mappings().all()
    return {"trade_date": trade_date, "stocks": [dict(r) for r in rows]}


@router.get("/lhb/seats/{ts_code}")
def get_lhb_seats(
    ts_code: str,
    trade_date: date_type | None = None,
    session: Session = Depends(get_session),
):
    """单股某日的龙虎榜席位明细。"""
    sql = """
        SELECT trade_date, side, rank, broker, buy_in, sell_out, net_buy, is_dy
        FROM kpl_lhb_seat WHERE ts_code=:c
    """
    params: dict = {"c": ts_code}
    if trade_date:
        sql += " AND trade_date=:td"
        params["td"] = trade_date
    sql += " ORDER BY trade_date DESC, side, rank"
    rows = session.execute(text(sql), params).mappings().all()
    return {"ts_code": ts_code, "seats": [dict(r) for r in rows]}


@router.get("/auction")
def get_auction(
    trade_date: date_type | None = None,
    session: Session = Depends(get_session),
):
    if trade_date is None:
        td = session.execute(text("SELECT MAX(trade_date) FROM kpl_auction")).scalar()
        if not td:
            return {"trade_date": None, "stocks": []}
        trade_date = date_type.fromisoformat(td) if isinstance(td, str) else td
    rows = session.execute(text("""
        SELECT ts_code, name, tag, direction, themes, pct_chg, turnover,
               net_amount, big_order_buy, big_order_sell, score
        FROM kpl_auction WHERE trade_date=:td ORDER BY score DESC
    """), {"td": trade_date}).mappings().all()
    return {"trade_date": trade_date, "stocks": [dict(r) for r in rows]}


@router.get("/sectors-heat")
def get_sectors_heat(
    trade_date: date_type | None = None,
    session: Session = Depends(get_session),
):
    """涨停板块热度对比：同时返 SQL 自己算的 + 开盘啦给的两份。

    - sql: 来自 sector_limit_up_heat（基于 limit_up_daily JOIN stock_sectors，count >= 10）
    - kpl: 来自 kpl_sectors_heat（开盘啦 /api/sectors，仅当天）
    """
    if trade_date is None:
        td = session.execute(text("""
            SELECT MAX(d) FROM (
              SELECT MAX(trade_date) d FROM kpl_sectors_heat
              UNION SELECT MAX(trade_date) FROM sector_limit_up_heat
            )
        """)).scalar()
        if not td:
            return {"trade_date": None, "sql": [], "kpl": []}
        trade_date = date_type.fromisoformat(td) if isinstance(td, str) else td
    sql_rows = session.execute(text("""
        SELECT sector_code, sector_name, limit_up_count, max_consecutive
        FROM sector_limit_up_heat WHERE trade_date=:td
        ORDER BY limit_up_count DESC
    """), {"td": trade_date}).mappings().all()
    kpl_rows = session.execute(text("""
        SELECT sector_code, sector_name, count
        FROM kpl_sectors_heat WHERE trade_date=:td
        ORDER BY count DESC
    """), {"td": trade_date}).mappings().all()
    # 合并 sector_ladder（每板块的成分股）到 KPL 行
    ladder_rows = session.execute(text("""
        SELECT sector_code, ts_code, stock_name, td_type, tips
        FROM kpl_sector_ladder WHERE trade_date=:td
        ORDER BY sector_code, td_type DESC
    """), {"td": trade_date}).mappings().all()
    by_sector: dict[str, list] = {}
    seen_in_sector: dict[str, set] = {}
    for r in ladder_rows:
        by_sector.setdefault(r["sector_code"], []).append({
            "ts_code": r["ts_code"],
            "name": r["stock_name"],
            "td_type": r["td_type"],
            "tips": r["tips"],
            "pct_chg": None,
        })
        seen_in_sector.setdefault(r["sector_code"], set()).add(r["ts_code"])
    # 从 daily_quotes pct_chg>=9.98 + stock_sectors 按板块 name 反查补全
    extra_rows = session.execute(text("""
        SELECT khh.sector_code AS kpl_sc, q.ts_code, st.name AS stock_name, q.pct_chg
        FROM kpl_sectors_heat khh
        JOIN sectors sec ON sec.name = khh.sector_name
        JOIN stock_sectors ss ON ss.sector_code = sec.ts_code
        JOIN daily_quotes q ON q.ts_code = ss.ts_code AND q.trade_date = khh.trade_date
        LEFT JOIN stocks st ON st.ts_code = q.ts_code
        WHERE khh.trade_date = :td AND q.pct_chg >= 9.98
        GROUP BY khh.sector_code, q.ts_code
        ORDER BY q.pct_chg DESC
    """), {"td": trade_date}).mappings().all()
    for r in extra_rows:
        sc = r["kpl_sc"]
        if r["ts_code"] in seen_in_sector.get(sc, set()):
            continue
        by_sector.setdefault(sc, []).append({
            "ts_code": r["ts_code"],
            "name": r["stock_name"],
            "td_type": None,
            "tips": None,
            "pct_chg": r["pct_chg"],
        })
        seen_in_sector.setdefault(sc, set()).add(r["ts_code"])
    # SQL 那边也补上 stocks（用 daily_quotes pct_chg>=9.98 + stock_sectors 算）
    sql_stocks_rows = session.execute(text("""
        SELECT ss.sector_code, q.ts_code, s.name AS stock_name, q.pct_chg
        FROM daily_quotes q
        JOIN stock_sectors ss ON ss.ts_code = q.ts_code
        LEFT JOIN stocks s ON s.ts_code = q.ts_code
        WHERE q.trade_date=:td AND q.pct_chg >= 9.98
          AND ss.sector_code IN (SELECT sector_code FROM sector_limit_up_heat WHERE trade_date=:td)
        ORDER BY ss.sector_code, q.pct_chg DESC
    """), {"td": trade_date}).mappings().all()
    sql_by_sector: dict[str, list] = {}
    for r in sql_stocks_rows:
        sql_by_sector.setdefault(r["sector_code"], []).append({
            "ts_code": r["ts_code"],
            "name": r["stock_name"],
            "pct_chg": r["pct_chg"],
        })
    return {
        "trade_date": trade_date,
        "sql": [{**dict(r), "stocks": sql_by_sector.get(r["sector_code"], [])} for r in sql_rows],
        "kpl": [{**dict(r), "stocks": by_sector.get(r["sector_code"], [])} for r in kpl_rows],
    }


@router.get("/withdrawal")
def get_withdrawal(
    trade_date: date_type | None = None,
    session: Session = Depends(get_session),
):
    if trade_date is None:
        td = session.execute(text("SELECT MAX(trade_date) FROM kpl_withdrawal")).scalar()
        if not td:
            return {"trade_date": None, "stocks": []}
        trade_date = date_type.fromisoformat(td) if isinstance(td, str) else td
    rows = session.execute(text("""
        SELECT ts_code, name, pct_chg, withdrawal_pct, price
        FROM kpl_withdrawal WHERE trade_date=:td
        ORDER BY withdrawal_pct ASC
    """), {"td": trade_date}).mappings().all()
    return {"trade_date": trade_date, "stocks": [dict(r) for r in rows]}


@router.get("/market-ladder")
def get_market_ladder(
    trade_date: date_type | None = None,
    session: Session = Depends(get_session),
):
    """空间板梯队：按 tip 分组返回。"""
    if trade_date is None:
        td = session.execute(text("SELECT MAX(trade_date) FROM kpl_market_ladder")).scalar()
        if not td:
            return {"trade_date": None, "groups": []}
        trade_date = date_type.fromisoformat(td) if isinstance(td, str) else td
    rows = session.execute(text("""
        SELECT tip, ts_code, stock_name, tips
        FROM kpl_market_ladder WHERE trade_date=:td
        ORDER BY tip ASC, ts_code ASC
    """), {"td": trade_date}).mappings().all()
    grouped: dict[str, list] = {}
    for r in rows:
        grouped.setdefault(r["tip"], []).append({
            "ts_code": r["ts_code"], "name": r["stock_name"], "tips": r["tips"],
        })
    return {
        "trade_date": trade_date,
        "groups": [{"tip": t, "stocks": s} for t, s in sorted(grouped.items())],
    }


@router.get("/news")
def get_news(
    limit: int = Query(30),
    keyword: str | None = None,
    session: Session = Depends(get_session),
):
    """题材新闻列表。每条带关联个股 + isTop 标记。"""
    sql = "SELECT * FROM kpl_news"
    params: dict = {"lim": limit}
    if keyword:
        sql += " WHERE keyword=:k"
        params["k"] = keyword
    sql += " ORDER BY news_time DESC LIMIT :lim"
    news_rows = session.execute(text(sql), params).mappings().all()
    if not news_rows:
        return {"news": []}
    ids = [r["news_id"] for r in news_rows]
    placeholders = ",".join(f":i{i}" for i in range(len(ids)))
    stock_rows = session.execute(
        text(f"SELECT * FROM kpl_news_stock WHERE news_id IN ({placeholders})"),
        {f"i{i}": v for i, v in enumerate(ids)},
    ).mappings().all()
    by_news: dict[int, list] = {}
    for r in stock_rows:
        by_news.setdefault(r["news_id"], []).append({
            "ts_code": r["ts_code"], "name": r["stock_name"],
            "pct_chg": r["pct_chg"], "is_top": bool(r["is_top"]),
        })
    return {"news": [{**dict(n), "stocks": by_news.get(n["news_id"], [])} for n in news_rows]}


@router.get("/conception-history")
def get_conception_history(
    trade_date: date_type | None = None,
    session: Session = Depends(get_session),
):
    """盘中题材异动事件流。"""
    if trade_date is None:
        td = session.execute(text("SELECT MAX(trade_date) FROM kpl_conception_history")).scalar()
        if not td:
            return {"trade_date": None, "events": []}
        trade_date = date_type.fromisoformat(td) if isinstance(td, str) else td
    rows = session.execute(text("""
        SELECT event_time, plate_text, plate_code, plate_name, plate_je, plate_zdf, event_type, color
        FROM kpl_conception_history WHERE trade_date=:td
        ORDER BY event_time ASC
    """), {"td": trade_date}).mappings().all()
    return {"trade_date": trade_date, "events": [dict(r) for r in rows]}


@router.get("/history-strength")
def get_history_strength(
    days: int = Query(100),
    session: Session = Depends(get_session),
):
    rows = session.execute(text("""
        SELECT trade_date, strength, limit_up_count, max_consecutive, big_drop_count
        FROM kpl_history_strength
        ORDER BY trade_date DESC LIMIT :n
    """), {"n": days}).mappings().all()
    return {"days": [dict(r) for r in rows]}


@router.get("/dashboard")
def get_dashboard(
    trade_date: date_type | None = None,
    session: Session = Depends(get_session),
):
    """竞价全景看板（15:00 快照入库）：board + tops + sectors。"""
    if trade_date is None:
        td = session.execute(text("SELECT MAX(trade_date) FROM kpl_dashboard")).scalar()
        if not td:
            return {"trade_date": None, "board": None, "tops": [], "sectors": []}
        trade_date = date_type.fromisoformat(td) if isinstance(td, str) else td
    board = session.execute(text("SELECT * FROM kpl_dashboard WHERE trade_date=:td"),
                            {"td": trade_date}).mappings().first()
    tops = session.execute(text("""
        SELECT direction, rank, ts_code, name, pct_chg, sector
        FROM kpl_dashboard_top WHERE trade_date=:td
        ORDER BY direction, rank
    """), {"td": trade_date}).mappings().all()
    sectors = session.execute(text("""
        SELECT sector_code, sector_name, pct_chg
        FROM kpl_dashboard_sector WHERE trade_date=:td
        ORDER BY pct_chg DESC
    """), {"td": trade_date}).mappings().all()
    return {
        "trade_date": trade_date,
        "board": dict(board) if board else None,
        "tops": [dict(r) for r in tops],
        "sectors": [dict(r) for r in sectors],
    }


@router.get("/emotion")
def get_emotion(
    trade_date: date_type | None = None,
    session: Session = Depends(get_session),
):
    if trade_date is None:
        td = session.execute(text("SELECT MAX(trade_date) FROM kpl_emotion")).scalar()
        if not td:
            return None
        trade_date = date_type.fromisoformat(td) if isinstance(td, str) else td
    r = session.execute(text("SELECT * FROM kpl_emotion WHERE trade_date=:td"),
                        {"td": trade_date}).mappings().first()
    return dict(r) if r else None


@router.get("/history-analysis")
def get_history_analysis(
    days: int = Query(60),
    session: Session = Depends(get_session),
):
    rows = session.execute(text("""
        SELECT * FROM kpl_history_analysis
        ORDER BY trade_date DESC LIMIT :n
    """), {"n": days}).mappings().all()
    return {"days": [dict(r) for r in rows]}


@router.get("/youzi/traders")
def list_youzi_traders(session: Session = Depends(get_session)):
    rows = session.execute(text("SELECT * FROM kpl_youzi ORDER BY trader_id")).mappings().all()
    return {"traders": [dict(r) for r in rows]}


@router.get("/youzi/trades")
def list_youzi_trades(
    trade_date: date_type | None = None,
    trader_id: str | None = None,
    ts_code: str | None = None,
    limit: int = Query(200),
    session: Session = Depends(get_session),
):
    sql = "SELECT * FROM kpl_youzi_trade WHERE 1=1"
    params: dict = {"lim": limit}
    if trade_date:
        sql += " AND trade_date=:td"; params["td"] = trade_date
    if trader_id:
        sql += " AND trader_id=:t"; params["t"] = trader_id
    if ts_code:
        sql += " AND ts_code=:c"; params["c"] = ts_code
    sql += " ORDER BY trade_date DESC, ABS(net_amount) DESC LIMIT :lim"
    rows = session.execute(text(sql), params).mappings().all()
    return {"trades": [dict(r) for r in rows]}


@router.get("/youzi/by-stock/{ts_code}")
def youzi_by_stock(ts_code: str, session: Session = Depends(get_session)):
    """某只股被哪些游资打过几次（个股游资标签累计）。"""
    rows = session.execute(text("""
        SELECT t.trader_id, y.name AS trader_name,
               COUNT(*) AS hit_count,
               SUM(CASE WHEN t.side='B' THEN 1 ELSE 0 END) AS buy_count,
               SUM(CASE WHEN t.side='S' THEN 1 ELSE 0 END) AS sell_count,
               SUM(t.net_amount) AS net_total
        FROM kpl_youzi_trade t
        LEFT JOIN kpl_youzi y ON y.trader_id = t.trader_id
        WHERE t.ts_code=:c
        GROUP BY t.trader_id, y.name
        ORDER BY hit_count DESC, ABS(net_total) DESC
    """), {"c": ts_code}).mappings().all()
    return {"ts_code": ts_code, "traders": [dict(r) for r in rows]}


@router.get("/sector-news/{sector_code}")
def get_sector_news(
    sector_code: str,
    limit: int = Query(30),
    session: Session = Depends(get_session),
):
    rows = session.execute(text("""
        SELECT news_id, title, news_time, news_type FROM kpl_sector_news
        WHERE sector_code=:s ORDER BY news_time DESC LIMIT :n
    """), {"s": sector_code, "n": limit}).mappings().all()
    return {"sector_code": sector_code, "news": [dict(r) for r in rows]}


@router.get("/news-selected")
def get_news_selected(
    limit: int = Query(20),
    session: Session = Depends(get_session),
):
    rows = session.execute(text("""
        SELECT * FROM kpl_news_selected ORDER BY create_time DESC LIMIT :n
    """), {"n": limit}).mappings().all()
    return {"articles": [dict(r) for r in rows]}


@router.post("/snapshot/run")
def trigger_realtime_snapshot():
    """手动触发一次 15:00 实时快照（auction/dashboard + emotion）。"""
    from stockdata.jobs.realtime_snapshot import run_realtime_snapshot
    return run_realtime_snapshot()


@router.get("/stock/ztgene/{ts_code}")
def get_ztgene(ts_code: str):
    """个股涨停基因（按需查 KPL，不入库）。"""
    from stockdata.providers.kaipanla import KaipanlaProvider
    kpl = KaipanlaProvider()
    try:
        return kpl.fetch_stock_ztgene(ts_code)
    finally:
        kpl.close()


@router.post("/run")
def trigger_kpl_job(
    trade_date: date_type | None = None,
    with_lhb_detail: bool = True,
):
    """手动触发一次 Kaipanla 数据抓取（不阻塞调用方，可指定历史日期回填）。"""
    return run_kpl_job(target_date=trade_date, with_lhb_detail=with_lhb_detail)
