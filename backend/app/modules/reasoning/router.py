"""Rotas autenticadas do Reasoning."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.interfaces.deps import CurrentAuth
from app.modules.reasoning.application import get_reasoning_service

router = APIRouter(prefix="/reasoning", tags=["reasoning"])


class ResolveIntentRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    context: dict[str, Any] | None = None


@router.post("/resolve")
async def resolve_intent(
    body: ResolveIntentRequest,
    auth: CurrentAuth,
) -> dict[str, Any]:
    user_id = auth.effective_user_id
    if not user_id:
        raise HTTPException(status_code=403, detail="user identity required")
    result = await get_reasoning_service().resolve_intent(
        body.text,
        user_id=user_id,
        context=body.context,
    )
    return {
        "intent": result.intent,
        "confidence": result.confidence,
        "entities": result.entities,
        "requires_plan": result.requires_plan,
        "suggested_tool": result.suggested_tool,
        "explicit_action": result.explicit_action,
    }
