"""Persistência temporária de planos em Redis."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.infrastructure.redis import get_redis
from app.modules.configuration.settings import get_settings
from app.modules.planner.domain import ExecutionPlan, PlanStep


def _key(user_id: str, plan_id: str) -> str:
    return f"planner:{user_id}:{plan_id}"


def _serialize(plan: ExecutionPlan) -> str:
    return json.dumps(
        {
            "plan_id": plan.plan_id,
            "user_id": plan.user_id,
            "goal": plan.goal,
            "intent": plan.intent,
            "revision": plan.revision,
            "created_at": plan.created_at.isoformat(),
            "updated_at": plan.updated_at.isoformat(),
            "steps": [
                {
                    "step_id": step.step_id,
                    "kind": step.kind,
                    "description": step.description,
                    "tool_name": step.tool_name,
                    "arguments": step.arguments,
                    "requires_confirmation": step.requires_confirmation,
                }
                for step in plan.steps
            ],
        },
        ensure_ascii=False,
    )


def _deserialize(raw: str) -> ExecutionPlan:
    data: dict[str, Any] = json.loads(raw)
    return ExecutionPlan(
        plan_id=str(data["plan_id"]),
        user_id=str(data["user_id"]),
        goal=str(data["goal"]),
        intent=str(data["intent"]),
        revision=int(data["revision"]),
        created_at=datetime.fromisoformat(str(data["created_at"])).astimezone(UTC),
        updated_at=datetime.fromisoformat(str(data["updated_at"])).astimezone(UTC),
        steps=tuple(
            PlanStep(
                step_id=str(item["step_id"]),
                kind=str(item["kind"]),
                description=str(item["description"]),
                tool_name=str(item["tool_name"]) if item.get("tool_name") else None,
                arguments=dict(item.get("arguments") or {}),
                requires_confirmation=bool(item.get("requires_confirmation", False)),
            )
            for item in data["steps"]
        ),
    )


class RedisPlanStore:
    async def save(self, plan: ExecutionPlan) -> None:
        await get_redis().set(
            _key(plan.user_id, plan.plan_id),
            _serialize(plan),
            ex=get_settings().planner_plan_ttl_seconds,
        )

    async def get(self, user_id: str, plan_id: str) -> ExecutionPlan | None:
        raw = await get_redis().get(_key(user_id, plan_id))
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return _deserialize(raw)
