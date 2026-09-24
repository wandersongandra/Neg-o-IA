"""Rotas autenticadas do Planner."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.interfaces.deps import CurrentAuth
from app.modules.planner.application import get_planner_service
from app.modules.planner.domain import ExecutionPlan

router = APIRouter(prefix="/planner", tags=["planner"])


class CreatePlanRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class ReplanRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class ExecutePlanRequest(BaseModel):
    confirmed_step_ids: list[str] = Field(default_factory=list, max_length=20)


def _user_id(auth: CurrentAuth) -> str:
    user_id = auth.effective_user_id
    if not user_id:
        raise HTTPException(status_code=403, detail="user identity required")
    return user_id


def _response(plan: ExecutionPlan) -> dict[str, Any]:
    return {
        "plan_id": plan.plan_id,
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
    }


@router.post("/plans")
async def create_plan(body: CreatePlanRequest, auth: CurrentAuth) -> dict[str, Any]:
    plan = await get_planner_service().create_plan(_user_id(auth), body.text)
    return _response(plan)


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str, auth: CurrentAuth) -> dict[str, Any]:
    plan = await get_planner_service().get_plan(_user_id(auth), plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="plan not found")
    return _response(plan)


@router.post("/plans/{plan_id}/replan")
async def replan(
    plan_id: str,
    body: ReplanRequest,
    auth: CurrentAuth,
) -> dict[str, Any]:
    try:
        plan = await get_planner_service().replan(
            _user_id(auth),
            plan_id,
            {"reason": body.reason},
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="plan not found") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _response(plan)


@router.post("/plans/{plan_id}/execute")
async def execute_plan(
    plan_id: str,
    body: ExecutePlanRequest,
    auth: CurrentAuth,
) -> dict[str, Any]:
    try:
        result = await get_planner_service().execute_plan(
            _user_id(auth),
            plan_id,
            confirmed_step_ids=set(body.confirmed_step_ids),
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="plan not found") from exc
    return {
        "plan_id": result.plan_id,
        "revision": result.revision,
        "status": result.status,
        "steps": [
            {
                "step_id": step.step_id,
                "status": step.status,
                "tool_name": step.tool_name,
                "output": step.output,
                "error": step.error,
            }
            for step in result.steps
        ],
    }
