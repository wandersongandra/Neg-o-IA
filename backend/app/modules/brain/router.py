"""Interface HTTP do módulo brain — status do router, completions e config do agente."""

from __future__ import annotations

from typing import Annotated, Any, Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.modules.brain.application import get_brain_service
from app.modules.brain.domain import ChatMessage, TaskType
from app.modules.brain.infrastructure import get_model_router
from app.modules.brain.user_config import (
    UserBrainConfig,
    load_user_config,
    save_user_config,
)
from app.modules.configuration.settings import get_settings
from app.modules.security.domain import AuthResult
from app.modules.security.router import require_authenticated_user

logger = structlog.get_logger("negao.brain")
router = APIRouter(prefix="/brain", tags=["brain"])

class BrainMessageRequest(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class CompleteRequest(BaseModel):
    """Pedido de completion autenticado e limitado."""

    messages: list[BrainMessageRequest] = Field(min_length=1, max_length=20)
    task_type: str | None = None


class DebugRequest(BaseModel):
    """Texto simples para teste rápido do pipeline."""

    text: str = Field(min_length=1, max_length=2000)


class AgentConfigUpdate(BaseModel):
    """Atualização parcial da configuração do agente."""

    system_prompt: str = Field(min_length=10, max_length=8000)
    temperature: float = Field(ge=0.0, le=2.0)
    max_tokens: int = Field(ge=1, le=8192)


def _parse_messages(raw: list[BrainMessageRequest]) -> list[ChatMessage]:
    return [ChatMessage(role=item.role, content=item.content) for item in raw]


@router.get("/status")
async def brain_status() -> dict[str, object]:
    settings = get_settings()
    return {
        "mode": "nvidia" if settings.external_ai_enabled and settings.nvidia_api_key else "local",
        "primary_model": settings.brain_chat_model,
        "fallback_model": settings.brain_fallback_model,
        "cache_ttl_seconds": settings.brain_cache_ttl_seconds,
        "retry_attempts": settings.brain_retry_attempts,
        "circuit_failures": settings.brain_circuit_failures,
    }


@router.post("/complete")
async def brain_complete(
    body: CompleteRequest,
    auth: Annotated[AuthResult, Depends(require_authenticated_user)],
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
            user_id=auth.effective_user_id,
        )
    except Exception as exc:
        logger.exception("brain_complete_failed")
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
    auth: Annotated[AuthResult, Depends(require_authenticated_user)],
) -> dict[str, object]:
    return await get_brain_service().process_input(
        body.text, session_id="debug", user_id=auth.effective_user_id
    )


@router.get("/router")
async def brain_router_status() -> dict[str, object]:
    """Estado interno do ModelRouter (para observabilidade)."""
    settings = get_settings()
    return {
        "mode": "nvidia" if settings.external_ai_enabled and settings.nvidia_api_key else "local",
        "primary_model": settings.brain_chat_model,
        "fallback_model": settings.brain_fallback_model,
        "instance_router": get_model_router() is not None,
    }


def _config_response(config: UserBrainConfig) -> dict[str, Any]:
    settings = get_settings()
    return {
        "system_prompt": config.system_prompt,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "primary_model": settings.brain_chat_model,
        "fallback_model": settings.brain_fallback_model,
        "tools_enabled": [],
        "voice": {
            "tts_enabled": settings.external_ai_enabled,
            "stt_enabled": settings.external_ai_enabled and bool(settings.nvidia_api_key),
            "voice": settings.tts_voice,
            "rate": settings.tts_rate,
            "managed_by_environment": True,
        },
    }


@router.get("/config")
async def get_agent_config(
    auth: Annotated[AuthResult, Depends(require_authenticated_user)],
) -> dict[str, Any]:
    """Configuração efetiva do usuário, sem expor segredos."""
    if not auth.effective_user_id:
        raise HTTPException(status_code=403, detail="user identity required")
    config = await load_user_config(auth.effective_user_id)
    return _config_response(config)


@router.patch("/config")
async def update_agent_config(
    body: AgentConfigUpdate,
    auth: Annotated[AuthResult, Depends(require_authenticated_user)],
) -> dict[str, Any]:
    """Atualiza apenas preferências que o runtime realmente consome."""
    if not auth.effective_user_id:
        raise HTTPException(status_code=403, detail="user identity required")
    config = UserBrainConfig(
        system_prompt=body.system_prompt,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )
    try:
        await save_user_config(auth.effective_user_id, config)
    except Exception as exc:
        logger.exception("brain_user_config_save_failed")
        raise HTTPException(status_code=503, detail="configuration storage unavailable") from exc
    return {"updated": True, "config": _config_response(config)}
