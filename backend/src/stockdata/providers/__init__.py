from stockdata.providers.base import DataProvider
from stockdata.providers.eastmoney import EastmoneyProvider
from stockdata.providers.tushare_provider import TushareProvider

__all__ = ["DataProvider", "EastmoneyProvider", "TushareProvider", "get_provider"]


def get_provider(name: str = "tushare") -> DataProvider:
    if name == "tushare":
        return TushareProvider()
    if name == "eastmoney":
        return EastmoneyProvider()
    raise ValueError(f"Unknown provider: {name}")
