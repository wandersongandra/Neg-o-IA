"""Contratos do Scheduler V1."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ScheduledJob:
    id: str
    user_id: str
    name: str
    action_tool: str
    action_args: dict[str, Any]
    run_at: datetime
    interval_seconds: int | None
    enabled: bool
    created_at: datetime
    updated_at: datetime
    last_run_at: datetime | None
    next_run_at: datetime


class SchedulerPort(Protocol):
    async def schedule(
        self,
        user_id: str,
        *,
        name: str,
        action_tool: str,
        action_args: dict[str, Any],
        run_at: datetime,
        interval_seconds: int | None = None,
    ) -> ScheduledJob: ...

    async def cancel(self, user_id: str, job_id: str) -> bool: ...
