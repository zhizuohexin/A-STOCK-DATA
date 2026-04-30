# A 股复盘 Agent 指南

> 给 LLM Agent（Hermes / Claude API 等）的复盘工作指南。
>
> Agent 的数据来源分**两类**：
> - **本项目 REST API**（已入库的累积数据，所有交易日历史可查）
> - **KPL 原始接口直连**（实时类数据，本项目**不转发**）

---

## 0. 两个数据源 Base URL

| 来源 | Base URL | 认证 | 用法 |
|---|---|---|---|
| 本项目 | `http://8.130.160.238/api` | 无 | 所有"已入库"的复盘数据 |
| **开盘啦原始接口** | `http://124.222.49.67:3000` | `x-api-key: sk_inst_d37ea1a202168c22` | 实时类数据，**Agent 直接调** |

> ⚠️ KPL 原始接口仅用于**实时数据**（盘中、L2、指数实时报价等）。Agent 调用时必须带 header `x-api-key: sk_inst_d37ea1a202168c22`。

---

## 1. 数据同步调度（重要！决定何时数据可查）

| 时间 | 任务 | 同步内容 | Agent 何时可查 |
|---|---|---|---|
| **每日 15:00** | `realtime_snapshot` | KPL 实时快照入库：竞价看板（dashboard）、情绪/量比（emotion） | 15:00 后调 `/api/kpl/dashboard` `/api/kpl/emotion` 拿到当日终值 |
| **每日 17:30**（周一-五） | `daily_job` | tushare 全市场日线 + 涨跌停 + 板块 + 板块日线 + 板块热度（双源）+ KPL 16 步：sentiment/ladder/connsecutive/broken/lhb/lhb_seat/auction/withdrawal/market_ladder/news/conception/history_strength/history_analysis/youzi/sector_news/news_selected | **17:30 之后**当日完整数据全部可查 |
| 每日 08:30 | cleanup_intraday | 清当日前一日的分时数据（内部维护，Agent 无感）| — |
| **周一 02:00** | weekly_stock_sectors_sync | 全量东财个股↔板块映射刷新（约 35 分钟） | 周一上午起题材库最新 |

### 时效性 Cheat Sheet

| 你想查的时间 | 可信数据 |
|---|---|
| **盘中（9:30-15:00）查当日** | ❌ 项目内**无当日数据**。Agent 须**直连 KPL 原始接口**拿实时（见 §4）|
| **15:00-17:30 查当日** | ⚠️ 只有 dashboard / emotion 快照。涨停/连板/板块这些要等 17:30 后 |
| **17:30 之后查当日** | ✅ 全套完整 |
| **查历史交易日（昨天及以前）** | ✅ 任意时间都齐全 |
| **查周末/节假日** | ❌ 不要传周末日期，会返空。传上一个交易日 |

---

## 2. 数据来源优先级（关键决策树）

### 同类数据有多个来源时的优先级

| 数据维度 | 优先 1 | 优先 2 | 何时用 2 |
|---|---|---|---|
| **涨停个股** | KPL `/api/kpl/consecutive`（含 theme/board_desc）| 自算 `/api/limit-up`（pct_chg≥9.98）| 需要全市场覆盖（含 ST、北交所），KPL 漏掉 |
| **板块涨停热度** | KPL `/api/kpl/sectors-heat` 的 `kpl` 数组 | 同接口的 `sql` 数组 | 想看完整板块涨停股（KPL 只给代表股）|
| **大盘情绪** | KPL `/api/kpl/sentiment` | 自己从 daily_quotes 算 | KPL 不可用时降级 |
| **连板梯队** | KPL `/api/kpl/ladder` | 自己 SQL 算 | 历史趋势分析（KPL 只给汇总值） |
| **历史 K 线** | 自己 `/api/quotes`（全市场） | KPL `/stock/kline` | 从来不需要 KPL，自己的覆盖全 |
| **个股板块归类** | 综合 `/api/stock-sectors/for-stock/{ts_code}`（已合并 EM/SW/MANUAL/KPL 多源） | — | 总是这个 |

### 一句话原则

