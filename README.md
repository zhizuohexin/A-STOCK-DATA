# A-Stock Data

每日 A 股行情数据采集 & 可视化。Python + FastAPI + SQLite + React + Antd。

## 功能

- **日线行情**：收盘后自动入库（APScheduler 16:00 Asia/Shanghai）
- **涨停 / 连板**：池子 + 连板数
- **板块**：行业（申万）+ 概念（同花顺），含板块日线
- **N 日涨幅排行**：5/10/20/30/60 日前 Top N（SQL 窗口函数实时算）
- **板块涨幅排行**：某日涨幅前 Top N（可按行业/概念筛选）
- **盘中 1 分钟 K 线**：按需拉取，当天存库供 agent 查询，次日凌晨自动清理
- **任务日志**：所有同步/回溯/清理任务留痕
- **API**：每个表都有 query / upsert / delete 接口供 agent 调用

## 目录结构

```
a-stock-data/
├── backend/              # Python FastAPI
│   ├── src/stockdata/
│   │   ├── providers/    # 数据源抽象：tushare + 后续扩展
│   │   ├── api/          # REST 路由
│   │   ├── jobs/         # APScheduler 任务
│   │   ├── analytics/    # 排行计算
│   │   ├── models.py     # SQLAlchemy ORM
│   │   └── main.py       # FastAPI 入口
│   ├── alembic/          # 数据库迁移
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/             # React + Vite + TS + Antd
│   ├── src/pages/        # Dashboard/Stocks/Quotes/LimitUp/Sectors/Rankings/Intraday/Jobs
│   ├── Dockerfile
│   └── nginx.conf
├── data/stocks.db        # SQLite（volume 挂载）
├── docker-compose.yml
└── README.md
```

## 本地开发

### Backend

```bash
cd backend
cp .env.example .env        # 填 TUSHARE_TOKEN
uv sync
uv run alembic upgrade head
uv run uvicorn stockdata.main:app --reload --port 8000
```

访问：
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/health

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

访问 http://localhost:5173 （默认代理 `/api` 到 `localhost:8000`）

## Docker 部署（单机）

```bash
# 根目录放 .env，内含 TUSHARE_TOKEN=xxx
docker compose up -d --build
```

- 前端： http://localhost/ （nginx 80 端口）
- 后端 API： http://localhost:8000/api/
- 数据库： `./data/stocks.db`（挂载到容器 `/app/data`）

容器启动时自动跑 `alembic upgrade head`，schema 有变更直接重启容器即可迁移。

## 数据库迁移

改 `backend/src/stockdata/models.py` 后：

```bash
cd backend
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

生成的迁移脚本在 `backend/alembic/versions/` 下，**提交到 git**。容器重启时会自动应用。

## 主要 API

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | /api/stocks | 股票列表（搜索、按行业过滤） |
| POST | /api/stocks/sync | 从 provider 同步股票列表 |
| GET | /api/quotes | 日线（code/日期范围） |
| POST | /api/quotes/backfill | 回溯入库（最多 31 天） |
| DELETE | /api/quotes | 删除日线 |
| GET | /api/limit-up | 涨停池（日期、连板数过滤） |
| POST | /api/limit-up/backfill | 回溯某日涨停 |
| GET | /api/sectors | 板块列表 |
| GET | /api/sectors/daily | 板块日线 |
| GET | /api/rankings/gainers?days=5&top=10 | N 日涨幅排行 |
| GET | /api/rankings/sectors?top=5 | 板块涨幅排行 |
| GET | /api/intraday?code=...&trade_date=... | 当日分时 |
| POST | /api/intraday/fetch | 按需拉取某股分钟 K 线 |
| GET | /api/jobs/runs | 任务执行日志 |
| GET | /api/health | 健康检查 |

完整 Schema 见 Swagger：`/docs`。

## 调度任务

| 任务 | cron（Asia/Shanghai） | 说明 |
|---|---|---|
| `daily_job` | 周一~周五 16:00 | 拉取当日股票/日线/涨停/板块/板块日线 |
| `cleanup_intraday` | 周一~周五 08:30 | 删除前一日及更早的分时数据 |

时间可在 `.env` 里调整（`DAILY_JOB_HOUR`/`MINUTE` 等）。

## 数据源

所有 provider 实现 `DataProvider` 抽象（`backend/src/stockdata/providers/base.py`）。

当前内置：

| Provider | 擅长 | 不用的 | 积分要求 |
|---|---|---|---|
| `tushare` | 日线、涨停池（`limit_list_d`）、股票基本面、分钟K线 | 板块（2000档没同花顺权限） | 2000 分 |
| `eastmoney` | **板块（行业+概念）、板块日线、分时K线** | 股票列表/全市场日线（需逐股循环） | 免费 |

**当前默认路由**：
- 股票/日线/涨停 → tushare
- 板块/板块日线 → eastmoney
- 分时 → tushare（可换 eastmoney）

API 调用加 `?provider=eastmoney` 或 `?provider=tushare` 手动切换。

新增 provider：

1. 新建 `backend/src/stockdata/providers/xxx.py` 实现 6 个 `fetch_*` 方法（不支持的 return []）
2. 在 `providers/__init__.py::get_provider` 里注册

## ECS 部署思路

1. 拷贝整个项目到服务器
2. `.env` 放 TUSHARE_TOKEN
3. `docker compose up -d --build`
4. 用 nginx 或直接暴露 80 端口

**扩展**：SQLite 单机够用，如需多实例改 `DATABASE_URL=postgresql://...`（SQLAlchemy 兼容，Alembic 重新生成迁移）。
