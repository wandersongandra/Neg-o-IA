"""Rotas HTTP do módulo memory — status do Redis e inspeção de sessão."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException

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
    """Verifica conectividade com o Redis (memória de curto prazo)."""
    connected = False
    try:
        from app.infrastructure.redis import get_redis

        await get_redis().ping()
        connected = True
    except Exception:
        connected = False
    return {"redis_connected": connected}


@router.get("/session/{session_id}")
async def memory_session(session_id: str) -> dict[str, Any]:
    """Lista as entradas STM da sessão — apenas em ambiente debug."""
    if not _is_debug():
        raise HTTPException(
            status_code=403, detail="inspeção de memória disponível apenas em debug"
        )
    service = get_memory_service()
    entries = await service.recall_session(session_id)
    return {"session_id": session_id, "entries": entries}
