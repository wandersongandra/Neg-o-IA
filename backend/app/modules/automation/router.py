"""Rotas autenticadas de Automation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.interfaces.deps import CurrentAuth
from app.modules.automation.application import (
    AUTOMATION_TRIGGER_EVENTS,
    get_automation_service,
)
from app.modules.automation.domain import AutomationRule

router = APIRouter(prefix="/automation", tags=["automation"])


class CreateRuleRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    event_type: str = Field(min_length=1, max_length=128)
    action_tool: str = Field(min_length=1, max_length=128)
    action_args: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class RuleStateRequest(BaseModel):
    enabled: bool


class EvaluateRulesRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)


def _user_id(auth: CurrentAuth) -> str:
    user_id = auth.effective_user_id
    if not user_id:
        raise HTTPException(status_code=403, detail="user identity required")
    return user_id


def _rule_response(rule: AutomationRule) -> dict[str, Any]:
    return {
        "id": rule.id,
        "name": rule.name,
        "event_type": rule.event_type,
        "action_tool": rule.action_tool,
        "action_args": rule.action_args,
        "enabled": rule.enabled,
        "created_at": rule.created_at.isoformat(),
        "updated_at": rule.updated_at.isoformat(),
        "last_triggered_at": (
            rule.last_triggered_at.isoformat() if rule.last_triggered_at else None
        ),
    }


@router.get("/capabilities")
async def automation_capabilities() -> dict[str, Any]:
    return {"trigger_events": sorted(AUTOMATION_TRIGGER_EVENTS)}


@router.post("/rules")
async def create_rule(
    body: CreateRuleRequest,
    auth: CurrentAuth,
) -> dict[str, Any]:
    try:
        rule = await get_automation_service().create_rule(
            _user_id(auth),
            name=body.name,
            event_type=body.event_type,
            action_tool=body.action_tool,
            action_args=body.action_args,
            enabled=body.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=409, detail="rule could not be created") from exc
    return _rule_response(rule)


@router.get("/rules")
async def list_rules(auth: CurrentAuth) -> dict[str, Any]:
    rules = await get_automation_service().list_rules(_user_id(auth))
    return {"rules": [_rule_response(rule) for rule in rules]}


@router.patch("/rules/{rule_id}")
async def set_rule_state(
    rule_id: str,
    body: RuleStateRequest,
    auth: CurrentAuth,
) -> dict[str, Any]:
    rule = await get_automation_service().set_enabled(
        _user_id(auth),
        rule_id,
        enabled=body.enabled,
    )
    if rule is None:
        raise HTTPException(status_code=404, detail="rule not found")
    return _rule_response(rule)


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, auth: CurrentAuth) -> dict[str, bool]:
    removed = await get_automation_service().delete_rule(_user_id(auth), rule_id)
    if not removed:
        raise HTTPException(status_code=404, detail="rule not found")
    return {"deleted": True}


@router.post("/evaluate")
async def evaluate_rules(
    body: EvaluateRulesRequest,
    auth: CurrentAuth,
) -> dict[str, Any]:
    if body.event_type not in AUTOMATION_TRIGGER_EVENTS:
        raise HTTPException(status_code=422, detail="event type is not allowed")
    executions = await get_automation_service().evaluate_rules(
        _user_id(auth),
        body.event_type,
        body.payload,
    )
    return {
        "executions": [
            {
                "rule_id": item.rule_id,
                "tool_name": item.tool_name,
                "output": item.output,
            }
            for item in executions
        ]
    }
