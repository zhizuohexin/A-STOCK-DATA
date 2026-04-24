from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class StockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ts_code: str
    symbol: str
    name: str
    area: str | None = None
    industry: str | None = None
    market: str | None = None
    list_date: date | None = None


class DailyQuoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ts_code: str
    name: str | None = None
    industry: str | None = None
    trade_date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    pre_close: float | None
    change: float | None
    pct_chg: float | None
    vol: float | None
    amount: float | None
    turnover_rate: float | None


class LimitUpOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ts_code: str
    trade_date: date
    name: str | None
    close: float | None
    pct_chg: float | None
    amount: float | None
    fd_amount: float | None
    first_time: str | None
    last_time: str | None
    open_times: int | None
    limit_times: int | None


class SectorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ts_code: str
    name: str
    type: str


class SectorDailyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    sector_code: str
    trade_date: date
    name: str | None
    close: float | None
    pct_chg: float | None
    vol: float | None
    amount: float | None


class IntradayBarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ts_code: str
    name: str | None = None
    bar_time: datetime
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    vol: float | None
    amount: float | None


class JobRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_name: str
    status: str
    message: str | None
    rows_affected: int | None
    started_at: datetime
    finished_at: datetime | None


class BackfillRequest(BaseModel):
    start_date: date
    end_date: date


class BackfillResponse(BaseModel):
    days_processed: int
    rows_upserted: int
    errors: list[str] = []


class DeleteResponse(BaseModel):
    rows_deleted: int


class JournalEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entry_date: date
    content: str
    images: list[str]
    created_at: datetime
    updated_at: datetime


class OcrOut(BaseModel):
    text: str
