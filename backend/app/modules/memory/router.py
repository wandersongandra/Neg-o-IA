"""Rotas HTTP do módulo memory — status e inspeção segura de sessão."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException

from app.interfaces.deps import CurrentAuth
from app.modules.conversation.application import get_conversation_service
from app.modules.conversation.infrastructure import ConversationPersistenceError
from app.modules.memory.application import get_memory_service

router = APIRouter(prefix="/memory", tags=["memory"])


def _is_debug() -> bool:
    try:
        from app.modules.configuration.settings import get_settings

        return bool(getattr(get_settings(), "debug", False))
    except Exception:
        return os.getenv("NEGAO_DEBUG", "").lower() in {"1", "true", "yes"}


@router.get("/status")
async def memory_status() -> dict[str, Any]:
    connected = False
    try:
        from app.infrastructure.redis import get_redis

        await get_redis().ping()
        connected = True
    except Exception:
        connected = False
    return {"redis_connected": connected}


@router.get("/session/{session_id}")
async def memory_session(session_id: str, auth: CurrentAuth) -> dict[str, Any]:
    """Inspeção de STM em debug, limitada à própria sessão do usuário."""
    if not _is_debug():
        raise HTTPException(
            status_code=403, detail="inspeção de memória disponível apenas em debug"
        )
    user_id = auth.effective_user_id
    if not user_id:
        raise HTTPException(status_code=403, detail="user identity required")
    try:
        owns_session = await get_conversation_service().owns_session(session_id, user_id)
    except ConversationPersistenceError as exc:
        raise HTTPException(status_code=503, detail="conversation storage unavailable") from exc
    if not owns_session:
        raise HTTPException(status_code=404, detail="session not found")
    entries = await get_memory_service().recall_session(user_id, session_id)
    return {"session_id": session_id, "entries": entries}
