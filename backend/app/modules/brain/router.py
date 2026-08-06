"""Interface HTTP do módulo brain — status do router, completions e config do agente."""

from __future__ import annotations

import json
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.infrastructure.redis import get_redis
from app.modules.brain.application import get_brain_service
from app.modules.brain.domain import ChatMessage, TaskType
from app.modules.brain.infrastructure import get_model_router
from app.modules.configuration.settings import get_settings
from app.modules.security.domain import AuthResult
from app.modules.security.router import require_api_key

logger = structlog.get_logger("negao.brain")
router = APIRouter(prefix="/brain", tags=["brain"])

CONFIG_KEY = "agent:config"

DEFAULT_CONFIG = {
    "system_prompt": (
        "Você é o NEGÃO, assistente pessoal de inteligência artificial do Wanderson. "
        "Fala sempre em português brasileiro, com tom profissional, elegante e direto, "
        "inspirado no JARVIS: nunca invente fatos, admita quando não souber, e use humor "
        "sutil quando apropriado. Trate o usuário como 'chefe'. Seja conciso: prefira "
        "respostas curtas e úteis, em vez de longas explicações. Nunca repita o que o "
        "usuário acabou de dizer."
    ),
    "primary_model": "nvidia/gpt-oss-120b",
    "fallback_model": "nvidia/llama-3.1-8b-instruct",
    "temperature": 0.3,
    "max_tokens": 1024,
    "tools_enabled": ["web_search", "code_exec", "file_ops", "memory", "calendar"],
    "voice": {
        "tts_enabled": True,
        "stt_enabled": True,
        "voice": "pt-BR-FranciscaNeural",
        "rate": "+0%",
    },
}

async def _load_config() -> dict[str, Any]:
    client = get_redis()
    raw = await client.get(CONFIG_KEY)
    if raw:
        return dict(json.loads(raw))
    return DEFAULT_CONFIG.copy()

async def _save_config(config: dict[str, Any]) -> None:
    client = get_redis()
    await client.set(CONFIG_KEY, json.dumps(config), ex=86400 * 30)

class CompleteRequest(BaseModel):
    """Pedido de completion (formato OpenAI-compatível)."""

    messages: list[dict[str, str]] = Field(min_length=1)
    task_type: str | None = None


class DebugRequest(BaseModel):
    """Texto simples para teste rápido do pipeline."""

    text: str = Field(min_length=1, max_length=2000)


class AgentConfigUpdate(BaseModel):
    """Atualização parcial da configuração do agente."""

    system_prompt: str | None = Field(default=None, min_length=10, max_length=8000)
    primary_model: str | None = Field(default=None, min_length=1)
    fallback_model: str | None = Field(default=None, min_length=1)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=8192)
    tools_enabled: list[str] | None = None
    voice: dict[str, Any] | None = None


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


@router.get("/config")
async def get_agent_config(
    auth: Annotated[AuthResult, Depends(require_api_key)],
) -> dict[str, Any]:
    """Configuração atual do agente NEGÃO."""
    config = await _load_config()
    # Merge com settings atuais para modelos
    settings = get_settings()
    config["primary_model"] = settings.brain_chat_model
    config["fallback_model"] = settings.brain_fallback_model
    return config


@router.patch("/config")
async def update_agent_config(
    body: AgentConfigUpdate,
    auth: Annotated[AuthResult, Depends(require_api_key)],
) -> dict[str, Any]:
    """Atualiza configuração do agente (merge parcial)."""
    config = await _load_config()
    update = body.model_dump(exclude_unset=True)
    # Deep merge para voice
    if "voice" in update and isinstance(update["voice"], dict):
        config["voice"] = {**config.get("voice", {}), **update["voice"]}
        del update["voice"]
    config.update(update)
    await _save_config(config)
    return {"updated": True, "config": config}