> **能用 KPL 就用 KPL**（专业题材归因、连板描述、龙头标记），自己 SQL 算的兜底（覆盖度优势）。

---

## 3. 复盘 4 步流程

### Step 1 大势判断
```
GET /api/kpl/sentiment           # 涨跌停 / 实际涨停（剔除 ST）
GET /api/kpl/ladder              # 连板梯队（首板/2连/3连/高度）+ rate 晋级率 + comment
GET /api/kpl/dashboard           # 15:00 快照：intensity 强度 + 风向标 + 板块涨跌面
GET /api/kpl/emotion             # 量比、量
GET /api/kpl/history-analysis    # 250 日趋势 + blown_rate 炸板率（情绪温度计）
```
**判断口径**：
- 强势：actual_limit_up ≥ 60，rate ≥ 20%，blown_rate < 20%，high_board ≥ 3
- 弱势：actual_limit_up < 30，blown_rate > 30%，or 无 3 连板及以上

### Step 2 板块热度
```
GET /api/kpl/sectors-heat        # 双源对比，每板块带成分股
GET /api/kpl/news                # 题材新闻 + 关联股 + isTop 龙头
GET /api/kpl/conception-history  # 盘中题材异动时序
GET /api/kpl/sector-news/{code}  # 单板块的催化剂新闻
```

### Step 3 个股结构
```
GET /api/kpl/consecutive?min_days=1     # 全部涨停（含首板，含题材）
GET /api/kpl/market-ladder              # 空间板梯队
GET /api/kpl/lhb                        # 龙虎榜上榜
GET /api/kpl/lhb/seats/{ts_code}        # 单股席位穿透
GET /api/kpl/youzi/by-stock/{ts_code}   # 该股被哪些游资打过几次（核心）
GET /api/kpl/stock/ztgene/{ts_code}     # 涨停基因（封板率/胜率）
```

### Step 4 风险信号
```
GET /api/kpl/broken              # 今日炸板
GET /api/kpl/withdrawal          # 高位跳水
```

---

## 4. KPL 实时数据 — Agent 直连指南

> **本项目不转发实时类接口**。Agent 在盘中需要实时数据时，**直接调 KPL 原始接口**。

### 4.1 通用调用规范

```
GET http://124.222.49.67:3000/api/{endpoint}?{params}
Headers:
  x-api-key: sk_inst_d37ea1a202168c22
```

返回 JSON。HTTP 200 不一定数据有效，需要看具体接口的 `errcode` 字段（如有）。

### 4.2 实时类接口清单（直连，不入库）

| 接口 | 用途 | 何时调 |
|---|---|---|
| `/api/auction/dashboard` | 盘中实时打板统计 + 风向标 + 板块涨跌面 | 9:25 / 10:00 / 11:30 / 13:00 / 14:00 / 14:50 任意时间 |
| `/api/realtime/limitcount` | 实时涨跌停家数（毫秒级） | 盘中任意 |
| `/api/emotion/mood` | 实时情绪极值报警 | 盘中 |
| `/api/index` | 上证/深证/创业板核心指数实时 | 盘中 |
| `/api/index/realtime/{code}` | 单指数极速实时价 | 盘中 |
| `/api/index/trend/{code}` | 指数全天分时坐标 | 盘后 |
| `/api/intraday/index/{code}` | 指数秒级分时切片（含 MACD 等衍生指标） | 盘中盘后均可 |
| `/api/intraday/stock/{ts_code}` | 个股秒级分时量价 | 盘中盘后 |
| `/api/stock/bigorder/{code}` | **L2 主力大单/特大单/小单真实净买入（Inst 独家）** | 盘中实时跟踪 |
| `/api/index/depth/{code}` | 指数 L2 深度十档买卖盘 | 盘中 |
| `/api/global/index` | 全球核心指数（纳斯达克/恒生等） | 任意 |
| `/api/commodity/list` | 大宗商品（黄金/原油等） | 任意 |
| `/api/news/focus` | 7x24 滚动金融快讯 | 任意（实时推） |
| `/api/live/content` | 大盘盘中直播（异动播报）| 盘中 |

