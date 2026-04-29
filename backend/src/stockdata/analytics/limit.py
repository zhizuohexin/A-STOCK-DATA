"""涨停/跌停从 daily_quotes 现算（不依赖 limit_up_daily 表）。

判定规则：pct_chg >= 9.98 视为涨停；<= -9.98 视为跌停。
连板数 = 从 trade_date 起向前数连续涨停天数（首板=1）。
"""

from datetime import date as date_type

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_streaks(
    session: Session,
    trade_date: date_type,
    direction: str = "up",
    threshold: float = 9.98,
    max_back_days: int = 60,
) -> dict[str, int]:
    """计算 trade_date 当天满足条件的所有股票的连续天数。

    direction='up' → pct_chg >= threshold（涨停）
    direction='down' → pct_chg <= -threshold（跌停，threshold 传正数即可）

    返回 {ts_code: streak}，streak >= 1（>=1 因为今天本身就触发）。
    """
    if direction == "up":
        op = ">="
        th = threshold
    else:
        op = "<="
        th = -abs(threshold)
    sql = f"""
    WITH hits AS (
      SELECT ts_code FROM daily_quotes
      WHERE trade_date = :td AND pct_chg {op} :th
    ),
    recent AS (
      SELECT q.ts_code, q.trade_date, q.pct_chg,
             CASE WHEN q.pct_chg {op} :th THEN 1 ELSE 0 END AS hit,
             ROW_NUMBER() OVER (PARTITION BY q.ts_code ORDER BY q.trade_date DESC) AS rn
      FROM daily_quotes q
      WHERE q.ts_code IN (SELECT ts_code FROM hits)
        AND q.trade_date <= :td
    ),
    runs AS (
      SELECT ts_code, rn, hit,
             SUM(1 - hit) OVER (PARTITION BY ts_code ORDER BY rn) AS gap_count
      FROM recent WHERE rn <= :back
    )
    SELECT ts_code, COUNT(*) AS streak
    FROM runs WHERE gap_count = 0
    GROUP BY ts_code
    """
    rows = session.execute(
        text(sql),
        {"td": trade_date, "th": th, "back": max_back_days},
    ).all()
    return {r[0]: r[1] for r in rows}
