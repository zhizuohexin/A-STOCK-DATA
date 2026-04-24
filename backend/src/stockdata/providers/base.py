from abc import ABC, abstractmethod
from datetime import date
from typing import Any


class DataProvider(ABC):
    """A-share data provider abstract base.

    All fetch_* methods return list[dict] so downstream upsert logic stays
    provider-agnostic. New providers (eastmoney, akshare, ...) implement this
    same interface.
    """

    name: str = "base"

    @abstractmethod
    def fetch_stock_list(self) -> list[dict[str, Any]]:
        """Return stock basic info: ts_code, symbol, name, area, industry, market, list_date."""

    @abstractmethod
    def fetch_daily_quotes(self, trade_date: date) -> list[dict[str, Any]]:
        """Return daily OHLC for all stocks on one trading day."""

    @abstractmethod
    def fetch_limit_up(self, trade_date: date) -> list[dict[str, Any]]:
        """Return limit-up pool (涨停板池) for one day, including consecutive limit-up count."""

    @abstractmethod
    def fetch_sectors(self) -> list[dict[str, Any]]:
        """Return all sectors (industry + concept)."""

    @abstractmethod
    def fetch_sector_daily(self, trade_date: date) -> list[dict[str, Any]]:
        """Return sector daily performance."""

    @abstractmethod
    def fetch_intraday_bars(self, ts_code: str, trade_date: date, freq: str = "1min") -> list[dict[str, Any]]:
        """Return intraday K-line bars for one stock on one day."""
