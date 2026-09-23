"""Rotas HTTP do módulo memory — status e inspeção segura de sessão."""

from __future__ import annotations

import os
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.interfaces.deps import CurrentAuth
from app.modules.conversation.application import get_conversation_service
from app.modules.conversation.infrastructure import ConversationPersistenceError
from app.modules.memory.application import get_memory_service
from app.modules.memory.domain import LongTermMemoryEntry
from app.modules.memory.infrastructure.long_term import LongTermMemoryPersistenceError

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


class LongTermMemoryCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    kind: Literal["note", "preference", "fact", "instruction"] = "note"
    importance: int = Field(default=3, ge=1, le=5)
    source_session_id: str | None = Field(default=None, min_length=1, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)


def _memory_payload(entry: LongTermMemoryEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "content": entry.content,
        "kind": entry.kind,
        "importance": entry.importance,
        "source_session_id": entry.source_session_id,
        "metadata": entry.metadata,
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
        "last_accessed_at": (
            entry.last_accessed_at.isoformat() if entry.last_accessed_at is not None else None
        ),
        "expires_at": entry.expires_at.isoformat() if entry.expires_at is not None else None,
        "score": entry.score,
    }


async def _require_user_id(auth: CurrentAuth) -> str:
    user_id = auth.effective_user_id
    if not user_id:
        raise HTTPException(status_code=403, detail="user identity required")
    return user_id


async def _validate_owned_source_session(user_id: str, session_id: str | None) -> None:
    if session_id is None:
        return
    try:
        owns_session = await get_conversation_service().owns_session(session_id, user_id)
    except ConversationPersistenceError as exc:
        raise HTTPException(status_code=503, detail="conversation storage unavailable") from exc
    if not owns_session:
        raise HTTPException(status_code=404, detail="session not found")


@router.post("/items", status_code=201)
async def create_memory_item(
    body: LongTermMemoryCreateRequest,
    auth: CurrentAuth,
) -> dict[str, Any]:
    user_id = await _require_user_id(auth)
    await _validate_owned_source_session(user_id, body.source_session_id)
    try:
        entry = await get_memory_service().remember_long_term(
            user_id,
            body.content,
            kind=body.kind,
            importance=body.importance,
            source_session_id=body.source_session_id,
            metadata=body.metadata,
            expires_in_days=body.expires_in_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LongTermMemoryPersistenceError as exc:
        raise HTTPException(status_code=503, detail="memory storage unavailable") from exc
    return _memory_payload(entry)


@router.get("/items")
async def list_memory_items(
    auth: CurrentAuth,
    q: str = Query(default="", max_length=1000),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10000),
) -> dict[str, Any]:
    user_id = await _require_user_id(auth)
    try:
        if q.strip():
            entries = await get_memory_service().recall_long_term(
                user_id,
                q,
                limit=min(limit, 20),
            )
        else:
            entries = await get_memory_service().list_long_term(
                user_id,
                limit=limit,
                offset=offset,
            )
    except LongTermMemoryPersistenceError as exc:
        raise HTTPException(status_code=503, detail="memory storage unavailable") from exc
    return {"items": [_memory_payload(entry) for entry in entries]}


@router.delete("/items/{memory_id}", status_code=204, response_model=None)
async def delete_memory_item(memory_id: str, auth: CurrentAuth) -> None:
    user_id = await _require_user_id(auth)
    try:
        removed = await get_memory_service().forget_long_term(user_id, memory_id)
    except LongTermMemoryPersistenceError as exc:
        raise HTTPException(status_code=503, detail="memory storage unavailable") from exc
    if not removed:
        raise HTTPException(status_code=404, detail="memory not found")