### 4.3 调用示例

**盘中实时涨停统计**：
```
GET http://124.222.49.67:3000/api/realtime/limitcount
Headers: x-api-key: sk_inst_d37ea1a202168c22
```

**单股 L2 主力净买入**：
```
GET http://124.222.49.67:3000/api/stock/bigorder/600519
Headers: x-api-key: sk_inst_d37ea1a202168c22
```
> 注：直接传 6 位代码（不带 .SH/.SZ 后缀）。

**当日竞价全景**：
```
GET http://124.222.49.67:3000/api/auction/dashboard
Headers: x-api-key: sk_inst_d37ea1a202168c22
```

### 4.4 Tool Use Schema（KPL 直连工具）

```json
{
  "name": "kpl_realtime",
  "description": "调用开盘啦原始 API 拿实时数据。仅用于实时类（盘中、L2、指数实时）。已入库的复盘数据用 stock_data_get 工具。",
  "input_schema": {
    "type": "object",
    "properties": {
      "endpoint": {
        "type": "string",
        "description": "/api/auction/dashboard / /api/stock/bigorder/{code} / /api/realtime/limitcount 等"
      },
      "params": {"type": "object"}
    },
    "required": ["endpoint"]
  }
}
```

执行：
```python
url = f"http://124.222.49.67:3000{endpoint}"
headers = {"x-api-key": "sk_inst_d37ea1a202168c22"}
return requests.get(url, headers=headers, params=params).json()
```

### 4.5 限频与配额

- inst 套餐：**5000 次/天**
- 单接口频率限制：见每个接口文档
- Agent 调用建议：**单次复盘控制在 30 次内**，避免无效循环

---

## 5. 项目 REST API 速查（已入库数据）

> 所有这些是**累积入库**的数据，盘后调用最稳。日期参数不传 = 最近一个有数据的交易日。

### 5.1 大盘环境
```
GET /api/kpl/sentiment[?trade_date=YYYY-MM-DD]
GET /api/kpl/ladder[?trade_date=]
GET /api/kpl/dashboard[?trade_date=]            # 15:00 快照
GET /api/kpl/emotion[?trade_date=]              # 15:00 快照
GET /api/kpl/history-strength?days=30
GET /api/kpl/history-analysis?days=60           # 含 blown_rate 炸板率
```

### 5.2 涨停 / 连板 / 跌停
```
GET /api/limit-up?trade_date=&min_limit_times=&limit=500
GET /api/kpl/consecutive?trade_date=&min_days=1   # 默认 1 = 全部涨停含首板
GET /api/limit-down?trade_date=
GET /api/kpl/broken?trade_date=
GET /api/kpl/withdrawal?trade_date=
GET /api/kpl/market-ladder?trade_date=
```

### 5.3 板块 / 题材
```
GET /api/kpl/sectors-heat?trade_date=             # 双源 + 成分股
GET /api/limit-up/by-sector?trade_date=&by=concept
GET /api/kpl/news?limit=30[&keyword=]             # 含关联股 isTop 龙头
GET /api/kpl/sector-news/{sector_code}?limit=30
GET /api/kpl/conception-history?trade_date=
GET /api/kpl/news-selected?limit=20
```

### 5.4 龙虎榜 / 游资
```
GET /api/kpl/lhb?trade_date=
GET /api/kpl/lhb/seats/{ts_code}[?trade_date=]
GET /api/kpl/youzi/traders                        # 8 个游资名册
GET /api/kpl/youzi/trades?trade_date=&trader_id=&ts_code=&limit=200
GET /api/kpl/youzi/by-stock/{ts_code}             # 游资标签累计（核心）
```

### 5.5 个股按需
```
GET /api/kpl/stock/ztgene/{ts_code}               # 涨停基因（实时穿透 KPL 接口）
GET /api/stock-sectors/for-stock/{ts_code}[?src=] # 个股所有板块
GET /api/quotes?ts_code=&start_date=&end_date=
```

### 5.6 衍生分析
```
GET /api/rankings/gainers?days=5&top=10[&end_date=]
GET /api/rankings/sectors?top=10[&days=&end_date=]
```

