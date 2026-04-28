import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from stockdata.config import settings
from stockdata.jobs.cleanup import cleanup_old_intraday
from stockdata.jobs.daily import run_daily_job
from stockdata.jobs.weekly import sync_stock_sectors_weekly

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    tz = ZoneInfo(settings.timezone)
    scheduler = BackgroundScheduler(timezone=tz)

    # 收盘后日线任务 (16:00 Asia/Shanghai, 周一-周五)
    scheduler.add_job(
        run_daily_job,
        CronTrigger(
            day_of_week="mon-fri",
            hour=settings.daily_job_hour,
            minute=settings.daily_job_minute,
            timezone=tz,
        ),
        id="daily_job",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # 次日凌晨清理分时 (08:30 Asia/Shanghai, 周一-周五)
    scheduler.add_job(
        cleanup_old_intraday,
        CronTrigger(
            day_of_week="mon-fri",
            hour=settings.cleanup_job_hour,
            minute=settings.cleanup_job_minute,
            timezone=tz,
        ),
        id="cleanup_intraday",
        replace_existing=True,
    )

    # 每周一 02:00 全量同步个股↔板块（约 35 分钟）
    scheduler.add_job(
        sync_stock_sectors_weekly,
        CronTrigger(day_of_week="mon", hour=2, minute=0, timezone=tz),
        id="weekly_stock_sectors_sync",
        replace_existing=True,
        misfire_grace_time=3600,
        max_instances=1,
    )

    scheduler.start()
    _scheduler = scheduler
    logger.info(
        "scheduler started: daily @%02d:%02d, cleanup @%02d:%02d, "
        "weekly_sectors @Mon 02:00 (%s)",
        settings.daily_job_hour,
        settings.daily_job_minute,
        settings.cleanup_job_hour,
        settings.cleanup_job_minute,
        settings.timezone,
    )
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
