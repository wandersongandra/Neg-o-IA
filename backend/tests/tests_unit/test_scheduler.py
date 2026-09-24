"""Testes do Scheduler V1."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.modules.scheduler.application import SchedulerService
from app.modules.scheduler.domain import ScheduledJob
from app.modules.tool_manager.domain import ToolSpec


@dataclass
class FakeStore:
    created: list[dict[str, Any]]

    async def create(self, user_id: str, **kwargs: Any) -> ScheduledJob:
        self.created.append({"user_id": user_id, **kwargs})
        now = datetime.now(UTC)
        return ScheduledJob(
            id="00000000-0000-0000-0000-000000000010",
            user_id=user_id,
            name=kwargs["name"],
            action_tool=kwargs["action_tool"],
            action_args=kwargs["action_args"],
            run_at=kwargs["run_at"],
            interval_seconds=kwargs["interval_seconds"],
            enabled=True,
            created_at=now,
            updated_at=now,
            last_run_at=None,
            next_run_at=kwargs["run_at"],
        )


class FakeTools:
    def __init__(self, safe: bool) -> None:
        self.safe = safe

    def get_spec(self, name: str) -> ToolSpec | None:
        return ToolSpec(
            name=name,
            description="test",
            input_schema={},
            risk="read" if self.safe else "write",
            requires_confirmation=not self.safe,
            automation_safe=self.safe,
        )


class FakeBus:
    async def publish_event(self, envelope: Any) -> None:
        del envelope


@pytest.mark.asyncio
async def test_scheduler_accepts_only_automation_safe_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FakeStore(created=[])
    monkeypatch.setattr(
        "app.modules.scheduler.application.get_tool_manager_service",
        lambda: FakeTools(True),
    )
    monkeypatch.setattr(
        "app.modules.events.application.get_event_bus_service",
        lambda: FakeBus(),
    )
    service = SchedulerService(store=store)  # type: ignore[arg-type]
    job = await service.schedule(
        "00000000-0000-0000-0000-000000000001",
        name="Health",
        action_tool="system.health",
        action_args={},
        run_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    assert job.action_tool == "system.health"
    assert len(store.created) == 1


@pytest.mark.asyncio
async def test_scheduler_rejects_write_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.modules.scheduler.application.get_tool_manager_service",
        lambda: FakeTools(False),
    )
    service = SchedulerService(store=FakeStore(created=[]))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="not safe"):
        await service.schedule(
            "00000000-0000-0000-0000-000000000001",
            name="Unsafe",
            action_tool="memory.remember",
            action_args={"content": "x"},
            run_at=datetime.now(UTC) + timedelta(minutes=5),
        )