---

## 6. 关键字段含义速查

### 涨停个股（KPL `/kpl/consecutive`）
- `days` 连板数（1 = 首板）
- `theme` 题材归因（开盘啦自己分类，逗号分隔）
- `board_desc` 口语描述："7天6板" / "4天3板" 等
- `market_cap` 流通市值（元）

### 板块热度（KPL `/kpl/sectors-heat.kpl[].stocks[]`）
- `td_type=2` 龙头
- `td_type=1` 首板
- `td_type=0` 连板（看 tips 描述）

### 龙虎榜席位（`/kpl/lhb/seats/{code}`）
- `side=B` 买方 / `side=S` 卖方
- `is_dy=1` KPL 标记游资（**目前数据多为 0，建议从 broker 名字识别马甲**）
- 常见游资马甲（broker 字段）：
  - "东方财富证券拉萨..." 系列 = 拉萨派量化
  - "国信证券浙江互联网" = 知名打板专员
  - "深股通专用" / "沪股通专用" = 北向资金（不是游资）
  - "机构专用" = 机构席位（不是游资）

### `stock_sectors.src` 板块来源
- `EM` 东财（自动同步）
- `SW` 申万（待接入）
- `KPL` 开盘啦（每日自动同步）
- `MANUAL` **手动喂入，永久保留**

---

## 7. 复盘报告输出格式（推荐 Agent 按这个结构输出）

```markdown
# 【YYYY-MM-DD】A 股复盘

## 一、市场环境
- 情绪温度：[强 / 中 / 弱]
- 涨停 N / 实际涨停 N / 跌停 N
- 连板梯队：首板 N · 2连 N · 3连 N · 高度 N
- 强度 X · 量比 X% · 炸板率 X%
- 与近 N 日比：[偏强/偏弱]，理由 xxx

## 二、热点板块
| # | 板块 | 涨停数 | 龙头 | 催化剂 |
|---|---|---|---|---|
| 1 | XXX | 14 | XXX (N板) | XXX 新闻 |

## 三、个股结构
### 高度板（最强股）
- {代码} {名称} {N板} {题材} {资金} → 简评

### 龙虎榜异动
- 进榜 N 只
- 重点游资动向：[XXX 净买 X 亿 in YYY]

## 四、风险信号
- 炸板率 X%（[正常/偏高]）
- 高位跳水 N 只（[X 龙头跳水]）

## 五、明日关注
1. 题材：[XXX 持续性观察]
2. 个股：[X 卡位 / 打板首选 / 防守]
3. 风险：[X 需警惕]
```

---

## 8. Tool Use Schema（推荐 Hermes 配两个工具）

```json
[
  {
    "name": "stock_data_get",
    "description": "调用本项目数据 API（已入库的复盘数据）。所有日期 YYYY-MM-DD。不传 trade_date 默认最近交易日。",
    "input_schema": {
      "type": "object",
      "properties": {
        "endpoint": {"type": "string", "description": "如 /kpl/sentiment / /kpl/sectors-heat / /limit-up"},
        "params": {"type": "object"}
      },
      "required": ["endpoint"]
    }
  },
  {
    "name": "kpl_realtime",
    "description": "调用开盘啦原始 API 拿实时数据。仅盘中实时类（auction/dashboard、stock/bigorder、index/realtime 等）。已入库的复盘数据用 stock_data_get。",
    "input_schema": {
      "type": "object",
      "properties": {
        "endpoint": {"type": "string", "description": "如 /api/auction/dashboard / /api/stock/bigorder/600519"},
        "params": {"type": "object"}
      },
      "required": ["endpoint"]
    }
  }
]
```

执行映射：
- `stock_data_get` → `GET http://8.130.160.238/api{endpoint}?{params}`
- `kpl_realtime` → `GET http://124.222.49.67:3000{endpoint}?{params}` + Header `x-api-key: sk_inst_d37ea1a202168c22`

---

## 9. 注意事项

