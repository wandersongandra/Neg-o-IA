"""Rotas autenticadas do Scheduler V1."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.interfaces.deps import CurrentAuth
from app.modules.scheduler.application import get_scheduler_service
from app.modules.scheduler.domain import ScheduledJob

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


class CreateJobRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    action_tool: str = Field(min_length=1, max_length=128)
    action_args: dict[str, Any] = Field(default_factory=dict)
    run_at: datetime
    interval_seconds: int | None = Field(default=None, ge=60, le=31_536_000)


class JobStateRequest(BaseModel):
    enabled: bool


def _user_id(auth: CurrentAuth) -> str:
    user_id = auth.effective_user_id
    if not user_id:
        raise HTTPException(status_code=403, detail="user identity required")
    return user_id


def _response(job: ScheduledJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "name": job.name,
        "action_tool": job.action_tool,
        "action_args": job.action_args,
        "run_at": job.run_at.isoformat(),
        "interval_seconds": job.interval_seconds,
        "enabled": job.enabled,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "last_run_at": job.last_run_at.isoformat() if job.last_run_at else None,
        "next_run_at": job.next_run_at.isoformat(),
    }


@router.post("/jobs")
async def create_job(body: CreateJobRequest, auth: CurrentAuth) -> dict[str, Any]:
    try:
        job = await get_scheduler_service().schedule(
            _user_id(auth),
            name=body.name,
            action_tool=body.action_tool,
            action_args=body.action_args,
            run_at=body.run_at,
            interval_seconds=body.interval_seconds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _response(job)


@router.get("/jobs")
async def list_jobs(auth: CurrentAuth) -> dict[str, Any]:
    jobs = await get_scheduler_service().list_jobs(_user_id(auth))
    return {"jobs": [_response(job) for job in jobs]}


@router.patch("/jobs/{job_id}")
async def set_job_state(
    job_id: str,
    body: JobStateRequest,
    auth: CurrentAuth,
) -> dict[str, Any]:
    job = await get_scheduler_service().set_enabled(
        _user_id(auth),
        job_id,
        enabled=body.enabled,
    )
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return _response(job)


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, auth: CurrentAuth) -> dict[str, bool]:
    removed = await get_scheduler_service().cancel(_user_id(auth), job_id)
    if not removed:
        raise HTTPException(status_code=404, detail="job not found")
    return {"deleted": True}
