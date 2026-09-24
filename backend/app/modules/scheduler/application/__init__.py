"""Scheduler V1 — jobs persistentes e ferramentas automation-safe."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from app.modules.events.envelope import build_envelope
from app.modules.scheduler.domain import ScheduledJob
from app.modules.scheduler.infrastructure import PostgresSchedulerStore
from app.modules.tool_manager.application import get_tool_manager_service

_LOGGER = logging.getLogger("app.modules.scheduler.application")
_service: SchedulerService | None = None


class SchedulerService:
    def __init__(self, store: PostgresSchedulerStore | None = None) -> None:
        self._store = store or PostgresSchedulerStore()
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def schedule(
        self,
        user_id: str,
        *,
        name: str,
        action_tool: str,
        action_args: dict[str, Any],
        run_at: datetime,
        interval_seconds: int | None = None,
    ) -> ScheduledJob:
        normalized = name.strip()
        if not normalized or len(normalized) > 160:
            raise ValueError("name must contain 1..160 characters")
        if run_at.tzinfo is None:
            raise ValueError("run_at must include timezone")
        normalized_run_at = run_at.astimezone(UTC)
        if normalized_run_at <= datetime.now(UTC):
            raise ValueError("run_at must be in the future")
        if interval_seconds is not None and not 60 <= interval_seconds <= 31_536_000:
            raise ValueError("interval_seconds must be between 60 and 31536000")

        spec = get_tool_manager_service().get_spec(action_tool)
        if spec is None:
            raise ValueError("unknown tool")
        if not spec.automation_safe or spec.requires_confirmation:
            raise ValueError("tool is not safe for unattended scheduling")

        job = await self._store.create(
            user_id,
            name=normalized,
            action_tool=action_tool,
            action_args=action_args,
            run_at=normalized_run_at,
            interval_seconds=interval_seconds,
        )
        await self._publish("scheduler.job.created", job, {"next_run_at": job.next_run_at.isoformat()})
        return job

    async def list_jobs(self, user_id: str) -> list[ScheduledJob]:
        return await self._store.list_for_user(user_id)

    async def set_enabled(
        self,
        user_id: str,
        job_id: str,
        *,
        enabled: bool,
    ) -> ScheduledJob | None:
        return await self._store.set_enabled(user_id, job_id, enabled=enabled)

    async def cancel(self, user_id: str, job_id: str) -> bool:
        removed = await self._store.delete(user_id, job_id)
        if removed:
            await self._publish_raw(
                "scheduler.job.deleted",
                user_id,
                {"job_id": job_id},
            )
        return removed

    async def run_due_once(self) -> int:
        jobs = await self._store.list_due(limit=50)
        tools = get_tool_manager_service()
        executed = 0
        for job in jobs:
            success = False
            try:
                spec = tools.get_spec(job.action_tool)
                if spec is None or not spec.automation_safe or spec.requires_confirmation:
                    raise RuntimeError("scheduled tool no longer allowed")
                await tools.execute_tool(
                    job.action_tool,
                    dict(job.action_args),
                    user_id=job.user_id,
                    confirmed=False,
                    idempotency_key=f"scheduler:{job.id}:{job.next_run_at.isoformat()}",
                )
                success = True
                executed += 1
                await self._publish(
                    "scheduler.job.executed",
                    job,
                    {"success": True},
                )
            except Exception:
                _LOGGER.warning(
                    "scheduler_job_failed",
                    extra={"job_id": job.id, "tool_name": job.action_tool},
                    exc_info=True,
                )
                await self._publish(
                    "scheduler.job.failed",
                    job,
                    {"success": False},
                )
            finally:
                await self._store.complete_run(job.id, success=success)
        return executed

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._loop(), name="sophie-scheduler")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                await self.run_due_once()
            except Exception:
                _LOGGER.warning("scheduler_tick_failed", exc_info=True)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=15.0)
            except TimeoutError:
                pass

    async def _publish(
        self,
        event_type: str,
        job: ScheduledJob,
        payload: dict[str, Any],
    ) -> None:
        await self._publish_raw(
            event_type,
            job.user_id,
            {"job_id": job.id, "tool_name": job.action_tool, **payload},
        )

    async def _publish_raw(
        self,
        event_type: str,
        user_id: str,
        payload: dict[str, Any],
    ) -> None:
        try:
            from app.modules.events.application import get_event_bus_service

            await get_event_bus_service().publish_event(
                build_envelope(
                    event_type,
                    "scheduler",
                    payload,
                    user_id=user_id,
                )
            )
        except Exception:
            _LOGGER.warning("scheduler_event_publish_failed", exc_info=True)


def get_scheduler_service() -> SchedulerService:
    global _service
    if _service is None:
        _service = SchedulerService()
    return _service
