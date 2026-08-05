"""Interface HTTP do módulo brain — status do router e completions de debug."""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.modules.brain.application import get_brain_service
from app.modules.brain.domain import ChatMessage, TaskType
from app.modules.brain.infrastructure import get_model_router
from app.modules.configuration.settings import get_settings
from app.modules.security.domain import AuthResult
from app.modules.security.router import require_api_key

logger = structlog.get_logger("negao.brain")
router = APIRouter(prefix="/brain", tags=["brain"])


class CompleteRequest(BaseModel):
    """Pedido de completion (formato OpenAI-compatível)."""

    messages: list[dict[str, str]] = Field(min_length=1)
    task_type: str | None = None


class DebugRequest(BaseModel):
    """Texto simples para teste rápido do pipeline."""

    text: str = Field(min_length=1, max_length=2000)


def _parse_messages(raw: list[dict[str, str]]) -> list[ChatMessage]:
    messages: list[ChatMessage] = []
    for item in raw:
        role = item.get("role", "user")
        content = item.get("content", "")
        messages.append(ChatMessage(role=role, content=content))
    return messages


@router.get("/status")
async def brain_status() -> dict[str, object]:
    settings = get_settings()
    return {
        "mode": "nvidia" if settings.nvidia_api_key else "local",
        "primary_model": settings.brain_chat_model,
        "fallback_model": settings.brain_fallback_model,
        "cache_ttl_seconds": settings.brain_cache_ttl_seconds,
        "retry_attempts": settings.brain_retry_attempts,
        "circuit_failures": settings.brain_circuit_failures,
    }


@router.post("/complete")
async def brain_complete(
    body: CompleteRequest,
    auth: Annotated[AuthResult, Depends(require_api_key)],
) -> dict[str, object]:
    try:
        messages = _parse_messages(body.messages)
        task_type = TaskType(body.task_type) if body.task_type else TaskType.CHAT
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        response = await get_brain_service().complete(
            messages,
            task_type=task_type,
            session_id="debug",
            user_id=auth.principal,
        )
    except Exception as exc:
        logger.exception("brain_complete_failed", error=str(exc))
        raise HTTPException(
            status_code=502, detail="Falha ao processar no modelo de linguagem"
        ) from exc
    return {
        "text": response.text,
        "model": response.model,
        "latency_ms": response.latency_ms,
        "cached": response.cached,
        "fallback_used": response.fallback_used,
    }


@router.post("/debug")
async def brain_debug(
    body: DebugRequest,
    auth: Annotated[AuthResult, Depends(require_api_key)],
) -> dict[str, object]:
    return await get_brain_service().process_input(
        body.text, session_id="debug", user_id=auth.principal
    )


@router.get("/router")
async def brain_router_status() -> dict[str, object]:
    """Estado interno do ModelRouter (para observabilidade)."""
    settings = get_settings()
    return {
        "mode": "nvidia" if settings.nvidia_api_key else "local",
        "primary_model": settings.brain_chat_model,
        "fallback_model": settings.brain_fallback_model,
        "instance_router": get_model_router() is not None,
    }
