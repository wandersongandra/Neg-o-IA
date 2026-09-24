"""Rotas HTTP do módulo memory."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.interfaces.deps import CurrentAuth
from app.modules.conversation.application import get_conversation_service
from app.modules.conversation.infrastructure import ConversationPersistenceError
from app.modules.memory.application import get_memory_service
from app.modules.memory.application.long_term import get_long_term_memory_service

router = APIRouter(prefix="/memory", tags=["memory"])


class RememberRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    session_id: str | None = Field(default=None, max_length=128)
    importance: float = Field(default=0.5, ge=0, le=1)
    retention_days: int | None = Field(default=None, ge=1, le=3650)


class MemoryPolicyRequest(BaseModel):
    auto_capture_enabled: bool
    retention_days: int = Field(ge=1, le=3650)


def _user_id(auth: CurrentAuth) -> str:
    user_id = auth.effective_user_id
    if not user_id:
        raise HTTPException(status_code=403, detail="user identity required")
    return user_id


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
    return {"redis_connected": connected, "long_term": "postgresql+pgvector"}


@router.get("/session/{session_id}")
async def memory_session(session_id: str, auth: CurrentAuth) -> dict[str, Any]:
    if not _is_debug():
        raise HTTPException(
            status_code=403,
            detail="inspeção de memória disponível apenas em debug",
        )
    user_id = _user_id(auth)
    try:
        owns_session = await get_conversation_service().owns_session(session_id, user_id)
    except ConversationPersistenceError as exc:
        raise HTTPException(status_code=503, detail="conversation storage unavailable") from exc
    if not owns_session:
        raise HTTPException(status_code=404, detail="session not found")
    entries = await get_memory_service().recall_session(user_id, session_id)
    return {"session_id": session_id, "entries": entries}


@router.get("/long-term")
async def list_long_term_memory(
    auth: CurrentAuth,
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    entries = await get_long_term_memory_service().list_recent(_user_id(auth), limit=limit)
    return {
        "memories": [
            {
                "id": entry.id,
                "content": entry.content,
                "source": entry.source,
                "importance": entry.importance,
                "created_at": entry.created_at.isoformat(),
                "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
            }
            for entry in entries
        ]
    }


@router.post("/long-term")
async def remember(body: RememberRequest, auth: CurrentAuth) -> dict[str, Any]:
    user_id = _user_id(auth)
    if body.session_id is not None:
        try:
            owns_session = await get_conversation_service().owns_session(body.session_id, user_id)
        except ConversationPersistenceError as exc:
            raise HTTPException(status_code=503, detail="conversation storage unavailable") from exc
        if not owns_session:
            raise HTTPException(status_code=404, detail="session not found")
    try:
        entry = await get_long_term_memory_service().remember(
            user_id,
            body.content,
            session_id=body.session_id,
            importance=body.importance,
            retention_days=body.retention_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "id": entry.id,
        "source": entry.source,
        "content": entry.content,
        "importance": entry.importance,
        "created_at": entry.created_at.isoformat(),
        "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
    }


@router.get("/search")
async def search_memory(
    auth: CurrentAuth,
    q: str = Query(min_length=1, max_length=1000),
    limit: int = Query(default=5, ge=1, le=10),
) -> dict[str, Any]:
    hits = await get_long_term_memory_service().search(_user_id(auth), q, limit=limit)
    return {
        "hits": [
            {
                "id": hit.entry.id,
                "content": hit.entry.content,
                "source": hit.entry.source,
                "importance": hit.entry.importance,
                "score": hit.score,
                "created_at": hit.entry.created_at.isoformat(),
            }
            for hit in hits
        ]
    }


@router.delete("/long-term/{memory_id}")
async def delete_memory(memory_id: str, auth: CurrentAuth) -> dict[str, bool]:
    removed = await get_long_term_memory_service().delete(_user_id(auth), memory_id)
    if not removed:
        raise HTTPException(status_code=404, detail="memory not found")
    return {"deleted": True}


@router.get("/policy")
async def get_memory_policy(auth: CurrentAuth) -> dict[str, Any]:
    policy = await get_long_term_memory_service().get_policy(_user_id(auth))
    return {
        "auto_capture_enabled": policy.auto_capture_enabled,
        "retention_days": policy.retention_days,
    }


@router.patch("/policy")
async def update_memory_policy(
    body: MemoryPolicyRequest,
    auth: CurrentAuth,
) -> dict[str, Any]:
    policy = await get_long_term_memory_service().update_policy(
        _user_id(auth),
        auto_capture_enabled=body.auto_capture_enabled,
        retention_days=body.retention_days,
    )
    return {
        "auto_capture_enabled": policy.auto_capture_enabled,
        "retention_days": policy.retention_days,
    }
