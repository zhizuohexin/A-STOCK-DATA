import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from stockdata import __version__
from stockdata.api import (
    dashboard,
    intraday,
    jobs,
    journal,
    kaipanla,
    limit_down,
    limit_up,
    ocr,
    quotes,
    rankings,
    sectors,
    stock_sectors,
    stocks,
)
from stockdata.config import settings
from stockdata.jobs.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.scheduler_enabled:
        start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="A-Stock Data API",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router, prefix="/api")
app.include_router(stocks.router, prefix="/api")
app.include_router(quotes.router, prefix="/api")
app.include_router(limit_up.router, prefix="/api")
app.include_router(limit_down.router, prefix="/api")
app.include_router(sectors.router, prefix="/api")
app.include_router(stock_sectors.router, prefix="/api")
app.include_router(intraday.router, prefix="/api")
app.include_router(rankings.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(ocr.router, prefix="/api")
app.include_router(journal.router, prefix="/api")
app.include_router(kaipanla.router, prefix="/api")

_uploads_path = Path(settings.uploads_dir)
_uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_path)), name="uploads")


@app.get("/api/health")
def health():
    return {"status": "ok", "version": __version__}
