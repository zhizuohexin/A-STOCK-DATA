from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from stockdata.api.schemas import JobRunOut
from stockdata.db import get_session
from stockdata.models import JobRun

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/runs", response_model=list[JobRunOut])
def list_job_runs(
    job_name: str | None = None,
    limit: int = 50,
    session: Session = Depends(get_session),
):
    stmt = select(JobRun)
    if job_name:
        stmt = stmt.where(JobRun.job_name == job_name)
    stmt = stmt.order_by(JobRun.started_at.desc()).limit(limit)
    return session.execute(stmt).scalars().all()
