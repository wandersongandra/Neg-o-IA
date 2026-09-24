"""Contratos do Planner — planos limitados, auditáveis e sem execução direta."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class PlanStep:
    step_id: str
    kind: str
    description: str
    tool_name: str | None
    arguments: dict[str, Any]
    requires_confirmation: bool = False


@dataclass(frozen=True, slots=True)
class PlanStepExecution:
    step_id: str
    status: str
    tool_name: str | None
    output: dict[str, Any] | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class PlanExecutionResult:
    plan_id: str
    revision: int
    status: str
    steps: tuple[PlanStepExecution, ...]


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    plan_id: str
    user_id: str
    goal: str
    intent: str
    steps: tuple[PlanStep, ...]
    revision: int
    created_at: datetime
    updated_at: datetime


class PlanStore(Protocol):
    async def save(self, plan: ExecutionPlan) -> None: ...

    async def get(self, user_id: str, plan_id: str) -> ExecutionPlan | None: ...


class PlannerPort(Protocol):
    async def create_plan(self, user_id: str, text: str) -> ExecutionPlan: ...

    async def get_plan(self, user_id: str, plan_id: str) -> ExecutionPlan | None: ...

    async def replan(
        self,
        user_id: str,
        plan_id: str,
        failure: dict[str, Any],
    ) -> ExecutionPlan: ...

    async def execute_plan(
        self,
        user_id: str,
        plan_id: str,
        *,
        confirmed_step_ids: set[str] | None = None,
    ) -> PlanExecutionResult: ...