1. **盘中复盘要混用两个数据源**：盘中数据走 KPL 实时接口；昨天及以前数据走本项目 API。
2. **失败容忍**：
   - 本项目 500 → 提示用户排查（可能 daily_job 没跑）
   - KPL 500 → **不要重试**（上游问题，重试会触发 ban）
3. **数据冲突**：自己 SQL 算的和 KPL 给的不一致是常态（口径差异），双源都展示更稳。
4. **限频意识**：KPL inst 套餐 5000 次/天总额度，单次复盘建议 ≤ 30 次调用。
5. **周末/节假日**：不要传周末日期。要查最近交易日不传 trade_date 即可。
6. **历史回溯极限**：自己日线 6 个交易日；KPL 大部分接口支持任意历史日期回溯。

---

## 附：完整 API 索引

### 本项目 API（http://8.130.160.238/api）

| 路径 | 用途 | 维度 |
|---|---|---|
| /kpl/sentiment | 大盘情绪 | 1 大势 |
| /kpl/ladder | 连板梯队汇总 | 1 大势 |
| /kpl/dashboard | 竞价/收盘快照（15:00 拍） | 1 大势 |
| /kpl/emotion | 量比/分布（15:00 拍） | 1 大势 |
| /kpl/history-strength | 100 日强度曲线 | 1 大势 |
| /kpl/history-analysis | 250 日含炸板率 | 1 大势 |
| /limit-up | 涨停（自己 SQL 算）| 3 个股 |
| /kpl/consecutive | 涨停 KPL（含题材）| 3 个股 |
| /limit-down | 跌停 | 3 个股 |
| /kpl/broken | 炸板池 | 4 风险 |
| /kpl/withdrawal | 高位跳水池 | 4 风险 |
| /kpl/market-ladder | 空间板梯队 | 3 个股 |
| /kpl/sectors-heat | 板块热度双源（含成分股） | 2 板块 |
| /limit-up/by-sector | 涨停按板块分组 | 2 板块 |
| /kpl/news | 题材新闻+关联股 | 2 板块 |
| /kpl/sector-news/{code} | 板块新闻 | 2 板块 |
| /kpl/conception-history | 盘中题材异动时序 | 2 板块 |
| /kpl/news-selected | 编辑精选 | 2 板块 |
| /kpl/lhb | 龙虎榜 | 3 个股 |
| /kpl/lhb/seats/{ts_code} | 席位穿透 | 3 个股 |
| /kpl/youzi/traders | 游资名册 | 3 个股 |
| /kpl/youzi/trades | 游资交易明细 | 3 个股 |
| /kpl/youzi/by-stock/{ts_code} | 个股游资标签 | 3 个股 |
| /kpl/stock/ztgene/{ts_code} | 涨停基因 | 3 个股 |
| /stock-sectors/for-stock/{ts_code} | 个股所有板块 | 3 个股 |
| /quotes | 个股 K 线 | 3 个股 |
| /rankings/gainers | N 日涨幅排行 | 衍生 |
| /rankings/sectors | N 日板块涨幅 | 衍生 |

### KPL 直连接口（http://124.222.49.67:3000，需 x-api-key）

| 路径 | 用途 |
|---|---|
| /api/auction/dashboard | 实时竞价全景 |
| /api/realtime/limitcount | 实时涨跌停家数 |
| /api/emotion/mood | 实时情绪极值 |
| /api/index | 核心指数实时 |
| /api/index/realtime/{code} | 单指数实时 |
| /api/index/trend/{code} | 指数分时坐标 |
| /api/intraday/index/{code} | 指数秒级分时 |
| /api/intraday/stock/{code} | 个股秒级分时 |
| /api/stock/bigorder/{code} | L2 主力大单 |
| /api/index/depth/{code} | 指数 L2 深度 |
| /api/global/index | 全球指数 |
| /api/commodity/list | 大宗商品 |
| /api/news/focus | 7x24 快讯 |
| /api/live/content | 大盘直播 |

---

**文档版本**：v2（2026-04-29）
**维护**：API 字段以 `backend/src/stockdata/api/` 实现为准。新增/修改 API 后请同步更新本文档。
