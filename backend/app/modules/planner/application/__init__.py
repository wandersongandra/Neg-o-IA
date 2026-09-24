"""Planner V1 — transforma intenção em passos controlados e replanejáveis."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.modules.configuration.settings import get_settings
from app.modules.events.envelope import build_envelope
from app.modules.planner.domain import ExecutionPlan, PlanStep
from app.modules.planner.infrastructure import RedisPlanStore
from app.modules.reasoning.application import get_reasoning_service

_LOGGER = logging.getLogger("app.modules.planner.application")
PRODUCER = "planner"
_service: PlannerService | None = None


class PlannerService:
    def __init__(self, store: RedisPlanStore | None = None) -> None:
        self._store = store or RedisPlanStore()

    async def create_plan(self, user_id: str, text: str) -> ExecutionPlan:
        resolution = await get_reasoning_service().resolve_intent(text, user_id=user_id)
        steps = self._steps_for_resolution(text, resolution.suggested_tool, resolution.entities)
        now = datetime.now(UTC)
        plan = ExecutionPlan(
            plan_id=str(uuid.uuid4()),
            user_id=user_id,
            goal=text.strip(),
            intent=resolution.intent,
            steps=tuple(steps[: get_settings().planner_max_steps]),
            revision=0,
            created_at=now,
            updated_at=now,
        )
        await self._store.save(plan)
        await self._publish("planner.plan.created", plan)
        return plan

    async def get_plan(self, user_id: str, plan_id: str) -> ExecutionPlan | None:
        return await self._store.get(user_id, plan_id)

    async def replan(
        self,
        user_id: str,
        plan_id: str,
        failure: dict[str, Any],
    ) -> ExecutionPlan:
        current = await self._store.get(user_id, plan_id)
        if current is None:
            raise LookupError("plan not found")
        if current.revision >= get_settings().planner_max_replans:
            raise RuntimeError("maximum replans reached")

        reason = str(failure.get("reason") or "falha não especificada")[:500]
        retry_steps = (
            PlanStep(
                step_id="r1",
                kind="internal",
                description=f"Reavaliar a falha anterior: {reason}",
                tool_name=None,
                arguments={},
            ),
            *current.steps,
        )
        now = datetime.now(UTC)
        updated = ExecutionPlan(
            plan_id=current.plan_id,
            user_id=current.user_id,
            goal=current.goal,
            intent=current.intent,
            steps=tuple(retry_steps[: get_settings().planner_max_steps]),
            revision=current.revision + 1,
            created_at=current.created_at,
            updated_at=now,
        )
        await self._store.save(updated)
        await self._publish("planner.plan.replanned", updated)
        return updated

    @staticmethod
    def _steps_for_resolution(
        text: str,
        suggested_tool: str | None,
        entities: dict[str, Any],
    ) -> list[PlanStep]:
        if suggested_tool:
            if suggested_tool == "memory.remember":
                arguments = {"content": str(entities.get("content") or text)}
            elif suggested_tool in {"memory.search", "knowledge.search"}:
                arguments = {"query": str(entities.get("query") or text), "limit": 5}
            else:
                arguments = {}
            return [
                PlanStep(
                    step_id="1",
                    kind="tool",
                    description=f"Executar {suggested_tool}",
                    tool_name=suggested_tool,
                    arguments=arguments,
                    requires_confirmation=suggested_tool == "memory.remember",
                ),
                PlanStep(
                    step_id="2",
                    kind="response",
                    description="Sintetizar o resultado para o usuário",
                    tool_name=None,
                    arguments={},
                ),
            ]

        return [
            PlanStep(
                step_id="1",
                kind="internal",
                description="Analisar objetivo, restrições e contexto disponível",
                tool_name=None,
                arguments={},
            ),
            PlanStep(
                step_id="2",
                kind="response",
                description="Produzir resposta ou plano final sem efeitos externos",
                tool_name=None,
                arguments={},
            ),
        ]

    async def _publish(self, event_type: str, plan: ExecutionPlan) -> None:
        try:
            from app.modules.events.application import get_event_bus_service

            await get_event_bus_service().publish_event(
                build_envelope(
                    event_type,
                    PRODUCER,
                    {
                        "plan_id": plan.plan_id,
                        "intent": plan.intent,
                        "revision": plan.revision,
                        "steps": len(plan.steps),
                    },
                    user_id=plan.user_id,
                )
            )
        except Exception:
            _LOGGER.warning("planner_event_publish_failed", exc_info=True)


def get_planner_service() -> PlannerService:
    global _service
    if _service is None:
        _service = PlannerService()
    return _service
