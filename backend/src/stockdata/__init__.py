"""A-stock data service."""

__version__ = "0.1.0"


def main() -> None:
    import uvicorn

    from stockdata.config import settings

    uvicorn.run(
        "stockdata.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )
