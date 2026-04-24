from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    tushare_token: str = ""

    database_url: str = "sqlite:///./data/stocks.db"
    uploads_dir: str = "./data/uploads"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173"

    scheduler_enabled: bool = True
    daily_job_hour: int = 16
    daily_job_minute: int = 0
    cleanup_job_hour: int = 8
    cleanup_job_minute: int = 30

    timezone: str = "Asia/Shanghai"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
