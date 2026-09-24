"""Testes dos limites de planejamento."""

from __future__ import annotations

from typing import Any

import pytest

from app.modules.planner.application import PlannerService


def test_memory_write_step_requires_confirmation() -> None:
    steps = PlannerService._steps_for_resolution(
        "Lembre que gosto de Python",
        "memory.remember",
        {"content": "gosto de Python"},
    )

    assert steps[0].tool_name == "memory.remember"
    assert steps[0].requires_confirmation is True
    assert steps[0].arguments["content"] == "gosto de Python"


def test_read_only_search_does_not_require_confirmation() -> None:
    steps = PlannerService._steps_for_resolution(
        "Procure na memória meu projeto",
        "memory.search",
        {"query": "meu projeto"},
    )

    assert steps[0].tool_name == "memory.search"
    assert steps[0].requires_confirmation is False
    assert steps[0].arguments["limit"] == 5


class _FakePlanStore:
    def __init__(self, plan: Any) -> None:
        self.plan = plan

    async def get(self, user_id: str, plan_id: str) -> Any:
        del user_id, plan_id
        return self.plan

    async def save(self, plan: Any) -> None:
        self.plan = plan


class _FakeToolManager:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        user_id: str,
        confirmed: bool = False,
        idempotency_key: str | None = None,
    ) -> Any:
        self.calls.append((tool_name, arguments, user_id, confirmed, idempotency_key))
        return type(
            "Result",
            (),
            {"tool_name": tool_name, "output": {"stored": True}, "cached": False},
        )()


@pytest.mark.asyncio
async def test_plan_execution_stops_before_unconfirmed_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import UTC, datetime

    from app.modules.planner.domain import ExecutionPlan, PlanStep

    plan = ExecutionPlan(
        plan_id="plan-1",
        user_id="user-1",
        goal="lembrar algo",
        intent="memory.remember",
        steps=(
            PlanStep(
                step_id="1",
                kind="tool",
                description="salvar memória",
                tool_name="memory.remember",
                arguments={"content": "abc"},
                requires_confirmation=True,
            ),
        ),
        revision=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    tools = _FakeToolManager()
    monkeypatch.setattr(
        "app.modules.tool_manager.application.get_tool_manager_service",
        lambda: tools,
    )
    service = PlannerService(store=_FakePlanStore(plan))

    result = await service.execute_plan("user-1", "plan-1")

    assert result.status == "confirmation_required"
    assert tools.calls == []


@pytest.mark.asyncio
async def test_plan_execution_runs_confirmed_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import UTC, datetime

    from app.modules.planner.domain import ExecutionPlan, PlanStep

    plan = ExecutionPlan(
        plan_id="plan-1",
        user_id="user-1",
        goal="lembrar algo",
        intent="memory.remember",
        steps=(
            PlanStep(
                step_id="1",
                kind="tool",
                description="salvar memória",
                tool_name="memory.remember",
                arguments={"content": "abc"},
                requires_confirmation=True,
            ),
        ),
        revision=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    tools = _FakeToolManager()
    monkeypatch.setattr(
        "app.modules.tool_manager.application.get_tool_manager_service",
        lambda: tools,
    )
    monkeypatch.setattr(
        "app.modules.events.application.get_event_bus_service",
        lambda: type("Bus", (), {"publish_event": staticmethod(lambda envelope: None)})(),
    )
    service = PlannerService(store=_FakePlanStore(plan))

    result = await service.execute_plan(
        "user-1",
        "plan-1",
        confirmed_step_ids={"1"},
    )

    assert result.status == "completed"
    assert tools.calls[0][3] is True
